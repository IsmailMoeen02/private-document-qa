"""Scores the question answering against hand-written answers.  python eval/run_eval.py dev|heldout [--show]
Per question: an answerable one is right when the answer contains the expected fact AND the first citation is the right document. An unanswerable or restricted one is right when it is refused.
Also counted: restricted documents that leaked (cited or quoted to someone who may not read them), and answers whose quote is not in the cited passage."""
import json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "data"))
from app import answer as A, ingest
from app.search import Index
from corpus import DOCS, USERS
GLOSS = json.loads((ROOT / "data" / "glossary.json").read_text()) if (ROOT / "data" / "glossary.json").exists() else {}
def build():
    chunks = []; n = 0
    for d in DOCS:
        r = ingest.read_document(f"{d['id']}.{d['format']}", (ROOT / "data" / "docs" / f"{d['id']}.{d['format']}").read_bytes())
        for h, pg, t in r["chunks"]: n += 1; chunks.append({"id": n, "doc": d["id"], "title": d["title"], "heading": h, "page": pg, "text": t, "groups": d["groups"]})
    return chunks
def groups_of(user): return {"everyone", *(next((g for u, _, g in USERS if u == user), []))}
def run(name, show=False):
    qa = json.loads((ROOT / "data" / f"{name}_qa.json").read_text()); chunks = build(); cache = {}; rows = []; t0 = time.time(); leaks = 0
    for q in qa:
        g = frozenset(groups_of(q["user"]))
        if g not in cache: cache[g] = Index([c for c in chunks if set(c["groups"]) & g], GLOSS)
        r = A.answer(cache[g], q["q"]); cited = [c["doc"] for c in r["citations"]]
        allowed = {c["doc"] for c in chunks if set(c["groups"]) & g}; leaks += sum(d not in allowed for d in cited)
        if q["kind"] == "answer": ok = r["outcome"] == "answered" and all(s.lower() in r["answer"].lower() for s in q["contains"]) and bool(cited) and cited[0] == q["doc"]
        else: ok = r["outcome"] == "refused"
        quote_ok = all(any(x in c["passage"] for x in c["quotes"]) for c in r["citations"] if c["quotes"])
        rows.append((q, r, ok, quote_ok))
    ans = [x for x in rows if x[0]["kind"] == "answer"]; ref = [x for x in rows if x[0]["kind"] == "refuse"]; rstr = [x for x in ref if "restricted" in x[0].get("why", "")]
    hit1 = sum(1 for q, r, *_ in ans if r["citations"] and r["citations"][0]["doc"] == q["doc"]); wrong_answer = sum(1 for q, r, ok, _ in ans if r["outcome"] == "answered" and not ok)
    print(f"\n== {name}: {len(qa)} questions in {time.time() - t0:.1f}s")
    print(f"  answerable: {sum(x[2] for x in ans)}/{len(ans)} right  (right document first: {hit1}/{len(ans)}; confident but wrong: {wrong_answer}; refused wrongly: {sum(1 for q, r, ok, _ in ans if r['outcome'] == 'refused')})")
    print(f"  not in the documents: {sum(x[2] for x in ref if x not in rstr)}/{len(ref) - len(rstr)} correctly refused")
    print(f"  restricted to another group: {sum(x[2] for x in rstr)}/{len(rstr)} correctly refused;  restricted documents leaked: {leaks}")
    print(f"  every shown quote is in its passage: {all(x[3] for x in rows)}")
    json.dump({"name": name, "n": len(qa), "answer_right": sum(x[2] for x in ans), "answer_n": len(ans), "hit1": hit1, "wrong_answer": wrong_answer, "refuse_right": sum(x[2] for x in ref if x not in rstr), "refuse_n": len(ref) - len(rstr),
               "restricted_right": sum(x[2] for x in rstr), "restricted_n": len(rstr), "leaks": leaks, "rows": [[q["q"], q["user"], q["kind"], r["outcome"], ok] for q, r, ok, _ in rows]}, open(ROOT / "eval" / f"result_{name}.json", "w"), indent=1)
    if show:
        for q, r, ok, _ in rows:
            if not ok: print(f"\n  MISS [{q['user']}] {q['q']}\n     want: {q.get('contains') or 'refusal'} / {q.get('doc')}\n     got : {r['outcome']} {r['answer'][:110]!r} | {[c['doc'] + ':' + c['heading'] for c in r['citations']][:2]} score {r['score']}")
if __name__ == "__main__": run(sys.argv[1] if len(sys.argv) > 1 else "dev", "--show" in sys.argv)

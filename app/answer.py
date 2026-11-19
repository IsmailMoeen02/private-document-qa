"""Turns the best passages into an answer that is a quote from the documents, or says it could not find one.
The answer is never composed: it is the sentence (or two) from the passages that best match the question. An optional local model may phrase it, but only if it quotes the passages."""
from __future__ import annotations
import json, re
from . import config, ingest
from .search import Index, tokens

REFUSAL = "I could not find this in the documents you have access to."
WHEN = re.compile(r"^(when|by when|how soon|how quickly)\b", re.I); TIMEWORD = re.compile(r"\b(before|by|within|after|until|at \d|from|on the|each|every)\b", re.I)
NUMERIC = re.compile(r"^(how (many|much|long|soon|often|far|old)|what (is|are) the (limit|rate|range|cap|budget|maximum|minimum)|when|by when|within)", re.I)

def best_sentences(idx: Index, question: str, hits: list[dict]):
    q = tokens(question); w = idx.expand(q); mass = sum(idx.idf(t) * wt for t, wt in w.items()) or 1.0; wants_number = bool(NUMERIC.search(question.strip()))
    cand = []
    for rank, h in enumerate(hits[:config.TOP_K]):
        c = h["chunk"]; head = set(tokens(c["heading"]))
        for s in ingest.sentences(c["text"]):
            st = set(tokens(s)); sc = sum(idx.idf(t) * wt for t, wt in w.items() if t in st) / mass
            sc += .25 * sum(idx.idf(t) * wt for t, wt in w.items() if t in head) / mass                      # the section heading names the topic
            if wants_number and re.search(r"\d", s): sc += .15
            if WHEN.search(question.strip()) and TIMEWORD.search(s): sc += .12                                     # a "when" question is answered by a sentence with a time rule
            sc += .1 * h["fused"] - .02 * rank
            cand.append((sc, rank, c, s))
    cand.sort(key=lambda x: -x[0]); return cand

def extractive(idx: Index, question: str, hits: list[dict]):
    cand = best_sentences(idx, question, hits)
    if not cand: return None
    top = cand[0]; picked = [top]
    for sc, rank, c, s in cand[1:]:
        if c["id"] == top[2]["id"] and sc >= .8 * top[0] and s != top[3]: picked.append((sc, rank, c, s)); break
    nums = {t for t in tokens(question) if t[0].isdigit()}
    if nums and not any(nums & set(tokens(p[3])) for p in picked):                  # the question has a figure the text does not (7 hours vs a rule about 6): show the neighbouring rule too
        extra = next(((sc, rank, c, s) for sc, rank, c, s in cand[1:] if c["id"] == top[2]["id"] and s != top[3]), None)
        if extra and extra not in picked: picked.append(extra)
    picked.sort(key=lambda x: x[2]["text"].find(x[3])); return {"text": " ".join(p[3] for p in picked), "quotes": [p[3] for p in picked], "chunk": top[2]}

def llm_answer(question: str, hits: list[dict], call=None):
    """Optional: a local model writes the answer from the passages. It must return the sentences it used, and each must appear in the passages, otherwise it is dropped."""
    passages = "\n\n".join(f"[{i + 1}] {h['chunk']['text']}" for i, h in enumerate(hits[:config.TOP_K]))
    prompt = ("Answer the question using ONLY the passages. Reply as JSON: {\"answer\": short answer, \"quotes\": [the exact sentences from the passages that support it]}. "
              "If the passages do not answer it, reply {\"answer\": null, \"quotes\": []}.\n\nQuestion: " + question + "\n\nPassages:\n" + passages)
    raw = (call or _ollama)(prompt)
    try: data = json.loads(raw)
    except Exception: return None
    ans, qs = data.get("answer"), data.get("quotes")
    if not isinstance(ans, str) or not ans.strip() or not isinstance(qs, list) or not qs: return None
    norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower()); blob = norm(" ".join(h["chunk"]["text"] for h in hits[:config.TOP_K]))
    if not all(isinstance(x, str) and x.strip() and norm(x) in blob for x in qs): return None
    chunk = next((h["chunk"] for h in hits if norm(qs[0]) in norm(h["chunk"]["text"])), hits[0]["chunk"])
    return {"text": ans.strip()[:600], "quotes": [x.strip() for x in qs], "chunk": chunk, "model": True}
def _ollama(prompt):
    import httpx
    r = httpx.post(config.OLLAMA_URL + "/api/chat", timeout=60, json={"model": config.OLLAMA_MODEL, "stream": False, "format": "json", "options": {"temperature": 0}, "messages": [{"role": "user", "content": prompt}]})
    r.raise_for_status(); return r.json()["message"]["content"]

def answer(idx: Index, question: str, llm=None) -> dict:
    """Returns {outcome, answer, citations, score}. Refuses when the best passage does not really cover the question."""
    hits = idx.search(question, config.TOP_K) if idx else []
    if not hits: return {"outcome": "refused", "answer": REFUSAL, "citations": [], "score": 0.0}
    top = hits[0]; score = top["confidence"]
    if score < config.MIN_SCORE or top["coverage"] < config.MIN_COVERAGE: return {"outcome": "refused", "answer": REFUSAL, "citations": [], "score": round(score, 2)}
    res = None
    if llm is not None:
        try: res = llm_answer(question, hits, llm if callable(llm) else None)
        except Exception: res = None
    res = res or extractive(idx, question, hits)
    if not res: return {"outcome": "refused", "answer": REFUSAL, "citations": [], "score": round(score, 2)}
    cites = []
    for h in hits[:3]:
        c = h["chunk"]; hit = c["id"] == res["chunk"]["id"]
        cites.append({"chunk": c["id"], "doc": c["doc"], "title": c["title"], "heading": c["heading"], "page": c["page"], "passage": c["text"], "quotes": [q for q in res["quotes"] if q in c["text"]] if hit else [], "match": round(h["confidence"], 2)})
    cites.sort(key=lambda c: not c["quotes"])
    return {"outcome": "answered", "answer": res["text"], "citations": cites, "score": round(score, 2), "model": bool(res.get("model"))}

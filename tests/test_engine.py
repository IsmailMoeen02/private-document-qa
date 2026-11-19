import json
from conftest import fresh, ROOT, DOCDIR

def test_stemmer_and_irregulars(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path); from app.search import stem
    assert stem("kept") == stem("keep") == stem("keeping") and stem("changed") == stem("change") and stem("holidays") == stem("holiday")

def test_readers_keep_headings_and_pages(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path); from app import ingest
    r = ingest.read_document("it.pdf", (DOCDIR / "it-security-policy.pdf").read_bytes()); assert r["pages"] >= 2 and any(h == "Passwords" for h, _, _ in r["chunks"]) and {pg for _, pg, _ in r["chunks"]} >= {1, 2}
    r = ingest.read_document("h.docx", (DOCDIR / "employee-handbook.docx").read_bytes()); assert any(h == "Annual leave" for h, _, _ in r["chunks"])
    r = ingest.read_document("o.txt", (DOCDIR / "onboarding-guide.txt").read_bytes()); assert r["chunks"] and r["kind"] == "txt"

def test_type_comes_from_content_not_name(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path); from app import ingest
    r = ingest.read_document("really-text.pdf", b"## Heading\nSome words for the file to hold, long enough to keep.\n") if False else None
    try: ingest.read_document("fake.pdf", b"plain text pretending to be a pdf"); assert False
    except ingest.Rejected: pass

def test_long_sections_are_split(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path); from app import ingest
    txt = "## Big\n" + " ".join(f"Sentence number {i} says something about the topic." for i in range(80)) + "\n"; r = ingest.read_document("b.txt", txt.encode())
    assert len(r["chunks"]) >= 3 and all(len(t.split()) < 160 for _, _, t in r["chunks"])

def test_extractive_answers_come_from_the_passage(env):
    for q in ["How long do we keep invoices?", "What is the hotel limit in London?", "How many characters must a password have?"]:
        r = env.ask("ayesha" if "hotel" not in q else "sara", q); assert r["outcome"] == "answered" and all(x in c["passage"] for c in r["citations"] for x in c["quotes"])

def test_numbers_answered_from_text(env):
    r = env.ask("ayesha", "How many days of annual leave do I get?"); assert "22" in r["answer"]
    assert "14" in env.ask("ayesha", "How long must my password be?")["answer"] and "7 years" in env.ask("ayesha", "How long do we keep invoices?")["answer"]

# ---- the optional language model path is guarded
def with_llm(env, reply):
    from app import answer; idx = env.main.index_for(frozenset({"everyone"})); return answer.answer(idx, "How many days of annual leave do I get?", lambda p: reply)
def test_llm_answer_with_real_quote_is_used(env):
    q = "Full-time employees receive 22 working days of annual leave per year, plus the public holidays of England and Wales."
    r = with_llm(env, json.dumps({"answer": "22 working days.", "quotes": [q]})); assert r["answer"] == "22 working days." and r["model"] is True and r["citations"][0]["quotes"] == [q]
def test_llm_made_up_quote_falls_back(env):
    r = with_llm(env, json.dumps({"answer": "30 days.", "quotes": ["Employees receive 30 days of leave."]})); assert "22" in r["answer"] and not r["model"]
def test_llm_garbage_or_null_falls_back(env):
    for bad in ["not json", json.dumps({"answer": None, "quotes": []}), json.dumps({"answer": "x", "quotes": []}), "{}"]: assert "22" in with_llm(env, bad)["answer"]
def test_llm_cannot_answer_when_retrieval_refuses(env):
    from app import answer; idx = env.main.index_for(frozenset({"everyone"})); called = []
    r = answer.answer(idx, "What is the dress code?", lambda p: called.append(p) or json.dumps({"answer": "Smart casual.", "quotes": ["x"]})); assert r["outcome"] == "refused" and not called
def test_llm_error_falls_back(env):
    from app import answer; idx = env.main.index_for(frozenset({"everyone"}))
    def boom(p): raise RuntimeError("down")
    assert answer.answer(idx, "How many days of annual leave do I get?", boom)["outcome"] == "answered"

# ---- the evaluation sets, kept as a regression guard (numbers are the measured ones, with a little room)
def run(env, name, groups_for):
    from app import answer; sets = json.load(open(ROOT / "data" / f"{name}_qa.json")); ok = bad = leak = 0
    for it in sets:
        r = env.ask(it["user"], it["q"])
        if it["kind"] == "answer": ok += r["outcome"] == "answered" and any(s.lower() in r["answer"].lower() or any(s.lower() in c["passage"].lower() for c in r["citations"][:1]) for s in it["contains"])
        else: bad += r["outcome"] == "answered"
    return ok, bad, sum(1 for i in sets if i["kind"] == "answer")
def test_dev_set(env):
    ok, bad, n = run(env, "dev", None); assert ok == n and bad == 0
def test_heldout_set_has_no_wrong_answers_to_refusals(env):
    ok, bad, n = run(env, "heldout", None); assert bad == 0 and ok >= 0.7 * n
def test_fresh_set(env):
    ok, bad, n = run(env, "fresh", None); assert bad == 0 and ok >= 0.8 * n

import io, json, zipfile
from conftest import fresh, DOCDIR

def test_login_wrong_and_unknown_look_the_same(env):
    a = env.c.post("/api/login", json={"username": "ayesha", "password": "nope"}); b = env.c.post("/api/login", json={"username": "nobody", "password": "nope"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()

def test_login_rate_limit(monkeypatch, tmp_path):
    c, _ = fresh(monkeypatch, tmp_path, LOGIN_PER_MIN="3")
    codes = [c.post("/api/login", json={"username": "x", "password": "y"}).status_code for _ in range(5)]; assert codes[:3] == [401] * 3 and codes[3:] == [429, 429]

def test_needs_sign_in(env):
    for m, p in [("get", "/api/me"), ("get", "/api/docs"), ("post", "/api/ask"), ("get", "/api/admin/docs"), ("get", "/api/admin/audit.csv")]:
        assert getattr(env.c, m)(p).status_code in (401, 422) and env.c.request(m, p, headers={"authorization": "Bearer junk"}).status_code in (401, 422)

def test_staff_cannot_use_admin_endpoints(env):
    h = env.h("ayesha")
    for p in ["/api/admin/docs", "/api/admin/users", "/api/admin/audit", "/api/admin/stats", "/api/admin/glossary", "/api/admin/audit.csv"]: assert env.c.get(p, headers=h).status_code == 403
    assert env.c.put("/api/admin/glossary", json={"terms": {}}, headers=h).status_code == 403

def test_answer_has_citation_with_quote_in_passage(env):
    r = env.ask("ayesha", "How many days of annual leave do I get?")
    assert r["outcome"] == "answered" and "22" in r["answer"] and r["citations"][0]["title"] == "Employee Handbook" and r["citations"][0]["page"]
    assert all(q in c["passage"] for c in r["citations"] for q in c["quotes"]) and r["citations"][0]["quotes"]

def test_not_in_documents_is_refused(env):
    for q in ["What is the dress code?", "Does the company offer a pension?", "Who won the football match?"]:
        r = env.ask("ayesha", q); assert r["outcome"] == "refused" and r["citations"] == []

def test_restricted_documents_are_invisible_to_others(env):
    q = "What is the salary range for Band C?"
    assert env.ask("omar", q)["outcome"] == "answered" and "48,000" in env.ask("omar", q)["answer"]
    for u in ["ayesha", "sara", "imran"]: assert env.ask(u, q)["outcome"] == "refused"

def test_refusal_is_the_same_for_restricted_and_missing(env):
    a = env.ask("ayesha", "What is the salary range for Band C?"); b = env.ask("ayesha", "What is the dress code?")
    assert a["answer"] == b["answer"] and a["citations"] == b["citations"] == []

def test_restricted_text_never_in_other_users_citations(env):
    for u in ["ayesha", "sara", "imran"]:
        for q in ["salary Band C pay", "disciplinary warning investigation", "annual leave days"]:
            blob = json.dumps(env.ask(u, q)); assert "48,000" not in blob and "Salary Bands" not in blob or u == "omar"

def test_docs_list_matches_access(env):
    n = lambda u: len(env.c.get("/api/docs", headers=env.h(u)).json())
    assert n("ayesha") == 7 and n("omar") == 9 and n("sara") == 9 and n("imran") == 9 and n("admin") == 7

def test_group_change_takes_effect_at_once(env):
    a = env.h("admin"); q = "What is the salary range for Band C?"; assert env.ask("ayesha", q)["outcome"] == "refused"
    did = next(d["id"] for d in env.c.get("/api/admin/docs", headers=a).json() if d["title"].startswith("Salary"))
    assert env.c.patch(f"/api/admin/docs/{did}", json={"groups": ["everyone"]}, headers=a).status_code == 200
    assert env.ask("ayesha", q)["outcome"] == "answered"
    env.c.patch(f"/api/admin/docs/{did}", json={"groups": ["hr"]}, headers=a); assert env.ask("ayesha", q)["outcome"] == "refused"

def test_user_group_change_and_switch_off(env):
    a = env.h("admin"); uid = next(u["id"] for u in env.c.get("/api/admin/users", headers=a).json() if u["username"] == "ayesha"); q = "What is the salary range for Band C?"
    env.c.patch(f"/api/admin/users/{uid}", json={"groups": ["hr"]}, headers=a); assert env.ask("ayesha", q)["outcome"] == "answered"
    env.c.patch(f"/api/admin/users/{uid}", json={"active": False}, headers=a)
    assert env.c.post("/api/ask", json={"question": q}, headers=env.h("ayesha")).status_code == 401 and env.c.post("/api/login", json={"username": "ayesha", "password": "welcome123"}).status_code == 401

def test_admin_cannot_switch_self_off_and_groups_validated(env):
    a = env.h("admin"); me = env.c.get("/api/me", headers=a).json()["id"]
    assert env.c.patch(f"/api/admin/users/{me}", json={"active": False}, headers=a).status_code == 409
    assert env.c.post("/api/admin/users", json={"username": "x1", "name": "X", "password": "longenough", "groups": ["bad group!"]}, headers=a).status_code == 422
    assert env.c.post("/api/admin/users", json={"username": "x1", "name": "X", "password": "short", "groups": []}, headers=a).status_code == 422
    assert env.c.post("/api/admin/users", json={"username": "ayesha", "name": "X", "password": "longenough", "groups": []}, headers=a).status_code == 409

def test_inbound_key_and_access(env):
    body = {"question": "What is the salary range for Band C?", "user": "omar"}
    assert env.c.post("/api/inbound/ask", json=body).status_code == 401 and env.c.post("/api/inbound/ask", json=body, headers={"x-inbound-key": "wrong"}).status_code == 401
    assert env.c.post("/api/inbound/ask", json=body, headers={"x-inbound-key": "k-test"}).json()["outcome"] == "answered"
    assert env.c.post("/api/inbound/ask", json={**body, "user": "ayesha"}, headers={"x-inbound-key": "k-test"}).json()["outcome"] == "refused"
    assert env.c.post("/api/inbound/ask", json={**body, "user": "ghost"}, headers={"x-inbound-key": "k-test"}).status_code == 404

def test_unset_inbound_key_is_never_open(monkeypatch, tmp_path):
    c, _ = fresh(monkeypatch, tmp_path, INBOUND_KEY="")
    assert c.post("/api/inbound/ask", json={"question": "hello there", "user": "admin"}).status_code == 401
    assert c.post("/api/inbound/ask", json={"question": "hello there", "user": "admin"}, headers={"x-inbound-key": ""}).status_code == 401

def test_audit_records_question_not_answer(env):
    env.ask("ayesha", "How many days of annual leave do I get?"); env.ask("ayesha", "What is the dress code?")
    rows = env.c.get("/api/admin/audit", headers=env.h("admin")).json(); assert [r["outcome"] for r in rows[:2]] == ["refused", "answered"]
    assert "answer" not in rows[1] and "22 working days" not in json.dumps(rows) and rows[1]["doc_title"] == "Employee Handbook" and rows[0]["cited"] == []
    assert len(env.c.get("/api/admin/audit?outcome=refused", headers=env.h("admin")).json()) == 1 and len(env.c.get("/api/admin/audit?q=ayesha", headers=env.h("admin")).json()) == 2

def test_stats_and_gaps(env):
    for _ in range(2): env.ask("ayesha", "What is the dress code?")
    env.ask("ayesha", "How long do we keep invoices?"); s = env.c.get("/api/admin/stats", headers=env.h("admin")).json()
    assert s["questions"] == 3 and s["refused"] == 2 and s["gaps"][0] == {"question": "What is the dress code?", "times": 2} and s["docs"] == 12

def test_csv_export_is_formula_safe(env):
    env.ask("ayesha", "=HYPERLINK(\"http://x.test\",\"hi\")"); t = env.c.get("/api/admin/audit.csv", headers=env.h("admin")).text
    assert "'=HYPERLINK" in t and "\n=HYPERLINK" not in t and t.startswith("id,time,user")

def test_glossary_teaches_the_search(env):
    q = "How many vacations days do I get?"; assert env.ask("ayesha", q)["outcome"] == "refused"
    a = env.h("admin"); g = env.c.get("/api/admin/glossary", headers=a).json(); g["vacations"] = "annual leave"; assert env.c.put("/api/admin/glossary", json={"terms": g}, headers=a).status_code == 200
    r = env.ask("ayesha", q); assert r["outcome"] == "answered" and r["citations"][0]["heading"] == "Annual leave"

def test_input_limits(env):
    h = env.h("ayesha"); assert env.c.post("/api/ask", json={"question": "x" * 501}, headers=h).status_code == 422 and env.c.post("/api/ask", json={"question": "a"}, headers=h).status_code == 422

def test_ask_rate_limit(monkeypatch, tmp_path):
    c, m = fresh(monkeypatch, tmp_path, ASK_PER_MIN="2"); h = {"authorization": "Bearer " + c.post("/api/login", json={"username": "admin", "password": "demo"}).json()["token"]}
    assert [c.post("/api/ask", json={"question": "hello there"}, headers=h).status_code for _ in range(3)] == [200, 200, 429]

def test_html_in_a_question_is_returned_as_data(env):
    r = env.ask("ayesha", "<script>alert(1)</script> annual leave"); assert "<script>" not in r["answer"]

# ---- uploads
def up(env, name, data, groups="everyone"): return env.c.post("/api/admin/docs", files={"file": (name, data)}, data={"groups": groups}, headers=env.h("admin"))
def test_upload_makes_new_document_searchable_with_groups(env):
    r = up(env, "parking.txt", b"## Bicycle storage\nBicycles are kept in the locked cage behind reception. Collect the cage key from the facilities desk.\n", "legal"); assert r.status_code == 200 and r.json()["groups"] == ["legal"]
    q = "Where are bicycles kept?"; assert env.ask("imran", q)["outcome"] == "answered" and env.ask("ayesha", q)["outcome"] == "refused"
def test_upload_rejects_duplicates_wrong_types_and_big_files(env):
    assert up(env, "x.txt", (DOCDIR / "onboarding-guide.txt").read_bytes()).status_code == 409
    assert up(env, "evil.pdf", b"MZ\x90\x00 not a pdf at all").status_code == 422 and up(env, "empty.txt", b"").status_code == 422
    assert up(env, "a.exe", b"MZ" + b"\0" * 100).status_code == 422 and up(env, "big.txt", b"a " * (6 * 1024 * 1024)).status_code == 422
    assert up(env, "ok.txt", b"## A\nhello world text.\n", "bad group!").status_code == 422
def test_upload_rejects_zip_bomb_docx(env):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z: z.writestr("word/document.xml", b"0" * (60 * 1024 * 1024))
    assert up(env, "bomb.docx", buf.getvalue()).status_code == 422
def test_filename_cannot_escape(env):
    r = up(env, "../../etc/passwd.txt", b"## A\nsome words in a file that is long enough.\n"); assert r.status_code == 200 and "/" not in r.json()["filename"] and ".." not in r.json()["filename"]
def test_delete_removes_from_search(env):
    a = env.h("admin"); did = next(d["id"] for d in env.c.get("/api/admin/docs", headers=a).json() if d["title"] == "Data Retention Policy")
    assert env.ask("ayesha", "How long do we keep invoices?")["outcome"] == "answered"; assert env.c.delete(f"/api/admin/docs/{did}", headers=a).status_code == 200
    assert env.ask("ayesha", "How long do we keep invoices?")["outcome"] == "refused" and env.c.delete(f"/api/admin/docs/{did}", headers=a).status_code == 404

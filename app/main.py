import csv, hmac, io, json, logging, re, threading
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File, Form
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import config, db, ingest, security, answer as ans
from .search import Index

logging.basicConfig(level=logging.INFO, format="%(message)s"); log = logging.getLogger("privateqa")
def jlog(**kw): log.info(json.dumps({"ts": config.wall().isoformat(timespec="seconds"), **kw}))
STATIC = Path(__file__).resolve().parent.parent / "static"
app = FastAPI(title=f"{config.COMPANY} Private Q&A", docs_url=None, redoc_url=None); db.init()
ask_rl, login_rl, inbound_rl = security.RateLimiter(config.ASK_PER_MIN), security.RateLimiter(config.LOGIN_PER_MIN), security.RateLimiter(config.INBOUND_PER_MIN)
GROUP = re.compile(r"^[a-z0-9_-]{1,30}$"); USERNAME = re.compile(r"^[a-z0-9._-]{2,30}$")
if config.GENERATED_PASSWORD: print(f"Admin password for this run: {config.GENERATED_PASSWORD}")

def ensure_admin():
    c = db.connect()
    try:
        if not c.execute("select 1 from users where username='admin'").fetchone():
            s, h = security.hash_password(config.ADMIN_PASSWORD); c.execute("insert into users(username,name,salt,hash,groups,is_admin,created) values('admin','Administrator',?,?,'[]',1,?)", (s, h, config.now().isoformat(timespec="seconds")))
    finally: c.close()
ensure_admin()

@app.middleware("http")
async def headers(request: Request, call_next):
    r = await call_next(request)
    r.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
                      "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:", "Cache-Control": "no-store" if request.url.path.startswith("/api") else "no-cache"})
    return r

# ---------------------------------------------------------------- who is asking
def current_user(r: Request):
    h = r.headers.get("authorization", ""); uid = security.verify_token(h[7:]) if h.startswith("Bearer ") else None
    if uid is None: raise HTTPException(401, "Not signed in")
    c = db.connect()
    try: u = c.execute("select * from users where id=? and active=1", (uid,)).fetchone()
    finally: c.close()
    if not u: raise HTTPException(401, "Not signed in")
    return u
def admin(u=Depends(current_user)):
    if not u["is_admin"]: raise HTTPException(403, "Administrators only")
    return u
def groups_of(u) -> frozenset: return frozenset({"everyone", *db.loads(u["groups"], [])})
def user_json(u): return {"id": u["id"], "username": u["username"], "name": u["name"], "groups": db.loads(u["groups"], []), "admin": bool(u["is_admin"])}

# ---------------------------------------------------------------- the search index, one per set of readable documents
_cache: dict = {}; _lock = threading.Lock()
def invalidate():
    with _lock: _cache.clear()
def index_for(groups: frozenset) -> Index:
    with _lock:
        if groups in _cache: return _cache[groups]
    c = db.connect()
    try:
        gl = {r["term"]: r["means"] for r in c.execute("select term, means from terms")}
        rows = [dict(r, groups=db.loads(r["groups"], [])) for r in c.execute("select ch.id, ch.doc, d.title, ch.heading, ch.page, ch.text, d.groups from chunks ch join docs d on d.id=ch.doc where d.active=1 order by ch.doc, ch.ord")]
    finally: c.close()
    idx = Index([r for r in rows if set(r["groups"]) & groups], gl)
    with _lock: _cache[groups] = idx
    return idx
def llm():
    return True if config.LLM_PROVIDER == "ollama" else None

# ---------------------------------------------------------------- login, ask
class Login(BaseModel): username: str = Field(max_length=60); password: str = Field(max_length=200)
@app.get("/health")
def health(): return {"ok": True}
@app.post("/api/login")
def login(body: Login, request: Request):
    if not login_rl.allow(request.client.host if request.client else "?"): raise HTTPException(429, "Too many attempts, wait a minute")
    c = db.connect()
    try: u = c.execute("select * from users where username=? and active=1", (body.username.strip().lower(),)).fetchone()
    finally: c.close()
    ok = security.check_password(body.password, u["salt"], u["hash"]) if u else (security.check_password(body.password, "00" * 16, "00" * 32) and False)      # same work whether or not the user exists
    if not (u and ok): raise HTTPException(401, "Wrong username or password")
    return {"token": security.make_token(u["id"]), "user": user_json(u)}
@app.get("/api/me")
def me(u=Depends(current_user)): return user_json(u)

class Ask(BaseModel): question: str = Field(min_length=2, max_length=500)
def run_ask(u, question: str, via: str):
    res = ans.answer(index_for(groups_of(u)), question, llm())
    c = db.connect()
    try: aid = c.execute("insert into audit(ts,username,question,outcome,cited,score) values(?,?,?,?,?,?)", (config.now().isoformat(timespec="seconds"), u["username"], question.strip()[:500], res["outcome"], json.dumps(sorted({x["doc"] for x in res["citations"][:1]})), res["score"])).lastrowid
    finally: c.close()
    jlog(event="ask", user=u["username"], outcome=res["outcome"], via=via); return {**res, "id": aid}
@app.post("/api/ask")
def ask(body: Ask, u=Depends(current_user)):
    if not ask_rl.allow(u["username"]): raise HTTPException(429, "Too many questions, slow down")
    return run_ask(u, body.question, "app")
class InboundAsk(BaseModel): question: str = Field(min_length=2, max_length=500); user: str = Field(max_length=60)
@app.post("/api/inbound/ask")
def inbound_ask(body: InboundAsk, request: Request):
    """For n8n and other tools: asks as a named user, so that person's document access applies. Needs the inbound key."""
    key = request.headers.get("x-inbound-key", "")
    if not (config.INBOUND_KEY and hmac.compare_digest(key, config.INBOUND_KEY)): raise HTTPException(401, "Missing or wrong inbound key")
    if not inbound_rl.allow(request.client.host if request.client else "?"): raise HTTPException(429, "Too many requests, slow down")
    c = db.connect()
    try: u = c.execute("select * from users where username=? and active=1", (body.user.strip().lower(),)).fetchone()
    finally: c.close()
    if not u: raise HTTPException(404, "No such user")
    return run_ask(u, body.question, "inbound")
@app.get("/api/docs")
def my_docs(u=Depends(current_user)):
    g = groups_of(u); c = db.connect()
    try: return [{"id": d["id"], "title": d["title"], "kind": d["kind"], "pages": d["pages"]} for d in c.execute("select * from docs where active=1 order by title") if set(db.loads(d["groups"], [])) & g]
    finally: c.close()

# ---------------------------------------------------------------- administration
def doc_row(d, c): return {"id": d["id"], "title": d["title"], "filename": d["filename"], "kind": d["kind"], "pages": d["pages"], "groups": db.loads(d["groups"], []), "chunks": c.execute("select count(*) from chunks where doc=?", (d["id"],)).fetchone()[0], "added_by": d["added_by"], "created": d["created"]}
def parse_groups(s: str):
    gs = [g.strip().lower() for g in (s or "").split(",") if g.strip()] or ["everyone"]
    if any(not GROUP.match(g) for g in gs): raise HTTPException(422, "Group names use letters, numbers, dashes and underscores")
    return sorted(set(gs))
@app.get("/api/admin/docs", dependencies=[Depends(admin)])
def admin_docs():
    c = db.connect()
    try: return [doc_row(d, c) for d in c.execute("select * from docs where active=1 order by title")]
    finally: c.close()
@app.post("/api/admin/docs")
async def upload(file: UploadFile = File(...), groups: str = Form("everyone"), u=Depends(admin)):
    raw = await file.read(config.MAX_UPLOAD + 1); gs = parse_groups(groups)
    try: r = ingest.read_document(file.filename or "document", raw)
    except ingest.Rejected as e: raise HTTPException(422, str(e))
    except Exception: raise HTTPException(422, "The file could not be read")
    c = db.connect()
    try:
        if c.execute("select 1 from docs where sha=? and active=1", (r["sha"],)).fetchone(): raise HTTPException(409, "This exact file is already in the library")
        did = c.execute("insert into docs(filename,title,kind,groups,sha,pages,added_by,created) values(?,?,?,?,?,?,?,?)", (ingest.safe_name(file.filename), r["title"][:150], r["kind"], json.dumps(gs), r["sha"], r["pages"], u["username"], config.now().isoformat(timespec="seconds"))).lastrowid
        c.executemany("insert into chunks(doc,ord,heading,page,text) values(?,?,?,?,?)", [(did, i, h, pg, t) for i, (h, pg, t) in enumerate(r["chunks"])])
        out = doc_row(c.execute("select * from docs where id=?", (did,)).fetchone(), c)
    finally: c.close()
    invalidate(); jlog(event="upload", by=u["username"], doc=did); return out
class DocPatch(BaseModel): groups: list[str] = Field(max_length=20)
@app.patch("/api/admin/docs/{did}", dependencies=[Depends(admin)])
def patch_doc(did: int, body: DocPatch):
    gs = parse_groups(",".join(body.groups)); c = db.connect()
    try:
        if not c.execute("select 1 from docs where id=? and active=1", (did,)).fetchone(): raise HTTPException(404, "No such document")
        c.execute("update docs set groups=? where id=?", (json.dumps(gs), did))
    finally: c.close()
    invalidate(); return {"ok": True, "groups": gs}
@app.delete("/api/admin/docs/{did}", dependencies=[Depends(admin)])
def delete_doc(did: int):
    c = db.connect()
    try:
        if not c.execute("select 1 from docs where id=? and active=1", (did,)).fetchone(): raise HTTPException(404, "No such document")
        c.execute("delete from chunks where doc=?", (did,)); c.execute("delete from docs where id=?", (did,))
    finally: c.close()
    invalidate(); return {"ok": True}

class NewUser(BaseModel): username: str = Field(max_length=30); name: str = Field(max_length=60); password: str = Field(min_length=8, max_length=100); groups: list[str] = Field(default_factory=list, max_length=20)
class UserPatch(BaseModel): groups: list[str] | None = Field(default=None, max_length=20); active: bool | None = None; password: str | None = Field(default=None, min_length=8, max_length=100)
@app.get("/api/admin/users", dependencies=[Depends(admin)])
def users():
    c = db.connect()
    try: return [user_json(r) | {"active": bool(r["active"])} for r in c.execute("select * from users order by id")]
    finally: c.close()
@app.post("/api/admin/users", dependencies=[Depends(admin)])
def new_user(body: NewUser):
    un = body.username.strip().lower()
    if not USERNAME.match(un): raise HTTPException(422, "Usernames use lowercase letters, numbers, dots, dashes and underscores")
    gs = [g for g in parse_groups(",".join(body.groups)) if g != "everyone"]; s, h = security.hash_password(body.password); c = db.connect()
    try:
        if c.execute("select 1 from users where username=?", (un,)).fetchone(): raise HTTPException(409, "That username is taken")
        uid = c.execute("insert into users(username,name,salt,hash,groups,created) values(?,?,?,?,?,?)", (un, body.name.strip(), s, h, json.dumps(gs), config.now().isoformat(timespec="seconds"))).lastrowid
        return user_json(c.execute("select * from users where id=?", (uid,)).fetchone())
    finally: c.close()
@app.patch("/api/admin/users/{uid}")
def patch_user(uid: int, body: UserPatch, me=Depends(admin)):
    c = db.connect()
    try:
        u = c.execute("select * from users where id=?", (uid,)).fetchone()
        if not u: raise HTTPException(404, "No such user")
        if body.active is False and u["id"] == me["id"]: raise HTTPException(409, "You cannot switch off your own account")
        if body.groups is not None: c.execute("update users set groups=? where id=?", (json.dumps([g for g in parse_groups(",".join(body.groups)) if g != "everyone"]), uid))
        if body.active is not None: c.execute("update users set active=? where id=?", (int(body.active), uid))
        if body.password: s, h = security.hash_password(body.password); c.execute("update users set salt=?, hash=? where id=?", (s, h, uid))
        return user_json(c.execute("select * from users where id=?", (uid,)).fetchone())
    finally: c.close()
    
class Terms(BaseModel): terms: dict[str, str] = Field(max_length=500)
@app.get("/api/admin/glossary", dependencies=[Depends(admin)])
def get_glossary():
    c = db.connect()
    try: return {r["term"]: r["means"] for r in c.execute("select * from terms order by term")}
    finally: c.close()
@app.put("/api/admin/glossary", dependencies=[Depends(admin)])
def put_glossary(body: Terms):
    clean = {k.strip().lower()[:60]: v.strip().lower()[:120] for k, v in body.terms.items() if k.strip() and v.strip()}; c = db.connect()
    try: c.execute("delete from terms"); c.executemany("insert into terms(term,means) values(?,?)", list(clean.items()))
    finally: c.close()
    invalidate(); return {"ok": True, "terms": len(clean)}

@app.get("/api/admin/audit", dependencies=[Depends(admin)])
def audit(outcome: str = "", q: str = "", limit: int = 300):
    c = db.connect()
    try:
        sql, a = "select a.*, d.title as doc_title from audit a left join docs d on d.id = json_extract(a.cited, '$[0]') where 1=1", []
        if outcome in ("answered", "refused"): sql += " and a.outcome=?"; a.append(outcome)
        if q: sql += " and (a.question like ? or a.username like ?)"; a += [f"%{q[:60]}%"] * 2
        return [dict(r, cited=db.loads(r["cited"], [])) for r in c.execute(sql + " order by a.id desc limit ?", a + [max(1, min(limit, 1000))])]
    finally: c.close()
@app.get("/api/admin/stats", dependencies=[Depends(admin)])
def stats():
    c = db.connect()
    try:
        q = lambda sql, *a: c.execute(sql, a).fetchone()[0]; total = q("select count(*) from audit"); refused = q("select count(*) from audit where outcome='refused'")
        return {"docs": q("select count(*) from docs where active=1"), "users": q("select count(*) from users where active=1"), "questions": total, "answered": total - refused, "refused": refused,
                "answer_rate": round(100 * (total - refused) / total) if total else 0,
                "gaps": [{"question": r[0], "times": r[1]} for r in c.execute("select question, count(*) n from audit where outcome='refused' group by lower(question) order by n desc, max(id) desc limit 8")],
                "top_docs": [{"title": r[0], "times": r[1]} for r in c.execute("select d.title, count(*) n from audit a join docs d on d.id = json_extract(a.cited, '$[0]') group by d.id order by n desc limit 6")]}
    finally: c.close()
def safe_cell(v): return "'" + v if isinstance(v, str) and v[:1] in "=+-@\t\r" else v
@app.get("/api/admin/audit.csv", dependencies=[Depends(admin)])
def audit_csv():
    buf = io.StringIO(); w = csv.writer(buf); w.writerow(["id", "time", "user", "question", "outcome", "top document", "score"])
    for r in audit(limit=1000): w.writerow([safe_cell(x) for x in (r["id"], r["ts"], r["username"], r["question"], r["outcome"], r["doc_title"] or "", r["score"])])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=audit.csv"})
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")

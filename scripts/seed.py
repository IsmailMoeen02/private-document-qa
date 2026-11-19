"""Loads the demo into a running app: the 12 dummy documents with their groups, four users, the glossary, and a few questions so the log has something in it.
  python scripts/seed.py [APP_URL]       (admin password: ADMIN_PASSWORD, default demo)"""
import json, mimetypes, os, sys, urllib.request, uuid
APP = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "http://127.0.0.1:8796").rstrip("/")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "data"))
from corpus import DOCS, USERS
def call(path, body=None, token=None, method=None):
    req = urllib.request.Request(APP + path, data=json.dumps(body).encode() if body is not None else None, method=method or ("POST" if body is not None else "GET"), headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
    return json.load(urllib.request.urlopen(req, timeout=60))
def upload(path, name, data, groups, token):
    b = uuid.uuid4().hex; body = (f'--{b}\r\nContent-Disposition: form-data; name="groups"\r\n\r\n{",".join(groups)}\r\n--{b}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + data + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(APP + path, data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}", "Authorization": "Bearer " + token}); return json.load(urllib.request.urlopen(req, timeout=60))
tok = call("/api/login", {"username": "admin", "password": os.environ.get("ADMIN_PASSWORD", "demo")})["token"]
if call("/api/admin/docs", token=tok): print("already seeded"); sys.exit(0)
call("/api/admin/glossary", {"terms": json.load(open(os.path.join(ROOT, "data", "glossary.json")))}, tok, "PUT")
for d in DOCS: upload("/api/admin/docs", f"{d['id']}.{d['format']}", open(os.path.join(ROOT, "data", "docs", f"{d['id']}.{d['format']}"), "rb").read(), d["groups"], tok)
for un, name, groups in USERS: call("/api/admin/users", {"username": un, "name": name, "password": "welcome123", "groups": groups}, tok)
ASKS = [("ayesha", "How many days of annual leave do I get?"), ("ayesha", "Can I work from home on Fridays?"), ("ayesha", "How long must my password be?"), ("ayesha", "What is the dress code?"), ("ayesha", "How long do we keep invoices?"),
        ("ayesha", "What is the dress code for client events?"), ("ayesha", "Where is the fire assembly point?"), ("ayesha", "Does the company offer a pension?"), ("omar", "What is the salary range for Band C?"), ("omar", "How long does a disciplinary investigation take?"),
        ("sara", "What is the marketing budget for 2027?"), ("sara", "What is the hotel limit in London?"), ("imran", "What is the liability cap in our customer agreement?"), ("imran", "How long does an NDA last?"), ("ayesha", "What is the dress code?"), ("ayesha", "Does the company offer a pension?")]
logins = {un: call("/api/login", {"username": un, "password": "welcome123"})["token"] for un, _, _ in USERS}
for u, q in ASKS: call("/api/ask", {"question": q}, logins[u])
print(call("/api/admin/stats", token=tok)["questions"], "questions in the log;", len(call("/api/admin/docs", token=tok)), "documents")

"""Imports workflow.json into a local n8n, activates it, and sends test questions through it.  python n8n/run_in_n8n.py
Needs n8n on :5678 (owner login below), the app on :8796 (INBOUND_KEY=demo-inbound-key), n8n/fake_slack.py on :8799."""
import json, os, sys, time, urllib.request, http.cookiejar
HERE = os.path.dirname(os.path.abspath(__file__)); N = "http://127.0.0.1:5678"
jar = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def call(path, body=None, method=None):
    r = urllib.request.Request(N + path, data=json.dumps(body).encode() if body is not None else None, method=method or ("POST" if body is not None else "GET"), headers={"Content-Type": "application/json"})
    try: return json.load(op.open(r, timeout=300))
    except urllib.error.HTTPError as e: print(path, e.code, e.read()[:300]); raise
call("/rest/login", {"emailOrLdapLoginId": "owner@leaddesk.example", "password": "LeadDesk#2026"})
wf = json.load(open(os.path.join(HERE, "workflow.json")))
for w in call("/rest/workflows")["data"]:
    if w["name"] == wf["name"]:
        try: call(f"/rest/workflows/{w['id']}/deactivate", {"versionId": w.get("versionId")})
        except Exception: pass
        call(f"/rest/workflows/{w['id']}/archive", {"versionId": w.get("versionId")}); call(f"/rest/workflows/{w['id']}", method="DELETE")
d = call("/rest/workflows", wf)["data"]; call(f"/rest/workflows/{d['id']}/activate", {"versionId": d["versionId"]}); print("imported and active:", d["id"])
if "--import-only" in sys.argv: sys.exit(0)
ASKS = [{"user": "ayesha", "question": "How many days of annual leave do I get?"}, {"user": "ayesha", "question": "What is the salary range for Band C?"}, {"user": "omar", "question": "What is the salary range for Band C?"}, {"user": "ayesha", "question": "What is the dress code?"}]
for a in ASKS:
    req = urllib.request.Request(N + "/webhook/ask-documents", data=json.dumps(a).encode(), headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120)); print(a["user"], "|", a["question"], "->", r["outcome"], "|", (r["citations"][0]["title"] + ", " + r["citations"][0]["heading"]) if r["citations"] else "no source")

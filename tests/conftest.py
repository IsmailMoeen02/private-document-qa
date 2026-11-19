import sys, json, io, zipfile
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "data"))
from corpus import DOCS, USERS
DOCDIR = ROOT / "data" / "docs"

def fresh(monkeypatch, tmp_path, **env):
    base = {"DB_PATH": str(tmp_path / "t.db"), "DEMO_MODE": "1", "INBOUND_KEY": "k-test", "LOGIN_PER_MIN": "1000", "FAKE_NOW": "2026-11-05T09:30", "LLM_PROVIDER": "rules"}
    for k, v in {**base, **env}.items(): monkeypatch.setenv(k, v)
    for m in [m for m in sys.modules if m == "app" or m.startswith("app.")]: del sys.modules[m]
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app), main

class Api:
    def __init__(self, c): self.c = c; self.tok = {}
    def login(self, u, pw="welcome123"):
        r = self.c.post("/api/login", json={"username": u, "password": "demo" if u == "admin" else pw}); assert r.status_code == 200, r.text
        self.tok[u] = {"authorization": "Bearer " + r.json()["token"]}; return self.tok[u]
    def h(self, u): return self.tok.get(u) or self.login(u)
    def ask(self, u, q): r = self.c.post("/api/ask", json={"question": q}, headers=self.h(u)); assert r.status_code == 200, r.text; return r.json()

@pytest.fixture()
def env(monkeypatch, tmp_path):
    c, main = fresh(monkeypatch, tmp_path); api = Api(c); a = api.h("admin")
    c.put("/api/admin/glossary", json={"terms": json.load(open(ROOT / "data" / "glossary.json"))}, headers=a)
    for d in DOCS:
        f = f"{d['id']}.{d['format']}"; r = c.post("/api/admin/docs", files={"file": (f, (DOCDIR / f).read_bytes())}, data={"groups": ",".join(d["groups"])}, headers=a); assert r.status_code == 200, r.text
    for un, name, g in USERS: assert c.post("/api/admin/users", json={"username": un, "name": name, "password": "welcome123", "groups": g}, headers=a).status_code == 200
    api.main = main; return api

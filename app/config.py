"""Settings, all from environment variables. No secrets live in the code."""
import os, secrets, datetime as dt
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("DB_PATH", str(BASE / "privateqa.db"))
COMPANY = os.environ.get("COMPANY_NAME", "Harbourview Advisory")
DEMO_MODE = os.environ.get("DEMO_MODE", "0") == "1"
INBOUND_KEY = os.environ.get("INBOUND_KEY", "")
_pw = os.environ.get("ADMIN_PASSWORD")
GENERATED_PASSWORD = None
if not _pw: _pw = "demo" if DEMO_MODE else secrets.token_urlsafe(9); GENERATED_PASSWORD = None if DEMO_MODE else _pw
ADMIN_PASSWORD = _pw; SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32)); TOKEN_TTL = int(os.environ.get("TOKEN_TTL", str(12 * 3600)))
# Documents
MAX_UPLOAD = int(os.environ.get("MAX_UPLOAD", str(10 * 1024 * 1024))); MAX_PAGES = int(os.environ.get("MAX_PAGES", "200")); MAX_UNZIPPED = int(os.environ.get("MAX_UNZIPPED", str(50 * 1024 * 1024)))
# Search and answers
MIN_SCORE = float(os.environ.get("MIN_SCORE", "0.30")); MIN_COVERAGE = float(os.environ.get("MIN_COVERAGE", "0.5")); TOP_K = int(os.environ.get("TOP_K", "4"))
# Optional local language model (an Ollama-style server on the same machine). Off unless set.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "rules"); OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"); OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
ASK_PER_MIN = int(os.environ.get("ASK_PER_MIN", "30")); LOGIN_PER_MIN = int(os.environ.get("LOGIN_PER_MIN", "5")); INBOUND_PER_MIN = int(os.environ.get("INBOUND_PER_MIN", "60"))
FAKE_NOW = os.environ.get("FAKE_NOW", "")
def now() -> dt.datetime: return dt.datetime.fromisoformat(FAKE_NOW) if FAKE_NOW else dt.datetime.now()
def wall() -> dt.datetime: return dt.datetime.now()

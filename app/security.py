"""Passwords (PBKDF2), signed tokens that carry the user id, and a rate limiter."""
import base64, hashlib, hmac, secrets, time
from collections import defaultdict, deque
from . import config

class RateLimiter:
    """Sliding window, in memory. Fine for one process; use Redis if you scale out."""
    def __init__(self, limit, window=60): self.limit, self.window, self.hits = limit, window, defaultdict(deque)
    def allow(self, key):
        now = time.monotonic(); q = self.hits[key]
        while q and now - q[0] > self.window: q.popleft()
        if len(q) >= self.limit: return False
        q.append(now); return True

def hash_password(pw: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16); return salt.hex(), hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()
def check_password(pw: str, salt_hex: str, hash_hex: str) -> bool:
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt_hex), 200_000).hex(), hash_hex)

def make_token(uid: int, now=None) -> str:
    body = f"{uid}.{int((time.time() if now is None else now) + config.TOKEN_TTL)}".encode()
    return base64.urlsafe_b64encode(body + b"." + hmac.new(config.SECRET_KEY.encode(), body, hashlib.sha256).digest()).decode()
def verify_token(tok: str, now=None):
    """Returns the user id, or None."""
    try:
        raw = base64.urlsafe_b64decode(tok.encode()); body, sig = raw[:-33], raw[-32:]           # the signature is 32 raw bytes and may itself contain a dot, so split by length
        if not hmac.compare_digest(sig, hmac.new(config.SECRET_KEY.encode(), body, hashlib.sha256).digest()): return None
        uid, exp = body.decode().split("."); return int(uid) if int(exp) > (time.time() if now is None else now) else None
    except Exception: return None

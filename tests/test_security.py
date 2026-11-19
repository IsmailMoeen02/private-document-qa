import time, pytest
from conftest import fresh

def test_token_round_trip_and_expiry(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path); from app import security
    t = security.make_token(7); assert security.verify_token(t) == 7
    assert security.verify_token(t, now=time.time() + 13 * 3600) is None

def test_token_signature_may_contain_a_dot(monkeypatch, tmp_path):
    """Regression: the signature is raw bytes and can contain 0x2e. About 1 token in 8 broke the first version."""
    fresh(monkeypatch, tmp_path); from app import security
    for uid in range(1, 400): assert security.verify_token(security.make_token(uid)) == uid

def test_tampered_or_garbage_tokens(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path); from app import security; import base64
    t = security.make_token(3); raw = bytearray(base64.urlsafe_b64decode(t)); raw[0] ^= 1
    assert security.verify_token(base64.urlsafe_b64encode(bytes(raw)).decode()) is None
    for bad in ["", "abc", "....", "x" * 500]: assert security.verify_token(bad) is None

def test_password_hash(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path); from app import security
    s, h = security.hash_password("correct horse"); assert security.check_password("correct horse", s, h) and not security.check_password("wrong", s, h)

def test_rate_limiter(monkeypatch, tmp_path):
    fresh(monkeypatch, tmp_path); from app import security
    r = security.RateLimiter(3); assert [r.allow("a") for _ in range(4)] == [True, True, True, False] and r.allow("b")

def test_security_headers(env):
    r = env.c.get("/health"); assert r.headers["x-frame-options"] == "DENY" and "default-src 'self'" in r.headers["content-security-policy"]
    assert env.c.get("/api/me").headers["cache-control"] == "no-store"

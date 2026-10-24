"""閒置逾時：通過驗證的 API 請求換發新 token，閒置超過 JWT_EXPIRE_MINUTES 才過期。"""
from datetime import datetime, timedelta, timezone

from httpx import ASGITransport, AsyncClient
from jose import jwt

from src.core.config import get_settings
from src.core.security import ALGORITHM, create_access_token, decode_token
from src.main import app


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _expired_token() -> str:
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {"sub": "admin", "role": "admin", "iat": past - timedelta(minutes=10), "exp": past}
    return jwt.encode(payload, get_settings().jwt_secret_key, algorithm=ALGORITHM)


async def test_token_expiry_uses_minutes(monkeypatch):
    monkeypatch.setattr(get_settings(), "jwt_expire_minutes", 10)
    payload = decode_token(create_access_token(sub="admin", role="admin"))
    assert payload["exp"] - payload["iat"] == 600


async def test_authenticated_request_returns_renewed_token(isolated_app, admin_headers):
    async with _client() as client:
        r = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert r.status_code == 200
    renewed = r.headers["X-Access-Token"]
    assert renewed != admin_headers["Authorization"][7:]
    assert decode_token(renewed)["sub"] == "admin"
    assert f"access_token={renewed}" in r.headers["set-cookie"]


async def test_rejected_cookie_only_request_is_not_renewed(isolated_app):
    token = create_access_token(sub="admin", role="admin")
    async with _client() as client:
        client.cookies.set("access_token", token)
        r = await client.get("/api/v1/auth/me")
    # /auth/me 只收 Bearer，cookie 單獨不足以通過驗證，不應換發
    assert r.status_code == 401
    assert "X-Access-Token" not in r.headers


async def test_expired_token_is_not_renewed(isolated_app):
    async with _client() as client:
        r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {_expired_token()}"})
    assert r.status_code == 401
    assert "X-Access-Token" not in r.headers


async def test_logout_does_not_renew(isolated_app, admin_headers):
    async with _client() as client:
        r = await client.post("/api/v1/auth/logout", headers=admin_headers)
    assert r.status_code == 200
    assert "X-Access-Token" not in r.headers
    assert 'access_token=""' in r.headers["set-cookie"]


async def test_request_without_token_is_not_renewed(isolated_app):
    async with _client() as client:
        r = await client.get("/health")
    assert "X-Access-Token" not in r.headers

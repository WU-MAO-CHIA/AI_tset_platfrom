"""驗證碼解碼內部 API：只接受執行時注入的 captcha token，由後端代為呼叫 LLM。"""
import base64

import pytest
from httpx import ASGITransport, AsyncClient

import src.api.internal as internal_api
from src.core.security import create_access_token, create_captcha_token
from src.main import app

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()


class FakeVisionProvider:
    def __init__(self):
        self.calls = []

    async def complete_with_vision(self, prompt, media_list):
        with open(media_list[0].file_path, "rb") as f:
            self.calls.append((prompt, media_list[0].mime_type, f.read()))
        return " AB12 \n"


@pytest.fixture
def provider(monkeypatch):
    fake = FakeVisionProvider()
    monkeypatch.setattr(internal_api, "get_provider", lambda model, settings: fake)
    monkeypatch.setattr(internal_api, "_CALLS", {})
    return fake


def _client(token: str | None) -> AsyncClient:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers)


def _body(**overrides):
    return {"image_base64": PNG, "media_type": "image/png", "prompt": "read it", **overrides}


async def test_solves_with_captcha_token(provider):
    async with _client(create_captcha_token()) as c:
        r = await c.post("/api/v1/internal/captcha/solve", json=_body())
    assert r.status_code == 200
    assert r.json()["text"] == "AB12"
    assert provider.calls == [("read it", "image/png", b"\x89PNG\r\n\x1a\nfake")]
    assert "X-Access-Token" not in r.headers  # 不是登入 token，不會被續期成登入 token


async def test_login_token_is_rejected(provider, admin_headers):
    async with _client(admin_headers["Authorization"][7:]) as c:
        r = await c.post("/api/v1/internal/captcha/solve", json=_body())
    assert r.status_code == 401
    assert provider.calls == []


async def test_captcha_token_cannot_be_used_as_login(isolated_app):
    async with _client(create_captcha_token()) as c:
        assert (await c.get("/api/v1/auth/me")).status_code == 401


async def test_missing_token_rejected(provider):
    async with _client(None) as c:
        assert (await c.post("/api/v1/internal/captcha/solve", json=_body())).status_code == 401


async def test_rejects_non_image_media_type(provider):
    async with _client(create_captcha_token()) as c:
        r = await c.post("/api/v1/internal/captcha/solve", json=_body(media_type="text/html"))
    assert r.status_code == 422


async def test_call_limit_per_token(provider, monkeypatch):
    monkeypatch.setattr(internal_api, "MAX_CALLS_PER_TOKEN", 2)
    token = create_captcha_token()
    async with _client(token) as c:
        assert (await c.post("/api/v1/internal/captcha/solve", json=_body())).status_code == 200
        assert (await c.post("/api/v1/internal/captcha/solve", json=_body())).status_code == 200
        assert (await c.post("/api/v1/internal/captcha/solve", json=_body())).status_code == 429
    # 另一次執行拿到新的 token，不受影響
    async with _client(create_captcha_token()) as c:
        assert (await c.post("/api/v1/internal/captcha/solve", json=_body())).status_code == 200

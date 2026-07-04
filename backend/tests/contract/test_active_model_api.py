"""Contract tests：後台「目前啟用模型」可切換（FR-027 / Phase 24）。

GET /admin/active-model、PUT /admin/active-model 寫入後 GET 一致，
且 /llm-models 的 default 反映；非 admin → 403；未帶 token → 401。
啟用模型存 DB（加密 app_settings），金鑰仍 .env 唯讀。
"""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _admin_token(client) -> str:
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert r.status_code == 200, "需要 admin seed 帳號（admin/admin）"
    return r.json()["access_token"]


class TestActiveModelReadWrite:
    async def test_put_then_get_consistent_and_reflected_in_llm_models(self, client):
        token = await _admin_token(client)
        h = {"Authorization": f"Bearer {token}"}

        # 記錄原值以利還原
        original = (await client.get("/api/v1/admin/active-model", headers=h)).json()["model"]
        try:
            r = await client.put("/api/v1/admin/active-model", headers=h, json={"model": "gpt-4o"})
            assert r.status_code == 200

            got = await client.get("/api/v1/admin/active-model", headers=h)
            assert got.status_code == 200
            assert got.json()["model"] == "gpt-4o"

            # /llm-models 的 default 反映目前啟用模型
            models = await client.get("/api/v1/llm-models")
            assert models.json()["default"] == "gpt-4o"
        finally:
            await client.put("/api/v1/admin/active-model", headers=h, json={"model": original})

    async def test_get_requires_auth(self, client):
        r = await client.get("/api/v1/admin/active-model")
        assert r.status_code == 401

    async def test_put_requires_auth(self, client):
        r = await client.put("/api/v1/admin/active-model", json={"model": "gpt-4o"})
        assert r.status_code == 401

    async def test_non_admin_forbidden(self, client):
        token = await _admin_token(client)
        h = {"Authorization": f"Bearer {token}"}

        username = f"viewer_{uuid.uuid4().hex[:8]}"
        password = "viewer-pass-123"
        await client.post(
            "/api/v1/admin/users",
            headers=h,
            json={"username": username, "password": password, "role": "viewer"},
        )
        login = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert login.status_code == 200
        viewer_h = {"Authorization": f"Bearer {login.json()['access_token']}"}

        r = await client.put("/api/v1/admin/active-model", headers=viewer_h, json={"model": "gpt-4o"})
        assert r.status_code == 403

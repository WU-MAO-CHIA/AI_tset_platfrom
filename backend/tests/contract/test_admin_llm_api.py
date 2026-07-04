"""Contract tests for /api/v1/admin LLM 唯讀端點（Phase 23 / env-only）。

金鑰與預設模型由 .env 配置；後台僅唯讀遮罩顯示，無編輯端點。
"""
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


class TestLlmKeysMasked:
    async def test_get_llm_keys_returns_masked_structure(self, client):
        token = await _admin_token(client)
        r = await client.get("/api/v1/admin/llm-keys", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        for f in ("anthropic_key_set", "anthropic_key_masked", "openai_key_set", "openai_key_masked"):
            assert f in data
        # 已設定者遮罩需含 ****；皆不得含完整明文
        for f in ("anthropic_key_masked", "openai_key_masked"):
            if data[f]:
                assert "****" in data[f]

    async def test_get_llm_keys_requires_auth(self, client):
        r = await client.get("/api/v1/admin/llm-keys")
        assert r.status_code == 401


class TestDefaultModelReadOnly:
    async def test_get_default_model(self, client):
        token = await _admin_token(client)
        r = await client.get("/api/v1/admin/llm-default-model", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert "model" in r.json()

    async def test_default_model_requires_auth(self, client):
        r = await client.get("/api/v1/admin/llm-default-model")
        assert r.status_code == 401

    async def test_no_write_endpoint(self, client):
        """env-only：不應存在 PUT 寫入端點。"""
        token = await _admin_token(client)
        h = {"Authorization": f"Bearer {token}"}
        r = await client.put("/api/v1/admin/llm-default-model", headers=h, json={"model": "gpt-4o"})
        assert r.status_code in (404, 405)

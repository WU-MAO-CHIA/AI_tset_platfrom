"""Contract tests for /api/v1/admin LLM key 遮罩 + 全域預設模型端點（Phase 23）。
RED: 在 masked llm-keys + llm-default-model 端點實作前應失敗。
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
        # 已設定者遮罩值需含 ****；未設定者為空，皆不得含完整明文
        for f in ("anthropic_key_masked", "openai_key_masked"):
            if data[f]:
                assert "****" in data[f]

    async def test_get_llm_keys_requires_auth(self, client):
        r = await client.get("/api/v1/admin/llm-keys")
        assert r.status_code == 401


class TestDefaultModelEndpoint:
    async def test_put_then_get_default_model(self, client):
        token = await _admin_token(client)
        h = {"Authorization": f"Bearer {token}"}
        put = await client.put("/api/v1/admin/llm-default-model", headers=h, json={"model": "claude-opus-4-7"})
        assert put.status_code == 200
        get = await client.get("/api/v1/admin/llm-default-model", headers=h)
        assert get.status_code == 200
        assert get.json()["model"] == "claude-opus-4-7"

    async def test_default_model_requires_auth(self, client):
        r = await client.get("/api/v1/admin/llm-default-model")
        assert r.status_code == 401

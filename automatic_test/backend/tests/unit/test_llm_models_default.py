"""Tests for /api/v1/llm-models `default` 解析（Phase 23）。
DB 有值 → 回 DB 值；無值 → fallback env settings.default_llm_model。
RED: 在 llm_models.py 改為 DB 優先前應失敗。
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
    assert r.status_code == 200
    return r.json()["access_token"]


class TestLlmModelsDefault:
    async def test_list_has_models_and_default(self, client):
        r = await client.get("/api/v1/llm-models")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        assert "default" in data

    async def test_default_reflects_db_setting(self, client):
        token = await _admin_token(client)
        h = {"Authorization": f"Bearer {token}"}
        # 透過 admin 設定全域預設模型後，/llm-models 的 default 應反映 DB 值
        await client.put("/api/v1/admin/llm-default-model", headers=h, json={"model": "gpt-4o-mini"})
        r = await client.get("/api/v1/llm-models")
        assert r.status_code == 200
        assert r.json()["default"] == "gpt-4o-mini"

"""Tests for /api/v1/llm-models `default`（Phase 23 / env-only）。

`default` 直接來自 .env 的 settings.default_llm_model。
"""
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestLlmModelsDefault:
    async def test_list_has_models_and_default(self, client):
        r = await client.get("/api/v1/llm-models")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        assert "default" in data

    async def test_default_equals_env_setting(self, client):
        from src.core.config import get_settings
        r = await client.get("/api/v1/llm-models")
        assert r.status_code == 200
        assert r.json()["default"] == get_settings().default_llm_model

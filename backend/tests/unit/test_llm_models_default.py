"""Tests for /api/v1/llm-models `default`（Phase 23 / env-only）。

`default` 直接來自 .env 的 settings.default_llm_model。
"""
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.config import get_settings
from src.main import app


@pytest.fixture
async def client(admin_headers, monkeypatch):
    # 清空供應商金鑰與 Ollama 位址，避免單元測試真的連到外部模型 API
    monkeypatch.setattr("src.api.llm_models.get_settings", lambda: SimpleNamespace(
        anthropic_api_key="", openai_api_key="", ollama_base_url="",
        default_llm_model=get_settings().default_llm_model,
    ))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=admin_headers) as c:
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

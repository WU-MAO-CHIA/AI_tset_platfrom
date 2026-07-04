"""Tests：/api/v1/llm-models 整合本地 Ollama（/api/tags）。

設定 OLLAMA_BASE_URL 後列出 ollama:<name>（provider=ollama, requires_setup=false）；
Ollama 連線失敗/逾時時 Ollama 區塊為空且不影響雲端模型。
"""
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _settings(ollama="http://localhost:11434"):
    return SimpleNamespace(
        anthropic_api_key="sk-ant-api03-REALKEY1234567890",
        openai_api_key="",
        default_llm_model="claude-sonnet-4-6",
        ollama_base_url=ollama,
    )


def _patch_tags(models=None, raise_exc=None):
    async def fake_get(url, **kwargs):
        if raise_exc:
            raise raise_exc
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"models": models or []})
        return resp

    c = MagicMock()
    c.get = AsyncMock(side_effect=fake_get)

    @asynccontextmanager
    async def ctx(*args, **kwargs):
        yield c

    return patch("src.api.llm_models.httpx.AsyncClient", ctx)


class TestLlmModelsOllama:
    async def test_lists_installed_ollama_models(self, client):
        tags = [{"name": "gemma4:e4b"}, {"name": "llama3"}]
        with patch("src.api.llm_models.get_settings", return_value=_settings()), _patch_tags(models=tags):
            r = await client.get("/api/v1/llm-models")
        assert r.status_code == 200
        models = r.json()["models"]
        ollama = [m for m in models if m["provider"] == "ollama"]
        ids = {m["id"] for m in ollama}
        assert "ollama:gemma4:e4b" in ids
        assert "ollama:llama3" in ids
        for m in ollama:
            assert m["requires_setup"] is False

    async def test_ollama_offline_does_not_break_cloud(self, client):
        with patch("src.api.llm_models.get_settings", return_value=_settings()), _patch_tags(
            raise_exc=ConnectionError("refused")
        ):
            r = await client.get("/api/v1/llm-models")
        assert r.status_code == 200
        models = r.json()["models"]
        # Ollama 區塊為空
        assert [m for m in models if m["provider"] == "ollama"] == []
        # 雲端 Claude 仍在
        assert any(m["provider"] == "anthropic" for m in models)

    async def test_no_ollama_base_url_skips_ollama(self, client):
        with patch("src.api.llm_models.get_settings", return_value=_settings(ollama="")):
            r = await client.get("/api/v1/llm-models")
        assert r.status_code == 200
        models = r.json()["models"]
        assert [m for m in models if m["provider"] == "ollama"] == []

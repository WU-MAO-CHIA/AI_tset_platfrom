"""Tests：Anthropic/OpenAI live 模型查詢（排除法過濾 + fallback + 快取）。"""
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api import llm_models


@pytest.fixture(autouse=True)
def _clear_cache():
    llm_models._live_cache.clear()
    yield
    llm_models._live_cache.clear()


def _settings(anthropic="", openai="", ollama=""):
    return SimpleNamespace(
        anthropic_api_key=anthropic,
        openai_api_key=openai,
        default_llm_model="claude-sonnet-4-6",
        ollama_base_url=ollama,
    )


def _patch_http(routes: dict):
    """routes: url 子字串 -> payload dict | Exception。未命中一律 AssertionError。"""
    calls: list[str] = []

    async def fake_get(url, **kwargs):
        calls.append(url)
        for needle, result in routes.items():
            if needle in url:
                if isinstance(result, Exception):
                    raise result
                resp = MagicMock()
                resp.raise_for_status = MagicMock()
                resp.json = MagicMock(return_value=result)
                return resp
        raise AssertionError(f"unexpected url {url}")

    c = MagicMock()
    c.get = AsyncMock(side_effect=fake_get)

    @asynccontextmanager
    async def ctx(*args, **kwargs):
        yield c

    return patch("src.api.llm_models.httpx.AsyncClient", ctx), calls


class TestAnthropicLive:
    async def test_parses_ids_and_display_names(self):
        payload = {"data": [
            {"id": "claude-sonnet-4-5-20250929", "display_name": "Claude Sonnet 4.5"},
            {"id": "claude-haiku-4-5-20251001", "display_name": "Claude Haiku 4.5"},
            {"no-id": True},
        ]}
        p, _ = _patch_http({"api.anthropic.com": payload})
        with p:
            models = await llm_models._fetch_anthropic_models("sk-ant-VALIDKEY1234567890abcdef")
        assert [m["id"] for m in models] == ["claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001"]
        assert models[0]["name"] == "Claude Sonnet 4.5"
        assert all(m["provider"] == "anthropic" and m["requires_setup"] is False for m in models)

    async def test_no_key_returns_empty_without_http(self):
        p, calls = _patch_http({})
        with p:
            assert await llm_models._fetch_anthropic_models("") == []
        assert calls == []

    async def test_auth_failure_returns_empty(self):
        p, _ = _patch_http({"api.anthropic.com": ConnectionError("401")})
        with p:
            assert await llm_models._fetch_anthropic_models("sk-ant-VALIDKEY1234567890abcdef") == []


class TestOpenAILive:
    async def test_filters_non_chat_models(self):
        payload = {"data": [
            {"id": "gpt-4o"},
            {"id": "gpt-4o-mini"},
            {"id": "o4-mini"},
            {"id": "text-embedding-3-small"},
            {"id": "whisper-1"},
            {"id": "tts-1"},
            {"id": "dall-e-3"},
            {"id": "omni-moderation-latest"},
            {"id": "gpt-4o-realtime-preview"},
            {"id": "gpt-4o-transcribe"},
            {"id": "gpt-4o-mini-audio-preview"},
        ]}
        p, _ = _patch_http({"api.openai.com": payload})
        with p:
            models = await llm_models._fetch_openai_models("sk-proj-VALIDKEY1234567890abcdef")
        ids = {m["id"] for m in models}
        assert {"gpt-4o", "gpt-4o-mini", "o4-mini"} <= ids
        assert not any(x in ids for x in (
            "text-embedding-3-small", "whisper-1", "tts-1", "dall-e-3",
            "omni-moderation-latest", "gpt-4o-realtime-preview",
            "gpt-4o-transcribe", "gpt-4o-mini-audio-preview",
        ))
        assert all(m["provider"] == "openai" for m in models)

    async def test_no_key_returns_empty_without_http(self):
        p, calls = _patch_http({})
        with p:
            assert await llm_models._fetch_openai_models("sk-...") == []
        assert calls == []

    async def test_timeout_returns_empty(self):
        p, _ = _patch_http({"api.openai.com": TimeoutError("timed out")})
        with p:
            assert await llm_models._fetch_openai_models("sk-proj-VALIDKEY1234567890abcdef") == []


class TestCache:
    async def test_successful_result_cached(self):
        payload = {"data": [{"id": "claude-sonnet-4-5-20250929", "display_name": "S"}]}
        p, calls = _patch_http({"api.anthropic.com": payload})
        with p:
            first = await llm_models._fetch_anthropic_models("sk-ant-CACHEKEY1234567890abcdef")
            second = await llm_models._fetch_anthropic_models("sk-ant-CACHEKEY1234567890abcdef")
        assert first == second
        assert len(calls) == 1


class TestEndpointMerge:
    async def test_live_preferred_and_missing_key_hidden(self):
        payload_a = {"data": [{"id": "claude-sonnet-4-5-20250929", "display_name": "S"}]}
        payload_o = {"data": [{"id": "gpt-4o"}, {"id": "text-embedding-3-small"}]}
        p, _ = _patch_http({"api.anthropic.com": payload_a, "api.openai.com": payload_o})
        settings = _settings(anthropic="sk-ant-ENDPOINTKEY1234567890ab", openai="sk-proj-ENDPOINTKEY1234567890ab")
        with patch("src.api.llm_models.get_settings", return_value=settings), p:
            res = await llm_models.list_llm_models(db=None)
        ids = {m["id"] for m in res["models"]}
        assert "claude-sonnet-4-5-20250929" in ids
        assert "gpt-4o" in ids
        assert "text-embedding-3-small" not in ids
        assert "default" in res

    async def test_no_keys_hides_cloud_providers(self):
        p, calls = _patch_http({})
        with patch("src.api.llm_models.get_settings", return_value=_settings()), p:
            res = await llm_models.list_llm_models(db=None)
        assert res["models"] == []
        assert calls == []

    async def test_live_failure_falls_back_to_hardcoded(self):
        p, _ = _patch_http({
            "api.anthropic.com": ConnectionError("down"),
            "api.openai.com": ConnectionError("down"),
        })
        settings = _settings(anthropic="sk-ant-FALLBACKKEY1234567890abcd", openai="sk-proj-FALLBACKKEY1234567890abcd")
        with patch("src.api.llm_models.get_settings", return_value=settings), p:
            res = await llm_models.list_llm_models(db=None)
        ids = {m["id"] for m in res["models"]}
        assert {m["id"] for m in llm_models.ANTHROPIC_MODELS} <= ids
        assert {m["id"] for m in llm_models.OPENAI_MODELS} <= ids

"""Unit tests：OllamaProvider（原生 /api/chat，stream:false）。

驗證 complete / complete_with_messages 正確解析 message.content；
模型名去除 `ollama:` 前綴後送出；get_provider 三方路由。
"""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.llm_provider import (
    AnthropicProvider,
    OllamaProvider,
    OpenAIProvider,
    get_provider,
)


def _patch_async_client(captured: dict, content: str = "你好，我是本地模型"):
    """patch src.core.llm_provider.httpx.AsyncClient，攔截 POST 並回傳模擬回應。"""

    async def fake_post(url, json=None, **kwargs):
        captured["url"] = url
        captured["json"] = json
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"message": {"role": "assistant", "content": content}})
        return resp

    client = MagicMock()
    client.post = AsyncMock(side_effect=fake_post)

    @asynccontextmanager
    async def fake_client_ctx(*args, **kwargs):
        yield client

    return patch("src.core.llm_provider.httpx.AsyncClient", fake_client_ctx)


class TestOllamaProvider:
    async def test_complete_parses_message_content(self):
        captured: dict = {}
        with _patch_async_client(captured, content="HELLO"):
            provider = OllamaProvider(base_url="http://localhost:11434", model="ollama:gemma4:e4b")
            out = await provider.complete("hi")
        assert out == "HELLO"
        # POST 到 /api/chat、stream:false
        assert captured["url"].endswith("/api/chat")
        assert captured["json"]["stream"] is False
        # 模型名去除 ollama: 前綴
        assert captured["json"]["model"] == "gemma4:e4b"
        assert captured["json"]["messages"][-1]["content"] == "hi"

    async def test_complete_with_messages_includes_system(self):
        captured: dict = {}
        with _patch_async_client(captured, content="OK"):
            provider = OllamaProvider(base_url="http://localhost:11434", model="gemma4:e4b")
            out = await provider.complete_with_messages(
                [{"role": "user", "content": "問題"}], system="你是助手"
            )
        assert out == "OK"
        roles = [m["role"] for m in captured["json"]["messages"]]
        assert roles[0] == "system"
        assert captured["json"]["messages"][0]["content"] == "你是助手"

    async def test_model_name_without_prefix_kept(self):
        captured: dict = {}
        with _patch_async_client(captured):
            provider = OllamaProvider(base_url="http://localhost:11434", model="llama3")
            await provider.complete("x")
        assert captured["json"]["model"] == "llama3"


class TestGetProviderRouting:
    def test_ollama_prefix_routes_to_ollama(self):
        settings = MagicMock(ollama_base_url="http://localhost:11434")
        provider = get_provider("ollama:gemma4:e4b", settings)
        assert isinstance(provider, OllamaProvider)
        assert provider.model == "gemma4:e4b"

    def test_claude_routes_to_anthropic(self):
        settings = MagicMock(anthropic_api_key="sk-ant-xxx")
        assert isinstance(get_provider("claude-sonnet-4-6", settings), AnthropicProvider)

    def test_other_routes_to_openai(self):
        settings = MagicMock(openai_api_key="sk-xxx")
        assert isinstance(get_provider("gpt-4o", settings), OpenAIProvider)

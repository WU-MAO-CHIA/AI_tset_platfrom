"""Unit tests：AnthropicProvider 的 prompt caching。

多輪對話用兩個快取點：system 固定開頭的結尾（明確標記）與對話尾端（request 層級自動快取）。
固定開頭之後每次可能不同的內容不得落在快取點之前，否則每次都付寫入費卻讀不到。
"""
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.llm_provider import AnthropicProvider
from src.services.ai_service import _CHAT_SYSTEM_PROMPT, AIService

EPHEMERAL = {"type": "ephemeral"}


@pytest.fixture
def client():
    message = SimpleNamespace(
        content=[SimpleNamespace(text="ok")],
        usage=SimpleNamespace(input_tokens=12, cache_creation_input_tokens=0,
                              cache_read_input_tokens=1500, output_tokens=5),
    )
    fake = MagicMock()
    fake.messages.create = AsyncMock(return_value=message)
    return fake


@pytest.fixture
def provider(client):
    p = AnthropicProvider(api_key="sk-ant-test", model="claude-sonnet-4-6")
    with patch.object(p, "_get_client", return_value=client):
        yield p


def _sent(client) -> dict:
    return client.messages.create.call_args.kwargs


class TestConversationCaching:
    async def test_cache_point_ends_at_stable_prefix(self, provider, client):
        await provider.complete_with_messages(
            [{"role": "user", "content": "hi"}], system="RULES\n\nCONTEXT", cache_prefix="RULES"
        )
        assert _sent(client)["system"] == [
            {"type": "text", "text": "RULES", "cache_control": EPHEMERAL},
            {"type": "text", "text": "\n\nCONTEXT"},
        ]

    async def test_conversation_tail_uses_automatic_caching(self, provider, client):
        await provider.complete_with_messages([{"role": "user", "content": "hi"}], system="RULES")
        assert _sent(client)["cache_control"] == EPHEMERAL

    async def test_whole_system_cached_when_no_prefix_given(self, provider, client):
        await provider.complete_with_messages([{"role": "user", "content": "hi"}], system="STATIC")
        assert _sent(client)["system"] == [{"type": "text", "text": "STATIC", "cache_control": EPHEMERAL}]

    async def test_mismatched_prefix_sets_no_system_cache_point(self, provider, client):
        await provider.complete_with_messages(
            [{"role": "user", "content": "hi"}], system="A then B", cache_prefix="X"
        )
        assert _sent(client)["system"] == [{"type": "text", "text": "A then B"}]

    async def test_whitespace_only_rest_is_not_sent_as_empty_block(self, provider, client):
        await provider.complete_with_messages(
            [{"role": "user", "content": "hi"}], system="RULES\n", cache_prefix="RULES"
        )
        assert _sent(client)["system"] == [{"type": "text", "text": "RULES", "cache_control": EPHEMERAL}]

    async def test_no_system_still_caches_conversation(self, provider, client):
        await provider.complete_with_messages([{"role": "user", "content": "hi"}])
        assert "system" not in _sent(client)
        assert _sent(client)["cache_control"] == EPHEMERAL

    async def test_cache_usage_is_logged(self, provider, caplog):
        caplog.set_level(logging.INFO, logger="src.core.llm_provider")
        await provider.complete_with_messages([{"role": "user", "content": "hi"}], system="RULES")
        assert "cache_read=1500" in caplog.text


class TestSingleShotPromptsNotCached:
    async def test_complete_sends_no_cache_control(self, provider, client):
        # 單次 prompt 中段夾著每次不同的測試步驟，設快取點只會多付寫入費
        await provider.complete("prompt")
        assert "cache_control" not in _sent(client)


class TestChatPassesStablePrefix:
    async def test_chat_marks_rules_cacheable_and_keeps_rf_code_after_cache_point(self):
        provider = MagicMock()
        provider.complete_with_messages = AsyncMock(return_value="---MESSAGE---\nok\n---RF_CODE---\nx\n---END---")
        await AIService(provider=provider).chat_and_generate_rf(
            messages=[], user_message="hi", llm_model="claude-sonnet-4-6",
            rf_code="*** Test Cases ***\nT\n    Log    x", rf_context_mode="full",
        )
        sent = provider.complete_with_messages.call_args.kwargs
        assert sent["cache_prefix"] == _CHAT_SYSTEM_PROMPT
        assert sent["system"].startswith(_CHAT_SYSTEM_PROMPT)
        assert "---UPLOADED RF CODE---" in sent["system"][len(_CHAT_SYSTEM_PROMPT):]

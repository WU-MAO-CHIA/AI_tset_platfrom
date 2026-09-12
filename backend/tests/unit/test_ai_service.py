"""Unit tests for AIService.
RED: Tests should fail until AIService is implemented.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.complete = AsyncMock(return_value="1. Open page\n2. Enter credentials\n3. Click login\n4. Verify success")
    provider.complete_with_vision = AsyncMock(return_value="1. Open page\n2. Enter credentials\n3. Click login\n4. Verify success")
    return provider


@pytest.fixture
def ai_service(mock_provider):
    from src.services.ai_service import AIService
    return AIService(provider=mock_provider)


class TestAIServiceCompleteSteps:
    async def test_complete_steps_calls_provider(self, ai_service, mock_provider):
        result = await ai_service.complete_steps(
            partial_steps="1. Open login page",
            description="Login flow test",
        )
        assert "login" in result.lower() or "open" in result.lower()
        mock_provider.complete.assert_called_once()

    async def test_complete_steps_with_media_uses_vision(self, ai_service, mock_provider):
        media_list = [MagicMock(attachment_type="image", file_path="/tmp/screenshot.png")]
        result = await ai_service.complete_steps(
            partial_steps="1. Open login page",
            description="Login flow",
            media_attachments=media_list,
        )
        assert result is not None
        mock_provider.complete_with_vision.assert_called_once()
        mock_provider.complete.assert_not_called()

    async def test_complete_steps_without_media_uses_text_complete(self, ai_service, mock_provider):
        result = await ai_service.complete_steps(
            partial_steps="1. Open login page",
            description="Login flow",
            media_attachments=[],
        )
        assert result is not None
        mock_provider.complete.assert_called_once()
        mock_provider.complete_with_vision.assert_not_called()


class TestProviderSwitch:
    async def test_different_providers_can_be_injected(self, mock_provider):
        from src.services.ai_service import AIService

        alt_provider = MagicMock()
        alt_provider.complete = AsyncMock(return_value="alt response")
        alt_provider.complete_with_vision = AsyncMock(return_value="alt vision response")

        service = AIService(provider=alt_provider)
        result = await service.complete_steps("partial steps", "description")
        alt_provider.complete.assert_called_once()
        assert result == "alt response"


class TestAIServiceChatAndGenerateRF:
    """Tests for chat_and_generate_rf with RF code context injection."""

    async def test_chat_full_mode_injects_rf_code(self, ai_service, mock_provider):
        """Full mode: injects full RF code into system prompt."""
        mock_provider.complete_with_messages = AsyncMock(return_value="這段代碼登入功能\n---RF_CODE---\n*** Test ***\nLog    Done")

        result = await ai_service.chat_and_generate_rf(
            messages=[{"role": "user", "content": "測試登入"}],
            user_message="這段代碼有什麼功能？",
            llm_model="claude-sonnet-4-6",
            rf_code="*** Test Cases ***\n登入測試\n    Log    Hello",
            rf_context_mode="full",
        )

        assert "assistant_message" in result
        assert "rf_code" in result
        # Verify the provider was called with RF code in system prompt
        call_args = mock_provider.complete_with_messages.call_args
        assert call_args is not None
        # The system prompt should contain the RF code block
        system_prompt = call_args.kwargs.get("system", "")
        assert "---UPLOADED RF CODE---" in system_prompt
        assert "*** Test Cases ***" in system_prompt
        assert "登入測試" in system_prompt

    async def test_chat_summary_mode_injects_summary(self, ai_service, mock_provider):
        """Summary mode: injects RF code summary instead of full code."""
        mock_provider.complete_with_messages = AsyncMock(return_value="代碼摘要：登入測試")

        result = await ai_service.chat_and_generate_rf(
            messages=[{"role": "user", "content": "測試登入"}],
            user_message="簡述這段代碼",
            llm_model="claude-sonnet-4-6",
            rf_code="*** Settings ***\nLibrary    Browser\n\n*** Test Cases ***\n登入測試\n    Log    Hello\n    Click    button\n    Wait    2s",
            rf_context_mode="summary",
        )

        assert "assistant_message" in result
        # Verify provider was called with summary (not full code)
        call_args = mock_provider.complete_with_messages.call_args
        system_prompt = call_args.kwargs.get("system", "")
        assert "---UPLOADED RF CODE (SUMMARY)---" in system_prompt
        # Summary should be shorter than full code
        assert len(system_prompt) < 2000  # summary is truncated

    async def test_chat_none_mode_skips_rf_context(self, ai_service, mock_provider):
        """None mode: no RF code injected even when rf_code provided."""
        mock_provider.complete_with_messages = AsyncMock(return_value="一般回應")

        result = await ai_service.chat_and_generate_rf(
            messages=[{"role": "user", "content": "測試"}],
            user_message="你好",
            llm_model="claude-sonnet-4-6",
            rf_code="*** Test Cases ***\n登入測試\n    Log    Hello",
            rf_context_mode="none",
        )

        call_args = mock_provider.complete_with_messages.call_args
        system_prompt = call_args.kwargs.get("system", "")
        assert "---UPLOADED RF CODE---" not in system_prompt

    async def test_chat_no_rf_code_works_normally(self, ai_service, mock_provider):
        """Backward compatibility: works without RF code."""
        mock_provider.complete_with_messages = AsyncMock(return_value="一般回應")

        result = await ai_service.chat_and_generate_rf(
            messages=[{"role": "user", "content": "測試"}],
            user_message="你好",
            llm_model="claude-sonnet-4-6",
            rf_code=None,
            rf_context_mode="full",
        )

        call_args = mock_provider.complete_with_messages.call_args
        system_prompt = call_args.kwargs.get("system", "")
        assert "---UPLOADED RF CODE---" not in system_prompt

    async def test_chat_empty_rf_code_skips_context(self, ai_service, mock_provider):
        """Empty RF code string should skip context injection."""
        mock_provider.complete_with_messages = AsyncMock(return_value="一般回應")

        result = await ai_service.chat_and_generate_rf(
            messages=[{"role": "user", "content": "測試"}],
            user_message="你好",
            llm_model="claude-sonnet-4-6",
            rf_code="",
            rf_context_mode="full",
        )

        call_args = mock_provider.complete_with_messages.call_args
        system_prompt = call_args.kwargs.get("system", "")
        assert "---UPLOADED RF CODE---" not in system_prompt

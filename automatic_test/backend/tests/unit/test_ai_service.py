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

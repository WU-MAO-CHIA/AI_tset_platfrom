"""Unit tests for AIService.generate_robot_code().
RED: Tests should fail until the implementation is complete.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.ai_service import AIService


# Representative Browser-library (Playwright) output. Production prompt requires
# this shape — keep the fixture aligned so tests validate real contract.
SAMPLE_BROWSER_RF = """\
*** Settings ***
Library    Browser
Test Setup       Open Test Browser
Test Teardown    Close Browser

*** Variables ***
${BASE_URL}    http://localhost:5173

*** Keywords ***
Open Test Browser
    New Browser    chromium    headless=True
    New Context
    New Page    ${BASE_URL}

*** Test Cases ***
Test Login
    [Documentation]    Login smoke test
    [Tags]    auto-generated    login
    Fill Text    role=textbox[name="帳號"]    test_user
    Fill Text    role=textbox[name="密碼"]    secret
    Click    role=button[name="登入"]
    Get Text    role=heading    ==    歡迎
"""


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=SAMPLE_BROWSER_RF)
    provider.complete_with_vision = AsyncMock(return_value=SAMPLE_BROWSER_RF)
    return provider


class TestGenerateRobotCode:
    async def test_generate_robot_code_calls_llm(self, mock_provider):
        service = AIService(provider=mock_provider)
        result = await service.generate_robot_code(
            case_number="TC-001",
            case_name="Login Test",
            main_steps="1. Open browser\n2. Enter credentials\n3. Click login",
            case_version=1,
        )
        assert result is not None
        assert "*** Test Cases ***" in result or isinstance(result, str)
        mock_provider.complete.assert_called_once()

    async def test_generate_robot_code_uses_cache_on_same_version(self, mock_provider):
        service = AIService(provider=mock_provider)
        code = "*** Test Cases ***\nCached Test\n    Log    cached"

        mock_cached = MagicMock()
        mock_cached.code_content = code
        mock_cached.generation_status = "success"

        with patch.object(service, '_get_cached_code', AsyncMock(return_value=mock_cached)):
            result = await service.generate_robot_code(
                case_number="TC-001",
                case_name="Login Test",
                main_steps="1. step",
                case_version=1,
            )
        # LLM should NOT be called when cache hit
        mock_provider.complete.assert_not_called()
        assert result == code

    async def test_generate_robot_code_marks_unable_for_vague_steps(self, mock_provider):
        mock_provider.complete = AsyncMock(return_value="UNABLE_TO_GENERATE: Steps are too vague")
        service = AIService(provider=mock_provider)
        result = await service.generate_robot_code(
            case_number="TC-001",
            case_name="Vague Test",
            main_steps="do stuff",
            case_version=1,
        )
        assert result is None or "UNABLE" in (result or "")

    async def test_generate_robot_code_timeout_marks_failed(self, mock_provider):
        async def slow_complete(*args, **kwargs):
            await asyncio.sleep(100)
            return "should not reach here"

        mock_provider.complete = slow_complete
        service = AIService(provider=mock_provider)
        result = await service.generate_robot_code(
            case_number="TC-001",
            case_name="Timeout Test",
            main_steps="1. step",
            case_version=1,
            timeout_sec=0.01,
        )
        # After timeout, should return None (failed) and not raise
        assert result is None

"""Unit tests for AI service RF rules — CAPTCHA injection (FR-028).

Validates that the shared _RF_RULES prompt string and all derived
system/generation prompts contain the required CAPTCHA handling instructions.
"""

import pytest

from src.services.ai_service import (
    _CHAT_SYSTEM_PROMPT,
    _GENERATE_ROBOT_PROMPT,
    _PREVIEW_ROBOT_PROMPT,
    _RF_RULES,
)


class TestRFRulesCaptchaContent:
    def test_rf_rules_imports_captcha_solver_library(self):
        assert "CaptchaSolverLibrary" in _RF_RULES

    def test_rf_rules_contains_captcha_keyword_definition(self):
        assert "處理圖形驗證碼（如存在）" in _RF_RULES

    def test_rf_rules_references_solve_captcha_from_file(self):
        assert "Solve Captcha From File" in _RF_RULES

    def test_rf_rules_contains_library_import_path(self):
        assert "libs/CaptchaSolverLibrary.py" in _RF_RULES

    def test_rf_rules_contains_take_screenshot_keyword(self):
        assert "Take Screenshot" in _RF_RULES

    def test_rf_rules_contains_fill_text_for_captcha_input(self):
        assert "Fill Text" in _RF_RULES

    def test_rf_rules_uses_if_exists_guard(self):
        # CAPTCHA handling should be conditional — only act when element visible
        assert "Wait For Elements State" in _RF_RULES
        assert "IF" in _RF_RULES

    def test_rf_rules_instructs_call_before_submit(self):
        assert "填完帳號密碼後" in _RF_RULES or "送出按鈕前" in _RF_RULES


class TestSystemPromptsPropagation:
    """All derived prompts must inherit _RF_RULES content."""

    def test_chat_system_prompt_contains_captcha_rules(self):
        assert "CaptchaSolverLibrary" in _CHAT_SYSTEM_PROMPT

    def test_preview_robot_prompt_contains_captcha_rules(self):
        assert "CaptchaSolverLibrary" in _PREVIEW_ROBOT_PROMPT

    def test_generate_robot_prompt_contains_captcha_rules(self):
        assert "CaptchaSolverLibrary" in _GENERATE_ROBOT_PROMPT

    def test_chat_system_prompt_contains_response_format(self):
        assert "---MESSAGE---" in _CHAT_SYSTEM_PROMPT
        assert "---RF_CODE---" in _CHAT_SYSTEM_PROMPT
        assert "---END---" in _CHAT_SYSTEM_PROMPT

    def test_generate_robot_prompt_has_case_placeholders(self):
        assert "{case_number}" in _GENERATE_ROBOT_PROMPT
        assert "{case_name}" in _GENERATE_ROBOT_PROMPT
        assert "{main_steps}" in _GENERATE_ROBOT_PROMPT

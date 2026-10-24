"""Unit tests for AI service RF rules — CAPTCHA injection (FR-028).

Validates that the shared _RF_RULES prompt string and all derived
system/generation prompts contain the required CAPTCHA handling instructions.
"""

import io

import pytest

from src.services.ai_service import (
    _BROWSER_KEYWORDS,
    _CHAT_SYSTEM_PROMPT,
    _GENERATE_ROBOT_PROMPT,
    _PREVIEW_ROBOT_PROMPT,
    _RF_RULES,
    _SCRIPT_SKELETON,
    _SELENIUM_ONLY_KEYWORDS,
    _render_prompt,
)


def _rendered_prompts() -> dict[str, str]:
    """LLM 實際收到的 prompt 文字（chat 直接送出；preview / generate 填入 placeholder 後送出）。"""
    return {
        "chat": _CHAT_SYSTEM_PROMPT,
        "preview": _render_prompt(_PREVIEW_ROBOT_PROMPT, main_steps="1. 開啟登入頁"),
        "generate": _render_prompt(
            _GENERATE_ROBOT_PROMPT, case_number="auth-001", case_name="登入", main_steps="1. 開啟登入頁"
        ),
    }


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


class TestRenderedPromptSyntax:
    @pytest.mark.parametrize("name", ["chat", "preview", "generate"])
    def test_rf_variables_use_single_braces(self, name):
        text = _rendered_prompts()[name]
        assert "${CURDIR}" in text and "${captcha_text}" in text
        # ${{...}} 在 RF 7 是 Python 運算式語法，LLM 照抄會產生錯誤的腳本
        assert "${{" not in text and "}}" not in text

    @pytest.mark.parametrize("name", ["preview", "generate"])
    def test_placeholders_are_filled(self, name):
        text = _rendered_prompts()[name]
        assert "1. 開啟登入頁" in text
        for placeholder in ("{main_steps}", "{case_number}", "{case_name}"):
            assert placeholder not in text

    def test_user_text_with_braces_is_inserted_verbatim(self):
        steps = "1. 輸入 ${USERNAME}\n2. 備註 {case_name} {0}"
        text = _render_prompt(_GENERATE_ROBOT_PROMPT, case_number="c-1", case_name="N", main_steps=steps)
        assert steps in text

    @pytest.mark.parametrize("name", ["chat", "preview", "generate"])
    def test_no_platform_localhost_default(self, name):
        assert "localhost:5173" not in _rendered_prompts()[name]

    @pytest.mark.parametrize("name", ["chat", "preview", "generate"])
    def test_forbids_markdown_fences(self, name):
        assert "不要加 Markdown 程式碼框" in _rendered_prompts()[name]


class TestKeywordReference:
    """prompt 列出的 keyword 必須與實際安裝的 Browser library 一致。"""

    @pytest.fixture(scope="class")
    def browser_keywords(self):
        from robot.libdocpkg import LibraryDocumentation

        return {kw.name for kw in LibraryDocumentation("Browser").keywords}

    def test_listed_keywords_exist_in_browser_library(self, browser_keywords):
        assert set(_BROWSER_KEYWORDS) - browser_keywords == set()

    def test_selenium_only_keywords_absent_from_browser_library(self, browser_keywords):
        assert set(_SELENIUM_ONLY_KEYWORDS) & browser_keywords == set()

    def test_rules_list_every_keyword(self):
        for keyword in _BROWSER_KEYWORDS + _SELENIUM_ONLY_KEYWORDS:
            assert keyword in _RF_RULES

    def test_skeleton_examples_pass_dry_run(self, tmp_path):
        from robot import run

        lines = []
        for line in _SCRIPT_SKELETON.splitlines():
            if "依測試步驟" in line:
                continue
            lines.append(line.replace("    # ", "    ", 1))
        script = "\n".join(lines).replace("<TEST_NAME>", "Example").replace(
            "<DOCUMENTATION>", "doc").replace("<TAGS>", "example")
        robot_file = tmp_path / "skeleton.robot"
        robot_file.write_text(script, encoding="utf-8")
        # outputdir 指向 tmp_path：Browser library 會把 playwright-log.txt 寫在輸出目錄
        failed = run(str(robot_file), dryrun=True, outputdir=str(tmp_path), output="NONE", report="NONE",
                     log="NONE", stdout=io.StringIO(), stderr=io.StringIO())
        assert failed == 0


class TestPrecisionRules:
    def test_forbids_inventing_locators(self):
        assert "禁止編造" in _RF_RULES
        assert "ContentPlaceHolder1_" in _RF_RULES  # 實際發生過的編造 id 樣式
        assert "# TODO: locator 未驗證" in _RF_RULES

    def test_secret_fields_use_fill_secret_dollar_syntax(self):
        # Browser library 的 Fill Secret 需要 $NAME；${NAME} 會執行失敗
        assert "Fill Secret    <locator>    $PASSWORD" in _RF_RULES

    def test_expected_results_become_assertions(self):
        assert "預期結果" in _RF_RULES
        assert "Get Url    *=" in _RF_RULES and "not contains" in _RF_RULES

    def test_chat_asks_to_report_unverified_locators(self):
        assert "TODO" in _CHAT_SYSTEM_PROMPT.split("---MESSAGE---", 1)[1]

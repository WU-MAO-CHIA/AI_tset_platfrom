"""Unit tests for AppSettingService — env-only 遮罩 + 預設模型（Phase 23 / env-only）。

金鑰與預設模型一律來自 .env；後台僅唯讀遮罩顯示。
"""
from types import SimpleNamespace
from unittest.mock import patch

from src.services.app_setting_service import AppSettingService, _mask


class TestMask:
    def test_long_key_keeps_prefix_and_last4(self):
        masked = _mask("sk-ant-api03-abcdefghIJKLdF3a")
        assert masked.startswith("sk-ant-")        # 前 7 字元
        assert "****" in masked
        assert masked.endswith("dF3a")             # 末 4 碼
        assert "abcdefghIJKL" not in masked        # 中段不外洩

    def test_short_key_fully_masked(self):
        assert _mask("short") == "****"
        assert _mask("sk-12345678") == "****"      # len 11 < 12

    def test_empty_or_none_returns_empty(self):
        assert _mask("") == ""
        assert _mask(None) == ""


def _settings(anthropic="", openai="", default="claude-sonnet-4-6", ollama=""):
    return SimpleNamespace(
        anthropic_api_key=anthropic,
        openai_api_key=openai,
        default_llm_model=default,
        ollama_base_url=ollama,
    )


class TestGetLlmKeysFromEnv:
    def test_configured_key_masked_not_plaintext(self):
        full = "sk-ant-api03-SECRETvalue1234"
        with patch("src.services.app_setting_service.get_settings", return_value=_settings(anthropic=full)):
            result = AppSettingService().get_llm_keys()
        assert result["anthropic_key_set"] is True
        assert result["anthropic_key_masked"] != full
        assert full not in str(result)             # 完整明文絕不可出現
        assert result["anthropic_key_masked"].endswith("1234")
        assert result["openai_key_set"] is False
        assert result["openai_key_masked"] == ""

    def test_placeholder_key_treated_as_unset(self):
        with patch("src.services.app_setting_service.get_settings", return_value=_settings(openai="sk-...")):
            result = AppSettingService().get_llm_keys()
        assert result["openai_key_set"] is False
        assert result["openai_key_masked"] == ""


class TestDefaultModelFromEnv:
    def test_returns_env_default(self):
        with patch("src.services.app_setting_service.get_settings", return_value=_settings(default="gpt-4o")):
            assert AppSettingService().get_default_model() == "gpt-4o"

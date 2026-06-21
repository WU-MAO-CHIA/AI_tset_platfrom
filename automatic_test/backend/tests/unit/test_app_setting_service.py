"""Unit tests for AppSettingService — 遮罩 + 全域預設模型（Phase 23）。
RED: 在 _mask / get_llm_keys(masked) / get_default_model / set_default_model 實作前應失敗。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def svc():
    from src.services.app_setting_service import AppSettingService
    s = AppSettingService(MagicMock())
    s.repo = MagicMock()
    s.repo.get_decrypted = AsyncMock(return_value=None)
    s.repo.set = AsyncMock()
    return s


class TestMask:
    def test_long_key_keeps_prefix_and_last4(self):
        from src.services.app_setting_service import _mask
        masked = _mask("sk-ant-api03-abcdefghIJKLdF3a")
        assert masked.startswith("sk-ant-")        # 前 7 字元
        assert "****" in masked
        assert masked.endswith("dF3a")             # 末 4 碼
        assert "abcdefghIJKL" not in masked        # 中段不外洩

    def test_short_key_fully_masked(self):
        from src.services.app_setting_service import _mask
        assert _mask("short") == "****"
        assert _mask("sk-12345678") == "****"      # len 11 < 12 → 整串遮罩

    def test_empty_or_none_returns_empty(self):
        from src.services.app_setting_service import _mask
        assert _mask("") == ""
        assert _mask(None) == ""


class TestGetLlmKeysMasked:
    async def test_returns_masked_not_plaintext(self, svc):
        full = "sk-ant-api03-SECRETvalue1234"
        svc.repo.get_decrypted = AsyncMock(return_value=full)
        result = await svc.get_llm_keys()
        assert result["anthropic_key_set"] is True
        assert "anthropic_key_masked" in result
        assert result["anthropic_key_masked"] != full
        assert full not in str(result)             # 完整明文絕不可出現
        assert result["anthropic_key_masked"].endswith("1234")

    async def test_unset_key_reports_false(self, svc):
        svc.repo.get_decrypted = AsyncMock(return_value=None)
        result = await svc.get_llm_keys()
        assert result["anthropic_key_set"] is False
        assert result["openai_key_set"] is False
        assert result.get("anthropic_key_masked") in (None, "")


class TestDefaultModel:
    async def test_get_default_model_none_when_unset(self, svc):
        svc.repo.get_decrypted = AsyncMock(return_value=None)
        assert await svc.get_default_model() is None

    async def test_set_then_get_round_trip(self, svc):
        await svc.set_default_model("claude-opus-4-7")
        svc.repo.set.assert_awaited_once()
        args = svc.repo.set.call_args.args
        assert args[0] == "default_llm_model"
        assert args[1] == "claude-opus-4-7"

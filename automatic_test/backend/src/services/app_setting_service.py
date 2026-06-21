"""LLM 設定一律來自環境設定（.env），唯讀。

後台 /admin 僅遮罩顯示，不寫入任何儲存；變更金鑰或預設模型需修改 .env 並重啟服務。
"""
from src.core.config import get_settings


def _mask(key: str | None) -> str:
    """遮罩 API 金鑰：前 7 字元 + ****… + 末 4 碼；長度 < 12 整串遮罩；空值回空字串。"""
    if not key:
        return ""
    if len(key) < 12:
        return "****"
    return f"{key[:7]}****…{key[-4:]}"


def _is_configured(key: str | None) -> bool:
    """env 金鑰是否視為已設定（排除空值與佔位字串如 'sk-...'）。"""
    return bool(key) and len(key) >= 20 and "..." not in key


class AppSettingService:
    def __init__(self, db=None):
        # 設定來源為 .env，無需資料庫；保留參數以相容既有呼叫端
        self._db = db

    def get_llm_keys(self) -> dict:
        s = get_settings()
        result = {}
        for provider, env_key in (("anthropic", s.anthropic_api_key), ("openai", s.openai_api_key)):
            configured = _is_configured(env_key)
            result[f"{provider}_key_set"] = configured
            result[f"{provider}_key_masked"] = _mask(env_key) if configured else ""
        return result

    def get_default_model(self) -> str:
        return get_settings().default_llm_model

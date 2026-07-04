"""LLM 設定：混合式來源。

- 金鑰（機密）與 OLLAMA_BASE_URL：一律來自環境設定（.env），唯讀、不落地 DB。
- 「目前啟用模型」（非機密指標）：讀寫 DB（加密 app_settings），後台可即時切換。

後台 /admin 對金鑰僅遮罩顯示；變更金鑰需修改 .env 並重啟服務。
"""
from src.core.config import get_settings
from src.repositories.app_setting_repo import AppSettingRepository

ACTIVE_MODEL_KEY = "active_llm_model"


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
        # 金鑰／連線讀 .env；啟用模型讀寫 DB（需 db session）
        self._db = db

    def get_llm_keys(self) -> dict:
        s = get_settings()
        result = {}
        for provider, env_key in (("anthropic", s.anthropic_api_key), ("openai", s.openai_api_key)):
            configured = _is_configured(env_key)
            result[f"{provider}_key_set"] = configured
            result[f"{provider}_key_masked"] = _mask(env_key) if configured else ""
        # 本地 Ollama 連線狀態（非機密，直接帶出 base_url）
        result["ollama_base_url"] = s.ollama_base_url or ""
        result["ollama_configured"] = bool(s.ollama_base_url)
        return result

    def get_default_model(self) -> str:
        return get_settings().default_llm_model

    async def get_active_model(self) -> str:
        """目前啟用模型：DB 優先，無則 fallback .env DEFAULT_LLM_MODEL。"""
        if self._db is not None:
            stored = await AppSettingRepository(self._db).get_decrypted(ACTIVE_MODEL_KEY)
            if stored:
                return stored
        return get_settings().default_llm_model

    async def set_active_model(self, model_id: str) -> None:
        """設定目前啟用模型（沿用既有加密欄，無 migration）。"""
        if self._db is None:
            raise RuntimeError("set_active_model 需要資料庫 session")
        await AppSettingRepository(self._db).set(ACTIVE_MODEL_KEY, model_id)

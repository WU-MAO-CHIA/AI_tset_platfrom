import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.app_setting_repo import AppSettingRepository

logger = logging.getLogger(__name__)

_PROVIDER_KEYS = {
    "anthropic": "llm_key_anthropic",
    "openai": "llm_key_openai",
}

_DEFAULT_MODEL_KEY = "default_llm_model"


def _mask(key: str | None) -> str:
    """遮罩 API 金鑰：前 7 字元 + ****… + 末 4 碼；長度 < 12 整串遮罩；空值回空字串。

    嚴禁回傳完整明文（FR-027 / FR-007）。
    """
    if not key:
        return ""
    if len(key) < 12:
        return "****"
    return f"{key[:7]}****…{key[-4:]}"


class AppSettingService:
    def __init__(self, db: AsyncSession):
        self.repo = AppSettingRepository(db)

    async def get_llm_keys(self) -> dict:
        results = {}
        for provider, db_key in _PROVIDER_KEYS.items():
            plain = await self.repo.get_decrypted(db_key)
            results[f"{provider}_key_set"] = bool(plain)
            results[f"{provider}_key_masked"] = _mask(plain)
        return results

    async def set_llm_key(self, provider: str, key: str):
        db_key = _PROVIDER_KEYS.get(provider)
        if not db_key:
            raise ValueError(f"Unknown provider: {provider}")
        await self.repo.set(db_key, key)

    async def get_decrypted_key(self, provider: str) -> str | None:
        db_key = _PROVIDER_KEYS.get(provider)
        if not db_key:
            return None
        return await self.repo.get_decrypted(db_key)

    async def get_default_model(self) -> str | None:
        """全域預設 LLM 模型（持久化於 app_setting）；未設定回 None。"""
        return await self.repo.get_decrypted(_DEFAULT_MODEL_KEY)

    async def set_default_model(self, model_id: str):
        await self.repo.set(_DEFAULT_MODEL_KEY, model_id)
        logger.info("Global default LLM model updated to %s", model_id)

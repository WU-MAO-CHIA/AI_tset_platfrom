from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.app_setting_repo import AppSettingRepository

_PROVIDER_KEYS = {
    "anthropic": "llm_key_anthropic",
    "openai": "llm_key_openai",
}


class AppSettingService:
    def __init__(self, db: AsyncSession):
        self.repo = AppSettingRepository(db)

    async def get_llm_keys(self) -> dict:
        results = {}
        for provider, db_key in _PROVIDER_KEYS.items():
            record = await self.repo.get(db_key)
            results[f"{provider}_key_set"] = bool(record and record.encrypted_value)
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

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.models.app_setting import AppSetting

settings = get_settings()


def _get_fernet() -> Fernet:
    raw = settings.jwt_secret_key.encode()
    key = base64.urlsafe_b64encode(raw.ljust(32)[:32])
    return Fernet(key)


class AppSettingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> Optional[AppSetting]:
        result = await self.session.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        return result.scalar_one_or_none()

    async def get_decrypted(self, key: str) -> Optional[str]:
        record = await self.get(key)
        if not record or not record.encrypted_value:
            return None
        try:
            fernet = _get_fernet()
            return fernet.decrypt(record.encrypted_value.encode()).decode()
        except Exception:
            return None

    async def set(self, key: str, value: str) -> AppSetting:
        fernet = _get_fernet()
        encrypted = fernet.encrypt(value.encode()).decode()
        record = await self.get(key)
        if record:
            record.encrypted_value = encrypted
        else:
            record = AppSetting(key=key, encrypted_value=encrypted)
            self.session.add(record)
        await self.session.flush()
        return record

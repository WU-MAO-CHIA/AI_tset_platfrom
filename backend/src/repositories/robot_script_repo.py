from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.robot_script import RobotScript
from src.models.base import generate_uuid
from .base import BaseRepository


class RobotScriptRepository(BaseRepository[RobotScript]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, id: str) -> Optional[RobotScript]:
        result = await self.session.execute(select(RobotScript).where(RobotScript.id == id))
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> RobotScript:
        record = RobotScript(id=generate_uuid(), **kwargs)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def update(self, id: str, **kwargs) -> Optional[RobotScript]:
        record = await self.get(id)
        if record is None:
            return None
        for key, value in kwargs.items():
            setattr(record, key, value)
        await self.session.flush()
        return record

    async def delete(self, id: str) -> bool:
        record = await self.get(id)
        if record is None:
            return False
        await self.session.delete(record)
        await self.session.flush()
        return True

    async def get_by_case_id(self, test_case_id: str) -> Optional[RobotScript]:
        result = await self.session.execute(
            select(RobotScript).where(RobotScript.test_case_id == test_case_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, test_case_id: str, rf_code: str, saved_by: Optional[str] = None) -> RobotScript:
        existing = await self.get_by_case_id(test_case_id)
        if existing:
            existing.rf_code = rf_code
            if saved_by is not None:
                existing.saved_by = saved_by
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        record = RobotScript(
            id=generate_uuid(),
            test_case_id=test_case_id,
            rf_code=rf_code,
            saved_by=saved_by,
        )
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

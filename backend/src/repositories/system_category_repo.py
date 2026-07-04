from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.system_category import SystemCategory
from src.models.test_case import TestCase


class SystemCategoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active(self) -> list[SystemCategory]:
        result = await self.session.execute(
            select(SystemCategory)
            .where(SystemCategory.is_deleted == False)
            .order_by(SystemCategory.name)
        )
        return list(result.scalars().all())

    async def get(self, category_id: str) -> Optional[SystemCategory]:
        result = await self.session.execute(
            select(SystemCategory).where(SystemCategory.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[SystemCategory]:
        result = await self.session.execute(
            select(SystemCategory).where(SystemCategory.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, name: str) -> SystemCategory:
        category = SystemCategory(name=name)
        self.session.add(category)
        await self.session.flush()
        return category

    async def update_name(self, category_id: str, name: str) -> Optional[SystemCategory]:
        category = await self.get(category_id)
        if not category:
            return None
        category.name = name
        await self.session.flush()
        return category

    async def soft_delete(self, category_id: str) -> bool:
        category = await self.get(category_id)
        if not category:
            return False
        category.is_deleted = True
        await self.session.flush()
        return True

    async def count_cases_using(self, name: str) -> int:
        result = await self.session.execute(
            select(func.count(TestCase.id)).where(
                TestCase.system_category == name,
                TestCase.is_deleted == False,
            )
        )
        return result.scalar_one() or 0

from typing import Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.test_case import TestCase
from src.models.base import generate_uuid
from .base import BaseRepository


class TestCaseRepository(BaseRepository[TestCase]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, id: str) -> Optional[TestCase]:
        result = await self.session.execute(
            select(TestCase).where(TestCase.id == id, TestCase.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def get_including_deleted(self, id: str) -> Optional[TestCase]:
        result = await self.session.execute(select(TestCase).where(TestCase.id == id))
        return result.scalar_one_or_none()

    async def get_by_case_number(self, case_number: str) -> Optional[TestCase]:
        result = await self.session.execute(
            select(TestCase).where(TestCase.case_number == case_number, TestCase.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> TestCase:
        case = TestCase(id=generate_uuid(), **kwargs)
        self.session.add(case)
        await self.session.flush()
        await self.session.refresh(case)
        return case

    async def update(self, id: str, **kwargs) -> Optional[TestCase]:
        case = await self.get(id)
        if not case:
            return None
        for key, value in kwargs.items():
            setattr(case, key, value)
        await self.session.flush()
        await self.session.refresh(case)
        return case

    async def increment_version(self, id: str) -> Optional[TestCase]:
        case = await self.get(id)
        if not case:
            return None
        case.version += 1
        await self.session.flush()
        return case

    async def soft_delete(self, id: str, deleted_by: str) -> bool:
        case = await self.get(id)
        if not case:
            return False
        case.is_deleted = True
        case.deleted_by = deleted_by
        await self.session.flush()
        return True

    async def delete(self, id: str) -> bool:
        case = await self.get(id)
        if not case:
            return False
        await self.session.delete(case)
        await self.session.flush()
        return True

    _SORTABLE_COLUMNS = {
        "case_number": lambda: TestCase.case_number,
        "name": lambda: TestCase.name,
        "system_category": lambda: TestCase.system_category,
        "created_at": lambda: TestCase.created_at,
        "updated_at": lambda: TestCase.updated_at,
        "version": lambda: TestCase.version,
    }

    async def list_with_filters(
        self,
        system_category: Optional[str] = None,
        keyword: Optional[str] = None,
        tags: Optional[list[str]] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[TestCase], int]:
        conditions = [TestCase.is_deleted.is_(False)]
        if system_category:
            conditions.append(TestCase.system_category == system_category)
        if keyword:
            conditions.append(or_(
                TestCase.name.ilike(f"%{keyword}%"),
                TestCase.case_number.ilike(f"%{keyword}%"),
            ))

        base_query = select(TestCase).where(and_(*conditions))
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        col_factory = self._SORTABLE_COLUMNS.get(sort_by, self._SORTABLE_COLUMNS["created_at"])
        col = col_factory()
        order_expr = col.asc() if order == "asc" else col.desc()

        offset = (page - 1) * page_size
        items_result = await self.session.execute(
            base_query.offset(offset).limit(page_size).order_by(order_expr)
        )
        items = list(items_result.scalars().all())
        return items, total

    async def list_by_prefix(self, prefix: str) -> list["TestCase"]:
        """Return all cases (including soft-deleted) whose case_number starts with '{prefix}-'."""
        result = await self.session.execute(
            select(TestCase).where(TestCase.case_number.like(f"{prefix}-%"))
        )
        return list(result.scalars().all())

    async def get_referencing_checklists_with_names(self, case_id: str) -> list[dict]:
        """Return list of {id, name} for checklists that contain this case and are not deleted."""
        from src.models.checklist_item import ChecklistItem
        from src.models.test_checklist import TestChecklist

        result = await self.session.execute(
            select(TestChecklist.id, TestChecklist.name)
            .join(ChecklistItem, ChecklistItem.checklist_id == TestChecklist.id)
            .where(ChecklistItem.test_case_id == case_id)
            .distinct()
        )
        return [{"id": row[0], "name": row[1]} for row in result.all()]

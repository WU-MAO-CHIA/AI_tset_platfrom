from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.test_checklist import TestChecklist
from src.models.checklist_item import ChecklistItem
from src.repositories.base import BaseRepository


class ChecklistRepository(BaseRepository[TestChecklist]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, id: str) -> Optional[TestChecklist]:
        result = await self.session.execute(
            select(TestChecklist).where(TestChecklist.id == id)
        )
        return result.scalar_one_or_none()

    async def get_with_items(self, id: str) -> Optional[TestChecklist]:
        from src.models.test_case import TestCase
        from src.models.test_data import TestData
        result = await self.session.execute(
            select(TestChecklist)
            .where(TestChecklist.id == id)
            .options(
                selectinload(TestChecklist.items)
                .selectinload(ChecklistItem.test_case)
                .selectinload(TestCase.test_data)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, created_by: str, case_ids: list[str], description: str = "") -> TestChecklist:
        checklist = TestChecklist(name=name, created_by=created_by, description=description or None)
        self.session.add(checklist)
        await self.session.flush()

        for idx, case_id in enumerate(case_ids):
            item = ChecklistItem(checklist_id=checklist.id, test_case_id=case_id, position=idx)
            self.session.add(item)

        await self.session.flush()
        await self.session.refresh(checklist)
        return checklist

    async def update(self, id: str, **kwargs) -> Optional[TestChecklist]:
        checklist = await self.get(id)
        if checklist is None:
            return None
        for key, value in kwargs.items():
            setattr(checklist, key, value)
        await self.session.flush()
        return checklist

    async def update_items(self, checklist_id: str, case_ids: list[str]) -> Optional[TestChecklist]:
        checklist = await self.get(checklist_id)
        if checklist is None:
            return None

        await self.session.execute(
            delete(ChecklistItem).where(ChecklistItem.checklist_id == checklist_id)
        )

        for idx, case_id in enumerate(case_ids):
            item = ChecklistItem(checklist_id=checklist_id, test_case_id=case_id, position=idx)
            self.session.add(item)

        await self.session.flush()
        return await self.get_with_items(checklist_id)

    _SORTABLE_COLUMNS = {
        "name": lambda: TestChecklist.name,
        "created_by": lambda: TestChecklist.created_by,
        "created_at": lambda: TestChecklist.created_at,
    }

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[TestChecklist], int]:
        from sqlalchemy import func, and_
        conditions = []
        if keyword:
            conditions.append(TestChecklist.name.ilike(f"%{keyword}%"))

        base_q = select(TestChecklist).where(and_(*conditions)) if conditions else select(TestChecklist)

        if sort_by == "status":
            # 狀態為衍生欄位：取最新一筆（排除 deleted）清單執行的 status
            from sqlalchemy import case
            from src.models.execution_record import ExecutionRecord
            latest_status = (
                select(ExecutionRecord.status)
                .where(ExecutionRecord.checklist_id == TestChecklist.id)
                .where(ExecutionRecord.status != "deleted")
                .order_by(ExecutionRecord.created_at.desc())
                .limit(1)
                .correlate(TestChecklist)
                .scalar_subquery()
            )
            # 自訂優先序（asc 由上而下）：completed → pending → running → failed → error → 未執行
            order_col = case(
                (latest_status == "completed", 0),
                (latest_status == "pending", 1),
                (latest_status == "running", 2),
                (latest_status == "failed", 3),
                (latest_status == "error", 4),
                else_=99,  # 未執行(NULL)或其他狀態排最後
            )
        else:
            col_factory = self._SORTABLE_COLUMNS.get(sort_by, self._SORTABLE_COLUMNS["created_at"])
            order_col = col_factory()
        order_expr = order_col.asc() if order == "asc" else order_col.desc()

        offset = (page - 1) * page_size
        result = await self.session.execute(base_q.order_by(order_expr).offset(offset).limit(page_size))
        items = list(result.scalars().all())

        count_result = await self.session.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total = count_result.scalar_one()
        return items, total

    async def delete(self, id: str) -> bool:
        checklist = await self.get(id)
        if checklist is None:
            return False
        await self.session.delete(checklist)
        await self.session.flush()
        return True

    async def get_active_executions(self, checklist_id: str) -> list[str]:
        from src.models.execution_record import ExecutionRecord
        result = await self.session.execute(
            select(ExecutionRecord.id)
            .where(ExecutionRecord.checklist_id == checklist_id)
            .where(ExecutionRecord.status.in_(["pending", "running"]))
        )
        return [row[0] for row in result.all()]

    async def get_execution_history(self, checklist_id: str):
        from src.models.execution_record import ExecutionRecord
        result = await self.session.execute(
            select(ExecutionRecord)
            .where(ExecutionRecord.checklist_id == checklist_id)
            .order_by(ExecutionRecord.created_at.desc())
        )
        return list(result.scalars().all())

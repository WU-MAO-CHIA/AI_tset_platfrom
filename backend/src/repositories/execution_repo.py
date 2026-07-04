from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.execution_record import ExecutionRecord
from src.repositories.base import BaseRepository


class ExecutionRepository(BaseRepository[ExecutionRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self, id: str) -> Optional[ExecutionRecord]:
        result = await self.session.execute(
            select(ExecutionRecord).where(ExecutionRecord.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> ExecutionRecord:
        record = ExecutionRecord(**kwargs)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def update(self, id: str, **kwargs) -> Optional[ExecutionRecord]:
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

    async def create_for_checklist(
        self, checklist_id: str, parallel_mode: bool, max_workers: int
    ) -> ExecutionRecord:
        return await self.create(
            checklist_id=checklist_id,
            source_case_id=None,
            execution_type="checklist",
            status="pending",
            parallel_mode=parallel_mode,
            max_workers=max_workers,
        )

    async def create_for_trial_run(self, source_case_id: str) -> ExecutionRecord:
        return await self.create(
            checklist_id=None,
            source_case_id=source_case_id,
            execution_type="trial_run",
            status="pending",
            parallel_mode=False,
            max_workers=1,
        )

    async def update_status(
        self,
        execution_id: str,
        status: str,
        passed_count: int = 0,
        failed_count: int = 0,
        total_count: int = 0,
    ) -> Optional[ExecutionRecord]:
        return await self.update(
            execution_id,
            status=status,
            passed_count=passed_count,
            failed_count=failed_count,
            total_count=total_count,
        )

    async def get_history_for_checklist(self, checklist_id: str) -> list[ExecutionRecord]:
        result = await self.session.execute(
            select(ExecutionRecord)
            .where(ExecutionRecord.checklist_id == checklist_id)
            .order_by(ExecutionRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_case_execution_history(self, case_id: str, page: int = 1, page_size: int = 20) -> tuple[list, int]:
        from sqlalchemy import func, or_
        from src.models.checklist_item import ChecklistItem

        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(ExecutionRecord)
            .outerjoin(ChecklistItem, ChecklistItem.checklist_id == ExecutionRecord.checklist_id)
            .where(
                or_(
                    ExecutionRecord.source_case_id == case_id,
                    ChecklistItem.test_case_id == case_id,
                )
            )
            .distinct()
            .order_by(ExecutionRecord.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        records = list(result.scalars().all())

        count_result = await self.session.execute(
            select(func.count())
            .select_from(ExecutionRecord)
            .outerjoin(ChecklistItem, ChecklistItem.checklist_id == ExecutionRecord.checklist_id)
            .where(
                or_(
                    ExecutionRecord.source_case_id == case_id,
                    ChecklistItem.test_case_id == case_id,
                )
            )
            .distinct()
        )
        total = count_result.scalar_one()
        return records, total

    async def get_case_results_summary(self, execution_id: str) -> list:
        return []

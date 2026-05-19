from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.test_checklist import TestChecklist
from src.repositories.checklist_repo import ChecklistRepository
from src.repositories.test_case_repo import TestCaseRepository


class ChecklistService:
    def __init__(self, session: AsyncSession) -> None:
        self._cl_repo = ChecklistRepository(session)
        self._case_repo = TestCaseRepository(session)

    async def create(self, name: str, created_by: str, case_ids: list[str], description: str = "") -> TestChecklist:
        await self._validate_cases_exist(case_ids)
        return await self._cl_repo.create(name=name, created_by=created_by, case_ids=case_ids, description=description)

    async def get_with_items(self, checklist_id: str) -> Optional[TestChecklist]:
        return await self._cl_repo.get_with_items(checklist_id)

    async def update_items(self, checklist_id: str, case_ids: list[str]) -> Optional[TestChecklist]:
        checklist = await self._cl_repo.get(checklist_id)
        if checklist is None:
            return None
        await self._validate_cases_exist(case_ids)
        return await self._cl_repo.update_items(checklist_id, case_ids)

    async def list_all(self, page: int = 1, page_size: int = 20) -> tuple[list[TestChecklist], int]:
        return await self._cl_repo.list_all(page=page, page_size=page_size)

    async def _validate_cases_exist(self, case_ids: list[str]) -> None:
        for case_id in case_ids:
            case = await self._case_repo.get(case_id)
            if case is None or case.is_deleted:
                raise ValueError(f"case_not_found:{case_id}")

import json
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.checklist_item import ChecklistItem
from src.models.test_checklist import TestChecklist
from src.repositories.checklist_repo import ChecklistRepository
from src.repositories.test_case_repo import TestCaseRepository


class ChecklistService:
    def __init__(self, session: AsyncSession) -> None:
        self._cl_repo = ChecklistRepository(session)
        self._case_repo = TestCaseRepository(session)
        self._session = session

    async def create(self, name: str, created_by: str, case_ids: list[str], description: str = "") -> TestChecklist:
        await self._validate_cases_exist(case_ids)
        return await self._cl_repo.create(name=name, created_by=created_by, case_ids=case_ids, description=description)

    async def get_with_items(self, checklist_id: str) -> Optional[TestChecklist]:
        return await self._cl_repo.get_with_items(checklist_id)

    async def update_checklist(self, checklist_id: str, name: str, created_by: str) -> Optional[TestChecklist]:
        return await self._cl_repo.update(checklist_id, name=name, created_by=created_by)

    async def delete_checklist(self, checklist_id: str) -> bool:
        checklist = await self._cl_repo.get(checklist_id)
        if checklist is None:
            return False
        active = await self._cl_repo.get_active_executions(checklist_id)
        if active:
            raise ValueError(f"checklist_in_use:{','.join(active)}")
        return await self._cl_repo.delete(checklist_id)

    async def list_checklist_cases(self, checklist_id: str) -> Optional[list[dict]]:
        checklist = await self._cl_repo.get_with_items(checklist_id)
        if checklist is None:
            return None
        items = sorted(checklist.items, key=lambda x: x.position or 0)
        result = []
        for item in items:
            actual_values: dict = {}
            if item.actual_values:
                try:
                    actual_values = json.loads(item.actual_values)
                except (json.JSONDecodeError, ValueError):
                    actual_values = {}

            test_data = []
            if item.test_case and item.test_case.test_data:
                sorted_td = sorted(item.test_case.test_data, key=lambda td: td.row_index or 0)
                test_data = [
                    {
                        "id": td.id,
                        "field_name": td.field_name,
                        "rf_variable": td.rf_variable,
                        "field_value": td.field_value,
                        "description": td.description,
                        "row_index": td.row_index,
                    }
                    for td in sorted_td
                ]

            result.append({
                "item_id": item.id,
                "test_case_id": item.test_case_id,
                "position": item.position or 0,
                "notes": item.notes,
                "actual_values": actual_values,
                "test_data": test_data,
                "case_number": item.test_case.case_number if item.test_case else None,
                "name": item.test_case.name if item.test_case else None,
            })
        return result

    async def add_case(self, checklist_id: str, case_id: str, position: Optional[int] = None) -> dict:
        checklist = await self._cl_repo.get_with_items(checklist_id)
        if checklist is None:
            raise ValueError("checklist_not_found")
        case = await self._case_repo.get(case_id)
        if case is None or case.is_deleted:
            raise ValueError(f"case_not_found:{case_id}")
        existing = [item for item in checklist.items if item.test_case_id == case_id]
        if existing:
            raise ValueError(f"case_already_in_checklist:{case_id}")
        if position is None:
            position = len(checklist.items)
        item = ChecklistItem(
            checklist_id=checklist_id,
            test_case_id=case_id,
            position=position,
        )
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        return {"item_id": item.id, "position": item.position}

    async def remove_case(self, checklist_id: str, case_id: str) -> bool:
        checklist = await self._cl_repo.get_with_items(checklist_id)
        if checklist is None:
            raise ValueError("checklist_not_found")
        item = next((i for i in checklist.items if i.test_case_id == case_id), None)
        if item is None:
            raise ValueError(f"case_not_in_checklist:{case_id}")
        await self._session.delete(item)
        await self._session.flush()
        return True

    async def update_case_item(
        self,
        checklist_id: str,
        case_id: str,
        notes: Optional[str] = None,
        position: Optional[int] = None,
        actual_values: Optional[dict] = None,
        clear_actual_values: bool = False,
    ) -> Optional[dict]:
        checklist = await self._cl_repo.get_with_items(checklist_id)
        if checklist is None:
            raise ValueError("checklist_not_found")
        item = next((i for i in checklist.items if i.test_case_id == case_id), None)
        if item is None:
            raise ValueError(f"case_not_in_checklist:{case_id}")
        if notes is not None:
            item.notes = notes
        if position is not None:
            item.position = position
        if clear_actual_values:
            item.actual_values = None
        elif actual_values is not None:
            item.actual_values = json.dumps(actual_values, ensure_ascii=False)
        await self._session.flush()

        parsed_actual_values: dict = {}
        if item.actual_values:
            try:
                parsed_actual_values = json.loads(item.actual_values)
            except (json.JSONDecodeError, ValueError):
                parsed_actual_values = {}

        return {
            "item_id": item.id,
            "test_case_id": item.test_case_id,
            "position": item.position,
            "notes": item.notes,
            "actual_values": parsed_actual_values,
        }

    async def reorder_cases(self, checklist_id: str, case_ids: list[str]) -> bool:
        checklist = await self._cl_repo.get_with_items(checklist_id)
        if checklist is None:
            raise ValueError("checklist_not_found")
        id_to_item = {item.test_case_id: item for item in checklist.items}
        for new_pos, case_id in enumerate(case_ids):
            if case_id in id_to_item:
                id_to_item[case_id].position = new_pos
        await self._session.flush()
        return True

    async def update_items(self, checklist_id: str, case_ids: list[str]) -> Optional[TestChecklist]:
        checklist = await self._cl_repo.get(checklist_id)
        if checklist is None:
            return None
        await self._validate_cases_exist(case_ids)
        return await self._cl_repo.update_items(checklist_id, case_ids)

    async def list_all(self, page: int = 1, page_size: int = 20, keyword: str | None = None, sort_by: str = "created_at", order: str = "desc") -> tuple[list[TestChecklist], int]:
        return await self._cl_repo.list_all(page=page, page_size=page_size, keyword=keyword, sort_by=sort_by, order=order)

    async def _validate_cases_exist(self, case_ids: list[str]) -> None:
        for case_id in case_ids:
            case = await self._case_repo.get(case_id)
            if case is None or case.is_deleted:
                raise ValueError(f"case_not_found:{case_id}")

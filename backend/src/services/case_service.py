from typing import Any, Optional

from src.repositories.test_case_repo import TestCaseRepository


class CaseService:
    def __init__(self, repo: TestCaseRepository) -> None:
        self.repo = repo

    async def generate_case_number(self, system_category: Optional[str]) -> str:
        prefix = (system_category or "TC").strip()
        cases = await self.repo.list_by_prefix(prefix)
        max_num = 0
        for c in cases:
            parts = c.case_number.rsplit("-", 1)
            if len(parts) == 2 and parts[-1].isdigit():
                max_num = max(max_num, int(parts[-1]))
        return f"{prefix}-{str(max_num + 1).zfill(3)}"

    async def create(
        self,
        name: str,
        main_steps: str,
        created_by: str,
        description: Optional[str] = None,
        precondition_steps: Optional[str] = None,
        system_category: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ):
        case_number = await self.generate_case_number(system_category)
        return await self.repo.create(
            case_number=case_number,
            name=name,
            main_steps=main_steps,
            created_by=created_by,
            description=description,
            precondition_steps=precondition_steps,
            system_category=system_category,
            tags=tags or [],
            version=1,
        )

    async def update(
        self,
        case_id: str,
        modified_by: str,
        name: Optional[str] = None,
        main_steps: Optional[str] = None,
        description: Optional[str] = None,
        precondition_steps: Optional[str] = None,
        system_category: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ):
        case = await self.repo.get(case_id)
        if not case:
            raise ValueError("not_found")

        update_data: dict[str, Any] = {"modified_by": modified_by}
        if name is not None:
            update_data["name"] = name
        if main_steps is not None:
            update_data["main_steps"] = main_steps
        if description is not None:
            update_data["description"] = description
        if precondition_steps is not None:
            update_data["precondition_steps"] = precondition_steps
        if system_category is not None:
            update_data["system_category"] = system_category
        if tags is not None:
            update_data["tags"] = tags

        update_data["version"] = case.version + 1
        return await self.repo.update(case_id, **update_data)

    async def soft_delete(self, case_id: str, deleted_by: str) -> dict:
        case = await self.repo.get(case_id)
        if not case:
            raise ValueError("not_found")

        referencing = await self.repo.get_referencing_checklists_with_names(case_id)
        if referencing:
            raise ValueError(f"case_in_use:{','.join(c['id'] for c in referencing)}")

        await self.repo.soft_delete(case_id, deleted_by)
        return {"success": True}

    async def get(self, case_id: str):
        case = await self.repo.get(case_id)
        if not case:
            raise ValueError("not_found")
        return case

    async def list_cases(
        self,
        system_category: Optional[str] = None,
        keyword: Optional[str] = None,
        tags: Optional[list[str]] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[list, int]:
        return await self.repo.list_with_filters(
            system_category=system_category,
            keyword=keyword,
            tags=tags,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            order=order,
        )

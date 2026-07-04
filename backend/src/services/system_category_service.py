from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.system_category_repo import SystemCategoryRepository


class SystemCategoryService:
    def __init__(self, db: AsyncSession):
        self.repo = SystemCategoryRepository(db)

    async def list(self) -> list:
        return await self.repo.list_active()

    async def create(self, name: str):
        existing = await self.repo.get_by_name(name)
        if existing and not existing.is_deleted:
            raise HTTPException(status_code=409, detail=f"系統別 '{name}' 已存在")
        return await self.repo.create(name)

    async def rename(self, category_id: str, name: str):
        existing = await self.repo.get_by_name(name)
        if existing and existing.id != category_id and not existing.is_deleted:
            raise HTTPException(status_code=409, detail=f"系統別名稱 '{name}' 已被使用")
        category = await self.repo.update_name(category_id, name)
        if not category:
            raise HTTPException(status_code=404, detail="系統別不存在")
        return category

    async def delete(self, category_id: str) -> dict:
        category = await self.repo.get(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="系統別不存在")
        affected = await self.repo.count_cases_using(category.name)
        await self.repo.soft_delete(category_id)
        return {"deleted": True, "affected_case_count": affected}

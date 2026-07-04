from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def list_all(self) -> list:
        return await self.repo.list_all()

    async def create(self, username: str, plain_pw: str, role: str = "viewer"):
        existing = await self.repo.get_by_username(username)
        if existing:
            raise HTTPException(status_code=409, detail=f"使用者 '{username}' 已存在")
        hashed = hash_password(plain_pw)
        return await self.repo.create(username, hashed, role)

    async def update_role(self, user_id: str, role: str):
        if role not in ("admin", "editor", "viewer"):
            raise HTTPException(status_code=422, detail="無效的角色")
        user = await self.repo.update(user_id, role=role)
        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")
        return user

    async def set_active(self, user_id: str, is_active: bool):
        user = await self.repo.set_active(user_id, is_active)
        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")
        return user

    async def reset_password(self, user_id: str, new_pw: str):
        hashed = hash_password(new_pw)
        user = await self.repo.update(user_id, hashed_password=hashed)
        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")
        return user

    async def delete(self, user_id: str, current_user_id: str):
        if user_id == current_user_id:
            raise HTTPException(status_code=400, detail="無法刪除當前登入的帳號")
        deleted = await self.repo.delete(user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="使用者不存在")

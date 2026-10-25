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
        if not username or not username.strip() or len(username.strip()) > 64:
            raise HTTPException(status_code=422, detail="無效的使用者名稱")
        if role not in ("admin", "editor", "viewer"):
            raise HTTPException(status_code=422, detail="無效的角色")
        if len(plain_pw) < 8 or len(plain_pw) > 128:
            raise HTTPException(status_code=422, detail="密碼長度需為 8-128 字元")
        existing = await self.repo.get_by_username(username)
        if existing:
            raise HTTPException(status_code=409, detail=f"使用者 '{username}' 已存在")
        hashed = hash_password(plain_pw)
        return await self.repo.create(username, hashed, role)

    async def _get_or_404(self, user_id: str):
        user = await self.repo.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")
        return user

    async def _ensure_not_last_admin(self, user) -> None:
        """移除最後一個啟用中的 admin 會讓系統無人能管理。"""
        if user.role != "admin" or not user.is_active:
            return
        active_admins = [u for u in await self.repo.list_all() if u.role == "admin" and u.is_active]
        if len(active_admins) <= 1:
            raise HTTPException(status_code=400, detail="至少需保留一個啟用中的管理員")

    async def revoke_tokens(self, user) -> None:
        """遞增 token_version，讓此帳號已簽發的 token 全部失效。"""
        await self.repo.update(user.id, token_version=user.token_version + 1)

    async def update_role(self, user_id: str, role: str):
        if role not in ("admin", "editor", "viewer"):
            raise HTTPException(status_code=422, detail="無效的角色")
        user = await self._get_or_404(user_id)
        if role == user.role:
            return user
        if role != "admin":
            await self._ensure_not_last_admin(user)
        return await self.repo.update(user_id, role=role, token_version=user.token_version + 1)

    async def set_active(self, user_id: str, is_active: bool):
        user = await self._get_or_404(user_id)
        if is_active == user.is_active:
            return user
        if not is_active:
            await self._ensure_not_last_admin(user)
            return await self.repo.update(user_id, is_active=False, token_version=user.token_version + 1)
        return await self.repo.set_active(user_id, True)

    async def reset_password(self, user_id: str, new_pw: str):
        if len(new_pw) < 8 or len(new_pw) > 128:
            raise HTTPException(status_code=422, detail="密碼長度需為 8-128 字元")
        user = await self._get_or_404(user_id)
        hashed = hash_password(new_pw)
        return await self.repo.update(user_id, hashed_password=hashed, token_version=user.token_version + 1)

    async def delete(self, user_id: str, current_user_id: str):
        if user_id == current_user_id:
            raise HTTPException(status_code=400, detail="無法刪除當前登入的帳號")
        await self._ensure_not_last_admin(await self._get_or_404(user_id))
        deleted = await self.repo.delete(user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="使用者不存在")

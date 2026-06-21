from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, verify_password
from src.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def login(self, username: str, password: str) -> dict:
        user = await self.repo.get_by_username(username)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
        token = create_access_token(sub=user.username, role=user.role)
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": user.role,
            "username": user.username,
        }

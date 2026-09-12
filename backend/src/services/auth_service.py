from fastapi import HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.security import create_access_token, verify_password
from src.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def login(self, username: str, password: str, response: Response = None) -> dict:
        user = await self.repo.get_by_username(username)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
        token = create_access_token(sub=user.username, role=user.role)

        if response is not None:
            settings = get_settings()
            # HttpOnly cookie 僅供 SSE（EventSource 無法自訂 header）使用；
            # 一般 API 仍走 Authorization: Bearer。prod 強制 Secure。
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                secure=settings.app_env == "prod",
                samesite="lax",
                max_age=settings.jwt_expire_hours * 3600,
                path="/",
            )

        return {
            "access_token": token,
            "token_type": "bearer",
            "role": user.role,
            "username": user.username,
        }

    @staticmethod
    def build_logout_response(response: Response) -> dict:
        response.delete_cookie(key="access_token", path="/")
        return {"logged_out": True}

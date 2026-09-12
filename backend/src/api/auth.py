import time

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import get_current_user
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


# 簡易 in-memory 登入限流：同 IP 5 分鐘內最多 60 次，避免無限爆破（多 worker 下為 best-effort）。
# 測試套件會頻繁登入，故閾值留寬；prod 如需更嚴請接 slowapi / WAF。
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_WINDOW_SEC = 300.0
_LOGIN_MAX_ATTEMPTS = 60


def _check_login_rate_limit(request: Request) -> None:
    from fastapi import HTTPException

    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = _LOGIN_ATTEMPTS.get(client_ip, [])
    attempts = [t for t in attempts if now - t < _LOGIN_WINDOW_SEC]
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="登入嘗試過於頻繁，請稍後再試")
    attempts.append(now)
    _LOGIN_ATTEMPTS[client_ip] = attempts


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    _check_login_rate_limit(request)
    service = AuthService(db)
    return await service.login(body.username, body.password, response=response)


@router.post("/logout")
async def logout(response: Response):
    return AuthService.build_logout_response(response)


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}

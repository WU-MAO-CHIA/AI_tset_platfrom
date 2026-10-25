import time

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import _user_from_token, get_current_user
from src.core.security import oauth2_scheme_optional
from src.services.auth_service import AuthService
from src.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str


class LogoutResponse(BaseModel):
    logged_out: bool


class CurrentUserResponse(BaseModel):
    username: str
    role: str


# 簡易 in-memory 登入限流：同 IP 5 分鐘內最多 60 次，避免無限爆破（多 worker 下為 best-effort）。
# 測試套件會頻繁登入，故閾值留寬；prod 如需更嚴請接 slowapi / WAF。
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_WINDOW_SEC = 300.0
_LOGIN_MAX_ATTEMPTS = 60


# 依帳號計算失敗次數：換 IP 也無法對同一帳號無限猜密碼。成功登入即清除。
_FAILED_LOGINS: dict[str, list[float]] = {}
_ACCOUNT_LOCK_WINDOW_SEC = 900.0
_ACCOUNT_MAX_FAILURES = 10


def _check_login_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = _LOGIN_ATTEMPTS.get(client_ip, [])
    attempts = [t for t in attempts if now - t < _LOGIN_WINDOW_SEC]
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="登入嘗試過於頻繁，請稍後再試")
    attempts.append(now)
    _LOGIN_ATTEMPTS[client_ip] = attempts


def _recent_failures(username: str) -> list[float]:
    now = time.monotonic()
    failures = [t for t in _FAILED_LOGINS.get(username, []) if now - t < _ACCOUNT_LOCK_WINDOW_SEC]
    _FAILED_LOGINS[username] = failures
    return failures


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    _check_login_rate_limit(request)
    username = body.username.strip().lower()
    if len(_recent_failures(username)) >= _ACCOUNT_MAX_FAILURES:
        raise HTTPException(status_code=429, detail="此帳號登入失敗次數過多，請 15 分鐘後再試")
    service = AuthService(db)
    try:
        result = await service.login(body.username, body.password, response=response)
    except HTTPException as exc:
        if exc.status_code == 401:
            if len(_FAILED_LOGINS) > 10000:  # 避免以大量假帳號名塞爆記憶體
                for name in list(_FAILED_LOGINS):
                    if not _recent_failures(name):
                        del _FAILED_LOGINS[name]
            _FAILED_LOGINS.setdefault(username, []).append(time.monotonic())
        raise
    _FAILED_LOGINS.pop(username, None)
    return result


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    token: str | None = Depends(oauth2_scheme_optional),
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    # 讓這個帳號已簽發的 token 全部失效（含其他裝置）；token 無效時仍照常清 cookie
    try:
        user = await _user_from_token(token or access_token, db)
    except HTTPException:
        user = None
    if user is not None:
        await UserService(db).revoke_tokens(user)
    return AuthService.build_logout_response(response)


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}

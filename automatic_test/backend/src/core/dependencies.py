from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .config import get_settings, Settings
from .security import oauth2_scheme, decode_token

import os


def get_session() -> AsyncSession:
    return Depends(get_db)


def get_app_settings() -> Settings:
    return get_settings()


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    from src.repositories.user_repo import UserRepository
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    repo = UserRepository(db)
    user = await repo.get_by_username(username)
    if not user or not user.is_active:
        raise credentials_exception
    return user


async def require_admin(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


async def require_editor_or_above(user=Depends(get_current_user)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Editor or Admin required")
    return user


async def llm_api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle LLM provider API errors with a 503 and retry hint."""
    return JSONResponse(
        status_code=503,
        content={
            "error": "llm_service_unavailable",
            "message": "LLM service is temporarily unavailable. Please retry in a few seconds.",
            "retry_after_seconds": 5,
        },
    )


def serve_placeholder_image() -> FileResponse:
    """Return a placeholder image when media file is not found."""
    placeholder_path = os.path.join(os.path.dirname(__file__), "..", "templates", "placeholder.png")
    if os.path.exists(placeholder_path):
        return FileResponse(placeholder_path, media_type="image/png")
    # Minimal 1x1 transparent PNG as fallback
    import base64
    from fastapi.responses import Response
    png_1x1 = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    return Response(content=png_1x1, media_type="image/png")

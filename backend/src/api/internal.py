"""給 robot 子程序呼叫的內部 API。

腳本可執行任意程式，所以子程序拿不到 LLM 金鑰；需要 LLM 的關鍵字（驗證碼）改由後端代為呼叫。
驗證方式是執行時注入的短期 captcha token（見 security.create_captcha_token），不接受一般登入 token。
"""
import base64
import binascii
import os
import tempfile
import time
from types import SimpleNamespace
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import get_db
from src.core.llm_provider import get_provider
from src.core.security import CAPTCHA_SCOPE, JWTError, decode_token
from src.services.app_setting_service import AppSettingService

router = APIRouter(prefix="/internal", tags=["internal"])

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_CALLS_PER_TOKEN = 50
_ALLOWED_MEDIA_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}

# 每個 token 的呼叫次數：限制外洩的 token 能消耗的 LLM 額度（token 本身 20 分鐘後過期）
_CALLS: dict[str, tuple[float, int]] = {}


def _require_captcha_token(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="captcha token required")
    try:
        payload = decode_token(authorization[7:])
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid captcha token")
    if payload.get("scope") != CAPTCHA_SCOPE or not payload.get("jti"):
        raise HTTPException(status_code=401, detail="invalid captcha token")
    jti = payload["jti"]
    now = time.time()
    for key, (exp, _) in list(_CALLS.items()):
        if exp < now:
            del _CALLS[key]
    _, count = _CALLS.get(jti, (payload["exp"], 0))
    if count >= MAX_CALLS_PER_TOKEN:
        raise HTTPException(status_code=429, detail="captcha call limit reached for this run")
    _CALLS[jti] = (payload["exp"], count + 1)
    return jti


class CaptchaSolveRequest(BaseModel):
    image_base64: str = Field(..., max_length=MAX_IMAGE_BYTES * 4 // 3 + 4)
    media_type: str = "image/png"
    prompt: str = Field(..., max_length=2000)
    model: Optional[str] = Field(default=None, max_length=100)


class CaptchaSolveResponse(BaseModel):
    text: str
    model_used: str


@router.post("/captcha/solve", response_model=CaptchaSolveResponse)
async def solve_captcha(
    body: CaptchaSolveRequest,
    _jti: str = Depends(_require_captcha_token),
    db: AsyncSession = Depends(get_db),
):
    if body.media_type not in _ALLOWED_MEDIA_TYPES:
        raise HTTPException(status_code=422, detail="unsupported media_type")
    try:
        image = base64.b64decode(body.image_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail="invalid base64 image")

    model = body.model or await AppSettingService(db).get_active_model()
    provider = get_provider(model, get_settings())
    # provider 的 vision 介面讀檔案路徑（與附件共用），先寫到暫存檔
    fd, path = tempfile.mkstemp(suffix=".img")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(image)
        media = SimpleNamespace(attachment_type="image", file_path=path, mime_type=body.media_type)
        text = await provider.complete_with_vision(body.prompt, [media])
    finally:
        os.remove(path)
    return {"text": (text or "").strip(), "model_used": model}

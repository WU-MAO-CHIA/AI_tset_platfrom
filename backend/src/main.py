import asyncio
import logging
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import delete, update

# Import all models to register them with SQLAlchemy mapper before any query
from src.models import test_case, test_data, media_attachment, test_checklist, checklist_item, execution_record, execution_event, execution_schedule, db_connection, automation_code, case_result, execution_media, case_chat_message, robot_script, user, system_category, app_setting  # noqa: F401
from src.models.execution_event import ExecutionEvent
from src.models.execution_record import ExecutionRecord

logger = logging.getLogger(__name__)

app = FastAPI(title="AutoTest Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["X-Access-Token"],
)


_NO_RENEW_PATHS = ("/api/v1/auth/login", "/api/v1/auth/logout")


@app.middleware("http")
async def sliding_session_middleware(request: Request, call_next):
    """閒置逾時：通過驗證的 API 請求都換發新 token（X-Access-Token header + cookie），
    有操作就延長，閒置超過 JWT_EXPIRE_MINUTES 才過期。"""
    from jose import JWTError
    from src.core.security import create_access_token, decode_token
    from src.services.auth_service import set_auth_cookie

    response = await call_next(request)
    path = request.url.path
    if response.status_code >= 400 or not path.startswith("/api/") or path in _NO_RENEW_PATHS:
        return response
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else request.cookies.get("access_token")
    if not token:
        return response
    try:
        payload = decode_token(token)
    except JWTError:
        return response
    if not payload.get("sub"):
        return response
    new_token = create_access_token(sub=payload["sub"], role=payload.get("role"))
    response.headers["X-Access-Token"] = new_token
    set_auth_cookie(response, new_token)
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """最小安全標頭（不依賴額外套件）。iframe 需同源顯示 RF 報告，故用 SAMEORIGIN。"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "validation_error", "message": str(exc)})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "An unexpected error occurred"},
    )


async def _cleanup_trial_runs() -> None:
    """每日清除 30 天以上的 trial_run 執行紀錄（軟刪除標記 status='deleted'）。"""
    from src.core.database import AsyncSessionLocal
    while True:
        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await asyncio.sleep((next_midnight - now).total_seconds())
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    update(ExecutionRecord)
                    .where(
                        ExecutionRecord.execution_type == "trial_run",
                        ExecutionRecord.created_at < cutoff,
                        ExecutionRecord.status != "deleted",
                    )
                    .values(status="deleted")
                )
                # 執行進度事件只用於即時顯示與重新整理補齊，同樣保留 30 天
                events_result = await session.execute(
                    delete(ExecutionEvent).where(ExecutionEvent.created_at < cutoff)
                )
                await session.commit()
                logger.info("Trial run cleanup: %d records marked deleted", result.rowcount)
                logger.info("Execution event cleanup: %d events deleted", events_result.rowcount)
        except Exception:
            logger.exception("Trial run cleanup failed")


@app.on_event("startup")
async def startup_event() -> None:
    import os
    from src.core.config import get_settings
    settings = get_settings()
    os.makedirs(settings.execution_reports_dir, exist_ok=True)
    # 啟動期弱配置檢查：prod 直接拒絕啟動，dev/test 僅警告（避免誤傷本地開發）。
    if settings.app_env == "prod":
        if settings.is_default_secret():
            raise RuntimeError("Refusing to start in prod with default JWT_SECRET_KEY")
        if settings.is_default_admin_password():
            raise RuntimeError("Refusing to start in prod with default ADMIN_PASSWORD")
    else:
        if settings.is_default_secret():
            logger.warning("Using default JWT_SECRET_KEY — set a strong value via .env for any shared deployment")
        if settings.is_default_admin_password():
            logger.warning("Using default ADMIN_PASSWORD — change it via .env")
    await _recover_executions()
    # 恢復程序之後才開啟 worker：重啟前的 running 已標為 interrupted，pending 會依序被領取
    from src.execution.worker import get_worker
    get_worker().start()
    # 排程只負責在時間到時排入佇列（spec 004），實際執行仍由上面的 worker 處理
    if settings.schedule_enabled:
        from src.scheduling.runner import get_schedule_runner
        get_schedule_runner().start()
    asyncio.create_task(_cleanup_trial_runs())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    from src.execution.worker import get_worker
    from src.scheduling.runner import get_schedule_runner
    await get_schedule_runner().stop()
    await get_worker().stop()


async def _recover_executions() -> None:
    from src.core.database import AsyncSessionLocal
    from src.execution.recovery import mark_interrupted_executions
    try:
        async with AsyncSessionLocal() as session:
            await mark_interrupted_executions(session)
    except Exception:
        # 恢復失敗不應阻止服務啟動（例如 migration 尚未套用）
        logger.exception("Execution recovery on startup failed")


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "ok"}


from src.api.auth import router as auth_router  # noqa: E402
from src.api.admin import router as admin_router  # noqa: E402
from src.api.cases import router as cases_router  # noqa: E402
from src.api.checklists import router as checklists_router  # noqa: E402
from src.api.db_connections import router as db_connections_router  # noqa: E402
from src.api.executions import router as executions_router  # noqa: E402
from src.api.media import router as media_router  # noqa: E402
from src.api.llm_models import router as llm_models_router  # noqa: E402
from src.api.schedules import router as schedules_router  # noqa: E402
from src.api.dashboard import router as dashboard_router  # noqa: E402

app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(checklists_router, prefix="/api/v1")
app.include_router(db_connections_router, prefix="/api/v1")
app.include_router(executions_router, prefix="/api/v1")
app.include_router(media_router, prefix="/api/v1")
app.include_router(llm_models_router, prefix="/api/v1")
app.include_router(schedules_router, prefix="/api/v1")

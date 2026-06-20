import asyncio
import logging
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import update

# Import all models to register them with SQLAlchemy mapper before any query
from src.models import test_case, test_data, media_attachment, test_checklist, checklist_item, execution_record, db_connection, automation_code, case_result, execution_media, case_chat_message  # noqa: F401
from src.models.execution_record import ExecutionRecord

logger = logging.getLogger(__name__)

app = FastAPI(title="AutoTest Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
                await session.commit()
                logger.info("Trial run cleanup: %d records marked deleted", result.rowcount)
        except Exception:
            logger.exception("Trial run cleanup failed")


@app.on_event("startup")
async def startup_event() -> None:
    asyncio.create_task(_cleanup_trial_runs())


@app.get("/health")
async def health_check():
    return {"status": "ok"}


from src.api.cases import router as cases_router  # noqa: E402
from src.api.checklists import router as checklists_router  # noqa: E402
from src.api.db_connections import router as db_connections_router  # noqa: E402
from src.api.executions import router as executions_router  # noqa: E402
from src.api.media import router as media_router  # noqa: E402
from src.api.llm_models import router as llm_models_router  # noqa: E402

app.include_router(cases_router, prefix="/api/v1")
app.include_router(checklists_router, prefix="/api/v1")
app.include_router(db_connections_router, prefix="/api/v1")
app.include_router(executions_router, prefix="/api/v1")
app.include_router(media_router, prefix="/api/v1")
app.include_router(llm_models_router, prefix="/api/v1")

import asyncio
import json
import os
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import AsyncSessionLocal, get_db
from src.core.dependencies import (
    _user_from_token,
    get_current_user,
    get_current_user_header_or_cookie,
    require_editor_or_above,
)
from src.core.path_utils import safe_join
from src.execution.events import fetch_events_after
from src.execution.recovery import TERMINAL_STATUSES
from src.execution.worker import emit_queue_positions
from src.models.execution_event import ExecutionEvent
from src.models.case_result import CaseResult
from src.models.execution_media import ExecutionMedia
from src.models.execution_record import ExecutionRecord
from src.repositories.execution_repo import ExecutionRepository
from src.services.report_service import ReportService
from src.services.schedule_service import ScheduleService

router = APIRouter(prefix="/executions", tags=["executions"])

_auth = [Depends(get_current_user)]
# 報告檔由前端 <iframe> 直接載入，無法帶 Bearer header，需同時接受 cookie
_auth_header_or_cookie = [Depends(get_current_user_header_or_cookie)]


class ExecutionResponse(BaseModel):
    id: str
    status: str
    checklist_id: Optional[str] = None
    source_case_id: Optional[str] = None
    parallel_mode: bool
    max_workers: int
    passed_count: int
    failed_count: int
    total_count: int
    # 排程觸發時才有值；排程已刪除時 schedule_name 為 null
    schedule_id: Optional[str] = None
    schedule_name: Optional[str] = None


class ExecutionMediaItem(BaseModel):
    id: str
    media_type: str
    file_path: Optional[str] = None
    step_index: Optional[int] = None


class CaseResultItem(BaseModel):
    id: str
    test_case_id: str
    case_number: str
    case_name: str
    status: str
    elapsed_ms: Optional[int] = None
    failure_message: Optional[str] = None
    media: list[ExecutionMediaItem]


class ExecutionResultsResponse(BaseModel):
    items: list[CaseResultItem]
    total: int


class RfReportStatusResponse(BaseModel):
    available: bool


@router.get("/{execution_id}", response_model=ExecutionResponse, dependencies=_auth)
async def get_execution(execution_id: str, db: AsyncSession = Depends(get_db)):
    repo = ExecutionRepository(db)
    record = await repo.get(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    schedule_names = await ScheduleService(db).names_by_id({record.schedule_id})
    return {
        "id": record.id,
        "status": record.status,
        "checklist_id": record.checklist_id,
        "source_case_id": record.source_case_id,
        "parallel_mode": record.parallel_mode,
        "max_workers": record.max_workers,
        "passed_count": record.passed_count,
        "failed_count": record.failed_count,
        "total_count": record.total_count,
        "schedule_id": record.schedule_id,
        "schedule_name": schedule_names.get(record.schedule_id),
    }


@router.post(
    "/{execution_id}/cancel",
    response_model=ExecutionResponse,
    dependencies=[Depends(require_editor_or_above)],
)
async def cancel_execution(execution_id: str, db: AsyncSession = Depends(get_db)):
    # 只取消排隊中的執行；條件式 UPDATE 與 worker 領取互斥，不會取消到剛被領走的記錄。
    # 執行中的 robot 子程序不在此處理，回 409。
    result = await db.execute(
        update(ExecutionRecord)
        .where(ExecutionRecord.id == execution_id, ExecutionRecord.status == "pending")
        .values(status="cancelled")
    )
    if result.rowcount == 0:
        record = await ExecutionRepository(db).get(execution_id)
        if record is None:
            raise HTTPException(status_code=404, detail={"error": "not_found"})
        raise HTTPException(
            status_code=409,
            detail={"error": "not_pending", "status": record.status},
        )

    db.add(ExecutionEvent(
        execution_id=execution_id,
        event="execution_cancelled",
        payload={
            "event": "execution_cancelled",
            "execution_id": execution_id,
            "status": "cancelled",
            "message": "已取消排隊",
            "__done__": True,
        },
    ))
    # 後面排隊的執行往前移一位
    await emit_queue_positions(db)
    await db.commit()
    return await get_execution(execution_id, db)


@router.get("/{execution_id}/results", response_model=ExecutionResultsResponse, dependencies=_auth)
async def get_execution_results(execution_id: str, db: AsyncSession = Depends(get_db)):
    repo = ExecutionRepository(db)
    record = await repo.get(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    from sqlalchemy.orm import joinedload
    from src.models.test_case import TestCase

    result = await db.execute(
        select(CaseResult)
        .options(joinedload(CaseResult.test_case))
        .where(CaseResult.execution_id == execution_id)
        .order_by(CaseResult.position)
    )
    case_results = result.unique().scalars().all()

    items = []
    for cr in case_results:
        media_result = await db.execute(
            select(ExecutionMedia).where(ExecutionMedia.case_result_id == cr.id).order_by(ExecutionMedia.step_index)
        )
        media_items = [
            {"id": m.id, "media_type": m.media_type, "file_path": m.file_path, "step_index": m.step_index}
            for m in media_result.scalars().all()
        ]
        tc = cr.test_case
        items.append({
            "id": cr.id,
            "test_case_id": cr.test_case_id,
            "case_number": tc.case_number if tc else "",
            "case_name": tc.name if tc else "",
            "status": cr.status,
            "elapsed_ms": cr.elapsed_ms,
            "failure_message": cr.failure_message,
            "media": media_items,
        })

    return {"items": items, "total": len(items)}


_SSE_POLL_INTERVAL_SEC = 1.0
# 連續無新事件的上限（約 15 分鐘）；pabot 只在整批結束後才送案例事件，最長 600 秒
_SSE_MAX_IDLE_TICKS = 900


def _parse_last_event_id(value: str | None) -> int:
    try:
        return max(0, int(value)) if value else 0
    except ValueError:
        return 0


@router.get("/{execution_id}/stream", response_class=StreamingResponse)
async def stream_execution(
    execution_id: str,
    access_token: str | None = Cookie(default=None),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    db: AsyncSession = Depends(get_db)
):
    # SSE 無法自訂 Authorization header，一律走 HttpOnly cookie（登入時寫入）。
    # 不再接受 ?token= query，避免 JWT 進 access log / browser history / Referer。
    if not access_token:
        raise HTTPException(status_code=401, detail="Token required")
    await _user_from_token(access_token, db)

    repo = ExecutionRepository(db)
    record = await repo.get(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    after_id = _parse_last_event_id(last_event_id)

    def _completion_from_record(rec) -> str:
        return f"data: {json.dumps({'event': 'execution_completed', 'execution_id': execution_id, 'status': rec.status, 'passed': rec.passed_count, 'failed': rec.failed_count, 'total': rec.total_count, 'report_url': f'/api/v1/executions/{execution_id}/results', '__done__': True})}\n\n"

    async def event_generator():
        # 事件存在 execution_events（spec 003），每次連線從 Last-Event-ID 之後補送；
        # 新連線（重新整理頁面）會從頭重播，前端狀態因此能補齊。
        last_id = after_id
        if last_id == 0:
            yield f"data: {json.dumps({'event': 'execution_started', 'execution_id': execution_id, 'status': record.status, 'total_cases': record.total_count})}\n\n"

        idle_ticks = 0
        saw_terminal = False
        while idle_ticks < _SSE_MAX_IDLE_TICKS:
            async with AsyncSessionLocal() as poll_session:
                events = await fetch_events_after(poll_session, execution_id, last_id)
                current = None if events else await ExecutionRepository(poll_session).get(execution_id)

            if events:
                idle_ticks = 0
                for ev in events:
                    last_id = ev.id
                    # Strip internal sentinel before sending to client
                    send_event = {k: v for k, v in ev.payload.items() if k != "__done__"}
                    yield f"id: {ev.id}\ndata: {json.dumps(send_event)}\n\n"
                    if ev.payload.get("__done__"):
                        return
                continue

            if current is None:
                return
            if current.status in TERMINAL_STATUSES:
                if not saw_terminal:
                    # 狀態與最後幾筆事件可能在上一次查詢之後才寫入，再讀一次事件
                    saw_terminal = True
                    continue
                # 已結束卻沒有結束事件（例如空清單、spec 003 之前的舊記錄）
                yield _completion_from_record(current)
                return

            idle_ticks += 1
            if idle_ticks % 15 == 0:
                yield ": keep-alive\n\n"
            await asyncio.sleep(_SSE_POLL_INTERVAL_SEC)

        # NOTE: only reached on a genuine timeout, never after a clean finish.
        yield f"data: {json.dumps({'event': 'execution_error', 'execution_id': execution_id, 'message': '執行逾時'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{execution_id}/export", response_class=HTMLResponse, dependencies=_auth)
async def export_report(execution_id: str, db: AsyncSession = Depends(get_db)):
    repo = ExecutionRepository(db)
    record = await repo.get(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    from sqlalchemy.orm import joinedload

    result = await db.execute(
        select(CaseResult)
        .options(joinedload(CaseResult.test_case))
        .where(CaseResult.execution_id == execution_id)
        .order_by(CaseResult.position)
    )
    case_results = result.unique().scalars().all()

    case_result_dicts = []
    for cr in case_results:
        media_result = await db.execute(
            select(ExecutionMedia).where(ExecutionMedia.case_result_id == cr.id)
        )
        media_list = [
            {"media_type": m.media_type, "file_path": m.file_path, "step_index": m.step_index, "step_name": m.step_name}
            for m in media_result.scalars().all()
        ]
        case_result_dicts.append({
            "case_name": cr.test_case.name if cr.test_case else cr.test_case_id,
            "status": cr.status,
            "elapsed_ms": cr.elapsed_ms or 0,
            "failure_message": cr.failure_message,
            "media": media_list,
        })

    execution_data = {
        "id": record.id,
        "status": record.status,
        "passed_count": record.passed_count,
        "failed_count": record.failed_count,
        "total_count": record.total_count,
        "elapsed_ms": (
            int((record.finished_at - record.started_at).total_seconds() * 1000)
            if record.started_at and record.finished_at
            else 0
        ),
    }

    report_service = ReportService()
    html_content = report_service.export_report(execution_data, case_result_dicts)

    return HTMLResponse(
        content=html_content,
        headers={"Content-Disposition": f'attachment; filename="report-{execution_id}.html"'},
    )


RF_REPORT_CSP = "sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox"


@router.get(
    "/{execution_id}/rf-report/{filename:path}",
    response_class=FileResponse,
    dependencies=_auth_header_or_cookie,
)
async def get_rf_report(execution_id: str, filename: str, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    # 先確認 execution 存在，避免任意檔案存在性 oracle。
    repo = ExecutionRepository(db)
    record = await repo.get(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail="報告尚未生成或不存在")
    try:
        file_path = safe_join(settings.execution_reports_dir, execution_id, filename)
    except ValueError:
        raise HTTPException(status_code=404, detail="報告尚未生成或不存在")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="報告尚未生成或不存在")
    # RF log.html 可被腳本寫入任意 HTML（*HTML* 訊息）。以 CSP sandbox 讓報告跑在獨立的
    # opaque origin：腳本仍可執行（RF 報告需要 JS），但讀不到平台的 localStorage token 或呼叫 API。
    return FileResponse(str(file_path), headers={"Content-Security-Policy": RF_REPORT_CSP})



@router.get("/{execution_id}/rf-report-status", response_model=RfReportStatusResponse, dependencies=_auth)
async def get_rf_report_status(
    execution_id: str, filename: str = "report.html", db: AsyncSession = Depends(get_db)
):
    """Check whether an RF report file exists (lets the UI avoid iframing a 404 JSON)."""
    settings = get_settings()
    repo = ExecutionRepository(db)
    record = await repo.get(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    try:
        file_path = safe_join(settings.execution_reports_dir, execution_id, filename)
    except ValueError:
        return {"available": False}
    return {"available": file_path.is_file()}

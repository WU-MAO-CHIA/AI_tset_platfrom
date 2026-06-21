import asyncio
import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import AsyncSessionLocal, get_db
from src.core.dependencies import get_current_user
from src.models.case_result import CaseResult
from src.models.execution_media import ExecutionMedia
from src.models.execution_record import ExecutionRecord
from src.repositories.execution_repo import ExecutionRepository
from src.services.report_service import ReportService

router = APIRouter(prefix="/executions", tags=["executions"], dependencies=[Depends(get_current_user)])


@router.get("/{execution_id}")
async def get_execution(execution_id: str, db: AsyncSession = Depends(get_db)):
    repo = ExecutionRepository(db)
    record = await repo.get(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
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
    }


@router.get("/{execution_id}/results")
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


@router.get("/{execution_id}/stream")
async def stream_execution(execution_id: str, db: AsyncSession = Depends(get_db)):
    repo = ExecutionRepository(db)
    record = await repo.get(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    async def event_generator():
        from src.execution.listener import get_execution_queue

        yield f"data: {json.dumps({'event': 'execution_started', 'execution_id': execution_id, 'status': record.status, 'total_cases': record.total_count})}\n\n"

        # If already completed (e.g., no cases), emit completion immediately
        if record.status in ("completed", "failed", "error"):
            yield f"data: {json.dumps({'event': 'execution_completed', 'execution_id': execution_id, 'status': record.status, 'passed': record.passed_count, 'failed': record.failed_count, 'total': record.total_count, 'report_url': f'/api/v1/executions/{execution_id}/results', '__done__': True})}\n\n"
            return

        queue = get_execution_queue(execution_id)
        timeout_ticks = 0
        max_ticks = 600  # 10 minutes

        while timeout_ticks < max_ticks:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                timeout_ticks += 1
                # Fallback DB check every 5 seconds to catch missed done events
                if timeout_ticks % 5 == 0:
                    async with AsyncSessionLocal() as poll_session:
                        poll_repo = ExecutionRepository(poll_session)
                        updated = await poll_repo.get(execution_id)
                    if updated and updated.status in ("completed", "failed", "error"):
                        yield f"data: {json.dumps({'event': 'execution_completed', 'execution_id': execution_id, 'status': updated.status, 'passed': updated.passed_count, 'failed': updated.failed_count, 'total': updated.total_count, 'report_url': f'/api/v1/executions/{execution_id}/results', '__done__': True})}\n\n"
                        return
                continue

            # Strip internal sentinel before sending to client
            send_event = {k: v for k, v in event.items() if k != "__done__"}
            yield f"data: {json.dumps(send_event)}\n\n"

            if event.get("__done__"):
                return

        yield f"data: {json.dumps({'event': 'execution_error', 'execution_id': execution_id, 'message': '執行逾時'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{execution_id}/export")
async def export_report(execution_id: str, db: AsyncSession = Depends(get_db)):
    repo = ExecutionRepository(db)
    record = await repo.get(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    result = await db.execute(
        select(CaseResult).where(CaseResult.execution_id == execution_id).order_by(CaseResult.position)
    )
    case_results = result.scalars().all()

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
            "case_name": cr.test_case_id,
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
        "elapsed_ms": 0,
    }

    report_service = ReportService()
    html_content = report_service.export_report(execution_data, case_result_dicts)

    return HTMLResponse(
        content=html_content,
        headers={"Content-Disposition": f'attachment; filename="report-{execution_id}.html"'},
    )


@router.get("/{execution_id}/rf-report/{filename:path}")
async def get_rf_report(execution_id: str, filename: str, db: AsyncSession = Depends(get_db)):
    from src.core.config import get_settings
    settings = get_settings()
    file_path = os.path.join(settings.execution_reports_dir, execution_id, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="報告尚未生成或不存在")
    return FileResponse(file_path)

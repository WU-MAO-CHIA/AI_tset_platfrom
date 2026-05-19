import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.case_result import CaseResult
from src.models.execution_media import ExecutionMedia
from src.models.execution_record import ExecutionRecord
from src.repositories.execution_repo import ExecutionRepository
from src.services.report_service import ReportService

router = APIRouter(prefix="/executions", tags=["executions"])


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

    result = await db.execute(
        select(CaseResult).where(CaseResult.execution_id == execution_id).order_by(CaseResult.position)
    )
    case_results = result.scalars().all()

    items = []
    for cr in case_results:
        media_result = await db.execute(
            select(ExecutionMedia).where(ExecutionMedia.case_result_id == cr.id).order_by(ExecutionMedia.step_index)
        )
        media_items = [
            {"id": m.id, "media_type": m.media_type, "file_path": m.file_path, "step_index": m.step_index}
            for m in media_result.scalars().all()
        ]
        items.append({
            "id": cr.id,
            "test_case_id": cr.test_case_id,
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
        # Send initial status event
        event = {
            "event": "execution_started",
            "execution_id": execution_id,
            "status": record.status,
        }
        yield f"data: {json.dumps(event)}\n\n"

        # Poll for completion (simple implementation)
        for _ in range(60):
            await asyncio.sleep(1)
            updated = await repo.get(execution_id)
            if updated and updated.status in ("completed", "failed", "error"):
                done_event = {
                    "event": "execution_completed",
                    "execution_id": execution_id,
                    "status": updated.status,
                    "passed": updated.passed_count,
                    "failed": updated.failed_count,
                    "report_url": f"/api/v1/executions/{execution_id}/results",
                }
                yield f"data: {json.dumps(done_event)}\n\n"
                return

        # Timeout
        error_event = {"event": "execution_error", "execution_id": execution_id, "error": "timeout"}
        yield f"data: {json.dumps(error_event)}\n\n"

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

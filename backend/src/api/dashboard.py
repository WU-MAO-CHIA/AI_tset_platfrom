"""管理員監控儀表板：目前執行中、排隊中的執行與已啟用排程，只有 admin 可讀。"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schedules import ScheduleResponse, _iso, _serialize
from src.core.config import get_settings
from src.core.database import get_db
from src.core.dependencies import require_admin
from src.models.execution_record import ExecutionRecord
from src.models.execution_schedule import ExecutionSchedule
from src.models.test_case import TestCase
from src.models.test_checklist import TestChecklist
from src.scheduling.timing import as_utc
from src.services.schedule_service import ScheduleService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class DashboardExecution(BaseModel):
    id: str
    execution_type: str
    status: str
    # 清單執行為清單名稱，試跑為案例名稱
    target_name: Optional[str] = None
    checklist_id: Optional[str] = None
    source_case_id: Optional[str] = None
    schedule_id: Optional[str] = None
    schedule_name: Optional[str] = None
    priority: int
    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    heartbeat_at: Optional[str] = None
    passed_count: int
    failed_count: int
    total_count: int


class DashboardCounts(BaseModel):
    running: int
    pending: int
    schedules_enabled: int
    schedules_total: int


class DashboardResponse(BaseModel):
    generated_at: str
    timezone: str
    max_concurrent: int
    counts: DashboardCounts
    running: list[DashboardExecution]
    # 依 worker 領取順序排列（priority 高者優先、再依 queued_at）
    pending: list[DashboardExecution]
    # 已啟用的排程，依下次執行時間排列
    schedules: list[ScheduleResponse]


async def _serialize_executions(db: AsyncSession, records: list[ExecutionRecord]) -> list[dict]:
    checklist_ids = {r.checklist_id for r in records if r.checklist_id}
    case_ids = {r.source_case_id for r in records if r.source_case_id}
    checklist_names: dict[str, str] = {}
    case_names: dict[str, str] = {}
    if checklist_ids:
        rows = await db.execute(select(TestChecklist.id, TestChecklist.name).where(TestChecklist.id.in_(checklist_ids)))
        checklist_names = dict(rows.all())
    if case_ids:
        rows = await db.execute(select(TestCase.id, TestCase.name).where(TestCase.id.in_(case_ids)))
        case_names = dict(rows.all())
    schedule_names = await ScheduleService(db).names_by_id({r.schedule_id for r in records if r.schedule_id})

    return [
        {
            "id": r.id,
            "execution_type": r.execution_type,
            "status": r.status,
            "target_name": checklist_names.get(r.checklist_id) if r.checklist_id else case_names.get(r.source_case_id),
            "checklist_id": r.checklist_id,
            "source_case_id": r.source_case_id,
            "schedule_id": r.schedule_id,
            "schedule_name": schedule_names.get(r.schedule_id) if r.schedule_id else None,
            "priority": r.priority,
            "queued_at": _iso(r.queued_at),
            "started_at": _iso(r.started_at),
            "heartbeat_at": _iso(r.heartbeat_at),
            "passed_count": r.passed_count,
            "failed_count": r.failed_count,
            "total_count": r.total_count,
        }
        for r in records
    ]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    settings = get_settings()

    running = (await db.execute(
        select(ExecutionRecord)
        .where(ExecutionRecord.status == "running")
        .order_by(ExecutionRecord.started_at)
    )).scalars().all()
    pending = (await db.execute(
        select(ExecutionRecord)
        .where(ExecutionRecord.status == "pending")
        .order_by(ExecutionRecord.priority.desc(), ExecutionRecord.queued_at, ExecutionRecord.created_at)
    )).scalars().all()

    service = ScheduleService(db)
    all_schedules = await service.list_schedules()
    enabled = [s for s in all_schedules if s.enabled]
    # next_run_at 為 null 的排在最後
    enabled.sort(key=lambda s: (s.next_run_at is None, as_utc(s.next_run_at) if s.next_run_at else datetime.min))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timezone": settings.schedule_timezone,
        "max_concurrent": settings.execution_max_concurrent,
        "counts": {
            "running": len(running),
            "pending": len(pending),
            "schedules_enabled": len(enabled),
            "schedules_total": len(all_schedules),
        },
        "running": await _serialize_executions(db, list(running)),
        "pending": await _serialize_executions(db, list(pending)),
        "schedules": await _serialize(service, enabled),
    }

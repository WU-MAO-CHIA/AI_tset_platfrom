"""排程 API（spec 004 第 2 階段）。登入即可讀取，editor 以上可新增、修改、刪除。"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import SuccessResponse
from src.core.database import get_db
from src.core.dependencies import get_current_user, require_editor_or_above
from src.models.execution_schedule import ExecutionSchedule
from src.scheduling.timing import as_utc
from src.services.schedule_service import ScheduleService

router = APIRouter(tags=["schedules"], dependencies=[Depends(get_current_user)])


class ScheduleCreateRequest(BaseModel):
    name: str = Field(max_length=100)
    enabled: bool = True
    frequency: str
    time_of_day: Optional[str] = None
    weekdays: Optional[list[int]] = None
    interval_minutes: Optional[int] = None
    parallel_mode: bool = False
    max_workers: int = 1


class ScheduleUpdateRequest(BaseModel):
    """只更新有帶的欄位（例如只送 enabled 來啟用 / 停用）。"""

    name: Optional[str] = Field(default=None, max_length=100)
    enabled: Optional[bool] = None
    frequency: Optional[str] = None
    time_of_day: Optional[str] = None
    weekdays: Optional[list[int]] = None
    interval_minutes: Optional[int] = None
    parallel_mode: Optional[bool] = None
    max_workers: Optional[int] = None


class ScheduleResponse(BaseModel):
    id: str
    checklist_id: str
    checklist_name: Optional[str] = None
    name: str
    enabled: bool
    frequency: str
    time_of_day: Optional[str] = None
    weekdays: Optional[list[int]] = None
    interval_minutes: Optional[int] = None
    parallel_mode: bool
    max_workers: int
    timezone: str
    next_run_at: Optional[str] = None
    last_triggered_at: Optional[str] = None
    last_execution_id: Optional[str] = None
    last_execution_status: Optional[str] = None
    last_skip_reason: Optional[str] = None
    created_by: str


class ScheduleListResponse(BaseModel):
    items: list[ScheduleResponse]
    total: int


def _iso(value: Optional[datetime]) -> Optional[str]:
    return as_utc(value).isoformat() if value else None


async def _serialize(service: ScheduleService, schedules: list[ExecutionSchedule]) -> list[dict]:
    from src.core.config import get_settings

    tz = get_settings().schedule_timezone
    checklist_names = await service.checklist_names(schedules)
    statuses = await service.last_execution_statuses(schedules)
    return [
        {
            "id": s.id,
            "checklist_id": s.checklist_id,
            "checklist_name": checklist_names.get(s.checklist_id),
            "name": s.name,
            "enabled": s.enabled,
            "frequency": s.frequency,
            "time_of_day": s.time_of_day,
            "weekdays": s.weekdays,
            "interval_minutes": s.interval_minutes,
            "parallel_mode": s.parallel_mode,
            "max_workers": s.max_workers,
            "timezone": tz,
            "next_run_at": _iso(s.next_run_at),
            "last_triggered_at": _iso(s.last_triggered_at),
            "last_execution_id": s.last_execution_id,
            "last_execution_status": statuses.get(s.last_execution_id) if s.last_execution_id else None,
            "last_skip_reason": s.last_skip_reason,
            "created_by": s.created_by,
        }
        for s in schedules
    ]


@router.get("/schedules", response_model=ScheduleListResponse)
async def list_schedules(db: AsyncSession = Depends(get_db)):
    service = ScheduleService(db)
    items = await _serialize(service, await service.list_schedules())
    return {"items": items, "total": len(items)}


@router.get("/checklists/{checklist_id}/schedules", response_model=ScheduleListResponse)
async def list_checklist_schedules(checklist_id: str, db: AsyncSession = Depends(get_db)):
    from src.models.test_checklist import TestChecklist

    if await db.get(TestChecklist, checklist_id) is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    service = ScheduleService(db)
    items = await _serialize(service, await service.list_schedules(checklist_id))
    return {"items": items, "total": len(items)}


@router.post(
    "/checklists/{checklist_id}/schedules",
    status_code=status.HTTP_201_CREATED,
    response_model=ScheduleResponse,
)
async def create_schedule(
    checklist_id: str,
    body: ScheduleCreateRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_editor_or_above),
):
    service = ScheduleService(db)
    schedule = await service.create(checklist_id, created_by=user.username, **body.model_dump())
    if schedule is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return (await _serialize(service, [schedule]))[0]


@router.put(
    "/schedules/{schedule_id}",
    response_model=ScheduleResponse,
    dependencies=[Depends(require_editor_or_above)],
)
async def update_schedule(schedule_id: str, body: ScheduleUpdateRequest, db: AsyncSession = Depends(get_db)):
    service = ScheduleService(db)
    schedule = await service.update(schedule_id, **body.model_dump(exclude_unset=True))
    if schedule is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return (await _serialize(service, [schedule]))[0]


@router.delete(
    "/schedules/{schedule_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(require_editor_or_above)],
)
async def delete_schedule(schedule_id: str, db: AsyncSession = Depends(get_db)):
    if not await ScheduleService(db).delete(schedule_id):
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return {"success": True}

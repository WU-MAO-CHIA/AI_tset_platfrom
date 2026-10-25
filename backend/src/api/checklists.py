from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ExecutionStartResponse, SuccessResponse
from src.core.database import get_db
from src.core.dependencies import get_current_user, require_editor_or_above
from src.services.checklist_service import ChecklistService
from src.services.execution_service import ExecutionService
from src.services.schedule_service import ScheduleService

router = APIRouter(prefix="/checklists", tags=["checklists"], dependencies=[Depends(get_current_user)])

RECENT_RUNS_LIMIT = 10


class ChecklistCreateRequest(BaseModel):
    name: str
    created_by: str
    case_ids: list[str] = []
    description: Optional[str] = None


class ChecklistUpdateRequest(BaseModel):
    name: str
    created_by: str


class ChecklistItemsUpdateRequest(BaseModel):
    case_ids: list[str]


class ChecklistItemTestCaseInfo(BaseModel):
    case_number: Optional[str] = None
    name: Optional[str] = None
    system_category: Optional[str] = None
    runner_environment_id: Optional[str] = None


class ChecklistItemResponse(BaseModel):
    id: str
    test_case_id: str
    position: int
    test_case: Optional[ChecklistItemTestCaseInfo] = None


class ChecklistResponse(BaseModel):
    id: str
    name: str
    created_by: str
    description: Optional[str] = None


class ChecklistDetailResponse(BaseModel):
    id: str
    name: str
    created_by: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    items: list[ChecklistItemResponse]


class ChecklistRecentRun(BaseModel):
    id: str
    status: str
    passed_count: int
    failed_count: int
    total_count: int
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ChecklistListItem(BaseModel):
    id: str
    name: str
    created_by: str
    description: Optional[str] = None
    case_count: int
    status: Optional[str] = None  # 最新一次執行狀態；未執行為 None
    created_at: Optional[str] = None
    recent_runs: list[ChecklistRecentRun] = []  # 最近 RECENT_RUNS_LIMIT 次執行，新到舊


class ChecklistListResponse(BaseModel):
    items: list[ChecklistListItem]
    total: int
    page: int
    page_size: int


class ChecklistExecutionItem(BaseModel):
    id: str
    status: str
    passed_count: int
    failed_count: int
    total_count: int
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    schedule_id: Optional[str] = None
    schedule_name: Optional[str] = None


class ChecklistExecutionsResponse(BaseModel):
    items: list[ChecklistExecutionItem]
    total: int


class ChecklistTestDataItem(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    id: str
    field_name: str
    rf_variable: Optional[str] = None
    field_value: Optional[str] = None
    description: Optional[str] = None
    row_index: Optional[int] = None


class ChecklistCaseItemResponse(BaseModel):
    item_id: str
    test_case_id: str
    position: int
    notes: Optional[str] = None
    actual_values: dict[str, Any]
    test_data: list[ChecklistTestDataItem]
    case_number: Optional[str] = None
    name: Optional[str] = None


class ChecklistCasesResponse(BaseModel):
    items: list[ChecklistCaseItemResponse]
    total: int


class AddCaseRequest(BaseModel):
    case_id: str
    position: Optional[int] = None


class AddCaseResponse(BaseModel):
    item_id: str
    position: int


class PatchCaseItemRequest(BaseModel):
    notes: Optional[str] = None
    position: Optional[int] = None
    actual_values: Optional[dict[str, Any]] = None


class PatchCaseItemResponse(BaseModel):
    item_id: str
    test_case_id: str
    position: Optional[int] = None
    notes: Optional[str] = None
    actual_values: dict[str, Any]


class ReorderCasesRequest(BaseModel):
    case_ids: list[str]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ChecklistResponse, dependencies=[Depends(require_editor_or_above)])
async def create_checklist(
    body: ChecklistCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    try:
        checklist = await service.create(
            name=body.name,
            created_by=body.created_by,
            case_ids=body.case_ids,
            description=body.description or "",
        )
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("case_not_found:"):
            raise HTTPException(status_code=404, detail={"error": "case_not_found", "case_id": msg.split(":")[1]})
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": msg})
    return ChecklistResponse(
        id=checklist.id,
        name=checklist.name,
        created_by=checklist.created_by,
        description=checklist.description,
    )


@router.get("", response_model=ChecklistListResponse)
async def list_checklists(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    keyword: str | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    items, total = await service.list_all(page=page, page_size=page_size, keyword=keyword, sort_by=sort_by, order=order)

    # 補上案例數與最新執行狀態（分組查詢，避免 N+1）
    from sqlalchemy import select, func
    from sqlalchemy.orm import aliased
    from src.models.checklist_item import ChecklistItem
    from src.models.execution_record import ExecutionRecord

    ids = [c.id for c in items]
    case_counts: dict[str, int] = {}
    statuses: dict[str, str] = {}
    recent_runs: dict[str, list[dict]] = {}
    if ids:
        cc = await db.execute(
            select(ChecklistItem.checklist_id, func.count())
            .where(ChecklistItem.checklist_id.in_(ids))
            .group_by(ChecklistItem.checklist_id)
        )
        case_counts = {row[0]: row[1] for row in cc.all()}

        # 每份清單只取最近 RECENT_RUNS_LIMIT 筆（window function），新到舊
        rn = (
            func.row_number()
            .over(
                partition_by=ExecutionRecord.checklist_id,
                order_by=(ExecutionRecord.created_at.desc(), ExecutionRecord.id.desc()),
            )
            .label("rn")
        )
        ranked = (
            select(ExecutionRecord, rn)
            .where(ExecutionRecord.checklist_id.in_(ids))
            .where(ExecutionRecord.status != "deleted")
            .subquery()
        )
        recent = aliased(ExecutionRecord, ranked)
        ex = await db.execute(
            select(recent)
            .where(ranked.c.rn <= RECENT_RUNS_LIMIT)
            .order_by(ranked.c.checklist_id, ranked.c.rn)
        )
        for run in ex.scalars().all():
            if run.checklist_id not in statuses:  # 第一筆即最新
                statuses[run.checklist_id] = run.status
            recent_runs.setdefault(run.checklist_id, []).append(
                {
                    "id": run.id,
                    "status": run.status,
                    "passed_count": run.passed_count,
                    "failed_count": run.failed_count,
                    "total_count": run.total_count,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                }
            )

    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "created_by": c.created_by,
                "description": c.description,
                "case_count": case_counts.get(c.id, 0),
                "status": statuses.get(c.id),
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "recent_runs": recent_runs.get(c.id, []),
            }
            for c in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{checklist_id}", response_model=ChecklistDetailResponse)
async def get_checklist(
    checklist_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    checklist = await service.get_with_items(checklist_id)
    if checklist is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return ChecklistDetailResponse(
        id=checklist.id,
        name=checklist.name,
        created_by=checklist.created_by,
        description=checklist.description,
        created_at=checklist.created_at.isoformat() if checklist.created_at else None,
        items=[
            ChecklistItemResponse(
                id=item.id,
                test_case_id=item.test_case_id,
                position=item.position or 0,
                test_case=ChecklistItemTestCaseInfo(
                    case_number=item.test_case.case_number if item.test_case else None,
                    name=item.test_case.name if item.test_case else None,
                    system_category=item.test_case.system_category if item.test_case else None,
                    runner_environment_id=item.test_case.runner_environment_id if item.test_case else None,
                ) if item.test_case else None,
            )
            for item in sorted(checklist.items, key=lambda x: x.position or 0)
        ],
    )


@router.get("/{checklist_id}/executions", response_model=ChecklistExecutionsResponse)
async def get_checklist_executions(
    checklist_id: str,
    db: AsyncSession = Depends(get_db),
):
    from src.repositories.execution_repo import ExecutionRepository
    from src.repositories.checklist_repo import ChecklistRepository

    cl_repo = ChecklistRepository(db)
    checklist = await cl_repo.get(checklist_id)
    if checklist is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    exec_repo = ExecutionRepository(db)
    records = await exec_repo.get_history_for_checklist(checklist_id)
    schedule_names = await ScheduleService(db).names_by_id({r.schedule_id for r in records})
    return {
        "items": [
            {
                "id": r.id,
                "status": r.status,
                "passed_count": r.passed_count,
                "failed_count": r.failed_count,
                "total_count": r.total_count,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "schedule_id": r.schedule_id,
                "schedule_name": schedule_names.get(r.schedule_id),
            }
            for r in records
        ],
        "total": len(records),
    }


@router.put("/{checklist_id}", response_model=ChecklistResponse, dependencies=[Depends(require_editor_or_above)])
async def update_checklist(
    checklist_id: str,
    body: ChecklistUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    checklist = await service.update_checklist(checklist_id, name=body.name, created_by=body.created_by)
    if checklist is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return ChecklistResponse(
        id=checklist.id,
        name=checklist.name,
        created_by=checklist.created_by,
        description=checklist.description,
    )


@router.delete("/{checklist_id}", response_model=SuccessResponse, dependencies=[Depends(require_editor_or_above)])
async def delete_checklist(
    checklist_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    try:
        deleted = await service.delete_checklist(checklist_id)
    except ValueError as exc:
        msg = str(exc)
        if msg.startswith("checklist_in_use:"):
            active = msg.split(":")[1].split(",")
            raise HTTPException(
                status_code=409,
                detail={"error": "checklist_in_use", "active_executions": active},
            )
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": msg})
    if not deleted:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return {"success": True}


@router.get("/{checklist_id}/cases", response_model=ChecklistCasesResponse)
async def get_checklist_cases(
    checklist_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    items = await service.list_checklist_cases(checklist_id)
    if items is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return {"items": items, "total": len(items)}


@router.post("/{checklist_id}/cases", status_code=status.HTTP_201_CREATED, response_model=AddCaseResponse, dependencies=[Depends(require_editor_or_above)])
async def add_case_to_checklist(
    checklist_id: str,
    body: AddCaseRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    try:
        result = await service.add_case(checklist_id, body.case_id, body.position)
    except ValueError as exc:
        msg = str(exc)
        if "case_not_found" in msg:
            raise HTTPException(status_code=404, detail={"error": "case_not_found"})
        if "case_already_in_checklist" in msg:
            raise HTTPException(status_code=409, detail={"error": "case_already_in_checklist"})
        if "checklist_not_found" in msg:
            raise HTTPException(status_code=404, detail={"error": "not_found"})
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": msg})
    return result


@router.delete("/{checklist_id}/cases/{case_id}", response_model=SuccessResponse, dependencies=[Depends(require_editor_or_above)])
async def remove_case_from_checklist(
    checklist_id: str,
    case_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    try:
        await service.remove_case(checklist_id, case_id)
    except ValueError as exc:
        msg = str(exc)
        if "case_not_in_checklist" in msg or "checklist_not_found" in msg:
            raise HTTPException(status_code=404, detail={"error": "not_found"})
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": msg})
    return {"success": True}


@router.patch("/{checklist_id}/cases/{case_id}", response_model=PatchCaseItemResponse, dependencies=[Depends(require_editor_or_above)])
async def patch_checklist_case_item(
    checklist_id: str,
    case_id: str,
    body: PatchCaseItemRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    try:
        result = await service.update_case_item(
            checklist_id,
            case_id,
            notes=body.notes,
            position=body.position,
            actual_values=body.actual_values if body.actual_values is not None else None,
            clear_actual_values=("actual_values" in body.model_fields_set and body.actual_values is None),
        )
    except ValueError as exc:
        msg = str(exc)
        if "case_not_in_checklist" in msg or "checklist_not_found" in msg:
            raise HTTPException(status_code=404, detail={"error": "not_found"})
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": msg})
    if result is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return result


@router.put("/{checklist_id}/cases/reorder", response_model=SuccessResponse, dependencies=[Depends(require_editor_or_above)])
async def reorder_checklist_cases(
    checklist_id: str,
    body: ReorderCasesRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    try:
        await service.reorder_cases(checklist_id, body.case_ids)
    except ValueError as exc:
        msg = str(exc)
        if "checklist_not_found" in msg:
            raise HTTPException(status_code=404, detail={"error": "not_found"})
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": msg})
    return {"success": True}


class ExecuteRequest(BaseModel):
    parallel_mode: bool = False
    max_workers: int = 1
    # 這次把整批網頁 / 桌面案例改送到指定環境（spec 005）；未指定時用各案例的預設環境
    linux_environment_id: Optional[str] = None
    windows_environment_id: Optional[str] = None


@router.post("/{checklist_id}/execute", status_code=status.HTTP_202_ACCEPTED, response_model=ExecutionStartResponse, dependencies=[Depends(require_editor_or_above)])
async def execute_checklist(
    checklist_id: str,
    body: ExecuteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    checklist = await service.get_with_items(checklist_id)
    if checklist is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    from src.services.runner_environment_service import RunnerEnvironmentService
    env_service = RunnerEnvironmentService(db)
    try:
        await env_service.require_kind(body.linux_environment_id, "linux")
        await env_service.require_kind(body.windows_environment_id, "windows")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": str(exc)})

    exec_service = ExecutionService(db)
    record = await exec_service.run_checklist_parallel(
        checklist_id=checklist_id,
        parallel_mode=body.parallel_mode,
        max_workers=body.max_workers,
        linux_environment_id=body.linux_environment_id,
        windows_environment_id=body.windows_environment_id,
    )
    return {
        "execution_id": record.id,
        "stream_url": f"/api/v1/executions/{record.id}/stream",
    }


@router.put("/{checklist_id}/items", response_model=ChecklistDetailResponse, dependencies=[Depends(require_editor_or_above)])
async def update_checklist_items(
    checklist_id: str,
    body: ChecklistItemsUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    checklist = await service.update_items(checklist_id, body.case_ids)
    if checklist is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return ChecklistDetailResponse(
        id=checklist.id,
        name=checklist.name,
        created_by=checklist.created_by,
        description=checklist.description,
        items=[
            ChecklistItemResponse(id=item.id, test_case_id=item.test_case_id, position=item.position or 0)
            for item in checklist.items
        ],
    )

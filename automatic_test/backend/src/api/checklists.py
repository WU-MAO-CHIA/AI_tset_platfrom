from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.services.checklist_service import ChecklistService
from src.services.execution_service import ExecutionService

router = APIRouter(prefix="/checklists", tags=["checklists"])


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


class ChecklistItemResponse(BaseModel):
    id: str
    test_case_id: str
    position: int


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
    items: list[ChecklistItemResponse]


class ChecklistCaseItemResponse(BaseModel):
    item_id: str
    test_case_id: str
    position: int
    notes: Optional[str] = None
    case_number: Optional[str] = None
    name: Optional[str] = None


class AddCaseRequest(BaseModel):
    case_id: str
    position: Optional[int] = None


class PatchCaseItemRequest(BaseModel):
    notes: Optional[str] = None
    position: Optional[int] = None


class ReorderCasesRequest(BaseModel):
    case_ids: list[str]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ChecklistResponse)
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


@router.get("", response_model=dict)
async def list_checklists(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    items, total = await service.list_all(page=page, page_size=page_size)
    return {
        "items": [
            {"id": c.id, "name": c.name, "created_by": c.created_by, "description": c.description}
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
        items=[
            ChecklistItemResponse(id=item.id, test_case_id=item.test_case_id, position=item.position or 0)
            for item in checklist.items
        ],
    )


@router.put("/{checklist_id}", response_model=ChecklistResponse)
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


@router.delete("/{checklist_id}")
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


@router.get("/{checklist_id}/cases", response_model=dict)
async def get_checklist_cases(
    checklist_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    items = await service.list_checklist_cases(checklist_id)
    if items is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return {"items": items, "total": len(items)}


@router.post("/{checklist_id}/cases", status_code=status.HTTP_201_CREATED)
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


@router.delete("/{checklist_id}/cases/{case_id}")
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


@router.patch("/{checklist_id}/cases/{case_id}")
async def patch_checklist_case_item(
    checklist_id: str,
    case_id: str,
    body: PatchCaseItemRequest,
    db: AsyncSession = Depends(get_db),
):
    service = ChecklistService(db)
    try:
        result = await service.update_case_item(
            checklist_id, case_id, notes=body.notes, position=body.position
        )
    except ValueError as exc:
        msg = str(exc)
        if "case_not_in_checklist" in msg or "checklist_not_found" in msg:
            raise HTTPException(status_code=404, detail={"error": "not_found"})
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": msg})
    if result is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return result


@router.put("/{checklist_id}/cases/reorder")
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


@router.post("/{checklist_id}/execute", status_code=status.HTTP_202_ACCEPTED)
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

    exec_service = ExecutionService(db)
    record = await exec_service.run_checklist_parallel(
        checklist_id=checklist_id,
        parallel_mode=body.parallel_mode,
        max_workers=body.max_workers,
    )
    return {
        "execution_id": record.id,
        "stream_url": f"/api/v1/executions/{record.id}/stream",
    }


@router.put("/{checklist_id}/items", response_model=ChecklistDetailResponse)
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

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

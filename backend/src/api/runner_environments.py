"""執行環境 API（spec 005）。登入即可讀取，admin 才能新增、修改、刪除；token 永不回傳。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import SuccessResponse
from src.core.database import get_db
from src.core.dependencies import get_current_user, require_admin, require_editor_or_above
from src.models.runner_environment import BUILTIN_ENVIRONMENT_ID, KIND_LINUX, RunnerEnvironment
from src.services.runner_environment_service import (
    BUILTIN_ENVIRONMENT_NAME,
    BUILTIN_TARGET,
    EnvironmentUnavailable,
    RunnerEnvironmentService,
    check_health,
    get_health,
    mark_unauthorized,
)

router = APIRouter(prefix="/runner-environments", tags=["runner-environments"])


class EnvironmentCreateRequest(BaseModel):
    name: str = Field(max_length=100)
    kind: str
    url: str = Field(max_length=500)
    token: str = Field(max_length=500)
    enabled: bool = True


class EnvironmentUpdateRequest(BaseModel):
    """只更新有帶的欄位；token 留空表示不變。"""

    name: Optional[str] = Field(default=None, max_length=100)
    url: Optional[str] = Field(default=None, max_length=500)
    token: Optional[str] = Field(default=None, max_length=500)
    enabled: Optional[bool] = None


class EnvironmentResponse(BaseModel):
    id: str
    name: str
    kind: str
    enabled: bool
    is_builtin: bool
    url: Optional[str] = None  # 只有 admin 看得到
    status: str
    checked_at: Optional[str] = None


class EnvironmentListResponse(BaseModel):
    items: list[EnvironmentResponse]
    total: int


def _builtin() -> dict:
    return {
        "id": BUILTIN_ENVIRONMENT_ID,
        "name": BUILTIN_ENVIRONMENT_NAME,
        "kind": KIND_LINUX,
        "enabled": True,
        "is_builtin": True,
        "url": None,
        **get_health(BUILTIN_ENVIRONMENT_ID),
    }


def _serialize(row: RunnerEnvironment, is_admin: bool) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "kind": row.kind,
        "enabled": row.enabled,
        "is_builtin": False,
        "url": row.url if is_admin else None,
        **get_health(row.id),
    }


@router.get("", response_model=EnvironmentListResponse)
async def list_environments(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    is_admin = user.role == "admin"
    rows = await RunnerEnvironmentService(db).list_rows()
    items = [_builtin()] + [_serialize(r, is_admin) for r in rows]
    return {"items": items, "total": len(items)}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=EnvironmentResponse,
             dependencies=[Depends(require_admin)])
async def create_environment(body: EnvironmentCreateRequest, db: AsyncSession = Depends(get_db)):
    service = RunnerEnvironmentService(db)
    try:
        row = await service.create(**body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": str(exc)})
    await db.commit()
    await check_health(service.to_target(row))
    return _serialize(row, True)


@router.put("/{environment_id}", response_model=EnvironmentResponse, dependencies=[Depends(require_admin)])
async def update_environment(environment_id: str, body: EnvironmentUpdateRequest, db: AsyncSession = Depends(get_db)):
    service = RunnerEnvironmentService(db)
    try:
        row = await service.update(environment_id, **body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": str(exc)})
    if row is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    await db.commit()
    if row.enabled:
        try:
            await check_health(service.to_target(row))
        except EnvironmentUnavailable:
            mark_unauthorized(row.id)
    return _serialize(row, True)


@router.delete("/{environment_id}", response_model=SuccessResponse, dependencies=[Depends(require_admin)])
async def delete_environment(environment_id: str, db: AsyncSession = Depends(get_db)):
    try:
        deleted = await RunnerEnvironmentService(db).delete(environment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": str(exc)})
    if not deleted:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return {"success": True}


@router.post("/{environment_id}/check", response_model=EnvironmentResponse)
async def check_environment(environment_id: str, db: AsyncSession = Depends(get_db),
                            user=Depends(require_editor_or_above)):
    is_admin = user.role == "admin"
    if environment_id == BUILTIN_ENVIRONMENT_ID:
        await check_health(BUILTIN_TARGET)
        return _builtin()
    service = RunnerEnvironmentService(db)
    row = await service.get_row(environment_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    try:
        await check_health(service.to_target(row))
    except EnvironmentUnavailable:
        mark_unauthorized(row.id)
    return _serialize(row, is_admin)

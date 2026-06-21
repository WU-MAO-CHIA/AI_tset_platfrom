from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import require_admin
from src.services.user_service import UserService
from src.services.system_category_service import SystemCategoryService
from src.services.app_setting_service import AppSettingService

router = APIRouter(prefix="/admin", tags=["admin"])


# ──────────────────────────── 帳號管理 ────────────────────────────

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"


class UpdateUserRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    new_password: str | None = None


@router.get("/users", dependencies=[Depends(require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    svc = UserService(db)
    users = await svc.list_all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.post("/users", status_code=201, dependencies=[Depends(require_admin)])
async def create_user(body: CreateUserRequest, db: AsyncSession = Depends(get_db)):
    svc = UserService(db)
    user = await svc.create(body.username, body.password, body.role)
    await db.commit()
    return {"id": user.id, "username": user.username, "role": user.role}


@router.put("/users/{user_id}", dependencies=[Depends(require_admin)])
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    if body.role is not None:
        await svc.update_role(user_id, body.role)
    if body.is_active is not None:
        await svc.set_active(user_id, body.is_active)
    if body.new_password is not None:
        await svc.reset_password(user_id, body.new_password)
    await db.commit()
    return {"updated": True}


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(
    user_id: str,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    await svc.delete(user_id, current_user.id)
    await db.commit()
    return {"deleted": True}


# ──────────────────────────── 系統別管理 ────────────────────────────

class CreateCategoryRequest(BaseModel):
    name: str


class RenameCategoryRequest(BaseModel):
    name: str


@router.get("/system-categories", dependencies=[Depends(require_admin)])
async def list_system_categories(db: AsyncSession = Depends(get_db)):
    svc = SystemCategoryService(db)
    categories = await svc.list()
    return [
        {"id": c.id, "name": c.name, "created_at": c.created_at.isoformat()}
        for c in categories
    ]


@router.post("/system-categories", status_code=201, dependencies=[Depends(require_admin)])
async def create_system_category(body: CreateCategoryRequest, db: AsyncSession = Depends(get_db)):
    svc = SystemCategoryService(db)
    category = await svc.create(body.name)
    await db.commit()
    return {"id": category.id, "name": category.name}


@router.put("/system-categories/{category_id}", dependencies=[Depends(require_admin)])
async def rename_system_category(
    category_id: str, body: RenameCategoryRequest, db: AsyncSession = Depends(get_db)
):
    svc = SystemCategoryService(db)
    category = await svc.rename(category_id, body.name)
    await db.commit()
    return {"id": category.id, "name": category.name}


@router.delete("/system-categories/{category_id}", dependencies=[Depends(require_admin)])
async def delete_system_category(category_id: str, db: AsyncSession = Depends(get_db)):
    svc = SystemCategoryService(db)
    result = await svc.delete(category_id)
    await db.commit()
    return result


# ──────────────────────────── LLM API Key 管理 ────────────────────────────

class SetLlmKeyRequest(BaseModel):
    key: str


@router.get("/llm-keys", dependencies=[Depends(require_admin)])
async def get_llm_key_status(db: AsyncSession = Depends(get_db)):
    svc = AppSettingService(db)
    return await svc.get_llm_keys()


@router.put("/llm-keys/{provider}", dependencies=[Depends(require_admin)])
async def set_llm_key(provider: str, body: SetLlmKeyRequest, db: AsyncSession = Depends(get_db)):
    svc = AppSettingService(db)
    await svc.set_llm_key(provider, body.key)
    await db.commit()
    return {"updated": True}

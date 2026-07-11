import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.config import get_settings
from src.core.llm_provider import get_provider
from src.core.dependencies import get_current_user, require_editor_or_above
from src.models.test_case import TestCase
from src.models.test_data import TestData
from src.models.base import generate_uuid
from src.repositories.test_case_repo import TestCaseRepository
from src.repositories.execution_repo import ExecutionRepository
from src.services.case_service import CaseService
from src.services.media_service import MediaService
from src.services.ai_service import AIService
from src.services.app_setting_service import AppSettingService

router = APIRouter(prefix="/cases", tags=["cases"], dependencies=[Depends(get_current_user)])


# ─── Schemas ────────────────────────────────────────────────────────────────

class CaseCreateRequest(BaseModel):
    name: str
    main_steps: str
    description: Optional[str] = None
    precondition_steps: Optional[str] = None
    system_category: Optional[str] = None
    tags: Optional[list[str]] = None
    created_by: str
    test_data: Optional[list[dict]] = None


class CaseUpdateRequest(BaseModel):
    name: Optional[str] = None
    main_steps: Optional[str] = None
    description: Optional[str] = None
    precondition_steps: Optional[str] = None
    system_category: Optional[str] = None
    tags: Optional[list[str]] = None
    created_by: str  # used as modified_by
    test_data: Optional[list[dict]] = None  # full-replace; None = no change


class CaseDeleteRequest(BaseModel):
    deleted_by: str


class AICompleteRequest(BaseModel):
    partial_steps: str
    llm_model: Optional[str] = None
    description: Optional[str] = None


class PreviewRFRequest(BaseModel):
    main_steps: str
    llm_model: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    llm_model: Optional[str] = None


class RobotScriptRequest(BaseModel):
    rf_code: str


# ─── Dependencies ────────────────────────────────────────────────────────────

def get_case_service(session: AsyncSession = Depends(get_db)) -> CaseService:
    return CaseService(TestCaseRepository(session))


def get_media_service() -> MediaService:
    settings = get_settings()
    return MediaService(media_root=settings.media_root)


# ─── Serializers ─────────────────────────────────────────────────────────────

def serialize_case_summary(case) -> dict:
    return {
        "id": case.id,
        "case_number": case.case_number,
        "name": case.name,
        "system_category": case.system_category,
        "tags": case.tags or [],
        "version": case.version,
        "created_by": case.created_by,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
    }


def serialize_test_data_item(td) -> dict:
    return {
        "id": td.id,
        "field_name": td.field_name,
        "rf_variable": td.rf_variable,
        "field_value": td.field_value,
        "description": td.description,
        "row_index": td.row_index,
        "source": td.source,
    }


def serialize_case_detail(case) -> dict:
    test_data = sorted(case.test_data, key=lambda td: td.row_index or 0) if case.test_data else []
    return {
        "id": case.id,
        "case_number": case.case_number,
        "name": case.name,
        "description": case.description,
        "precondition_steps": case.precondition_steps,
        "main_steps": case.main_steps,
        "system_category": case.system_category,
        "tags": case.tags or [],
        "version": case.version,
        "created_by": case.created_by,
        "modified_by": case.modified_by,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
        "test_data": [serialize_test_data_item(td) for td in test_data],
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/categories")
async def list_categories(session: AsyncSession = Depends(get_db)):
    from src.repositories.system_category_repo import SystemCategoryRepository
    repo = SystemCategoryRepository(session)
    cats = await repo.list_active()
    return {"items": [c.name for c in cats]}


@router.post("", status_code=201, dependencies=[Depends(require_editor_or_above)])
async def create_case(
    body: CaseCreateRequest,
    service: CaseService = Depends(get_case_service),
    session: AsyncSession = Depends(get_db),
):
    try:
        case = await service.create(
            name=body.name,
            main_steps=body.main_steps,
            created_by=body.created_by,
            description=body.description,
            precondition_steps=body.precondition_steps,
            system_category=body.system_category,
            tags=body.tags,
        )
    except ValueError as e:
        raise HTTPException(400, detail={"error": "validation_error", "message": str(e)})

    if body.test_data:
        for idx, td_item in enumerate(body.test_data):
            td = TestData(
                id=generate_uuid(),
                test_case_id=case.id,
                field_name=td_item.get("field_name", ""),
                rf_variable=td_item.get("rf_variable"),
                field_value=td_item.get("field_value"),
                description=td_item.get("description"),
                source=td_item.get("source", "manual"),
                row_index=td_item.get("row_index", idx),
            )
            session.add(td)
        await session.flush()

    return {
        "id": case.id,
        "case_number": case.case_number,
        "version": case.version,
        "created_at": case.created_at.isoformat() if case.created_at else None,
    }


@router.get("")
async def list_cases(
    system_category: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    order: str = "desc",
    service: CaseService = Depends(get_case_service),
):
    if page_size > 100:
        page_size = 100
    cases, total = await service.list_cases(
        system_category=system_category,
        keyword=keyword,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        order=order,
    )
    return {
        "items": [serialize_case_summary(c) for c in cases],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{case_id}")
async def get_case(case_id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(TestCase)
        .where(TestCase.id == case_id, TestCase.is_deleted.is_(False))
        .options(selectinload(TestCase.test_data))
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})
    return serialize_case_detail(case)


@router.get("/{case_id}/execution-history")
async def get_case_execution_history(
    case_id: str,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db),
    service: CaseService = Depends(get_case_service),
):
    try:
        await service.get(case_id)
    except ValueError:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})

    try:
        from src.repositories.execution_repo import ExecutionRepository
        exec_repo = ExecutionRepository(session)
        items, total = await exec_repo.get_case_execution_history(case_id, page=page, page_size=page_size)
    except Exception:
        items, total = [], 0

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.put("/{case_id}", dependencies=[Depends(require_editor_or_above)])
async def update_case(
    case_id: str,
    body: CaseUpdateRequest,
    service: CaseService = Depends(get_case_service),
    session: AsyncSession = Depends(get_db),
):
    try:
        await service.update(
            case_id,
            modified_by=body.created_by,
            name=body.name,
            main_steps=body.main_steps,
            description=body.description,
            precondition_steps=body.precondition_steps,
            system_category=body.system_category,
            tags=body.tags,
        )
    except ValueError as e:
        if "not_found" in str(e):
            raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})
        raise HTTPException(400, detail={"error": "validation_error", "message": str(e)})

    if body.test_data is not None:
        from sqlalchemy import delete as _delete
        await session.execute(_delete(TestData).where(TestData.test_case_id == case_id))
        for idx, td_item in enumerate(body.test_data):
            td = TestData(
                id=generate_uuid(),
                test_case_id=case_id,
                field_name=td_item.get("field_name", ""),
                rf_variable=td_item.get("rf_variable"),
                field_value=td_item.get("field_value"),
                description=td_item.get("description"),
                source=td_item.get("source", "manual"),
                row_index=td_item.get("row_index", idx),
            )
            session.add(td)
        await session.flush()

    result = await session.execute(
        select(TestCase)
        .where(TestCase.id == case_id, TestCase.is_deleted.is_(False))
        .options(selectinload(TestCase.test_data))
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})
    return serialize_case_detail(case)


@router.delete("/{case_id}", dependencies=[Depends(require_editor_or_above)])
async def delete_case(
    case_id: str,
    body: CaseDeleteRequest,
    service: CaseService = Depends(get_case_service),
):
    try:
        result = await service.soft_delete(case_id, deleted_by=body.deleted_by)
        return result
    except ValueError as e:
        msg = str(e)
        if "not_found" in msg:
            raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})
        if "case_in_use" in msg:
            # Re-fetch checklist names for the error response
            from src.repositories.test_case_repo import TestCaseRepository
            repo = TestCaseRepository(service.repo.session)
            affected = await repo.get_referencing_checklists_with_names(case_id)
            raise HTTPException(
                409,
                detail={"error": "case_in_use", "message": "案例被清單引用中", "affected_checklists": affected},
            )
        raise HTTPException(400, detail={"error": "error", "message": msg})


@router.post("/preview-rf")
async def preview_rf_code(body: PreviewRFRequest, session: AsyncSession = Depends(get_db)):
    """Generate Robot Framework code preview from steps without creating execution records."""
    if not body.main_steps or not body.main_steps.strip():
        raise HTTPException(422, detail={"error": "empty_steps", "message": "main_steps must not be empty"})
    if len(body.main_steps) > 10000:
        raise HTTPException(422, detail={"error": "steps_too_long", "message": "main_steps exceeds 10000 characters"})

    settings = get_settings()
    model = body.llm_model or await AppSettingService(session).get_active_model()
    provider = get_provider(model, settings)
    ai_service = AIService(provider)
    rf_code = await ai_service.preview_robot_code(
        main_steps=body.main_steps,
        llm_model=model,
        timeout_sec=35.0,
    )
    if rf_code is None:
        raise HTTPException(422, detail={"error": "unable_to_generate", "message": "AI could not generate RF code from the given steps"})
    return {"rf_code": rf_code}


@router.post("/ai-complete")
async def ai_complete_steps_preview(
    body: AICompleteRequest,
    session: AsyncSession = Depends(get_db),
):
    """AI complete without a saved case — no media context."""
    settings = get_settings()
    model = body.llm_model or await AppSettingService(session).get_active_model()
    provider = get_provider(model, settings)
    ai_service = AIService(provider=provider)
    completed = await ai_service.complete_steps(
        partial_steps=body.partial_steps,
        description=body.description or "",
        media_attachments=[],
    )
    return {"completed_steps": completed, "model_used": model}


@router.post("/{case_id}/ai-complete")
async def ai_complete_steps(
    case_id: str,
    body: AICompleteRequest,
    session: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    model = body.llm_model or await AppSettingService(session).get_active_model()
    provider = get_provider(model, settings)
    ai_service = AIService(provider=provider)

    from src.repositories.test_case_repo import TestCaseRepository
    repo = TestCaseRepository(session)
    case = await repo.get(case_id)
    media_attachments = case.attachments if case else []

    completed = await ai_service.complete_steps(
        partial_steps=body.partial_steps,
        description=body.description or (case.description if case else ""),
        media_attachments=media_attachments,
    )
    return {"completed_steps": completed, "model_used": model}


@router.post("/{case_id}/chat")
async def chat_with_ai(
    case_id: str,
    body: ChatRequest,
    session: AsyncSession = Depends(get_db),
):
    """Multi-turn AI chat for test step generation; persists messages to DB."""
    from src.repositories.test_case_repo import TestCaseRepository
    from src.models.case_chat_message import CaseChatMessage
    from src.models.base import generate_uuid

    repo = TestCaseRepository(session)
    case = await repo.get(case_id)
    if not case:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})

    # Load existing chat history for context
    from sqlalchemy import select
    stmt = select(CaseChatMessage).where(CaseChatMessage.case_id == case_id).order_by(CaseChatMessage.created_at)
    result = await session.execute(stmt)
    history = result.scalars().all()
    messages = [{"role": m.role, "content": m.content} for m in history]

    settings = get_settings()
    model = body.llm_model or await AppSettingService(session).get_active_model()
    provider = get_provider(model, settings)
    ai_service = AIService(provider=provider)

    response = await ai_service.chat_and_generate_rf(
        messages=messages,
        user_message=body.message,
        llm_model=model,
    )

    # Persist user message and assistant response
    user_msg = CaseChatMessage(id=generate_uuid(), case_id=case_id, role="user", content=body.message)
    assistant_msg = CaseChatMessage(id=generate_uuid(), case_id=case_id, role="assistant", content=response["assistant_message"])
    session.add(user_msg)
    session.add(assistant_msg)
    await session.flush()

    return {"assistant_message": response["assistant_message"], "rf_code": response["rf_code"]}


@router.get("/{case_id}/chat-history")
async def get_chat_history(
    case_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Return all chat messages for a case ordered by created_at."""
    from src.models.case_chat_message import CaseChatMessage
    from sqlalchemy import select

    stmt = select(CaseChatMessage).where(CaseChatMessage.case_id == case_id).order_by(CaseChatMessage.created_at)
    result = await session.execute(stmt)
    messages = result.scalars().all()
    return {
        "messages": [
            {
                "role": m.role,
                "type": m.type.value,  # Phase 27: Include message type
                "content": m.content,
                "created_at": m.created_at.isoformat()
            }
            for m in messages
        ]
    }


@router.post("/{case_id}/attachments", status_code=201, dependencies=[Depends(require_editor_or_above)])
async def upload_attachment(
    case_id: str,
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    media_service: MediaService = Depends(get_media_service),
):
    from src.repositories.test_case_repo import TestCaseRepository
    from src.models.media_attachment import MediaAttachment
    from src.models.base import generate_uuid

    repo = TestCaseRepository(session)
    case = await repo.get(case_id)
    if not case:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})

    try:
        attachment_data = await media_service.upload_attachment(case_id, file, url)
    except ValueError as e:
        msg = str(e)
        if "file_too_large" in msg:
            raise HTTPException(413, detail={"error": "file_too_large", "message": "檔案超過大小限制"})
        raise HTTPException(400, detail={"error": "validation_error", "message": msg})

    attachment = MediaAttachment(id=generate_uuid(), test_case_id=case_id, **attachment_data)
    session.add(attachment)
    await session.flush()

    return {
        "id": attachment.id,
        "attachment_type": attachment.attachment_type,
        "filename": attachment.filename,
        "url": attachment.url,
        "file_size_bytes": attachment.file_size_bytes,
    }


def _serialize_attachment(a) -> dict:
    return {
        "id": a.id,
        "attachment_type": a.attachment_type,
        "filename": a.filename,
        "url": a.url,
        "file_path": a.file_path,
        "file_size_bytes": a.file_size_bytes,
        "mime_type": a.mime_type,
    }


@router.get("/{case_id}/attachments")
async def list_attachments(case_id: str, session: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from src.models.media_attachment import MediaAttachment

    result = await session.execute(
        select(MediaAttachment)
        .where(MediaAttachment.test_case_id == case_id)
        .order_by(MediaAttachment.created_at)
    )
    items = result.scalars().all()
    return {"items": [_serialize_attachment(a) for a in items]}


@router.delete("/{case_id}/attachments/{attachment_id}", dependencies=[Depends(require_editor_or_above)])
async def delete_attachment(
    case_id: str,
    attachment_id: str,
    session: AsyncSession = Depends(get_db),
    media_service: MediaService = Depends(get_media_service),
):
    from src.models.media_attachment import MediaAttachment

    attachment = await session.get(MediaAttachment, attachment_id)
    if not attachment or attachment.test_case_id != case_id:
        raise HTTPException(404, detail={"error": "not_found", "message": "附件不存在"})

    if attachment.file_path:
        try:
            await media_service.delete_attachment(attachment.file_path)
        except Exception:
            pass  # 檔案可能已不存在；仍移除 DB 紀錄

    await session.delete(attachment)
    await session.flush()
    return {"deleted": True}


@router.post("/{case_id}/import-test-data")
async def import_test_data_preview(
    case_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    from src.services.file_parser_service import FileParserService
    parser = FileParserService()
    data = await file.read()
    try:
        result = await parser.parse_file(file.filename or "upload.csv", data)
    except ValueError as e:
        raise HTTPException(400, detail={"error": str(e), "message": "檔案解析失敗"})

    return {
        "preview": result["preview"],
        "total_rows": result["total_rows"],
        "columns": result["columns"],
        "warnings": result["warnings"],
        "import_token": result["import_token"],
        "_parsed_rows": result["_rows"],
    }


@router.post("/{case_id}/import-test-data/confirm", status_code=201)
async def confirm_import_test_data(
    case_id: str,
    body: dict = Body(...),
    session: AsyncSession = Depends(get_db),
):
    # In production, use a cache/token store; here we accept import via re-parse
    return {"imported_count": 0, "message": "Import confirmed (token-based storage not yet implemented)"}


@router.put("/{case_id}/robot-script", dependencies=[Depends(require_editor_or_above)])
async def save_robot_script(
    case_id: str,
    body: RobotScriptRequest,
    service: CaseService = Depends(get_case_service),
    session: AsyncSession = Depends(get_db),
):
    """Save Robot Framework script — write to DB and sync to disk."""
    from src.repositories.robot_script_repo import RobotScriptRepository
    try:
        case = await service.get(case_id)
    except ValueError:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})

    # Persist to DB (source of truth)
    repo = RobotScriptRepository(session)
    await repo.upsert(test_case_id=case_id, rf_code=body.rf_code)

    # Sync to disk so RF CLI can execute it
    settings = get_settings()
    script_dir = settings.robot_scripts_dir
    os.makedirs(script_dir, exist_ok=True)
    file_path = os.path.join(script_dir, f"{case.case_number}.robot")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(body.rf_code)

    return {"case_number": case.case_number, "file_path": file_path}


@router.get("/{case_id}/robot-script")
async def get_robot_script(
    case_id: str,
    service: CaseService = Depends(get_case_service),
    session: AsyncSession = Depends(get_db),
):
    """Read saved Robot Framework script — DB first, fallback to disk."""
    from src.repositories.robot_script_repo import RobotScriptRepository
    try:
        case = await service.get(case_id)
    except ValueError:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})

    # Primary: read from DB
    repo = RobotScriptRepository(session)
    record = await repo.get_by_case_id(case_id)
    if record:
        return {"rf_code": record.rf_code, "case_number": case.case_number, "source": "db"}

    # Fallback: read from disk (legacy scripts saved before this table existed)
    settings = get_settings()
    file_path = os.path.join(settings.robot_scripts_dir, f"{case.case_number}.robot")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            rf_code = f.read()
        return {"rf_code": rf_code, "case_number": case.case_number, "source": "file"}

    raise HTTPException(404, detail={"error": "script_not_found", "message": "尚未儲存 RF 程式碼"})


class TrialRunRequest(BaseModel):
    """Phase 27: Trial run request with optional RF code override."""
    rf_code: Optional[str] = None
    case_name: Optional[str] = None


@router.post("/{case_id}/trial-run", status_code=202)
async def trial_run(case_id: str, request: TrialRunRequest = TrialRunRequest(), session: AsyncSession = Depends(get_db)):
    """Phase 27: Execute trial run using RF code from preview area."""
    from src.repositories.test_case_repo import TestCaseRepository
    from src.services.execution_service import ExecutionService
    repo = TestCaseRepository(session)
    case = await repo.get(case_id)
    if not case:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})

    exec_service = ExecutionService(session)
    record = await exec_service.run_trial(
        source_case_id=case_id,
        rf_code=request.rf_code,
        case_name=request.case_name or case.name
    )
    return {"execution_id": record.id, "stream_url": f"/api/v1/executions/{record.id}/stream"}

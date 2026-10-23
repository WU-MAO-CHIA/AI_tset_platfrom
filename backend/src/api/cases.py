import os
from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import DeletedResponse, ExecutionStartResponse, SuccessResponse
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

RfContextMode = Literal["full", "summary", "none"]


class CaseTestDataInput(BaseModel):
    """test_data 單筆；預設值沿用先前 dict.get() 的 fallback。匯入的數值一律轉成字串存。"""
    model_config = ConfigDict(coerce_numbers_to_str=True)

    field_name: str = ""
    rf_variable: Optional[str] = None
    field_value: Optional[str] = None
    description: Optional[str] = None
    source: str = "manual"
    row_index: Optional[int] = None  # 未提供時以陣列順序補上


class ChatTurnInput(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class CaseCreateRequest(BaseModel):
    name: str
    main_steps: str
    description: Optional[str] = None
    precondition_steps: Optional[str] = None
    system_category: Optional[str] = None
    tags: Optional[list[str]] = None
    created_by: str
    test_data: Optional[list[CaseTestDataInput]] = None


class CaseUpdateRequest(BaseModel):
    name: Optional[str] = None
    main_steps: Optional[str] = None
    description: Optional[str] = None
    precondition_steps: Optional[str] = None
    system_category: Optional[str] = None
    tags: Optional[list[str]] = None
    created_by: str  # used as modified_by
    test_data: Optional[list[CaseTestDataInput]] = None  # full-replace; None = no change


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
    rf_context_mode: Optional[RfContextMode] = "full"
    catalog: Optional[list[dict[str, Any]]] = None  # 頁面探索結果，欄位由 agent 決定


class ChatPreviewRequest(BaseModel):
    """Stateless chat (case-creation page): no case_id, nothing persisted."""
    message: str
    llm_model: Optional[str] = None
    rf_context_mode: Optional[RfContextMode] = "full"
    history: Optional[list[ChatTurnInput]] = None
    rf_code: Optional[str] = None
    catalog: Optional[list[dict[str, Any]]] = None


class RobotScriptRequest(BaseModel):
    rf_code: str


class ConfirmImportRequest(BaseModel):
    import_token: str


# 回應 schema 的欄位順序與 serializer 輸出一致，避免改變 JSON key 順序。

class CategoryListResponse(BaseModel):
    items: list[str]


class CaseCreateResponse(BaseModel):
    id: str
    case_number: str
    version: int
    created_at: Optional[str] = None


class CaseSummaryResponse(BaseModel):
    id: str
    case_number: str
    name: str
    system_category: Optional[str] = None
    tags: list[str]
    version: int
    created_by: str
    updated_at: Optional[str] = None


class CaseListResponse(BaseModel):
    items: list[CaseSummaryResponse]
    total: int
    page: int
    page_size: int


class CaseTestDataResponse(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    id: str
    field_name: str
    rf_variable: Optional[str] = None
    field_value: Optional[str] = None
    description: Optional[str] = None
    row_index: Optional[int] = None
    source: str


class CaseDetailResponse(BaseModel):
    id: str
    case_number: str
    name: str
    description: Optional[str] = None
    precondition_steps: Optional[str] = None
    main_steps: str
    system_category: Optional[str] = None
    tags: list[str]
    version: int
    created_by: str
    modified_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    test_data: list[CaseTestDataResponse]


class ExecutionHistoryItem(BaseModel):
    execution_id: str
    execution_type: str
    status: str
    passed_count: int
    failed_count: int
    total_count: int
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ExecutionHistoryResponse(BaseModel):
    items: list[ExecutionHistoryItem]
    total: int
    page: int
    page_size: int


class PreviewRFResponse(BaseModel):
    rf_code: str


class AICompleteResponse(BaseModel):
    completed_steps: str
    model_used: str


class ChatResponse(BaseModel):
    assistant_message: str
    rf_code: str


class ExploreLaunchResponse(BaseModel):
    session_id: str
    status_url: str


class ExploreSessionResponse(BaseModel):
    session_id: str
    case_id: str
    url: str
    status: str
    steps: int
    log: list[dict[str, Any]]  # agent 每一步的紀錄，欄位由 agent 決定
    catalog: list[dict[str, Any]]
    note: str


class ChatHistoryMessage(BaseModel):
    role: str
    type: str
    content: str
    created_at: str


class ChatHistoryResponse(BaseModel):
    messages: list[ChatHistoryMessage]


class AttachmentResponse(BaseModel):
    id: str
    attachment_type: str
    filename: Optional[str] = None
    url: Optional[str] = None
    file_size_bytes: Optional[int] = None


class AttachmentListItem(AttachmentResponse):
    mime_type: Optional[str] = None


class AttachmentListResponse(BaseModel):
    items: list[AttachmentListItem]


class ImportPreviewResponse(BaseModel):
    preview: list[dict[str, Any]]  # 欄位依匯入檔的表頭而定
    total_rows: int
    columns: list[str]
    warnings: list[str]
    import_token: str
    # 底線開頭的名稱在 pydantic 屬於私有屬性，以 alias 維持既有的 JSON key
    parsed_rows: list[dict[str, Any]] = Field(alias="_parsed_rows")


class ConfirmImportResponse(BaseModel):
    imported_count: int
    message: str


class RobotScriptSaveResponse(BaseModel):
    """儲存回 file_path；空白內容視為刪除則回 deleted（搭配 exclude_unset 只輸出實際設定的欄位）。"""
    case_number: str
    file_path: Optional[str] = None
    deleted: Optional[bool] = None


class RobotScriptUploadResponse(BaseModel):
    rf_code: str
    case_number: str
    file_path: str
    size_bytes: int
    encoding: str


class RobotScriptResponse(BaseModel):
    rf_code: str
    case_number: str
    source: str  # "db" | "file"


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


def serialize_execution_history_item(record) -> dict:
    # 前端（CaseDetailPage）以 execution_id 取值並導向 /results/:id
    return {
        "execution_id": record.id,
        "execution_type": record.execution_type,
        "status": record.status,
        "passed_count": record.passed_count,
        "failed_count": record.failed_count,
        "total_count": record.total_count,
        "started_at": record.started_at.isoformat() if record.started_at else None,
        "finished_at": record.finished_at.isoformat() if record.finished_at else None,
    }


def _build_test_data_rows(case_id: str, items: list[CaseTestDataInput]) -> list[TestData]:
    return [
        TestData(
            id=generate_uuid(),
            test_case_id=case_id,
            field_name=item.field_name,
            rf_variable=item.rf_variable,
            field_value=item.field_value,
            description=item.description,
            source=item.source,
            row_index=item.row_index if "row_index" in item.model_fields_set else idx,
        )
        for idx, item in enumerate(items)
    ]


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(session: AsyncSession = Depends(get_db)):
    from src.repositories.system_category_repo import SystemCategoryRepository
    repo = SystemCategoryRepository(session)
    cats = await repo.list_active()
    return {"items": [c.name for c in cats]}


@router.post("", status_code=201, response_model=CaseCreateResponse, dependencies=[Depends(require_editor_or_above)])
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
    except IntegrityError:
        raise HTTPException(409, detail={"error": "case_number_conflict", "message": "案例編號重複，請重試"})
    except ValueError as e:
        raise HTTPException(400, detail={"error": "validation_error", "message": str(e)})

    if body.test_data:
        session.add_all(_build_test_data_rows(case.id, body.test_data))
        await session.flush()

    return {
        "id": case.id,
        "case_number": case.case_number,
        "version": case.version,
        "created_at": case.created_at.isoformat() if case.created_at else None,
    }


@router.get("", response_model=CaseListResponse)
async def list_cases(
    system_category: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
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


@router.get("/{case_id}", response_model=CaseDetailResponse)
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


@router.get("/{case_id}/execution-history", response_model=ExecutionHistoryResponse)
async def get_case_execution_history(
    case_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
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

    return {
        "items": [serialize_execution_history_item(r) for r in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.put("/{case_id}", response_model=CaseDetailResponse, dependencies=[Depends(require_editor_or_above)])
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
        session.add_all(_build_test_data_rows(case_id, body.test_data))
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


@router.delete("/{case_id}", response_model=SuccessResponse, dependencies=[Depends(require_editor_or_above)])
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


@router.post("/preview-rf", response_model=PreviewRFResponse)
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


@router.post("/ai-complete", response_model=AICompleteResponse)
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


@router.post("/{case_id}/ai-complete", response_model=AICompleteResponse)
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


@router.post("/chat-preview", response_model=ChatResponse)
async def chat_preview(
    body: ChatPreviewRequest,
    session: AsyncSession = Depends(get_db),
):
    """Stateless AI chat for the case-creation page — no case required, nothing persisted."""
    settings = get_settings()
    model = body.llm_model or await AppSettingService(session).get_active_model()
    provider = get_provider(model, settings)
    ai_service = AIService(provider=provider)

    history = [
        {"role": m.role, "content": m.content}
        for m in (body.history or [])
        if m.role in ("user", "assistant") and m.content
    ]
    response = await ai_service.chat_and_generate_rf(
        messages=history,
        user_message=body.message,
        llm_model=model,
        rf_code=body.rf_code,
        rf_context_mode=body.rf_context_mode or "full",
        element_catalog=body.catalog,
    )
    return {"assistant_message": response["assistant_message"], "rf_code": response["rf_code"]}


class ExplorePageRequest(BaseModel):
    url: str
    goals: list[str]
    variables: Optional[list[str]] = None
    llm_model: Optional[str] = None
    max_steps: Optional[int] = 12


def _resolve_credential_vars(test_data_items, requested: Optional[list[str]]) -> dict[str, str]:
    """Match requested var names against the case's test-data (rf_variable or field_name).

    Returns {VARNAME: value}. Values never leave the server except masked.
    """
    creds: dict[str, str] = {}
    if not requested:
        return creds
    wanted = {v.strip().removeprefix("${").removesuffix("}").upper() for v in requested if v and v.strip()}
    for td in test_data_items or []:
        rf_var = (td.rf_variable or "").strip().removeprefix("${").removesuffix("}").upper()
        field = (td.field_name or "").strip().upper()
        key = rf_var or field
        if key and key in wanted and td.field_value:
            creds[rf_var or field] = td.field_value
    return creds


@router.post("/{case_id}/explore-page", status_code=202, response_model=ExploreLaunchResponse, dependencies=[Depends(require_editor_or_above)])
async def explore_page(
    case_id: str,
    body: ExplorePageRequest,
    session: AsyncSession = Depends(get_db),
):
    """Launch an autonomous page-exploration session (AI drives headless Chromium).

    Returns 202 immediately; poll GET explore-sessions/{session_id} for progress.
    """
    import asyncio as _asyncio

    from src.services.explore_session_store import launch_explore_session

    if not body.url or not body.url.strip():
        raise HTTPException(422, detail={"error": "empty_url", "message": "url 不可為空"})
    goals = [g.strip() for g in (body.goals or []) if g and g.strip()]
    if not goals:
        raise HTTPException(422, detail={"error": "empty_goals", "message": "goals 不可為空"})
    if len(goals) > 20:
        raise HTTPException(422, detail={"error": "too_many_goals", "message": "goals 最多 20 個"})
    max_steps = body.max_steps if body.max_steps is not None else 12
    if max_steps < 1 or max_steps > 30:
        raise HTTPException(422, detail={"error": "bad_max_steps", "message": "max_steps 需介於 1 到 30"})

    result = await session.execute(
        select(TestCase)
        .options(selectinload(TestCase.test_data))
        .where(TestCase.id == case_id, TestCase.is_deleted.is_(False))
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})

    from src.services.page_explorer_service import validate_explore_url
    try:
        # DNS resolution blocks — keep it off the event loop. NOTE: this check
        # is best-effort (TOCTOU vs Playwright's own resolution at goto time);
        # it stops accidents, not a determined attacker. Internal deployments
        # should additionally restrict egress at the network layer.
        await _asyncio.to_thread(validate_explore_url, body.url.strip())
    except ValueError as e:
        raise HTTPException(422, detail={"error": "bad_url", "message": str(e)})

    credentials = _resolve_credential_vars(case.test_data, body.variables)

    settings = get_settings()
    model = body.llm_model or await AppSettingService(session).get_active_model()
    provider = get_provider(model, settings)

    embarked = launch_explore_session(
        case_id=case_id,
        url=body.url.strip(),
        goals=goals,
        credentials=credentials,
        provider=provider,
        max_steps=max_steps,
    )
    return {"session_id": embarked["session_id"],
            "status_url": f"/api/v1/cases/{case_id}/explore-sessions/{embarked['session_id']}"}


@router.get("/{case_id}/explore-sessions/{session_id}", response_model=ExploreSessionResponse)
async def get_explore_session(case_id: str, session_id: str):
    """Poll an exploration session's progress/result."""
    from src.services.explore_session_store import get_session, public_view

    snippet = get_session(session_id)
    if not snippet or snippet.get("case_id") != case_id:
        raise HTTPException(404, detail={"error": "not_found", "message": "探索工作階段不存在"})
    return public_view(snippet)


@router.post("/{case_id}/chat", response_model=ChatResponse)
async def chat_with_ai(
    case_id: str,
    body: ChatRequest,
    session: AsyncSession = Depends(get_db),
):
    """Multi-turn AI chat for test step generation; persists messages to DB."""
    from src.repositories.test_case_repo import TestCaseRepository
    from src.repositories.robot_script_repo import RobotScriptRepository
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
    # Trial-run-result messages (role="system") are for UI display only — the
    # Anthropic Messages API rejects a bare "system" role turn mid-conversation.
    messages = [{"role": m.role, "content": m.content} for m in history if m.role != "system"]

    # Fetch RF code for context injection
    rf_repo = RobotScriptRepository(session)
    rf_record = await rf_repo.get_by_case_id(case_id)
    rf_code = rf_record.rf_code if rf_record else None

    settings = get_settings()
    model = body.llm_model or await AppSettingService(session).get_active_model()
    provider = get_provider(model, settings)
    ai_service = AIService(provider=provider)

    response = await ai_service.chat_and_generate_rf(
        messages=messages,
        user_message=body.message,
        llm_model=model,
        rf_code=rf_code,
        rf_context_mode=body.rf_context_mode or "full",
        element_catalog=body.catalog,
    )

    # Persist user message and assistant response
    user_msg = CaseChatMessage(id=generate_uuid(), case_id=case_id, role="user", content=body.message)
    assistant_msg = CaseChatMessage(id=generate_uuid(), case_id=case_id, role="assistant", content=response["assistant_message"])
    session.add(user_msg)
    session.add(assistant_msg)
    await session.flush()

    return {"assistant_message": response["assistant_message"], "rf_code": response["rf_code"]}


@router.get("/{case_id}/chat-history", response_model=ChatHistoryResponse)
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


@router.post("/{case_id}/attachments", status_code=201, response_model=AttachmentResponse, dependencies=[Depends(require_editor_or_above)])
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
    # 不回傳內部 file_path，避免洩露伺服器佈局；前端改走 /media 下載端點。
    return {
        "id": a.id,
        "attachment_type": a.attachment_type,
        "filename": a.filename,
        "url": a.url,
        "file_size_bytes": a.file_size_bytes,
        "mime_type": a.mime_type,
    }


@router.get("/{case_id}/attachments", response_model=AttachmentListResponse)
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


@router.delete("/{case_id}/attachments/{attachment_id}", response_model=DeletedResponse, dependencies=[Depends(require_editor_or_above)])
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


@router.post("/{case_id}/import-test-data", response_model=ImportPreviewResponse)
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
        msg = str(e)
        if msg.startswith("file_too_large"):
            raise HTTPException(413, detail={"error": "file_too_large", "message": "檔案大小超過限制 (最大 10MB)"})
        raise HTTPException(400, detail={"error": msg, "message": "檔案解析失敗"})

    return {
        "preview": result["preview"],
        "total_rows": result["total_rows"],
        "columns": result["columns"],
        "warnings": result["warnings"],
        "import_token": result["import_token"],
        "_parsed_rows": result["_rows"],
    }


@router.post("/{case_id}/import-test-data/confirm", status_code=201, response_model=ConfirmImportResponse)
async def confirm_import_test_data(
    case_id: str,
    body: ConfirmImportRequest,
    session: AsyncSession = Depends(get_db),
):
    # In production, use a cache/token store; here we accept import via re-parse
    return {"imported_count": 0, "message": "Import confirmed (token-based storage not yet implemented)"}


@router.put(
    "/{case_id}/robot-script",
    response_model=RobotScriptSaveResponse,
    response_model_exclude_unset=True,
    dependencies=[Depends(require_editor_or_above)],
)
async def save_robot_script(
    case_id: str,
    body: RobotScriptRequest,
    service: CaseService = Depends(get_case_service),
    session: AsyncSession = Depends(get_db),
):
    """Save Robot Framework script — write to DB and sync to disk. Empty rf_code deletes the record."""
    from src.repositories.robot_script_repo import RobotScriptRepository
    try:
        case = await service.get(case_id)
    except ValueError:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})

    repo = RobotScriptRepository(session)

    # Empty rf_code = delete RF script
    if not body.rf_code or not body.rf_code.strip():
        await repo.delete_by_case_id(case_id)
        # Remove disk file
        settings = get_settings()
        file_path = os.path.join(settings.robot_scripts_dir, f"{case.case_number}.robot")
        if os.path.exists(file_path):
            os.remove(file_path)
        return {"case_number": case.case_number, "deleted": True}

    # Persist to DB (source of truth)
    await repo.upsert(test_case_id=case_id, rf_code=body.rf_code)

    # Sync to disk so RF CLI can execute it
    settings = get_settings()
    script_dir = settings.robot_scripts_dir
    os.makedirs(script_dir, exist_ok=True)
    file_path = os.path.join(script_dir, f"{case.case_number}.robot")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(body.rf_code)

    return {"case_number": case.case_number, "file_path": file_path}


@router.post("/{case_id}/robot-script/upload", response_model=RobotScriptUploadResponse, dependencies=[Depends(require_editor_or_above)])
async def upload_robot_script(
    case_id: str,
    file: UploadFile = File(..., description="Robot Framework .robot file"),
    service: CaseService = Depends(get_case_service),
    session: AsyncSession = Depends(get_db),
):
    """Upload Robot Framework script file — validate and persist."""
    from src.repositories.robot_script_repo import RobotScriptRepository

    # Validate file extension
    if not file.filename or not file.filename.lower().endswith('.robot'):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_extension", "message": "只接受 .robot 檔案"}
        )

    # Read file content
    content = await file.read()
    if len(content) > 500 * 1024:
        raise HTTPException(
            status_code=413,
            detail={"error": "file_too_large", "message": "檔案超過 500KB 限制"}
        )

    # Decode with fallback encodings
    rf_code: str | None = None
    for encoding in ['utf-8', 'utf-8-sig', 'big5', 'gbk']:
        try:
            rf_code = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if rf_code is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "encoding_error", "message": "無法解碼檔案內容，請確認檔案為 UTF-8、Big5 或 GBK 編碼"}
        )

    # Verify case exists
    try:
        case = await service.get(case_id)
    except ValueError:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})

    # Persist to DB
    repo = RobotScriptRepository(session)
    await repo.upsert(test_case_id=case_id, rf_code=rf_code)

    # Sync to disk
    settings = get_settings()
    script_dir = settings.robot_scripts_dir
    os.makedirs(script_dir, exist_ok=True)
    file_path = os.path.join(script_dir, f"{case.case_number}.robot")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(rf_code)

    return {
        "rf_code": rf_code,
        "case_number": case.case_number,
        "file_path": file_path,
        "size_bytes": len(content),
        "encoding": "utf-8"
    }


@router.get("/{case_id}/robot-script", response_model=RobotScriptResponse)
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


@router.post("/{case_id}/trial-run", status_code=202, response_model=ExecutionStartResponse, dependencies=[Depends(require_editor_or_above)])
async def trial_run(case_id: str, request: TrialRunRequest = TrialRunRequest(), session: AsyncSession = Depends(get_db)):
    """Phase 27: Execute trial run using RF code from preview area."""
    import logging
    from src.repositories.test_case_repo import TestCaseRepository
    from src.services.execution_service import ExecutionService, MAX_RF_CODE_BYTES
    repo = TestCaseRepository(session)
    case = await repo.get(case_id)
    if not case:
        raise HTTPException(404, detail={"error": "not_found", "message": "案例不存在"})
    if request.rf_code and len(request.rf_code.encode("utf-8")) > MAX_RF_CODE_BYTES:
        raise HTTPException(413, detail={"error": "file_too_large", "message": "RF code too large"})
    logging.getLogger(__name__).info("trial-run requested case_id=%s", case_id)

    # Fail fast with a clear message when there is no RF code to run —
    # otherwise the trial would instantly record a confusing failure.
    # Read path mirrors get_robot_script: DB first, then disk fallback.
    if not (request.rf_code and request.rf_code.strip()):
        from src.repositories.robot_script_repo import RobotScriptRepository
        record = await RobotScriptRepository(session).get_by_case_id(case_id)
        has_db_code = bool(record and record.rf_code and record.rf_code.strip())
        script_path = os.path.join(get_settings().robot_scripts_dir, f"{case.case_number}.robot")
        if not has_db_code and not os.path.exists(script_path):
            raise HTTPException(422, detail={"error": "no_robot_code", "message": "尚未產生 RF 程式碼，請先透過 AI 對話生成或上傳後再試跑"})

    exec_service = ExecutionService(session)
    record = await exec_service.run_trial(
        source_case_id=case_id,
        rf_code=request.rf_code,
        case_name=request.case_name or case.name
    )
    return {"execution_id": record.id, "stream_url": f"/api/v1/executions/{record.id}/stream"}

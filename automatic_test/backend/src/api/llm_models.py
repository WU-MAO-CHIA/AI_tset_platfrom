import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import get_db
from src.services.app_setting_service import AppSettingService

router = APIRouter(prefix="/llm-models", tags=["llm-models"])

ANTHROPIC_MODELS = [
    {"id": "claude-opus-4-7", "name": "Claude Opus 4.7", "provider": "anthropic"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "provider": "anthropic"},
    {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "provider": "anthropic"},
    {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "provider": "anthropic"},
]

OPENAI_MODELS = [
    {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai"},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai"},
]

OLLAMA_TAGS_TIMEOUT = 2.0


def _is_valid_key(key: str) -> bool:
    return bool(key) and len(key) >= 20 and "..." not in key


async def _fetch_ollama_models(base_url: str) -> list[dict]:
    """查 {base}/api/tags 取得已安裝模型；連線失敗/逾時則回空清單（不影響雲端）。"""
    if not base_url:
        return []
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TAGS_TIMEOUT) as client:
            resp = await client.get(f"{base_url.rstrip('/')}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []
    models = []
    for m in data.get("models", []):
        name = m.get("name")
        if not name:
            continue
        models.append({
            "id": f"ollama:{name}",
            "name": name,
            "provider": "ollama",
            "requires_setup": False,
        })
    return models


@router.get("")
async def list_llm_models(db: AsyncSession = Depends(get_db)):
    settings = get_settings()

    anthropic_ready = _is_valid_key(settings.anthropic_api_key)
    openai_ready = _is_valid_key(settings.openai_api_key)

    models: list[dict] = []
    for m in ANTHROPIC_MODELS:
        models.append({**m, "requires_setup": not anthropic_ready})
    for m in OPENAI_MODELS:
        models.append({**m, "requires_setup": not openai_ready})

    # 本地 Ollama 已安裝模型（離線則略過）
    models.extend(await _fetch_ollama_models(settings.ollama_base_url))

    # default = 目前啟用模型（DB 優先，無則 .env DEFAULT_LLM_MODEL）
    default = await AppSettingService(db).get_active_model()
    return {"models": models, "default": default}

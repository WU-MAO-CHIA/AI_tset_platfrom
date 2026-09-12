import asyncio
import re
import time

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import get_db
from src.core.dependencies import get_current_user
from src.services.app_setting_service import AppSettingService

router = APIRouter(
    prefix="/llm-models", tags=["llm-models"], dependencies=[Depends(get_current_user)]
)

ANTHROPIC_MODELS = [
    {"id": "claude-opus-4-7", "name": "Claude Opus 4.7", "provider": "anthropic"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "provider": "anthropic"},
    {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "provider": "anthropic"},]

OPENAI_MODELS = [
    {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai"},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai"},
]

OLLAMA_TAGS_TIMEOUT = 2.0
CLOUD_FETCH_TIMEOUT = 5.0

# live 模型清單快取（process 內、best-effort）：避免每次開下拉都打三家供應商。
_LIVE_CACHE_TTL_SEC = 600.0
_live_cache: dict[str, tuple[float, list[dict]]] = {}

# OpenAI /v1/models 會回數十個非對話模型，排除法只留聊天可用（新對話模型自動出現）。
_NON_CHAT_MODEL_RE = re.compile(
    r"embedding|whisper|tts|dall-e|moderation|transcri|realtime|audio", re.IGNORECASE
)


def _is_valid_key(key: str) -> bool:
    return bool(key) and len(key) >= 20 and "..." not in key


def _cache_get(provider: str, api_key: str) -> list[dict] | None:
    entry = _live_cache.get(provider + ":" + api_key[:7])
    if not entry:
        return None
    ts, models = entry
    if time.monotonic() - ts > _LIVE_CACHE_TTL_SEC:
        _live_cache.pop(provider + ":" + api_key[:7], None)
        return None
    return models


def _cache_set(provider: str, api_key: str, models: list[dict]) -> None:
    _live_cache[provider + ":" + api_key[:7]] = (time.monotonic(), models)


async def _fetch_anthropic_models(api_key: str) -> list[dict]:
    """打 Anthropic Models API 取 live 模型清單；無 Key 或失敗回 []（呼叫端決定 fallback/隱藏）。"""
    if not _is_valid_key(api_key):
        return []
    cached = _cache_get("anthropic", api_key)
    if cached is not None:
        return cached
    try:
        async with httpx.AsyncClient(timeout=CLOUD_FETCH_TIMEOUT) as client:
            resp = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    models = []
    for m in data.get("data", []) or []:
        if not isinstance(m, dict):
            continue
        mid = m.get("id")
        if not mid:
            continue
        models.append({
            "id": mid,
            "name": m.get("display_name") or mid,
            "provider": "anthropic",
            "requires_setup": False,
        })
    if models:
        _cache_set("anthropic", api_key, models)
    return models


async def _fetch_openai_models(api_key: str) -> list[dict]:
    """打 OpenAI Models API 取 live 模型清單並排除非對話模型；無 Key 或失敗回 []。"""
    if not _is_valid_key(api_key):
        return []
    cached = _cache_get("openai", api_key)
    if cached is not None:
        return cached
    try:
        async with httpx.AsyncClient(timeout=CLOUD_FETCH_TIMEOUT) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    models = []
    for m in data.get("data", []) or []:
        if not isinstance(m, dict):
            continue
        mid = m.get("id")
        if not mid or _NON_CHAT_MODEL_RE.search(mid):
            continue
        models.append({"id": mid, "name": mid, "provider": "openai", "requires_setup": False})
    models.sort(key=lambda m: m["id"])
    if models:
        _cache_set("openai", api_key, models)
    return models


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

    # 有 Key 才查/顯示該供應商；無 Key 直接隱藏（前端本就過濾 requires_setup）。
    anthropic_key = settings.anthropic_api_key if _is_valid_key(settings.anthropic_api_key) else ""
    openai_key = settings.openai_api_key if _is_valid_key(settings.openai_api_key) else ""

    live_anthropic, live_openai, ollama_models = await asyncio.gather(
        _fetch_anthropic_models(anthropic_key),
        _fetch_openai_models(openai_key),
        _fetch_ollama_models(settings.ollama_base_url),
    )

    models: list[dict] = []
    if anthropic_key:
        # live 失敗（斷網/401）則 fallback 寫死清單，離線仍可用
        models.extend(live_anthropic or [{**m, "requires_setup": False} for m in ANTHROPIC_MODELS])
    if openai_key:
        models.extend(live_openai or [{**m, "requires_setup": False} for m in OPENAI_MODELS])
    models.extend(ollama_models)

    # default = 目前啟用模型（DB 優先，無則 .env DEFAULT_LLM_MODEL）
    default = await AppSettingService(db).get_active_model()
    return {"models": models, "default": default}

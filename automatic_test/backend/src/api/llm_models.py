from fastapi import APIRouter

from src.core.config import get_settings

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


@router.get("")
async def list_llm_models():
    settings = get_settings()
    available = []

    if settings.anthropic_api_key:
        available.extend(ANTHROPIC_MODELS)

    if settings.openai_api_key:
        available.extend(OPENAI_MODELS)

    if not available:
        # No keys configured — return all models but mark them as requiring setup
        all_models = ANTHROPIC_MODELS + OPENAI_MODELS
        for m in all_models:
            m["requires_setup"] = True
        available = all_models

    return {"models": available, "default": settings.default_llm_model}

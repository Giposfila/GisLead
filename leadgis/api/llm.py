"""GET /llm/models — models list from the active LLM provider."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from leadgis.api.deps import get_settings
from leadgis.config import Settings
from leadgis.llm.registry import get_llm_provider

router = APIRouter(tags=["llm"])


@router.get("/llm/models", response_model=list[str])
async def list_llm_models(settings: Settings = Depends(get_settings)) -> list[str]:
    provider = get_llm_provider(settings)
    return await provider.list_models()

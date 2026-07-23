"""POST /llm/models — models list from the active LLM provider.

POST (not GET) so an unsaved base_url/api_key override can be sent in the
body instead of a query string, which would leak the api_key into logs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from leadgis.api.deps import get_settings
from leadgis.api.schemas import LLMSettingsIn
from leadgis.api.settings import with_llm_override
from leadgis.config import Settings
from leadgis.llm.registry import get_llm_provider

router = APIRouter(tags=["llm"])


@router.post("/llm/models", response_model=list[str])
async def list_llm_models(
    override: LLMSettingsIn | None = None,
    settings: Settings = Depends(get_settings),
) -> list[str]:
    settings = with_llm_override(settings, override)
    provider = get_llm_provider(settings)
    return await provider.list_models()

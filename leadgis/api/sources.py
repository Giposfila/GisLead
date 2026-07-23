"""GET /sources — available data sources with availability info."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from leadgis.api.deps import get_settings
from leadgis.api.schemas import SourceInfoOut
from leadgis.config import Settings
from leadgis.sources.registry import available_sources

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=list[SourceInfoOut])
async def list_sources(settings: Settings = Depends(get_settings)) -> list[SourceInfoOut]:
    return [
        SourceInfoOut(
            id=info.id,
            display_name=info.display_name,
            available=info.available,
            missing=info.missing,
        )
        for info in available_sources(settings)
    ]

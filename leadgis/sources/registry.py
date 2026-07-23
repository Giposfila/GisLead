"""Source discovery/selection. Adding a source requires zero service changes."""

from __future__ import annotations

from dataclasses import dataclass

from leadgis.config import Settings
from leadgis.sources.base import DataSource
from leadgis.sources.twogis_api import TwoGisApiAdapter


@dataclass(slots=True)
class SourceInfo:
    id: str
    display_name: str
    available: bool
    missing: list[str]


def available_sources(settings: Settings) -> list[SourceInfo]:
    missing = [] if settings.source.twogis_api_key else ["twogis_api_key"]
    return [
        SourceInfo(
            id=TwoGisApiAdapter.id,
            display_name=TwoGisApiAdapter.display_name,
            available=not missing,
            missing=missing,
        ),
    ]


def get_source(source_id: str, settings: Settings) -> DataSource:
    if source_id == TwoGisApiAdapter.id:
        if not settings.source.twogis_api_key:
            raise ValueError("2GIS API key is not configured")
        return TwoGisApiAdapter(
            api_key=settings.source.twogis_api_key,
            rps=settings.limits.twogis_rps,
        )
    raise ValueError(f"Unknown data source: {source_id}")

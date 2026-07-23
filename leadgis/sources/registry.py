"""Source discovery/selection. Adding a source requires zero service changes."""

from __future__ import annotations

from dataclasses import dataclass

from leadgis.config import Settings
from leadgis.sources.base import DataSource
from leadgis.sources.twogis_api import TwoGisApiAdapter
from leadgis.sources.yandex_maps import YandexMapsAdapter


@dataclass(slots=True)
class SourceInfo:
    id: str
    display_name: str
    available: bool
    missing: list[str]


def available_sources(settings: Settings) -> list[SourceInfo]:
    twogis_missing = [] if settings.source.twogis_api_key else ["twogis_api_key"]
    yandex_missing = [] if settings.source.yandex_maps_api_key else ["yandex_maps_api_key"]
    return [
        SourceInfo(
            id=TwoGisApiAdapter.id,
            display_name=TwoGisApiAdapter.display_name,
            available=not twogis_missing,
            missing=twogis_missing,
        ),
        SourceInfo(
            id=YandexMapsAdapter.id,
            display_name=YandexMapsAdapter.display_name,
            available=not yandex_missing,
            missing=yandex_missing,
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
    if source_id == YandexMapsAdapter.id:
        if not settings.source.yandex_maps_api_key:
            raise ValueError("Yandex Maps API key is not configured")
        return YandexMapsAdapter(
            api_key=settings.source.yandex_maps_api_key,
            rps=settings.limits.yandex_maps_rps,
        )
    raise ValueError(f"Unknown data source: {source_id}")

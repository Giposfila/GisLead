"""GET/PUT /api/settings — secret fields are write-only."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from leadgis.api.deps import get_settings as get_settings_dep
from leadgis.api.schemas import (
    AppSettingsOut,
    HealthCheckOut,
    LimitsSettingsOut,
    LLMSettingsIn,
    LLMSettingsOut,
    OutreachSettingsOut,
    SettingsIn,
    SettingsOut,
    SourceSettingsIn,
    SourceSettingsOut,
)
from leadgis.config import Settings, load_settings, save_settings
from leadgis.llm.base import (
    AuthError,
    GenerationError,
    ModelNotFoundError,
    ProviderUnavailable,
    RateLimitError,
)
from leadgis.llm.registry import get_llm_provider
from leadgis.sources.registry import get_source

router = APIRouter(tags=["settings"])


def _to_out(settings: Settings) -> SettingsOut:
    return SettingsOut(
        app=AppSettingsOut(
            host=settings.app.host,
            port=settings.app.port,
            open_browser=settings.app.open_browser,
            auth_token_is_set=bool(settings.app.auth_token),
        ),
        source=SourceSettingsOut(
            active=settings.source.active,
            twogis_api_key_is_set=bool(settings.source.twogis_api_key),
            yandex_maps_api_key_is_set=bool(settings.source.yandex_maps_api_key),
            scraper_enabled=settings.source.scraper.enabled,
            scraper_max_orgs=settings.source.scraper.max_orgs,
        ),
        llm=LLMSettingsOut(
            provider=settings.llm.provider,
            base_url=settings.llm.base_url,
            api_key_is_set=bool(settings.llm.api_key),
            model=settings.llm.model,
            concurrency=settings.llm.concurrency,
        ),
        limits=LimitsSettingsOut(
            twogis_rps=settings.limits.twogis_rps,
            website_check_concurrency=settings.limits.website_check_concurrency,
        ),
        outreach=OutreachSettingsOut(
            user_offer=settings.outreach.user_offer,
            extra_instructions=settings.outreach.extra_instructions,
            template=settings.outreach.template,
        ),
    )


@router.get("/settings", response_model=SettingsOut)
async def get_settings() -> SettingsOut:
    return _to_out(load_settings())


@router.put("/settings", response_model=SettingsOut)
async def update_settings(payload: SettingsIn) -> SettingsOut:
    current = load_settings()

    if payload.app is not None:
        current.app = current.app.model_copy(update=payload.app.model_dump(exclude_none=True))
    if payload.source is not None:
        scraper_fields = {"scraper_enabled", "scraper_max_orgs"}
        update = payload.source.model_dump(exclude_none=True, exclude=scraper_fields)
        current.source = current.source.model_copy(update=update)
        if payload.source.scraper_enabled is not None:
            current.source.scraper.enabled = payload.source.scraper_enabled
        if payload.source.scraper_max_orgs is not None:
            current.source.scraper.max_orgs = payload.source.scraper_max_orgs
    if payload.llm is not None:
        update = payload.llm.model_dump(exclude_none=True)
        current.llm = current.llm.model_copy(update=update)
    if payload.limits is not None:
        update = payload.limits.model_dump(exclude_none=True)
        current.limits = current.limits.model_copy(update=update)
    if payload.outreach is not None:
        update = payload.outreach.model_dump(exclude_none=True)
        current.outreach = current.outreach.model_copy(update=update)

    save_settings(current)
    return _to_out(current)


_SOURCE_SECRET_FIELDS = {"twogis_api_key", "yandex_maps_api_key"}
_SOURCE_TEST_OVERRIDE_FIELDS = {"active", *_SOURCE_SECRET_FIELDS}


def _with_source_override(settings: Settings, override: SourceSettingsIn | None) -> Settings:
    if override is None:
        return settings
    update = override.model_dump(exclude_none=True, include=_SOURCE_TEST_OVERRIDE_FIELDS)
    for field in _SOURCE_SECRET_FIELDS:
        if not update.get(field):
            update.pop(field, None)
    if not update:
        return settings
    merged = settings.model_copy(deep=True)
    merged.source = merged.source.model_copy(update=update)
    return merged


def with_llm_override(settings: Settings, override: LLMSettingsIn | None) -> Settings:
    if override is None:
        return settings
    update = override.model_dump(exclude_none=True)
    if not update.get("api_key"):
        update.pop("api_key", None)
    if not update:
        return settings
    merged = settings.model_copy(deep=True)
    merged.llm = merged.llm.model_copy(update=update)
    return merged


@router.post("/settings/test/source", response_model=HealthCheckOut)
async def test_source(
    override: SourceSettingsIn | None = None,
    settings: Settings = Depends(get_settings_dep),
) -> HealthCheckOut:
    settings = _with_source_override(settings, override)
    try:
        source = get_source(settings.source.active, settings)
    except ValueError as exc:
        return HealthCheckOut(ok=False, detail=str(exc))
    status = await source.healthcheck()
    return HealthCheckOut(ok=status.ok, detail=status.detail)


@router.post("/settings/test/llm", response_model=HealthCheckOut)
async def test_llm(
    override: LLMSettingsIn | None = None,
    settings: Settings = Depends(get_settings_dep),
) -> HealthCheckOut:
    settings = with_llm_override(settings, override)
    try:
        provider = get_llm_provider(settings)
    except ValueError as exc:
        return HealthCheckOut(ok=False, detail=str(exc))
    status = await provider.healthcheck()
    if not status.ok:
        return HealthCheckOut(ok=False, detail=status.detail)
    llm_errors = (
        AuthError,
        RateLimitError,
        ModelNotFoundError,
        ProviderUnavailable,
        GenerationError,
    )
    try:
        result = await provider.complete("Reply with one word.", "Say OK.", max_tokens=10)
    except llm_errors as exc:
        return HealthCheckOut(ok=False, detail=str(exc))
    return HealthCheckOut(ok=True, detail=f"Test completion succeeded: {result.text[:50]!r}")

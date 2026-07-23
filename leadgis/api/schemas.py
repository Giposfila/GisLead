"""Pydantic request/response models for the HTTP API boundary."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    host: str
    port: int
    open_browser: bool
    auth_token_is_set: bool


class SourceSettingsOut(BaseModel):
    active: str
    twogis_api_key_is_set: bool
    yandex_maps_api_key_is_set: bool
    scraper_enabled: bool
    scraper_max_orgs: int


class LLMSettingsOut(BaseModel):
    provider: str
    base_url: str
    api_key_is_set: bool
    model: str
    concurrency: int


class LimitsSettingsOut(BaseModel):
    twogis_rps: int
    website_check_concurrency: int


class OutreachSettingsOut(BaseModel):
    user_offer: str
    extra_instructions: str
    template: str


class SettingsOut(BaseModel):
    app: AppSettingsOut
    source: SourceSettingsOut
    llm: LLMSettingsOut
    limits: LimitsSettingsOut
    outreach: OutreachSettingsOut


class AppSettingsIn(BaseModel):
    host: str | None = None
    port: int | None = None
    open_browser: bool | None = None
    auth_token: str | None = None


class SourceSettingsIn(BaseModel):
    active: str | None = None
    twogis_api_key: str | None = None
    yandex_maps_api_key: str | None = None
    scraper_enabled: bool | None = None
    scraper_max_orgs: int | None = None


class LLMSettingsIn(BaseModel):
    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    concurrency: int | None = None


class LimitsSettingsIn(BaseModel):
    twogis_rps: int | None = None
    website_check_concurrency: int | None = None


class OutreachSettingsIn(BaseModel):
    user_offer: str | None = None
    extra_instructions: str | None = None
    template: str | None = None


class SettingsIn(BaseModel):
    app: AppSettingsIn | None = None
    source: SourceSettingsIn | None = None
    llm: LLMSettingsIn | None = None
    limits: LimitsSettingsIn | None = None
    outreach: OutreachSettingsIn | None = None


class SourceInfoOut(BaseModel):
    id: str
    display_name: str
    available: bool
    missing: list[str]


class CampaignIn(BaseModel):
    name: str
    niche: str
    city: str
    source: str


class CampaignOut(BaseModel):
    id: int
    name: str
    niche: str
    city: str
    source: str
    status: str
    created_at: datetime
    lead_counts: dict[str, int] = {}


class LeadOut(BaseModel):
    id: int
    campaign_id: int
    external_id: str | None
    name: str
    category: str | None
    address: str | None
    phone_e164: str | None
    website: str | None
    website_status: str
    whatsapp_url: str | None
    telegram_url: str | None
    instagram_url: str | None
    rating: float | None
    reviews_count: int | None
    status: str
    created_at: datetime
    updated_at: datetime


class LeadPatchIn(BaseModel):
    status: str | None = None
    name: str | None = None
    phone_e164: str | None = None
    website: str | None = None


class LeadPageOut(BaseModel):
    items: list[LeadOut]
    total: int
    page: int
    page_size: int


class JobOut(BaseModel):
    id: str
    kind: str
    campaign_id: int | None
    status: str
    progress: int
    detail: str | None
    created_at: datetime
    finished_at: datetime | None


class JobIdOut(BaseModel):
    job_id: str


class HealthCheckOut(BaseModel):
    ok: bool
    detail: str


class MessageOut(BaseModel):
    id: int
    lead_id: int
    text: str
    provider: str
    model: str
    created_at: datetime


class MessagePutIn(BaseModel):
    text: str


class WaLinkOut(BaseModel):
    url: str

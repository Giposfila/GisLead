"""Campaign endpoints: create/list/detail + start collect job."""

from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from leadgis.api.deps import get_job_runner, get_session, get_settings
from leadgis.api.schemas import CampaignIn, CampaignOut, JobIdOut
from leadgis.config import Settings
from leadgis.constants import NICHE_CATALOG
from leadgis.db.models import Campaign
from leadgis.generation.generator import generate_for_leads, lead_ids_for_campaign
from leadgis.services import campaigns as campaigns_service
from leadgis.services.enrichment import enrich_campaign_leads
from leadgis.services.export import CampaignNotFoundError, export_campaign_bytes
from leadgis.worker import JobContext, JobRunner

router = APIRouter(tags=["campaigns"])

EXPORT_MEDIA_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _ascii_filename_part(value: str) -> str:
    # HTTP header values must be latin-1; non-ASCII campaign names (e.g. Cyrillic)
    # go through the RFC 6266 filename* parameter instead, this is just the fallback.
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_") or "campaign"


@router.get("/niches", response_model=list[str])
async def list_niches() -> list[str]:
    return NICHE_CATALOG


async def _to_out(session: AsyncSession, campaign: Campaign) -> CampaignOut:
    counts = await campaigns_service.lead_status_counts(session, campaign.id)
    return CampaignOut(
        id=campaign.id,
        name=campaign.name,
        niche=campaign.niche,
        city=campaign.city,
        source=campaign.source,
        status=campaign.status,
        created_at=campaign.created_at,
        lead_counts=counts,
    )


@router.post("/campaigns", response_model=CampaignOut)
async def create_campaign(
    payload: CampaignIn, session: AsyncSession = Depends(get_session)
) -> CampaignOut:
    campaign = await campaigns_service.create_campaign(
        session, name=payload.name, niche=payload.niche, city=payload.city, source=payload.source
    )
    return await _to_out(session, campaign)


@router.get("/campaigns", response_model=list[CampaignOut])
async def list_campaigns(session: AsyncSession = Depends(get_session)) -> list[CampaignOut]:
    campaigns = await campaigns_service.list_campaigns(session)
    return [await _to_out(session, campaign) for campaign in campaigns]


@router.get("/campaigns/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: int, session: AsyncSession = Depends(get_session)
) -> CampaignOut:
    campaign = await campaigns_service.get_campaign(session, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return await _to_out(session, campaign)


@router.post("/campaigns/{campaign_id}/collect", response_model=JobIdOut)
async def collect_campaign(
    campaign_id: int,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    runner: JobRunner = Depends(get_job_runner),
) -> JobIdOut:
    campaign = await campaigns_service.get_campaign(session, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    async def _run(ctx: JobContext) -> None:
        await campaigns_service.run_collect_job(ctx, campaign_id, settings)

    job_id = await runner.submit("collect", campaign_id, _run)
    return JobIdOut(job_id=job_id)


@router.post("/campaigns/{campaign_id}/enrich", response_model=JobIdOut)
async def enrich_campaign(
    campaign_id: int,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    runner: JobRunner = Depends(get_job_runner),
) -> JobIdOut:
    campaign = await campaigns_service.get_campaign(session, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    async def _run(ctx: JobContext) -> None:
        await enrich_campaign_leads(ctx, campaign_id, settings)

    job_id = await runner.submit("enrich", campaign_id, _run)
    return JobIdOut(job_id=job_id)


@router.post("/campaigns/{campaign_id}/generate", response_model=JobIdOut)
async def generate_campaign_messages(
    campaign_id: int,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    runner: JobRunner = Depends(get_job_runner),
) -> JobIdOut:
    campaign = await campaigns_service.get_campaign(session, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    async def _run(ctx: JobContext) -> None:
        lead_ids = await lead_ids_for_campaign(campaign_id)
        await generate_for_leads(ctx, lead_ids, settings)

    job_id = await runner.submit("generate", campaign_id, _run)
    return JobIdOut(job_id=job_id)


@router.get("/campaigns/{campaign_id}/export")
async def export_campaign_route(
    campaign_id: int,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        data = await export_campaign_bytes(session, campaign_id, format)
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    campaign = await campaigns_service.get_campaign(session, campaign_id)
    raw_name = campaign.name if campaign else str(campaign_id)
    ascii_filename = f"leadgis_{_ascii_filename_part(raw_name)}.{format}"
    utf8_filename = quote(f"leadgis_{raw_name}.{format}")
    disposition = f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{utf8_filename}"
    return Response(
        content=data,
        media_type=EXPORT_MEDIA_TYPES[format],
        headers={"Content-Disposition": disposition},
    )

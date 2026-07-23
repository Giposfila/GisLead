"""Campaign orchestration: collect -> enrich -> store."""

from __future__ import annotations

import json
import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from leadgis.config import Settings
from leadgis.db.engine import session_scope
from leadgis.db.models import Campaign, CampaignStatus, Lead
from leadgis.enrichment.messengers import build_telegram_url, build_whatsapp_url
from leadgis.enrichment.phone import normalize_phone
from leadgis.services.enrichment import enrich_campaign_leads
from leadgis.sources.base import SourceError
from leadgis.sources.registry import get_source
from leadgis.worker import JobCancelled, JobContext

logger = logging.getLogger("leadgis.campaigns")


async def create_campaign(
    session: AsyncSession, *, name: str, niche: str, city: str, source: str
) -> Campaign:
    campaign = Campaign(
        name=name, niche=niche, city=city, source=source, status=CampaignStatus.DRAFT
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return campaign


async def get_campaign(session: AsyncSession, campaign_id: int) -> Campaign | None:
    return await session.get(Campaign, campaign_id)


async def list_campaigns(session: AsyncSession) -> list[Campaign]:
    result = await session.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    return list(result.scalars().all())


async def lead_status_counts(session: AsyncSession, campaign_id: int) -> dict[str, int]:
    stmt = (
        select(Lead.status, func.count())
        .where(Lead.campaign_id == campaign_id)
        .group_by(Lead.status)
    )
    result = await session.execute(stmt)
    return {status: count for status, count in result.all()}


DEFAULT_COLLECT_LIMIT = 200


async def run_collect_job(ctx: JobContext, campaign_id: int, settings: Settings) -> None:
    async with session_scope() as session:
        campaign = await session.get(Campaign, campaign_id)
        if campaign is None:
            raise ValueError(f"Campaign {campaign_id} not found")
        campaign.status = CampaignStatus.COLLECTING
        await session.commit()

    try:
        source = get_source(campaign.source, settings)
    except ValueError as exc:
        async with session_scope() as session:
            campaign = await session.get(Campaign, campaign_id)
            assert campaign is not None
            campaign.status = CampaignStatus.FAILED
            await session.commit()
        raise SourceError(str(exc)) from exc

    collected = 0
    try:
        async for org in source.search(campaign.niche, campaign.city, DEFAULT_COLLECT_LIMIT):
            ctx.check_cancelled()
            phone_e164 = next((p for p in (normalize_phone(raw) for raw in org.phones) if p), None)
            async with session_scope() as session:
                lead = Lead(
                    campaign_id=campaign_id,
                    external_id=org.external_id,
                    name=org.name,
                    category=org.category,
                    address=org.address,
                    phones_raw=json.dumps(org.phones) if org.phones else None,
                    phone_e164=phone_e164,
                    website=org.website,
                    whatsapp_url=build_whatsapp_url(phone_e164),
                    instagram_url=org.instagram,
                    telegram_url=build_telegram_url(org.telegram),
                    rating=org.rating,
                    reviews_count=org.reviews_count,
                )
                session.add(lead)
                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                else:
                    collected += 1
            await ctx.set_progress(collected, DEFAULT_COLLECT_LIMIT, detail=org.name)
    except SourceError:
        async with session_scope() as session:
            campaign = await session.get(Campaign, campaign_id)
            assert campaign is not None
            campaign.status = CampaignStatus.FAILED
            await session.commit()
        raise

    # Graceful degradation: leads are already stored, so an enrichment failure must
    # not prevent the campaign from reaching "ready" (JobCancelled still propagates).
    try:
        await enrich_campaign_leads(ctx, campaign_id, settings)
    except JobCancelled:
        raise
    except Exception:
        logger.exception("enrichment failed for campaign %s", campaign_id)

    async with session_scope() as session:
        campaign = await session.get(Campaign, campaign_id)
        assert campaign is not None
        campaign.status = CampaignStatus.READY
        await session.commit()

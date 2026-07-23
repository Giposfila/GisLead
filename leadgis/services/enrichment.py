"""Enrichment pass: website liveness for a campaign's leads."""

from __future__ import annotations

from sqlalchemy import select

from leadgis.config import Settings
from leadgis.db.engine import session_scope
from leadgis.db.models import Lead
from leadgis.enrichment.website import check_websites
from leadgis.worker import JobContext


async def enrich_campaign_leads(ctx: JobContext, campaign_id: int, settings: Settings) -> None:
    async with session_scope() as session:
        result = await session.execute(select(Lead).where(Lead.campaign_id == campaign_id))
        leads = result.scalars().all()
        lead_ids = [lead.id for lead in leads]
        urls = [lead.website for lead in leads]
        names = [lead.name for lead in leads]

    if not lead_ids:
        return

    statuses = await check_websites(urls, concurrency=settings.limits.website_check_concurrency)

    for i, (lead_id, status, name) in enumerate(zip(lead_ids, statuses, names, strict=True)):
        ctx.check_cancelled()
        async with session_scope() as session:
            lead = await session.get(Lead, lead_id)
            assert lead is not None
            lead.website_status = status
            await session.commit()
        await ctx.set_progress(i + 1, len(lead_ids), detail=name)

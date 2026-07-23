from __future__ import annotations

import json

import httpx
import pytest
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from leadgis.config import Settings
from leadgis.db.models import CampaignStatus, Lead
from leadgis.services import campaigns as campaigns_service
from leadgis.sources.base import SourceError
from leadgis.sources.twogis_api import BASE_URL
from leadgis.worker import JobContext, JobRunner


def _fixture(name: str) -> dict:
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "fixtures" / name
    return json.loads(path.read_text())


async def test_create_and_list_campaign(db_session: AsyncSession) -> None:
    campaign = await campaigns_service.create_campaign(
        db_session, name="Тест", niche="веб-студия", city="Москва", source="twogis_api"
    )
    assert campaign.id is not None
    assert campaign.status == CampaignStatus.DRAFT

    campaigns = await campaigns_service.list_campaigns(db_session)
    assert len(campaigns) == 1


@respx.mock
async def test_run_collect_job_stores_leads(db_ready: Settings) -> None:
    respx.get(f"{BASE_URL}/2.0/region/search").mock(
        return_value=httpx.Response(200, json=_fixture("twogis_region_search_response.json"))
    )
    respx.get(f"{BASE_URL}/3.0/items").mock(
        return_value=httpx.Response(200, json=_fixture("twogis_items_response.json"))
    )
    respx.head("https://example.com").mock(return_value=httpx.Response(200))
    db_ready.source.twogis_api_key = "test-key"

    from leadgis.db.engine import session_scope

    async with session_scope() as session:
        campaign = await campaigns_service.create_campaign(
            session, name="Тест", niche="веб-студия", city="Москва", source="twogis_api"
        )
        campaign_id = campaign.id

    runner = JobRunner()
    ctx = JobContext("job-1", runner)
    await campaigns_service.run_collect_job(ctx, campaign_id, db_ready)

    async with session_scope() as session:
        campaign = await campaigns_service.get_campaign(session, campaign_id)
        assert campaign is not None
        assert campaign.status == CampaignStatus.READY

        result = await session.execute(Lead.__table__.select())
        leads = result.fetchall()
        assert len(leads) == 2


@respx.mock
async def test_run_collect_job_still_reaches_ready_when_enrichment_crashes(
    db_ready: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    respx.get(f"{BASE_URL}/2.0/region/search").mock(
        return_value=httpx.Response(200, json=_fixture("twogis_region_search_response.json"))
    )
    respx.get(f"{BASE_URL}/3.0/items").mock(
        return_value=httpx.Response(200, json=_fixture("twogis_items_response.json"))
    )
    db_ready.source.twogis_api_key = "test-key"

    async def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("enrichment blew up")

    monkeypatch.setattr("leadgis.services.campaigns.enrich_campaign_leads", _boom)

    from leadgis.db.engine import session_scope

    async with session_scope() as session:
        campaign = await campaigns_service.create_campaign(
            session, name="Тест", niche="веб-студия", city="Москва", source="twogis_api"
        )
        campaign_id = campaign.id

    runner = JobRunner()
    ctx = JobContext("job-3", runner)
    await campaigns_service.run_collect_job(ctx, campaign_id, db_ready)

    async with session_scope() as session:
        campaign = await campaigns_service.get_campaign(session, campaign_id)
        assert campaign is not None
        assert campaign.status == CampaignStatus.READY


async def test_run_collect_job_fails_without_api_key(db_ready: Settings) -> None:
    from leadgis.db.engine import session_scope

    async with session_scope() as session:
        campaign = await campaigns_service.create_campaign(
            session, name="Тест", niche="веб-студия", city="Москва", source="twogis_api"
        )
        campaign_id = campaign.id

    runner = JobRunner()
    ctx = JobContext("job-2", runner)
    with pytest.raises(SourceError, match="2GIS API key is not configured"):
        await campaigns_service.run_collect_job(ctx, campaign_id, db_ready)

    async with session_scope() as session:
        campaign = await campaigns_service.get_campaign(session, campaign_id)
        assert campaign is not None
        assert campaign.status == CampaignStatus.FAILED

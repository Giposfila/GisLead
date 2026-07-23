from __future__ import annotations

from httpx import AsyncClient

from leadgis.db.engine import session_scope
from leadgis.db.models import Lead, WebsiteStatus


async def test_list_leads_empty_campaign(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]

    resp = await client.get(f"/api/campaigns/{campaign_id}/leads")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"items": [], "total": 0, "page": 1, "page_size": 50}


async def _seed_lead(campaign_id: int) -> int:
    async with session_scope() as session:
        lead = Lead(
            campaign_id=campaign_id,
            name="Бизнес Альфа",
            phone_e164="+79991112233",
            website_status=WebsiteStatus.NONE,
        )
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        return lead.id


async def test_patch_lead_updates_status(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]
    lead_id = await _seed_lead(campaign_id)

    resp = await client.patch(f"/api/leads/{lead_id}", json={"status": "message_ready"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "message_ready"

    resp = await client.get(f"/api/campaigns/{campaign_id}/leads")
    assert resp.json()["items"][0]["status"] == "message_ready"


async def test_patch_lead_rejects_unknown_status(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]
    lead_id = await _seed_lead(campaign_id)

    resp = await client.patch(f"/api/leads/{lead_id}", json={"status": "not_a_status"})
    assert resp.status_code == 400


async def test_patch_missing_lead_404s(client: AsyncClient) -> None:
    resp = await client.patch("/api/leads/999", json={"status": "sent"})
    assert resp.status_code == 404


async def test_list_leads_filters_by_has_phone_and_website_status(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]
    await _seed_lead(campaign_id)
    async with session_scope() as session:
        session.add(
            Lead(
                campaign_id=campaign_id,
                name="Без телефона",
                website="https://example.com",
                website_status=WebsiteStatus.ALIVE,
            )
        )
        await session.commit()

    resp = await client.get(
        f"/api/campaigns/{campaign_id}/leads",
        params={"has_phone": "true", "website_status": "none"},
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Бизнес Альфа"

    resp = await client.get(f"/api/campaigns/{campaign_id}/leads", params={"q": "телефона"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["name"] == "Без телефона"

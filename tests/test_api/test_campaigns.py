from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import respx
from httpx import AsyncClient

from leadgis.sources.twogis_api import BASE_URL


def _fixture(name: str) -> dict:
    path = Path(__file__).resolve().parents[1] / "fixtures" / name
    return json.loads(path.read_text())


async def test_create_list_and_get_campaign(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    assert resp.status_code == 200
    campaign = resp.json()
    assert campaign["status"] == "draft"

    resp = await client.get("/api/campaigns")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get(f"/api/campaigns/{campaign['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Тест"


async def test_get_missing_campaign_404s(client: AsyncClient) -> None:
    resp = await client.get("/api/campaigns/999")
    assert resp.status_code == 404


async def test_list_niches(client: AsyncClient) -> None:
    resp = await client.get("/api/niches")
    assert resp.status_code == 200
    assert "веб-студия" in resp.json()


@respx.mock
async def test_collect_job_runs_end_to_end(client: AsyncClient) -> None:
    respx.get(f"{BASE_URL}/2.0/region/search").mock(
        return_value=httpx.Response(200, json=_fixture("twogis_region_search_response.json"))
    )
    respx.get(f"{BASE_URL}/3.0/items").mock(
        return_value=httpx.Response(200, json=_fixture("twogis_items_response.json"))
    )
    respx.head("https://example.com").mock(return_value=httpx.Response(200))

    await client.put("/api/settings", json={"source": {"twogis_api_key": "test-key"}})

    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]

    resp = await client.post(f"/api/campaigns/{campaign_id}/collect")
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    for _ in range(50):
        job = (await client.get(f"/api/jobs/{job_id}")).json()
        if job["status"] in ("done", "failed", "cancelled"):
            break
        await asyncio.sleep(0.05)
    assert job["status"] == "done", job

    resp = await client.get(f"/api/campaigns/{campaign_id}/leads")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2

    with_website = next(item for item in body["items"] if item["website"])
    assert with_website["website_status"] == "alive"
    assert with_website["phone_e164"] == "+79991234567"
    assert with_website["whatsapp_url"] == "https://wa.me/79991234567"

    without_website = next(item for item in body["items"] if not item["website"])
    assert without_website["website_status"] == "none"

    resp = await client.get(
        f"/api/campaigns/{campaign_id}/leads",
        params={"has_phone": "true", "website_status": "none"},
    )
    assert resp.json()["total"] == 1

    resp = await client.get(f"/api/campaigns/{campaign_id}")
    assert resp.json()["status"] == "ready"

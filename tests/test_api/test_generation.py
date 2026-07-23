from __future__ import annotations

import asyncio

import httpx
import pytest
from httpx import AsyncClient

from leadgis.db.engine import session_scope
from leadgis.db.models import Lead, Message, WebsiteStatus

OLLAMA_BASE_URL = "http://localhost:11434"


async def _ollama_available() -> str | None:
    try:
        async with httpx.AsyncClient(timeout=2.0) as http_client:
            resp = await http_client.get(f"{OLLAMA_BASE_URL}/api/tags")
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return models[0]["name"] if models else None
    except httpx.HTTPError:
        return None


async def _seed_lead(campaign_id: int, *, with_message: bool = False) -> int:
    async with session_scope() as session:
        lead = Lead(
            campaign_id=campaign_id,
            name="Бизнес Альфа",
            category="Веб-студия",
            phone_e164="+79991112233",
            rating=4.5,
            reviews_count=12,
            website_status=WebsiteStatus.NONE,
        )
        session.add(lead)
        await session.flush()
        if with_message:
            session.add(
                Message(
                    lead_id=lead.id,
                    text="Старое сообщение",
                    provider="stub",
                    model="stub-model",
                    prompt_template="outreach_ru.md",
                    is_current=True,
                )
            )
        await session.commit()
        return lead.id


async def test_generate_lead_message_end_to_end_with_ollama(client: AsyncClient) -> None:
    model = await _ollama_available()
    if not model:
        pytest.skip("Ollama not reachable locally")

    await client.put(
        "/api/settings",
        json={
            "llm": {
                "provider": "openai_compat",
                "base_url": f"{OLLAMA_BASE_URL}/v1",
                "model": model,
            }
        },
    )

    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]
    lead_id = await _seed_lead(campaign_id)

    resp = await client.post(f"/api/leads/{lead_id}/generate")
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    job = {}
    for _ in range(600):
        job = (await client.get(f"/api/jobs/{job_id}")).json()
        if job["status"] in ("done", "failed", "cancelled"):
            break
        await asyncio.sleep(0.5)
    assert job["status"] == "done", job

    resp = await client.get(f"/api/campaigns/{campaign_id}/leads")
    lead_body = resp.json()["items"][0]
    assert lead_body["status"] == "message_ready"


async def test_get_lead_message_returns_null_when_none(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]
    lead_id = await _seed_lead(campaign_id, with_message=False)

    resp = await client.get(f"/api/leads/{lead_id}/message")
    assert resp.status_code == 200
    assert resp.json() is None


async def test_get_lead_message_returns_current_message(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]
    lead_id = await _seed_lead(campaign_id, with_message=True)

    resp = await client.get(f"/api/leads/{lead_id}/message")
    assert resp.status_code == 200
    assert resp.json()["text"] == "Старое сообщение"


async def test_put_lead_message_updates_current_message(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]
    lead_id = await _seed_lead(campaign_id, with_message=True)

    resp = await client.put(f"/api/leads/{lead_id}/message", json={"text": "Новый текст"})
    assert resp.status_code == 200
    assert resp.json()["text"] == "Новый текст"


async def test_put_lead_message_404_when_no_message_exists(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]
    lead_id = await _seed_lead(campaign_id, with_message=False)

    resp = await client.put(f"/api/leads/{lead_id}/message", json={"text": "Новый текст"})
    assert resp.status_code == 404


async def test_wa_link_urlencodes_current_message(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]
    lead_id = await _seed_lead(campaign_id, with_message=True)

    resp = await client.get(f"/api/leads/{lead_id}/wa-link")
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert url.startswith("https://wa.me/79991112233?text=")


async def test_wa_link_404_without_phone(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]
    async with session_scope() as session:
        lead = Lead(campaign_id=campaign_id, name="Без телефона", website_status=WebsiteStatus.NONE)
        session.add(lead)
        await session.commit()
        lead_id = lead.id

    resp = await client.get(f"/api/leads/{lead_id}/wa-link")
    assert resp.status_code == 404


async def test_generate_missing_lead_404s(client: AsyncClient) -> None:
    resp = await client.post("/api/leads/999/generate")
    assert resp.status_code == 404

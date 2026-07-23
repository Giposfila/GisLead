from __future__ import annotations

import io

import openpyxl
from httpx import AsyncClient

from leadgis.db.engine import session_scope
from leadgis.db.models import Lead, WebsiteStatus


async def _create_campaign_with_lead(client: AsyncClient) -> int:
    resp = await client.post(
        "/api/campaigns",
        json={"name": "Тест", "niche": "веб-студия", "city": "Москва", "source": "twogis_api"},
    )
    campaign_id = resp.json()["id"]
    async with session_scope() as session:
        session.add(
            Lead(
                campaign_id=campaign_id,
                name="Кафе «Ромашка»",
                phone_e164="+79991112233",
                website_status=WebsiteStatus.NONE,
            )
        )
        await session.commit()
    return campaign_id


async def test_export_csv_returns_bom_and_attachment_headers(client: AsyncClient) -> None:
    campaign_id = await _create_campaign_with_lead(client)

    resp = await client.get(f"/api/campaigns/{campaign_id}/export?format=csv")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"\xef\xbb\xbf")
    assert "Кафе" in resp.content.decode("utf-8-sig")


async def test_export_xlsx_returns_valid_workbook(client: AsyncClient) -> None:
    campaign_id = await _create_campaign_with_lead(client)

    resp = await client.get(f"/api/campaigns/{campaign_id}/export?format=xlsx")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    ws = wb.active
    assert ws["A1"].value == "Название"


async def test_export_404s_for_missing_campaign(client: AsyncClient) -> None:
    resp = await client.get("/api/campaigns/999/export?format=csv")
    assert resp.status_code == 404


async def test_export_400s_for_unsupported_format(client: AsyncClient) -> None:
    campaign_id = await _create_campaign_with_lead(client)
    resp = await client.get(f"/api/campaigns/{campaign_id}/export?format=pdf")
    assert resp.status_code == 422

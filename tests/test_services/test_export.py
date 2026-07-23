from __future__ import annotations

import csv
import io

import openpyxl
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadgis.db.models import Campaign, Lead, Message, WebsiteStatus
from leadgis.services.export import (
    CampaignNotFoundError,
    export_campaign_bytes,
    fetch_export_rows,
    render_csv,
    render_xlsx,
)


async def _seed(session: AsyncSession) -> int:
    campaign = Campaign(name="Тест", niche="веб-студия", city="Москва", source="twogis_api")
    session.add(campaign)
    await session.flush()

    lead_with_message = Lead(
        campaign_id=campaign.id,
        name="Кафе «Ромашка»",
        category="Кафе",
        phone_e164="+79991112233",
        website_status=WebsiteStatus.NONE,
    )
    lead_without_message = Lead(
        campaign_id=campaign.id,
        name="Бар «Полночь»",
        website_status=WebsiteStatus.UNKNOWN,
    )
    session.add_all([lead_with_message, lead_without_message])
    await session.flush()

    session.add(
        Message(
            lead_id=lead_with_message.id,
            text="Здравствуйте! Привет из LeadGis.",
            provider="stub",
            model="stub-model",
            prompt_template="outreach_ru.md",
            is_current=True,
        )
    )
    await session.commit()
    return campaign.id


async def test_fetch_export_rows_joins_current_message(db_session: AsyncSession) -> None:
    campaign_id = await _seed(db_session)
    rows = await fetch_export_rows(db_session, campaign_id)

    assert len(rows) == 2
    by_name = {row.name: row for row in rows}
    assert by_name["Кафе «Ромашка»"].message == "Здравствуйте! Привет из LeadGis."
    assert by_name["Бар «Полночь»"].message == ""


async def test_export_campaign_bytes_raises_for_missing_campaign(db_session: AsyncSession) -> None:
    with pytest.raises(CampaignNotFoundError):
        await export_campaign_bytes(db_session, 999, "csv")


async def test_export_campaign_bytes_rejects_unknown_format(db_session: AsyncSession) -> None:
    campaign_id = await _seed(db_session)
    with pytest.raises(ValueError, match="Unsupported export format"):
        await export_campaign_bytes(db_session, campaign_id, "pdf")


def test_render_csv_has_bom_and_cyrillic_row() -> None:
    from leadgis.services.export import ExportRow

    row = ExportRow(
        name="Кафе",
        category=None,
        address=None,
        phone_e164="+79991112233",
        website=None,
        website_status="none",
        whatsapp_url=None,
        telegram_url=None,
        instagram_url=None,
        rating=None,
        reviews_count=None,
        status="new",
        message="Привет!",
    )
    data = render_csv([row])
    assert data.startswith(b"\xef\xbb\xbf")

    text = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header, body = list(reader)
    assert header[0] == "Название"
    assert body[0] == "Кафе"
    assert body[-1] == "Привет!"


def test_render_xlsx_produces_readable_workbook() -> None:
    from leadgis.services.export import ExportRow

    row = ExportRow(
        name="Кафе",
        category="Общепит",
        address=None,
        phone_e164=None,
        website=None,
        website_status="none",
        whatsapp_url=None,
        telegram_url=None,
        instagram_url=None,
        rating=4.8,
        reviews_count=10,
        status="new",
        message="",
    )
    data = render_xlsx([row])
    wb = openpyxl.load_workbook(io.BytesIO(data))
    ws = wb.active
    assert ws["A1"].value == "Название"
    assert ws["A2"].value == "Кафе"
    assert ws["B2"].value == "Общепит"

"""CSV/XLSX export of a campaign's leads."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadgis.db.engine import session_scope
from leadgis.db.models import Campaign, Lead, Message

SUPPORTED_FORMATS = ("csv", "xlsx")

COLUMNS: tuple[tuple[str, str], ...] = (
    ("name", "Название"),
    ("category", "Категория"),
    ("address", "Адрес"),
    ("phone_e164", "Телефон"),
    ("website", "Сайт"),
    ("website_status", "Статус сайта"),
    ("whatsapp_url", "WhatsApp"),
    ("telegram_url", "Telegram"),
    ("instagram_url", "Instagram"),
    ("rating", "Рейтинг"),
    ("reviews_count", "Отзывов"),
    ("status", "Статус лида"),
    ("message", "Сообщение"),
)


class CampaignNotFoundError(Exception):
    pass


@dataclass
class ExportRow:
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
    message: str


def _cell(row: ExportRow, field: str) -> Any:
    value = getattr(row, field)
    return value if value is not None else ""


async def fetch_export_rows(session: AsyncSession, campaign_id: int) -> list[ExportRow]:
    """Only data the user collected/generated — no hidden fields (AGENT.md §14.5)."""
    result = await session.execute(
        select(Lead, Message.text)
        .outerjoin(Message, (Message.lead_id == Lead.id) & Message.is_current.is_(True))
        .where(Lead.campaign_id == campaign_id)
        .order_by(Lead.id)
    )
    return [
        ExportRow(
            name=lead.name,
            category=lead.category,
            address=lead.address,
            phone_e164=lead.phone_e164,
            website=lead.website,
            website_status=lead.website_status,
            whatsapp_url=lead.whatsapp_url,
            telegram_url=lead.telegram_url,
            instagram_url=lead.instagram_url,
            rating=lead.rating,
            reviews_count=lead.reviews_count,
            status=lead.status,
            message=message_text or "",
        )
        for lead, message_text in result.all()
    ]


def render_csv(rows: list[ExportRow]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(label for _, label in COLUMNS)
    for row in rows:
        writer.writerow(_cell(row, field) for field, _ in COLUMNS)
    # utf-8-sig (BOM) so Excel renders Cyrillic correctly instead of mojibake.
    return buf.getvalue().encode("utf-8-sig")


def render_xlsx(rows: list[ExportRow]) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Leads"
    ws.append([label for _, label in COLUMNS])
    for row in rows:
        ws.append([_cell(row, field) for field, _ in COLUMNS])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def render(rows: list[ExportRow], fmt: str) -> bytes:
    if fmt == "csv":
        return render_csv(rows)
    if fmt == "xlsx":
        return render_xlsx(rows)
    raise ValueError(f"Unsupported export format: {fmt!r}, expected one of {SUPPORTED_FORMATS}")


async def export_campaign_bytes(session: AsyncSession, campaign_id: int, fmt: str) -> bytes:
    """Used by the HTTP API: renders in memory, no file left on the server."""
    if await session.get(Campaign, campaign_id) is None:
        raise CampaignNotFoundError(f"Campaign {campaign_id} not found")
    rows = await fetch_export_rows(session, campaign_id)
    return render(rows, fmt)


async def export_campaign(campaign_id: int, fmt: str, output: str | None) -> str:
    """CLI entry point: writes the export to disk and returns the file path."""
    async with session_scope() as session:
        data = await export_campaign_bytes(session, campaign_id, fmt)
    path = Path(output) if output else Path(f"leadgis_export_{campaign_id}.{fmt}")
    path.write_bytes(data)
    return str(path)

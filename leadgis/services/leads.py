"""Lead CRUD, filtering, and status transitions."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadgis.db.models import Lead, LeadStatus, Message
from leadgis.enrichment.messengers import build_whatsapp_url


class LeadNotFoundError(Exception):
    pass


class InvalidLeadStatusError(Exception):
    pass


class MessageNotFoundError(Exception):
    pass


async def list_leads(
    session: AsyncSession,
    *,
    campaign_id: int,
    status: str | None = None,
    website_status: str | None = None,
    has_phone: bool | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Lead], int]:
    stmt = select(Lead).where(Lead.campaign_id == campaign_id)
    if status:
        stmt = stmt.where(Lead.status == status)
    if website_status:
        stmt = stmt.where(Lead.website_status == website_status)
    if has_phone is not None:
        stmt = stmt.where(Lead.phone_e164.is_not(None) if has_phone else Lead.phone_e164.is_(None))
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            Lead.name.ilike(pattern) | Lead.category.ilike(pattern) | Lead.address.ilike(pattern)
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(Lead.id).offset((page - 1) * page_size).limit(page_size)
    leads = (await session.execute(stmt)).scalars().all()
    return list(leads), total


async def update_lead(
    session: AsyncSession,
    lead_id: int,
    *,
    status: str | None = None,
    name: str | None = None,
    phone_e164: str | None = None,
    website: str | None = None,
) -> Lead:
    lead = await session.get(Lead, lead_id)
    if lead is None:
        raise LeadNotFoundError(f"Lead {lead_id} not found")

    if status is not None:
        if status not in {s.value for s in LeadStatus}:
            raise InvalidLeadStatusError(f"Unknown lead status: {status}")
        lead.status = status
    if name is not None:
        lead.name = name
    if phone_e164 is not None:
        lead.phone_e164 = phone_e164
    if website is not None:
        lead.website = website

    await session.commit()
    await session.refresh(lead)
    return lead


async def get_current_message(session: AsyncSession, lead_id: int) -> Message | None:
    stmt = select(Message).where(Message.lead_id == lead_id, Message.is_current.is_(True))
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_current_message(session: AsyncSession, lead_id: int, text: str) -> Message:
    message = await get_current_message(session, lead_id)
    if message is None:
        raise MessageNotFoundError(f"Lead {lead_id} has no current message")
    message.text = text
    await session.commit()
    await session.refresh(message)
    return message


async def build_wa_link(session: AsyncSession, lead_id: int) -> str:
    lead = await session.get(Lead, lead_id)
    if lead is None:
        raise LeadNotFoundError(f"Lead {lead_id} not found")
    message = await get_current_message(session, lead_id)
    url = build_whatsapp_url(lead.phone_e164, message.text if message else None)
    if url is None:
        raise LeadNotFoundError(f"Lead {lead_id} has no phone number")
    return url

"""Lead listing (filtered, paginated) and status/field updates."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from leadgis.api.deps import get_job_runner, get_session, get_settings
from leadgis.api.schemas import (
    JobIdOut,
    LeadOut,
    LeadPageOut,
    LeadPatchIn,
    MessageOut,
    MessagePutIn,
    WaLinkOut,
)
from leadgis.config import Settings
from leadgis.db.models import Lead
from leadgis.generation.generator import generate_for_leads
from leadgis.services import leads as leads_service
from leadgis.worker import JobContext, JobRunner

router = APIRouter(tags=["leads"])


@router.get("/campaigns/{campaign_id}/leads", response_model=LeadPageOut)
async def list_leads(
    campaign_id: int,
    status: str | None = None,
    website_status: str | None = None,
    has_phone: bool | None = None,
    q: str | None = Query(None, description="Search in name/category/address"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> LeadPageOut:
    leads, total = await leads_service.list_leads(
        session,
        campaign_id=campaign_id,
        status=status,
        website_status=website_status,
        has_phone=has_phone,
        q=q,
        page=page,
        page_size=page_size,
    )
    return LeadPageOut(
        items=[LeadOut.model_validate(lead, from_attributes=True) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/leads/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: int, payload: LeadPatchIn, session: AsyncSession = Depends(get_session)
) -> LeadOut:
    try:
        lead = await leads_service.update_lead(
            session,
            lead_id,
            status=payload.status,
            name=payload.name,
            phone_e164=payload.phone_e164,
            website=payload.website,
        )
    except leads_service.LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Lead not found") from exc
    except leads_service.InvalidLeadStatusError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LeadOut.model_validate(lead, from_attributes=True)


@router.post("/leads/{lead_id}/generate", response_model=JobIdOut)
async def generate_lead_message(
    lead_id: int,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    runner: JobRunner = Depends(get_job_runner),
) -> JobIdOut:
    lead = await session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    async def _run(ctx: JobContext) -> None:
        await generate_for_leads(ctx, [lead_id], settings)

    job_id = await runner.submit("generate", lead.campaign_id, _run)
    return JobIdOut(job_id=job_id)


@router.get("/leads/{lead_id}/message", response_model=MessageOut | None)
async def get_lead_message(
    lead_id: int, session: AsyncSession = Depends(get_session)
) -> MessageOut | None:
    message = await leads_service.get_current_message(session, lead_id)
    if message is None:
        return None
    return MessageOut.model_validate(message, from_attributes=True)


@router.put("/leads/{lead_id}/message", response_model=MessageOut)
async def update_lead_message(
    lead_id: int, payload: MessagePutIn, session: AsyncSession = Depends(get_session)
) -> MessageOut:
    try:
        message = await leads_service.update_current_message(session, lead_id, payload.text)
    except leads_service.MessageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MessageOut.model_validate(message, from_attributes=True)


@router.get("/leads/{lead_id}/wa-link", response_model=WaLinkOut)
async def get_wa_link(lead_id: int, session: AsyncSession = Depends(get_session)) -> WaLinkOut:
    try:
        url = await leads_service.build_wa_link(session, lead_id)
    except leads_service.LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WaLinkOut(url=url)

"""Job status and cancellation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from leadgis.api.deps import get_job_runner, get_session
from leadgis.api.schemas import JobOut
from leadgis.db.models import Job
from leadgis.worker import JobRunner

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)) -> JobOut:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job, from_attributes=True)


@router.post("/jobs/{job_id}/cancel", status_code=204)
async def cancel_job(job_id: str, runner: JobRunner = Depends(get_job_runner)) -> None:
    await runner.cancel(job_id)

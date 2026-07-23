"""GET /events — Server-Sent Events stream of job progress."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from leadgis.api.deps import get_job_runner
from leadgis.worker import JobRunner

router = APIRouter(tags=["events"])

HEARTBEAT_SECONDS = 15


@router.get("/events")
async def stream_events(
    request: Request, runner: JobRunner = Depends(get_job_runner)
) -> StreamingResponse:
    queue = runner.event_bus.subscribe()

    async def generate() -> AsyncIterator[str]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                    yield message
                except TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            runner.event_bus.unsubscribe(queue)

    return StreamingResponse(generate(), media_type="text/event-stream")

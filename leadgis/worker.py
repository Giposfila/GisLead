"""In-process job queue, JobRunner, and SSE event bus (AGENT.md §10)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, update

from leadgis.db.engine import session_scope
from leadgis.db.models import Job, JobStatus

logger = logging.getLogger("leadgis.worker")


class JobCancelled(Exception):
    pass


class EventBus:
    """In-memory pub/sub backing the SSE endpoint."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: str, data: dict[str, object]) -> None:
        payload = f"event: {event}\ndata: {json.dumps(data)}\n\n"
        for queue in list(self._subscribers):
            await queue.put(payload)


class JobContext:
    def __init__(self, job_id: str, runner: JobRunner, campaign_id: int | None = None) -> None:
        self.job_id = job_id
        self.campaign_id = campaign_id
        self._runner = runner

    def check_cancelled(self) -> None:
        if self.job_id in self._runner._cancelled:
            raise JobCancelled()

    async def set_progress(self, done: int, total: int, detail: str | None = None) -> None:
        self.check_cancelled()
        progress = int(done / total * 100) if total else 0
        async with session_scope() as session:
            await session.execute(
                update(Job).where(Job.id == self.job_id).values(progress=progress, detail=detail)
            )
            await session.commit()
        await self._runner.event_bus.publish(
            "job_progress",
            {
                "job_id": self.job_id,
                "campaign_id": self.campaign_id,
                "done": done,
                "total": total,
                "detail": detail,
            },
        )


@dataclass(slots=True)
class JobSpec:
    job_id: str
    kind: str
    campaign_id: int | None
    run: Callable[[JobContext], Awaitable[None]]


class JobRunner:
    def __init__(self, concurrency: int = 1) -> None:
        self.concurrency = concurrency
        self.event_bus = EventBus()
        self.queue: asyncio.Queue[JobSpec] = asyncio.Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._cancelled: set[str] = set()

    async def start(self) -> None:
        async with session_scope() as session:
            result = await session.execute(select(Job).where(Job.status == JobStatus.RUNNING))
            interrupted = result.scalars().all()
            for job in interrupted:
                job.status = JobStatus.FAILED
                job.detail = "Interrupted by server restart"
                job.finished_at = datetime.now(UTC)
            await session.commit()

        self._workers = [asyncio.create_task(self._worker_loop()) for _ in range(self.concurrency)]

    async def stop(self) -> None:
        for task in self._workers:
            task.cancel()
        for task in self._workers:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._workers = []

    async def submit(
        self,
        kind: str,
        campaign_id: int | None,
        run: Callable[[JobContext], Awaitable[None]],
    ) -> str:
        job_id = uuid.uuid4().hex
        async with session_scope() as session:
            session.add(Job(id=job_id, kind=kind, campaign_id=campaign_id, status=JobStatus.QUEUED))
            await session.commit()
        await self.queue.put(JobSpec(job_id=job_id, kind=kind, campaign_id=campaign_id, run=run))
        return job_id

    async def cancel(self, job_id: str) -> None:
        self._cancelled.add(job_id)

    async def _worker_loop(self) -> None:
        while True:
            spec = await self.queue.get()
            await self._run_job(spec)

    async def _run_job(self, spec: JobSpec) -> None:
        async with session_scope() as session:
            await session.execute(
                update(Job).where(Job.id == spec.job_id).values(status=JobStatus.RUNNING)
            )
            await session.commit()
        await self.event_bus.publish(
            "job_progress",
            {"job_id": spec.job_id, "campaign_id": spec.campaign_id, "status": "running"},
        )

        ctx = JobContext(spec.job_id, self, spec.campaign_id)
        status = JobStatus.DONE
        detail: str | None = None
        try:
            await spec.run(ctx)
        except JobCancelled:
            status = JobStatus.CANCELLED
        except Exception as exc:  # noqa: BLE001 - one bad job must not kill the runner
            status = JobStatus.FAILED
            detail = str(exc)
            logger.exception("job %s failed", spec.job_id)
        finally:
            self._cancelled.discard(spec.job_id)

        async with session_scope() as session:
            await session.execute(
                update(Job)
                .where(Job.id == spec.job_id)
                .values(status=status, detail=detail, finished_at=datetime.now(UTC))
            )
            await session.commit()
        await self.event_bus.publish(
            "job_progress",
            {
                "job_id": spec.job_id,
                "campaign_id": spec.campaign_id,
                "status": status,
                "detail": detail,
            },
        )

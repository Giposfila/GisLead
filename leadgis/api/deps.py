"""FastAPI dependencies: DB session, settings, job runner."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from leadgis.config import Settings, load_settings
from leadgis.db.engine import get_sessionmaker
from leadgis.worker import JobRunner


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


def get_settings() -> Settings:
    """Always reload from config.toml so Settings-UI changes apply without a restart."""
    return load_settings()


def get_job_runner(request: Request) -> JobRunner:
    return request.app.state.job_runner  # type: ignore[no-any-return]

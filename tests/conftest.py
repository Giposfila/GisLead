from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from leadgis.config import Settings
from leadgis.db import engine as db_engine
from leadgis.db.models import Base


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test.db")


@pytest_asyncio.fixture
async def db_session(tmp_db_path: str):
    await db_engine.reset_engine()
    engine = db_engine.get_engine(tmp_db_path)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with db_engine.session_scope() as session:
        yield session
    await db_engine.reset_engine()


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "leadgis.db"
    monkeypatch.setattr("leadgis.config.CONFIG_PATH", config_path)
    monkeypatch.setattr("leadgis.config.LEADGIS_HOME", tmp_path)
    monkeypatch.setattr("leadgis.config.DB_PATH", db_path)
    result = Settings()
    result.app.open_browser = False
    return result


@pytest_asyncio.fixture
async def db_ready(settings: Settings) -> AsyncIterator[Settings]:
    """Settings with config.DB_PATH patched and schema created (no HTTP app)."""
    await db_engine.reset_engine()
    engine = db_engine.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield settings
    await db_engine.reset_engine()


@pytest_asyncio.fixture
async def client(settings: Settings, tmp_path: Path) -> AsyncIterator[AsyncClient]:
    await db_engine.reset_engine()
    from leadgis.main import create_app

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    await db_engine.reset_engine()

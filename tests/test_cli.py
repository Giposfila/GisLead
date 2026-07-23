from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from leadgis.cli import app
from leadgis.config import Settings
from leadgis.db import engine as db_engine
from leadgis.db.models import Base, Campaign, Lead, WebsiteStatus

runner = CliRunner()


@pytest.fixture
async def seeded_campaign(settings: Settings) -> int:
    await db_engine.reset_engine()
    engine = db_engine.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with db_engine.session_scope() as session:
        campaign = Campaign(name="CLI-тест", niche="кафе", city="Казань", source="twogis_api")
        session.add(campaign)
        await session.flush()
        session.add(
            Lead(
                campaign_id=campaign.id,
                name="Пекарня",
                phone_e164="+79995554433",
                website_status=WebsiteStatus.NONE,
            )
        )
        await session.commit()
        campaign_id = campaign.id
    yield campaign_id
    await db_engine.reset_engine()


def test_export_writes_csv_file(seeded_campaign: int, tmp_path: Path) -> None:
    output = tmp_path / "out.csv"
    result = runner.invoke(app, ["export", str(seeded_campaign), "--output", str(output)])

    assert result.exit_code == 0, result.output
    assert output.exists()
    text = output.read_bytes().decode("utf-8-sig")
    assert "Пекарня" in text


def test_export_missing_campaign_exits_nonzero(db_ready: Settings) -> None:
    result = runner.invoke(app, ["export", "999"])

    assert result.exit_code == 1
    assert "not found" in result.output

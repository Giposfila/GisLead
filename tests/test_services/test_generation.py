from __future__ import annotations

import pytest
from sqlalchemy import select

from leadgis.config import Settings
from leadgis.db.engine import session_scope
from leadgis.db.models import Campaign, CampaignStatus, Lead, LeadStatus, Message, WebsiteStatus
from leadgis.generation.generator import generate_for_leads
from leadgis.llm.base import LLMResult, RateLimitError
from leadgis.worker import JobContext, JobRunner


async def _seed_lead(settings: Settings, name: str = "Бизнес Альфа") -> int:
    async with session_scope() as session:
        campaign = Campaign(
            name="Тест",
            niche="веб-студия",
            city="Москва",
            source="twogis_api",
            status=CampaignStatus.READY,
        )
        session.add(campaign)
        await session.flush()
        lead = Lead(
            campaign_id=campaign.id,
            name=name,
            category="Веб-студия",
            rating=4.5,
            reviews_count=10,
            website_status=WebsiteStatus.NONE,
            status=LeadStatus.NEW,
        )
        session.add(lead)
        await session.commit()
        return lead.id


class _StubProvider:
    id = "stub"

    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self.calls = 0

    async def complete(self, system: str, user: str, **kwargs: object) -> LLMResult:
        self.calls += 1
        return LLMResult(text=next(self._responses), tokens_in=10, tokens_out=5, model="stub-model")

    async def healthcheck(self):  # pragma: no cover - unused
        raise NotImplementedError

    async def list_models(self):  # pragma: no cover - unused
        raise NotImplementedError


async def test_generate_for_leads_stores_message_and_flips_status(
    db_ready: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    lead_id = await _seed_lead(db_ready)
    stub = _StubProvider(['"Привет! У вас классный рейтинг." '])
    monkeypatch.setattr("leadgis.generation.generator.get_llm_provider", lambda settings: stub)

    runner = JobRunner()
    ctx = JobContext("job-gen-1", runner)
    await generate_for_leads(ctx, [lead_id], db_ready)

    async with session_scope() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        assert lead.status == LeadStatus.MESSAGE_READY

        result = await session.execute(select(Message).where(Message.lead_id == lead_id))
        messages = result.scalars().all()
        assert len(messages) == 1
        assert messages[0].is_current is True
        # quotes stripped by post-processing
        assert messages[0].text == "Привет! У вас классный рейтинг."


async def test_generate_for_leads_regenerates_when_too_long(
    db_ready: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    lead_id = await _seed_lead(db_ready)
    too_long = "x" * 700
    short = "Короткое сообщение."
    stub = _StubProvider([too_long, short])
    monkeypatch.setattr("leadgis.generation.generator.get_llm_provider", lambda settings: stub)

    runner = JobRunner()
    ctx = JobContext("job-gen-2", runner)
    await generate_for_leads(ctx, [lead_id], db_ready)

    assert stub.calls == 2
    async with session_scope() as session:
        result = await session.execute(select(Message).where(Message.lead_id == lead_id))
        message = result.scalars().one()
        assert message.text == short


async def test_generate_for_leads_one_bad_lead_does_not_kill_batch(
    db_ready: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    lead_id_1 = await _seed_lead(db_ready, name="Обречённый Лид")
    lead_id_2 = await _seed_lead(db_ready, name="Здоровый Лид")

    class _FailingProvider(_StubProvider):
        async def complete(self, system: str, user: str, **kwargs: object) -> LLMResult:
            self.calls += 1
            if "Обречённый Лид" in user:
                raise RateLimitError("nope", retry_after=0.01)
            return await super().complete(system, user, **kwargs)

    stub = _FailingProvider(["Сообщение для второго лида."])
    monkeypatch.setattr("leadgis.generation.generator.get_llm_provider", lambda settings: stub)
    monkeypatch.setattr("leadgis.generation.generator.MAX_RETRIES", 0)

    runner = JobRunner()
    ctx = JobContext("job-gen-3", runner)
    await generate_for_leads(ctx, [lead_id_1, lead_id_2], db_ready)

    async with session_scope() as session:
        lead_1 = await session.get(Lead, lead_id_1)
        lead_2 = await session.get(Lead, lead_id_2)
        assert lead_1 is not None and lead_1.status == LeadStatus.NEW
        assert lead_2 is not None and lead_2.status == LeadStatus.MESSAGE_READY

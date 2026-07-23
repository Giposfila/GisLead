"""Prompt rendering + batch message generation (AGENT.md §9)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from sqlalchemy import select, update

from leadgis.config import Settings
from leadgis.constants import MAX_MESSAGE_LENGTH
from leadgis.db.engine import session_scope
from leadgis.db.models import Campaign, Lead, LeadStatus, Message, WebsiteStatus
from leadgis.llm.base import LLMProvider, RateLimitError
from leadgis.llm.registry import get_llm_provider
from leadgis.worker import JobCancelled, JobContext

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
MAX_RETRIES = 3
DEFAULT_RETRY_AFTER = 20.0

WEBSITE_STATUS_HUMAN: dict[str, str] = {
    WebsiteStatus.NONE: "нет сайта (только соцсети)",
    WebsiteStatus.ALIVE: "есть сайт",
    WebsiteStatus.DEAD: "сайт не работает",
    WebsiteStatus.UNKNOWN: "не проверено",
}


class _SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""


def parse_template(text: str) -> tuple[str, str]:
    if "# system" not in text or "# user" not in text:
        raise ValueError("Template must contain '# system' and '# user' sections")
    system_part = text.split("# system", 1)[1].split("# user", 1)[0].strip()
    user_part = text.split("# user", 1)[1].strip()
    return system_part, user_part


def render_template(template: str, context: dict[str, Any]) -> str:
    return template.format_map(_SafeDict(context))


def _postprocess(text: str) -> str:
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.strip("`").strip()
    return text.strip("\"'").strip()


async def _complete_with_retry(
    provider: LLMProvider, system: str, user: str
) -> tuple[str, str, int | None, int | None]:
    attempts = 0
    while True:
        try:
            result = await provider.complete(system, user)
        except RateLimitError as exc:
            attempts += 1
            if attempts > MAX_RETRIES:
                raise
            await asyncio.sleep(exc.retry_after or DEFAULT_RETRY_AFTER)
            continue

        text = _postprocess(result.text)
        if len(text) > MAX_MESSAGE_LENGTH:
            retry_result = await provider.complete(system, user, temperature=0.6)
            text = _postprocess(retry_result.text)
        return text, result.model, result.tokens_in, result.tokens_out


def _build_context(lead: Lead, campaign: Campaign, settings: Settings) -> dict[str, Any]:
    return {
        "name": lead.name,
        "category": lead.category or "",
        "city": campaign.city,
        # Some sources (e.g. Yandex Maps) never provide rating/reviews at
        # all — rendering that as "0 отзывов" would read as a verified fact
        # ("we checked, there are none") instead of "this data is missing".
        "rating_human": (
            f"{lead.rating} ({lead.reviews_count or 0} отзывов)"
            if lead.rating is not None
            else "нет данных"
        ),
        "website_status_human": WEBSITE_STATUS_HUMAN.get(lead.website_status, "не проверено"),
        "user_offer": settings.outreach.user_offer,
        "extra_instructions": settings.outreach.extra_instructions,
    }


async def generate_for_leads(ctx: JobContext, lead_ids: list[int], settings: Settings) -> None:
    provider = get_llm_provider(settings)
    template_text = (PROMPTS_DIR / settings.outreach.template).read_text()
    system_tmpl, user_tmpl = parse_template(template_text)

    concurrency = max(settings.llm.concurrency, 1)
    semaphore = asyncio.Semaphore(concurrency)
    total = len(lead_ids)
    done = 0
    lock = asyncio.Lock()

    async def _one(lead_id: int) -> None:
        nonlocal done
        async with semaphore:
            ctx.check_cancelled()
            async with session_scope() as session:
                lead = await session.get(Lead, lead_id)
                if lead is None:
                    return
                campaign = await session.get(Campaign, lead.campaign_id)
                assert campaign is not None
                context = _build_context(lead, campaign, settings)
                lead_name = lead.name

            system = render_template(system_tmpl, context)
            user = render_template(user_tmpl, context)

            try:
                text, model, tokens_in, tokens_out = await _complete_with_retry(
                    provider, system, user
                )
            except JobCancelled:
                raise
            except Exception:  # noqa: BLE001 - one bad lead must not kill the batch
                pass
            else:
                async with session_scope() as session:
                    await session.execute(
                        update(Message)
                        .where(Message.lead_id == lead_id, Message.is_current.is_(True))
                        .values(is_current=False)
                    )
                    session.add(
                        Message(
                            lead_id=lead_id,
                            text=text,
                            provider=provider.id,
                            model=model,
                            prompt_template=settings.outreach.template,
                            tokens_in=tokens_in,
                            tokens_out=tokens_out,
                            is_current=True,
                        )
                    )
                    lead = await session.get(Lead, lead_id)
                    assert lead is not None
                    lead.status = LeadStatus.MESSAGE_READY
                    await session.commit()

            async with lock:
                done += 1
            await ctx.set_progress(done, total, detail=lead_name)

    await asyncio.gather(*(_one(lead_id) for lead_id in lead_ids))


async def lead_ids_for_campaign(campaign_id: int) -> list[int]:
    async with session_scope() as session:
        result = await session.execute(select(Lead.id).where(Lead.campaign_id == campaign_id))
        return [row[0] for row in result.all()]

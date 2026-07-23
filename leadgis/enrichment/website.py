"""Website liveness check (AGENT.md §7.1)."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import httpx

from leadgis.constants import SOCIAL_ONLY_DOMAINS
from leadgis.db.models import WebsiteStatus

TIMEOUT_SECONDS = 8.0
MAX_REDIRECTS = 3


def _is_social_only(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return any(host == domain or host.endswith(f".{domain}") for domain in SOCIAL_ONLY_DOMAINS)


async def _probe(client: httpx.AsyncClient, url: str) -> str:
    """One scheme attempt: HEAD, falling back to GET if HEAD is rejected."""
    resp = await client.head(url, timeout=TIMEOUT_SECONDS)
    if resp.status_code >= 400:
        resp = await client.get(url, timeout=TIMEOUT_SECONDS)
    return WebsiteStatus.ALIVE if resp.status_code < 400 else WebsiteStatus.DEAD


async def check_website(url: str | None) -> str:
    if not url or not url.strip():
        return WebsiteStatus.NONE

    candidate = url.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"

    try:
        if _is_social_only(candidate):
            return WebsiteStatus.NONE
    except ValueError:
        return WebsiteStatus.DEAD

    schemes = [candidate]
    if candidate.startswith("https://"):
        schemes.append("http://" + candidate.removeprefix("https://"))

    async with httpx.AsyncClient(follow_redirects=True, max_redirects=MAX_REDIRECTS) as client:
        for i, scheme_url in enumerate(schemes):
            is_last = i == len(schemes) - 1
            try:
                return await _probe(client, scheme_url)
            except httpx.TimeoutException:
                return WebsiteStatus.UNKNOWN
            except (httpx.HTTPError, ValueError):
                # ValueError covers malformed URLs httpx rejects before any I/O
                # (e.g. bad IPv6 literals) — a bad website string is "dead", not a crash.
                if is_last:
                    return WebsiteStatus.DEAD
                continue
        return WebsiteStatus.DEAD


async def check_websites(urls: list[str | None], concurrency: int = 10) -> list[str]:
    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded(url: str | None) -> str:
        async with semaphore:
            return await check_website(url)

    return await asyncio.gather(*(_bounded(url) for url in urls))

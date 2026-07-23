from __future__ import annotations

import httpx
import respx

from leadgis.db.models import WebsiteStatus
from leadgis.enrichment.website import check_website


async def test_check_website_none_for_empty_url() -> None:
    assert await check_website(None) == WebsiteStatus.NONE
    assert await check_website("") == WebsiteStatus.NONE


async def test_check_website_none_for_social_only_domain() -> None:
    assert await check_website("https://instagram.com/example") == WebsiteStatus.NONE
    assert await check_website("vk.com/example") == WebsiteStatus.NONE


@respx.mock
async def test_check_website_alive_on_2xx() -> None:
    respx.head("https://example.com").mock(return_value=httpx.Response(200))
    assert await check_website("https://example.com") == WebsiteStatus.ALIVE


@respx.mock
async def test_check_website_alive_falls_back_to_get_when_head_rejected() -> None:
    respx.head("https://example.com").mock(return_value=httpx.Response(405))
    respx.get("https://example.com").mock(return_value=httpx.Response(200))
    assert await check_website("https://example.com") == WebsiteStatus.ALIVE


@respx.mock
async def test_check_website_dead_on_connection_error() -> None:
    respx.head("https://example.com").mock(side_effect=httpx.ConnectError("boom"))
    respx.get("https://example.com").mock(side_effect=httpx.ConnectError("boom"))
    respx.head("http://example.com").mock(side_effect=httpx.ConnectError("boom"))
    respx.get("http://example.com").mock(side_effect=httpx.ConnectError("boom"))
    assert await check_website("https://example.com") == WebsiteStatus.DEAD


@respx.mock
async def test_check_website_unknown_on_timeout() -> None:
    respx.head("https://example.com").mock(side_effect=httpx.TimeoutException("slow"))
    assert await check_website("https://example.com") == WebsiteStatus.UNKNOWN


@respx.mock
async def test_check_website_dead_on_5xx() -> None:
    respx.head("https://example.com").mock(return_value=httpx.Response(500))
    respx.get("https://example.com").mock(return_value=httpx.Response(500))
    assert await check_website("https://example.com") == WebsiteStatus.DEAD


async def test_check_website_dead_on_malformed_url_instead_of_raising() -> None:
    # A bad URL from a messy real-world data source must degrade gracefully,
    # not crash the enrichment pass for every other lead in the batch.
    assert await check_website("https://[bad") == WebsiteStatus.DEAD

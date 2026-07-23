from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from leadgis.config import Settings
from leadgis.sources.base import SourceError
from leadgis.sources.twogis_api import BASE_URL, TwoGisApiAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


async def _instant_sleep(_seconds: float) -> None:
    return None


@respx.mock
async def test_search_yields_parsed_orgs(db_ready: Settings) -> None:
    respx.get(f"{BASE_URL}/2.0/region/search").mock(
        return_value=httpx.Response(200, json=_load("twogis_region_search_response.json"))
    )
    respx.get(f"{BASE_URL}/3.0/items").mock(
        return_value=httpx.Response(200, json=_load("twogis_items_response.json"))
    )

    adapter = TwoGisApiAdapter(api_key="test-key", rps=1000)
    orgs = [org async for org in adapter.search("веб-студия", "Москва", limit=10)]

    assert len(orgs) == 2
    assert orgs[0].name == "Пример Студия"
    assert orgs[0].external_id == "70000001"
    assert orgs[0].phones == ["+7 999 123-45-67"]
    assert orgs[0].website == "https://example.com"
    assert orgs[0].instagram == "https://instagram.com/example"
    assert orgs[0].rating == 4.5
    assert orgs[0].reviews_count == 12
    assert orgs[1].category == "Автосервис"


@respx.mock
async def test_search_sends_region_id_not_city_id(db_ready: Settings) -> None:
    """Regression test: 2GIS's /3.0/items only recognizes `region_id`. Sending
    `city_id` (a param it doesn't understand) makes it silently drop the
    location filter and return 404 "Results not found" for most queries."""
    respx.get(f"{BASE_URL}/2.0/region/search").mock(
        return_value=httpx.Response(200, json=_load("twogis_region_search_response.json"))
    )
    items_route = respx.get(f"{BASE_URL}/3.0/items").mock(
        return_value=httpx.Response(200, json=_load("twogis_items_response.json"))
    )

    adapter = TwoGisApiAdapter(api_key="test-key", rps=1000)
    [_ async for _ in adapter.search("веб-студия", "Москва", limit=10)]

    sent_params = items_route.calls.last.request.url.params
    assert "region_id" in sent_params
    assert "city_id" not in sent_params


@respx.mock
async def test_search_respects_limit(db_ready: Settings) -> None:
    respx.get(f"{BASE_URL}/2.0/region/search").mock(
        return_value=httpx.Response(200, json=_load("twogis_region_search_response.json"))
    )
    respx.get(f"{BASE_URL}/3.0/items").mock(
        return_value=httpx.Response(200, json=_load("twogis_items_response.json"))
    )

    adapter = TwoGisApiAdapter(api_key="test-key", rps=1000)
    orgs = [org async for org in adapter.search("веб-студия", "Москва", limit=1)]

    assert len(orgs) == 1


@respx.mock
async def test_rate_limited_response_raises_after_retries(
    db_ready: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("leadgis.sources.twogis_api.asyncio.sleep", _instant_sleep)
    respx.get(f"{BASE_URL}/2.0/region/search").mock(return_value=httpx.Response(429))

    adapter = TwoGisApiAdapter(api_key="bad-key", rps=1000)

    with pytest.raises(SourceError, match="2GIS key exhausted or invalid"):
        async for _ in adapter.search("веб-студия", "Москва", limit=1):
            pass


@respx.mock
async def test_search_raises_on_2gis_error_in_200_response(db_ready: Settings) -> None:
    """2GIS reports request errors (bad params, quota, etc.) inside a 200-status
    JSON body. Regression test: these must surface as SourceError, not be
    silently treated as "0 leads found" (as page_size=50 was, before PAGE_SIZE
    was lowered to the free-tier cap of 10)."""
    respx.get(f"{BASE_URL}/2.0/region/search").mock(
        return_value=httpx.Response(200, json=_load("twogis_region_search_response.json"))
    )
    respx.get(f"{BASE_URL}/3.0/items").mock(
        return_value=httpx.Response(
            200,
            json={
                "meta": {
                    "code": 400,
                    "error": {
                        "message": "Length of parameter 'page_size' should be from 1 to 10",
                        "type": "paramIsOutsideSet",
                    },
                }
            },
        )
    )

    adapter = TwoGisApiAdapter(api_key="test-key", rps=1000)
    with pytest.raises(SourceError, match="page_size"):
        async for _ in adapter.search("веб-студия", "Москва", limit=10):
            pass


@respx.mock
async def test_healthcheck_ok(db_ready: Settings) -> None:
    respx.get(f"{BASE_URL}/2.0/region/search").mock(
        return_value=httpx.Response(200, json=_load("twogis_region_search_response.json"))
    )
    adapter = TwoGisApiAdapter(api_key="test-key", rps=1000)
    status = await adapter.healthcheck()
    assert status.ok is True

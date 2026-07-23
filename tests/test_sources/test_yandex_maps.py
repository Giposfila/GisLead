from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from leadgis.config import Settings
from leadgis.sources.base import SourceError
from leadgis.sources.yandex_maps import BASE_URL, YandexMapsAdapter

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@respx.mock
async def test_search_yields_parsed_orgs(db_ready: Settings) -> None:
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, json=_load("yandex_places_response.json"))
    )

    adapter = YandexMapsAdapter(api_key="test-key", rps=1000)
    orgs = [org async for org in adapter.search("кафе", "Красноярск", limit=10)]

    assert len(orgs) == 2
    assert orgs[0].name == "Пример Кафе"
    assert orgs[0].external_id == "1234567890"
    assert orgs[0].phones == ["+7 391 123-45-67"]
    assert orgs[0].website == "https://example.com"
    assert orgs[0].category == "Кафе"
    # Yandex Places API doesn't expose these at all — must stay None, not 0/"".
    assert orgs[0].rating is None
    assert orgs[0].reviews_count is None
    assert orgs[0].instagram is None
    assert orgs[0].telegram is None
    # second item has no Phones/url at all
    assert orgs[1].phones == []
    assert orgs[1].website is None


@respx.mock
async def test_search_sends_documented_request_params(db_ready: Settings) -> None:
    route = respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, json=_load("yandex_places_response.json"))
    )

    adapter = YandexMapsAdapter(api_key="test-key", rps=1000)
    [_ async for _ in adapter.search("кафе", "Красноярск", limit=5)]

    sent = route.calls.last.request.url.params
    assert sent["text"] == "кафе, Красноярск"
    assert sent["type"] == "biz"
    assert sent["apikey"] == "test-key"


@respx.mock
async def test_search_respects_limit(db_ready: Settings) -> None:
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, json=_load("yandex_places_response.json"))
    )

    adapter = YandexMapsAdapter(api_key="test-key", rps=1000)
    orgs = [org async for org in adapter.search("кафе", "Красноярск", limit=1)]

    assert len(orgs) == 1


@respx.mock
async def test_search_stops_on_empty_page(db_ready: Settings) -> None:
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json={"features": []}))

    adapter = YandexMapsAdapter(api_key="test-key", rps=1000)
    orgs = [org async for org in adapter.search("кафе", "Красноярск", limit=50)]

    assert orgs == []


@respx.mock
async def test_response_missing_features_key_raises_instead_of_empty(
    db_ready: Settings,
) -> None:
    """The exact 200-with-error-body shape isn't verified against a live key.
    A response that omits "features" entirely (e.g. an error payload) must
    not be silently treated as "0 leads found"."""
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, json={"message": "bad request"}))

    adapter = YandexMapsAdapter(api_key="test-key", rps=1000)
    with pytest.raises(SourceError, match="bad request"):
        async for _ in adapter.search("кафе", "Красноярск", limit=1):
            pass


@respx.mock
async def test_invalid_key_raises_source_error(db_ready: Settings) -> None:
    respx.get(BASE_URL).mock(return_value=httpx.Response(403, json={"error": "invalid key"}))

    adapter = YandexMapsAdapter(api_key="bad-key", rps=1000)

    with pytest.raises(SourceError, match="invalid"):
        async for _ in adapter.search("кафе", "Красноярск", limit=1):
            pass


@respx.mock
async def test_healthcheck_ok(db_ready: Settings) -> None:
    respx.get(BASE_URL).mock(
        return_value=httpx.Response(200, json=_load("yandex_places_response.json"))
    )
    adapter = YandexMapsAdapter(api_key="test-key", rps=1000)
    status = await adapter.healthcheck()
    assert status.ok is True


@respx.mock
async def test_healthcheck_reports_error(db_ready: Settings) -> None:
    respx.get(BASE_URL).mock(return_value=httpx.Response(403))
    adapter = YandexMapsAdapter(api_key="bad-key", rps=1000)
    status = await adapter.healthcheck()
    assert status.ok is False

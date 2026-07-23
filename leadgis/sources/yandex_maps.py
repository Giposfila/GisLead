"""Yandex Maps Places (geosearch) API adapter (AGENT.md §6.2/§4.1).

Request/response shape verified against
https://yandex.com/maps-api/docs/geosearch-api/{request,response}.html
(2026-07). Unlike 2GIS, errors are reported via HTTP status, not a 200
body — a non-2xx status is always a real error.

Known data gap (not a bug, the API just doesn't expose these): no rating,
no review count, no Instagram/Telegram links. Only phone (`Phones`) and
website (`url`) are available, via `properties.CompanyMetaData`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, ClassVar

import httpx

from leadgis.health import HealthStatus
from leadgis.ratelimit import TokenBucket
from leadgis.sources.base import DataSource, OrgDTO, SourceError

BASE_URL = "https://search-maps.yandex.ru/v1/"
RESULTS_PER_PAGE = 50
MAX_SKIP = 1000


class YandexMapsAdapter(DataSource):
    id: ClassVar[str] = "yandex_maps"
    display_name: ClassVar[str] = "Яндекс.Карты"
    requires: ClassVar[list[str]] = ["yandex_maps_api_key"]

    def __init__(
        self,
        api_key: str,
        rps: int = 5,
        base_url: str = BASE_URL,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self._limiter = TokenBucket(rate=rps)

    async def _get(self, client: httpx.AsyncClient, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "apikey": self.api_key}
        await self._limiter.acquire()
        resp = await client.get(self.base_url, params=params, timeout=self.timeout)
        if resp.status_code in (401, 403):
            raise SourceError("Yandex Maps API key is invalid or not activated yet")
        if resp.status_code == 429:
            raise SourceError("Yandex Maps API quota exceeded")
        if resp.status_code >= 400:
            raise SourceError(f"Yandex Maps API error: {resp.status_code} {resp.text[:200]}")
        data: dict[str, Any] = resp.json()
        # Defensive: the exact 200-with-error-in-body shape isn't confirmed
        # against a live key (docs 404'd). A response missing "features"
        # entirely is unexpected — treat it as a real error rather than
        # silently defaulting to zero results, the same failure mode that
        # made the 2GIS adapter swallow real errors as "no leads found".
        if "features" not in data:
            detail = data.get("message") or data.get("error") or data
            raise SourceError(f"Unexpected Yandex Maps API response: {detail}")
        return data

    async def search(self, niche: str, city: str, limit: int) -> AsyncIterator[OrgDTO]:
        async with httpx.AsyncClient() as client:
            yielded = 0
            skip = 0
            found = None
            while yielded < limit and skip <= MAX_SKIP and (found is None or yielded < found):
                data = await self._get(
                    client,
                    {
                        "text": f"{niche}, {city}",
                        "type": "biz",
                        "lang": "ru_RU",
                        "results": RESULTS_PER_PAGE,
                        "skip": skip,
                    },
                )
                found = (
                    data.get("properties", {})
                    .get("ResponseMetaData", {})
                    .get("SearchResponse", {})
                    .get("found")
                )
                features = data.get("features", [])
                if not features:
                    break
                for feature in features:
                    if yielded >= limit:
                        break
                    yield _parse_feature(feature)
                    yielded += 1
                skip += RESULTS_PER_PAGE

    async def healthcheck(self) -> HealthStatus:
        try:
            params = {"text": "кафе", "type": "biz", "lang": "ru_RU", "results": 1}
            async with httpx.AsyncClient() as client:
                await self._get(client, params)
            return HealthStatus(ok=True, detail="Yandex Maps API reachable")
        except SourceError as exc:
            return HealthStatus(ok=False, detail=str(exc))
        except httpx.HTTPError as exc:
            return HealthStatus(ok=False, detail=f"Yandex Maps API unreachable: {exc}")


def _parse_feature(feature: dict[str, Any]) -> OrgDTO:
    meta = feature.get("properties", {}).get("CompanyMetaData", {})

    phones = [p["formatted"] for p in meta.get("Phones", []) or [] if p.get("formatted")]
    categories = meta.get("Categories") or []
    category = categories[0].get("name") if categories else None
    address = meta.get("address") or (meta.get("Address") or {}).get("formatted")

    return OrgDTO(
        external_id=meta.get("id"),
        name=meta.get("name", ""),
        category=category,
        address=address,
        phones=phones,
        website=meta.get("url"),
        instagram=None,
        telegram=None,
        rating=None,
        reviews_count=None,
        raw=feature,
    )

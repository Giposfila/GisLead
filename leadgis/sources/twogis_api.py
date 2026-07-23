"""Official 2GIS Catalog API adapter (AGENT.md §6.2)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, ClassVar

import httpx

from leadgis.db.kv import kv_get, kv_set
from leadgis.health import HealthStatus
from leadgis.ratelimit import TokenBucket
from leadgis.sources.base import DataSource, OrgDTO, SourceError

BASE_URL = "https://catalog.api.2gis.com"
ITEMS_FIELDS = (
    "items.contact_groups,items.reviews,items.name_ex,items.address,items.rubrics,items.point"
)
PAGE_SIZE = 50
RETRY_DELAYS = (1.0, 2.0, 4.0)


class TwoGisApiAdapter(DataSource):
    id: ClassVar[str] = "twogis_api"
    display_name: ClassVar[str] = "2GIS Catalog API"
    requires: ClassVar[list[str]] = ["twogis_api_key"]

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

    async def _get(
        self, client: httpx.AsyncClient, path: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        params = {**params, "key": self.api_key}
        delay_iter = iter(RETRY_DELAYS)
        while True:
            await self._limiter.acquire()
            resp = await client.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
            if resp.status_code in (403, 429):
                delay = next(delay_iter, None)
                if delay is None:
                    raise SourceError("2GIS key exhausted or invalid")
                await asyncio.sleep(delay)
                continue
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def _resolve_city_id(self, client: httpx.AsyncClient, city: str) -> str | None:
        cache_key = f"twogis_city_id:{city.strip().lower()}"
        cached = await kv_get(cache_key)
        if cached is not None:
            return cached or None

        data = await self._get(client, "/2.0/region/search", {"q": city})
        items = data.get("result", {}).get("items", [])
        city_id = str(items[0]["id"]) if items else ""
        await kv_set(cache_key, city_id)
        return city_id or None

    async def search(self, niche: str, city: str, limit: int) -> AsyncIterator[OrgDTO]:
        async with httpx.AsyncClient() as client:
            city_id = await self._resolve_city_id(client, city)
            params: dict[str, Any] = {
                "q": niche,
                "fields": ITEMS_FIELDS,
                "page_size": min(PAGE_SIZE, limit),
            }
            if city_id:
                params["city_id"] = city_id
            else:
                params["q"] = f"{niche} {city}"

            yielded = 0
            page = 1
            total = None
            while yielded < limit and (total is None or yielded < total):
                data = await self._get(client, "/3.0/items", {**params, "page": page})
                meta = data.get("meta", {})
                total = meta.get("total", 0)
                items = data.get("result", {}).get("items", [])
                if not items:
                    break
                for item in items:
                    if yielded >= limit:
                        break
                    yield _parse_item(item)
                    yielded += 1
                page += 1

    async def healthcheck(self) -> HealthStatus:
        try:
            async with httpx.AsyncClient() as client:
                await self._get(client, "/2.0/region/search", {"q": "Москва"})
            return HealthStatus(ok=True, detail="2GIS API reachable")
        except SourceError as exc:
            return HealthStatus(ok=False, detail=str(exc))
        except httpx.HTTPError as exc:
            return HealthStatus(ok=False, detail=f"2GIS API unreachable: {exc}")


def _parse_item(item: dict[str, Any]) -> OrgDTO:
    phones: list[str] = []
    website: str | None = None
    instagram: str | None = None
    telegram: str | None = None
    for group in item.get("contact_groups", []) or []:
        for contact in group.get("contacts", []) or []:
            ctype = contact.get("type")
            value = contact.get("value") or contact.get("text")
            if not value:
                continue
            if ctype == "phone":
                phones.append(value)
            elif ctype == "website":
                website = value
            elif ctype == "instagram":
                instagram = value
            elif ctype == "telegram":
                telegram = value

    reviews = item.get("reviews") or {}
    address = item.get("address_name") or (item.get("address") or {}).get("name")
    rubrics = item.get("rubrics") or []
    category = rubrics[0].get("name") if rubrics else None

    return OrgDTO(
        external_id=item.get("id"),
        name=(item.get("name_ex") or {}).get("primary") or item.get("name", ""),
        category=category,
        address=address,
        phones=phones,
        website=website,
        instagram=instagram,
        telegram=telegram,
        rating=reviews.get("general_rating"),
        reviews_count=reviews.get("general_review_count"),
        raw=item,
    )

from __future__ import annotations

from httpx import AsyncClient


async def test_list_sources_reports_missing_key(client: AsyncClient) -> None:
    resp = await client.get("/api/sources")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["id"] == "twogis_api"
    assert body[0]["available"] is False
    assert "twogis_api_key" in body[0]["missing"]


async def test_list_sources_available_after_key_set(client: AsyncClient) -> None:
    await client.put("/api/settings", json={"source": {"twogis_api_key": "sk-123"}})
    resp = await client.get("/api/sources")
    body = resp.json()
    assert body[0]["available"] is True
    assert body[0]["missing"] == []


async def test_settings_test_source_without_key_reports_not_ok(client: AsyncClient) -> None:
    resp = await client.post("/api/settings/test/source")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False


async def test_settings_test_llm_reports_error_for_unknown_provider(
    client: AsyncClient,
) -> None:
    await client.put("/api/settings", json={"llm": {"provider": "bogus"}})
    resp = await client.post("/api/settings/test/llm")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "bogus" in body["detail"]

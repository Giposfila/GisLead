from __future__ import annotations

from httpx import AsyncClient


async def test_list_sources_reports_missing_key(client: AsyncClient) -> None:
    resp = await client.get("/api/sources")
    assert resp.status_code == 200
    body = resp.json()
    assert [s["id"] for s in body] == ["twogis_api", "yandex_maps"]
    assert body[0]["available"] is False
    assert "twogis_api_key" in body[0]["missing"]
    assert body[1]["available"] is False
    assert "yandex_maps_api_key" in body[1]["missing"]


async def test_list_sources_available_after_key_set(client: AsyncClient) -> None:
    await client.put(
        "/api/settings",
        json={"source": {"twogis_api_key": "sk-123", "yandex_maps_api_key": "yk-456"}},
    )
    resp = await client.get("/api/sources")
    body = resp.json()
    assert body[0]["available"] is True
    assert body[0]["missing"] == []
    assert body[1]["available"] is True
    assert body[1]["missing"] == []


async def test_settings_test_source_without_key_reports_not_ok(client: AsyncClient) -> None:
    resp = await client.post("/api/settings/test/source")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False


async def test_settings_test_source_can_target_yandex_via_override(client: AsyncClient) -> None:
    """Regression test: the saved `source.active` defaults to "twogis_api", but
    the Settings page's per-source "Проверить подключение" button must be able
    to test Yandex specifically via the request body override, not just
    whatever source happens to be saved as active."""
    resp = await client.post(
        "/api/settings/test/source",
        json={"active": "yandex_maps"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "Yandex" in body["detail"]


async def test_settings_test_llm_reports_error_for_unknown_provider(
    client: AsyncClient,
) -> None:
    await client.put("/api/settings", json={"llm": {"provider": "bogus"}})
    resp = await client.post("/api/settings/test/llm")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "bogus" in body["detail"]

from __future__ import annotations

from httpx import AsyncClient


async def test_get_settings_returns_defaults(client: AsyncClient) -> None:
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["app"]["host"] == "127.0.0.1"
    assert body["source"]["active"] == "twogis_api"
    assert body["llm"]["api_key_is_set"] is False


async def test_put_settings_roundtrips_without_leaking_secrets(client: AsyncClient) -> None:
    resp = await client.put(
        "/api/settings",
        json={"llm": {"api_key": "sk-secret", "model": "gpt-4o-mini"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm"]["model"] == "gpt-4o-mini"
    assert body["llm"]["api_key_is_set"] is True
    assert "sk-secret" not in resp.text

    resp2 = await client.get("/api/settings")
    assert resp2.json()["llm"]["api_key_is_set"] is True

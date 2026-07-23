from __future__ import annotations

import httpx
import pytest
from httpx import AsyncClient

from leadgis.llm.base import ProviderUnavailable

OLLAMA_BASE_URL = "http://localhost:11434"


async def _ollama_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as http_client:
            resp = await http_client.get(f"{OLLAMA_BASE_URL}/api/tags")
        return resp.status_code == 200
    except httpx.HTTPError:
        return False


async def test_list_llm_models_from_ollama(client: AsyncClient) -> None:
    if not await _ollama_available():
        pytest.skip("Ollama not reachable locally")

    await client.put(
        "/api/settings",
        json={"llm": {"provider": "openai_compat", "base_url": f"{OLLAMA_BASE_URL}/v1"}},
    )
    resp = await client.post("/api/llm/models")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) > 0


async def test_list_llm_models_uses_unsaved_override_not_persisted_settings(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test: Settings page Check/List buttons must send the
    current (possibly unsaved) form values, not silently fall back to the
    base_url last written to config.toml."""
    seen_base_urls: list[str] = []

    class _RecordingProvider:
        def __init__(self, base_url: str) -> None:
            seen_base_urls.append(base_url)

        async def list_models(self) -> list[str]:
            return ["dummy"]

    monkeypatch.setattr(
        "leadgis.api.llm.get_llm_provider",
        lambda settings: _RecordingProvider(settings.llm.base_url),
    )

    resp = await client.post(
        "/api/llm/models",
        json={"base_url": "http://example.internal:9999/v1"},
    )

    assert resp.status_code == 200
    assert seen_base_urls == ["http://example.internal:9999/v1"]


async def test_list_llm_models_maps_provider_unavailable_to_502(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _BrokenProvider:
        async def list_models(self) -> list[str]:
            raise ProviderUnavailable("connection refused")

    monkeypatch.setattr("leadgis.api.llm.get_llm_provider", lambda settings: _BrokenProvider())

    resp = await client.post("/api/llm/models")

    assert resp.status_code == 502
    assert "connection refused" in resp.json()["detail"]

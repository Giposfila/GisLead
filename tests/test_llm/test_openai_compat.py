from __future__ import annotations

import httpx
import pytest
import respx

from leadgis.llm.base import (
    AuthError,
    ModelNotFoundError,
    ProviderUnavailable,
    RateLimitError,
)
from leadgis.llm.openai_compat import OpenAICompatProvider

BASE_URL = "http://localhost:11434/v1"


def _provider() -> OpenAICompatProvider:
    return OpenAICompatProvider(base_url=BASE_URL, api_key="", model="qwen2.5:14b")


@respx.mock
async def test_complete_parses_successful_response() -> None:
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "qwen2.5:14b",
                "choices": [{"message": {"content": "  Привет, как дела?  "}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 5},
            },
        )
    )
    result = await _provider().complete("system", "user")
    assert result.text == "  Привет, как дела?  "
    assert result.tokens_in == 12
    assert result.tokens_out == 5


@respx.mock
async def test_complete_raises_auth_error_on_401() -> None:
    respx.post(f"{BASE_URL}/chat/completions").mock(return_value=httpx.Response(401))
    with pytest.raises(AuthError):
        await _provider().complete("system", "user")


@respx.mock
async def test_complete_raises_model_not_found_on_404() -> None:
    respx.post(f"{BASE_URL}/chat/completions").mock(return_value=httpx.Response(404))
    with pytest.raises(ModelNotFoundError):
        await _provider().complete("system", "user")


@respx.mock
async def test_complete_raises_rate_limit_error_with_retry_after_on_429() -> None:
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(429, headers={"retry-after": "12"})
    )
    with pytest.raises(RateLimitError) as exc_info:
        await _provider().complete("system", "user")
    assert exc_info.value.retry_after == 12.0


@respx.mock
async def test_complete_raises_provider_unavailable_on_500() -> None:
    respx.post(f"{BASE_URL}/chat/completions").mock(return_value=httpx.Response(500))
    with pytest.raises(ProviderUnavailable):
        await _provider().complete("system", "user")


@respx.mock
async def test_complete_raises_provider_unavailable_on_connect_error() -> None:
    respx.post(f"{BASE_URL}/chat/completions").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ProviderUnavailable):
        await _provider().complete("system", "user")


@respx.mock
async def test_list_models_uses_ollama_native_tags_endpoint() -> None:
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "qwen2.5:14b"}]})
    )
    models = await _provider().list_models()
    assert models == ["qwen2.5:14b"]


@respx.mock
async def test_healthcheck_flags_missing_ollama_model() -> None:
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "other-model"}]})
    )
    status = await _provider().healthcheck()
    assert status.ok is False
    assert "ollama pull qwen2.5:14b" in status.detail

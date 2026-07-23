"""OpenAI-compatible provider: OpenAI, Ollama, LM Studio, Groq, OpenRouter, DeepSeek."""

from __future__ import annotations

from typing import Any, ClassVar
from urllib.parse import urlparse

import httpx

from leadgis.llm.base import (
    AuthError,
    GenerationError,
    HealthStatus,
    LLMProvider,
    LLMResult,
    ModelNotFoundError,
    ProviderUnavailable,
    RateLimitError,
)

CONNECT_TIMEOUT = 5.0
READ_TIMEOUT_LOCAL = 120.0
READ_TIMEOUT_CLOUD = 60.0


def _is_local(base_url: str) -> bool:
    return urlparse(base_url).hostname in ("localhost", "127.0.0.1", "::1")


class OpenAICompatProvider(LLMProvider):
    id: ClassVar[str] = "openai_compat"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        read_timeout = READ_TIMEOUT_LOCAL if _is_local(base_url) else READ_TIMEOUT_CLOUD
        self.timeout = httpx.Timeout(
            connect=CONNECT_TIMEOUT, read=read_timeout, write=10.0, pool=5.0
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}{path}", json=json, headers=self._headers()
                )
        except httpx.TimeoutException as exc:
            raise ProviderUnavailable(f"{self.base_url} timed out") from exc
        except httpx.ConnectError as exc:
            raise ProviderUnavailable(f"Cannot connect to {self.base_url}") from exc

        if resp.status_code in (401, 403):
            raise AuthError("LLM API key invalid or missing")
        if resp.status_code == 404:
            raise ModelNotFoundError(f"Model '{self.model}' not found at {self.base_url}")
        if resp.status_code == 429:
            retry_after = resp.headers.get("retry-after")
            raise RateLimitError(
                "LLM provider rate limited the request",
                retry_after=float(retry_after) if retry_after else None,
            )
        if resp.status_code >= 500:
            raise ProviderUnavailable(f"{self.base_url} returned {resp.status_code}")
        if resp.status_code >= 400:
            raise GenerationError(f"LLM request failed: {resp.status_code} {resp.text}")
        return resp.json()  # type: ignore[no-any-return]

    async def _get(self, path: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}{path}", headers=self._headers())
        except httpx.TimeoutException as exc:
            raise ProviderUnavailable(f"{self.base_url} timed out") from exc
        except httpx.ConnectError as exc:
            raise ProviderUnavailable(f"Cannot connect to {self.base_url}") from exc

        if resp.status_code in (401, 403):
            raise AuthError("LLM API key invalid or missing")
        if resp.status_code >= 400:
            raise GenerationError(f"LLM request failed: {resp.status_code} {resp.text}")
        return resp.json()  # type: ignore[no-any-return]

    async def complete(
        self, system: str, user: str, *, max_tokens: int = 1024, temperature: float = 0.8
    ) -> LLMResult:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        data = await self._post("/chat/completions", body)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise GenerationError(f"Unexpected response shape from {self.base_url}") from exc

        usage = data.get("usage") or {}
        return LLMResult(
            text=text,
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            model=data.get("model", self.model),
        )

    async def list_models(self) -> list[str]:
        if _is_local(self.base_url) and ":11434" in self.base_url:
            tags_url = self.base_url.removesuffix("/v1")
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(f"{tags_url}/api/tags")
                if resp.status_code == 200:
                    return [m["name"] for m in resp.json().get("models", [])]
            except httpx.HTTPError:
                pass
        data = await self._get("/models")
        return [m["id"] for m in data.get("data", [])]

    async def healthcheck(self) -> HealthStatus:
        try:
            models = await self.list_models()
        except AuthError as exc:
            return HealthStatus(ok=False, detail=str(exc))
        except ProviderUnavailable as exc:
            return HealthStatus(ok=False, detail=str(exc))
        except GenerationError as exc:
            return HealthStatus(ok=False, detail=str(exc))

        if ":11434" in self.base_url and models and self.model not in models:
            return HealthStatus(
                ok=False,
                detail=f"Model not found. Run: ollama pull {self.model}",
            )
        return HealthStatus(ok=True, detail=f"{self.base_url} reachable")

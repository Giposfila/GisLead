"""Anthropic provider using the official async SDK (AGENT.md §8.3)."""

from __future__ import annotations

from typing import ClassVar

import anthropic

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


class AnthropicLLMProvider(LLMProvider):
    id: ClassVar[str] = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self, system: str, user: str, *, max_tokens: int = 1024, temperature: float = 0.8
    ) -> LLMResult:
        try:
            message = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as exc:
            raise _translate(exc) from exc

        text = next((block.text for block in message.content if block.type == "text"), "")
        return LLMResult(
            text=text,
            tokens_in=message.usage.input_tokens,
            tokens_out=message.usage.output_tokens,
            model=message.model,
        )

    async def list_models(self) -> list[str]:
        try:
            return sorted([model.id async for model in self._client.models.list()])
        except anthropic.APIError as exc:
            raise _translate(exc) from exc

    async def healthcheck(self) -> HealthStatus:
        try:
            await self._client.models.retrieve(self.model)
        except anthropic.APIError as exc:
            return HealthStatus(ok=False, detail=str(_translate(exc)))
        return HealthStatus(ok=True, detail="Anthropic API reachable")


def _translate(exc: anthropic.APIError) -> Exception:
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return AuthError(str(exc))
    if isinstance(exc, anthropic.NotFoundError):
        return ModelNotFoundError(str(exc))
    if isinstance(exc, anthropic.RateLimitError):
        retry_after = exc.response.headers.get("retry-after") if exc.response else None
        return RateLimitError(str(exc), retry_after=float(retry_after) if retry_after else None)
    if isinstance(exc, anthropic.APIConnectionError):
        return ProviderUnavailable(str(exc))
    if isinstance(exc, anthropic.APIStatusError) and exc.status_code >= 500:
        return ProviderUnavailable(str(exc))
    return GenerationError(str(exc))

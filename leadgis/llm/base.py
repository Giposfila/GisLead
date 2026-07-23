"""LLMProvider ABC + common error taxonomy (AGENT.md §8.1, §8.4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from leadgis.health import HealthStatus

__all__ = [
    "LLMProvider",
    "LLMResult",
    "HealthStatus",
    "AuthError",
    "RateLimitError",
    "ModelNotFoundError",
    "ProviderUnavailable",
    "GenerationError",
]


@dataclass(slots=True)
class LLMResult:
    text: str
    tokens_in: int | None
    tokens_out: int | None
    model: str


class AuthError(Exception):
    """API key missing or rejected by the provider."""


class RateLimitError(Exception):
    """Provider is rate-limiting us; retry_after is seconds, if known."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ModelNotFoundError(Exception):
    """The configured model does not exist on this provider."""


class ProviderUnavailable(Exception):
    """Network/connection failure or the provider is down."""


class GenerationError(Exception):
    """Any other failure while generating a completion."""


class LLMProvider(ABC):
    id: ClassVar[str]

    @abstractmethod
    async def complete(
        self, system: str, user: str, *, max_tokens: int = 1024, temperature: float = 0.8
    ) -> LLMResult: ...

    @abstractmethod
    async def healthcheck(self) -> HealthStatus: ...

    @abstractmethod
    async def list_models(self) -> list[str]: ...

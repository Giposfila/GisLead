"""DataSource ABC + DTOs. Adapters live behind this interface (AGENT.md §4.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, ClassVar

from leadgis.health import HealthStatus

__all__ = ["DataSource", "OrgDTO", "SourceError", "HealthStatus"]


@dataclass(slots=True)
class OrgDTO:
    external_id: str | None
    name: str
    category: str | None
    address: str | None
    phones: list[str]
    website: str | None
    instagram: str | None
    telegram: str | None
    rating: float | None
    reviews_count: int | None
    raw: dict[str, Any] = field(default_factory=dict)


class SourceError(Exception):
    """Raised when a data source cannot complete a request; message is user-facing."""


class DataSource(ABC):
    id: ClassVar[str]
    display_name: ClassVar[str]
    requires: ClassVar[list[str]]

    @abstractmethod
    def search(self, niche: str, city: str, limit: int) -> AsyncIterator[OrgDTO]: ...

    @abstractmethod
    async def healthcheck(self) -> HealthStatus: ...

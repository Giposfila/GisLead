"""Shared healthcheck result type for data sources and LLM providers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HealthStatus:
    ok: bool
    detail: str

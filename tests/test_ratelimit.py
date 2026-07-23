from __future__ import annotations

import time

from leadgis.ratelimit import RateLimiterRegistry, TokenBucket


async def test_token_bucket_limits_rate() -> None:
    bucket = TokenBucket(rate=10, capacity=1)
    start = time.monotonic()
    for _ in range(3):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    # 3 acquisitions at 10/s with capacity 1 should take at least ~0.2s
    assert elapsed >= 0.15


async def test_token_bucket_allows_burst_up_to_capacity() -> None:
    bucket = TokenBucket(rate=1, capacity=5)
    start = time.monotonic()
    for _ in range(5):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1


def test_registry_returns_same_bucket_for_same_rate() -> None:
    registry = RateLimiterRegistry()
    a = registry.get("2gis", 5)
    b = registry.get("2gis", 5)
    assert a is b


def test_registry_resets_bucket_when_rate_changes() -> None:
    registry = RateLimiterRegistry()
    a = registry.get("2gis", 5)
    b = registry.get("2gis", 10)
    assert a is not b

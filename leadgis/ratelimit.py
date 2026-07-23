"""Token-bucket rate limiter. All external calls must acquire a handle here."""

from __future__ import annotations

import asyncio
import time


class TokenBucket:
    """Simple async token-bucket: `rate` tokens/second, refilled continuously."""

    def __init__(self, rate: float, capacity: float | None = None) -> None:
        self.rate = rate
        self.capacity = capacity if capacity is not None else max(rate, 1.0)
        self._tokens = self.capacity
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, cost: float = 1.0) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last
                self._last = now
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
                if self._tokens >= cost:
                    self._tokens -= cost
                    return
                wait = (cost - self._tokens) / self.rate
                await asyncio.sleep(wait)


class RateLimiterRegistry:
    """Named token buckets so all calls to e.g. "2gis" share one limiter."""

    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}

    def get(self, name: str, rate: float) -> TokenBucket:
        bucket = self._buckets.get(name)
        if bucket is None or bucket.rate != rate:
            bucket = TokenBucket(rate)
            self._buckets[name] = bucket
        return bucket


limiters = RateLimiterRegistry()

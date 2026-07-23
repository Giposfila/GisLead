from __future__ import annotations

from httpx import AsyncClient


async def test_get_missing_job_404s(client: AsyncClient) -> None:
    resp = await client.get("/api/jobs/does-not-exist")
    assert resp.status_code == 404


async def test_cancel_unknown_job_is_a_noop(client: AsyncClient) -> None:
    resp = await client.post("/api/jobs/does-not-exist/cancel")
    assert resp.status_code == 204

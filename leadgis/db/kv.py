"""Small persisted key/value cache helpers (e.g. resolved 2GIS city ids)."""

from __future__ import annotations

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from leadgis.db.engine import session_scope
from leadgis.db.models import KV


async def kv_get(key: str) -> str | None:
    async with session_scope() as session:
        row = await session.get(KV, key)
        return row.value if row else None


async def kv_set(key: str, value: str) -> None:
    async with session_scope() as session:
        stmt = sqlite_insert(KV).values(key=key, value=value)
        stmt = stmt.on_conflict_do_update(index_elements=[KV.key], set_={"value": value})
        await session.execute(stmt)
        await session.commit()

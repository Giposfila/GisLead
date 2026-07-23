"""Run Alembic migrations programmatically (called from app startup and CLI)."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

# Resolved relative to this package, not the cwd or repo root, so migrations
# work identically from a source checkout, an editable install, and a real
# pipx/wheel install (the migrations dir ships as package data; a top-level
# alembic.ini would not).
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _build_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("path_separator", "os")
    cfg.set_main_option("version_path_separator", "os")
    return cfg


def _upgrade_sync(db_path: str | None) -> None:
    cfg = _build_config()
    if db_path:
        cfg.cmd_opts = argparse.Namespace(x=[f"db_path={db_path}"])
    command.upgrade(cfg, "head")


async def run_migrations(db_path: str | None = None) -> None:
    """Upgrade the SQLite DB to head. Safe to call on every startup."""
    from leadgis import config

    await asyncio.to_thread(_upgrade_sync, db_path or str(config.DB_PATH))

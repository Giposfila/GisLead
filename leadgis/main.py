"""FastAPI app factory and uvicorn entry point."""

from __future__ import annotations

import logging
import os
import threading
import webbrowser
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from leadgis.api.error_handlers import register_exception_handlers
from leadgis.api.router import api_router
from leadgis.config import Settings, load_settings
from leadgis.db.migrate import run_migrations
from leadgis.worker import JobRunner

logger = logging.getLogger("leadgis")

FRONTEND_DIST = Path(
    os.environ.get("LEADGIS_FRONTEND_DIST") or Path(__file__).resolve().parent / "webui"
)

_PLACEHOLDER_HTML = """<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>LeadGis</title></head>
<body style="font-family: sans-serif; max-width: 40rem; margin: 4rem auto;">
<h1>LeadGis</h1>
<p>Frontend build not found. Run <code>npm install &amp;&amp; npm run build</code>
inside <code>frontend/</code>, or <code>npm run dev</code> for local development.</p>
<p>API is live at <a href="/api/settings">/api/settings</a>.</p>
</body>
</html>"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await run_migrations()
    settings: Settings = app.state.settings

    job_runner: JobRunner = app.state.job_runner
    await job_runner.start()

    if settings.app.open_browser:
        url = f"http://{settings.app.host}:{settings.app.port}"
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    logger.info("leadgis started")
    try:
        yield
    finally:
        await job_runner.stop()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="LeadGis", lifespan=lifespan)
    app.state.settings = settings
    app.state.job_runner = JobRunner()

    @app.middleware("http")
    async def _lan_auth_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        cfg: Settings = app.state.settings
        needs_auth = cfg.app.host not in ("127.0.0.1", "localhost") and cfg.app.auth_token
        if needs_auth and request.url.path.startswith("/api/"):
            header = request.headers.get("authorization", "")
            if header != f"Bearer {cfg.app.auth_token}":
                raise HTTPException(status_code=401, detail="Missing or invalid Authorization")
        return await call_next(request)

    register_exception_handlers(app)
    app.include_router(api_router)

    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def _spa(full_path: str) -> FileResponse:
            candidate = FRONTEND_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")
    else:

        @app.get("/{full_path:path}", include_in_schema=False)
        async def _placeholder(full_path: str) -> HTMLResponse:
            return HTMLResponse(_PLACEHOLDER_HTML)

    return app


def run() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(create_app(settings), host=settings.app.host, port=settings.app.port)

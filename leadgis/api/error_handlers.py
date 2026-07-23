"""Single exception handler mapping the LLM/source error taxonomy to HTTP (AGENT.md §15)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from leadgis.llm.base import (
    AuthError,
    GenerationError,
    ModelNotFoundError,
    ProviderUnavailable,
    RateLimitError,
)
from leadgis.sources.base import SourceError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def _auth_error(request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": f"API key invalid: {exc}"})

    @app.exception_handler(RateLimitError)
    async def _rate_limit_error(request: Request, exc: RateLimitError) -> JSONResponse:
        retry_after = int(exc.retry_after) if exc.retry_after else 20
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limited, retry in {retry_after}s"},
            headers={"Retry-After": str(retry_after)},
        )

    @app.exception_handler(ModelNotFoundError)
    async def _model_not_found_error(request: Request, exc: ModelNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ProviderUnavailable)
    async def _provider_unavailable(request: Request, exc: ProviderUnavailable) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": f"Provider unavailable: {exc}"})

    @app.exception_handler(GenerationError)
    async def _generation_error(request: Request, exc: GenerationError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": f"Generation failed: {exc}"})

    @app.exception_handler(SourceError)
    async def _source_error(request: Request, exc: SourceError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": f"Source unavailable: {exc}"})

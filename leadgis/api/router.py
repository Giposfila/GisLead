"""Mounts all API routers under /api."""

from __future__ import annotations

from fastapi import APIRouter

from leadgis.api import campaigns as campaigns_api
from leadgis.api import events as events_api
from leadgis.api import jobs as jobs_api
from leadgis.api import leads as leads_api
from leadgis.api import llm as llm_api
from leadgis.api import settings as settings_api
from leadgis.api import sources as sources_api

api_router = APIRouter(prefix="/api")
api_router.include_router(settings_api.router)
api_router.include_router(sources_api.router)
api_router.include_router(llm_api.router)
api_router.include_router(campaigns_api.router)
api_router.include_router(leads_api.router)
api_router.include_router(jobs_api.router)
api_router.include_router(events_api.router)

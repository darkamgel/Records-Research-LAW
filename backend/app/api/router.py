from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    ai_settings,
    audit,
    auth,
    dashboard,
    documents,
    matches,
    misc,
    projects,
    records,
    saved_searches,
    sources,
    uploads,
)

api_router = APIRouter()
api_router.include_router(misc.router)
api_router.include_router(auth.router)
api_router.include_router(sources.router)
api_router.include_router(uploads.router)
api_router.include_router(documents.router)
api_router.include_router(records.router)
api_router.include_router(matches.router)
api_router.include_router(projects.router)
api_router.include_router(saved_searches.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit.router)
api_router.include_router(ai_settings.router)

"""
Main API router for v1 endpoints.

Auth routes are public (login / accept-invite). All other routes require a Bearer token.
"""
from fastapi import APIRouter, Depends
from app.api.v1.endpoints import (
    documents,
    personas,
    prompts,
    analytics,
    projects,
    simulations,
    judge,
    persona_chats,
    auth,
)
from app.core.deps import get_current_user

api_router = APIRouter()

# Root endpoint for /api/v1 (public — useful for smoke checks)
@api_router.get("/")
async def api_root():
    """API root endpoint."""
    return {
        "message": "PEP API v1",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/v1/auth",
            "projects": "/api/v1/projects",
            "documents": "/api/v1/documents",
            "personas": "/api/v1/personas",
            "prompts": "/api/v1/prompts",
            "analytics": "/api/v1/analytics",
            "simulations": "/api/v1/simulations",
            "judge": "/api/v1/judge",
            "persona_chats": "/api/v1/persona-chats",
        },
    }


# Public auth routes (login / accept-invite / invite preview)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Persona image bytes are loaded via <img src>, which cannot send Authorization.
# Keep this GET public; all other persona routes stay protected.
api_router.include_router(personas.public_router, prefix="/personas", tags=["personas"])

# Everything else requires authentication
protected = APIRouter(dependencies=[Depends(get_current_user)])
protected.include_router(projects.router, prefix="/projects", tags=["projects"])
protected.include_router(documents.router, prefix="/documents", tags=["documents"])
protected.include_router(personas.router, prefix="/personas", tags=["personas"])
protected.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
protected.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
protected.include_router(simulations.router, prefix="/simulations", tags=["simulations"])
protected.include_router(judge.router, prefix="/judge", tags=["judge"])
protected.include_router(persona_chats.router, prefix="/persona-chats", tags=["persona-chats"])
api_router.include_router(protected)

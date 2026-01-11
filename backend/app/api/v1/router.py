"""
Main API router for v1 endpoints.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import documents, personas, prompts, analytics, projects

api_router = APIRouter()

# Root endpoint for /api/v1
@api_router.get("/")
async def api_root():
    """API root endpoint."""
    return {
        "message": "PEP API v1",
        "version": "1.0.0",
        "endpoints": {
            "projects": "/api/v1/projects",
            "documents": "/api/v1/documents",
            "personas": "/api/v1/personas",
            "prompts": "/api/v1/prompts",
            "analytics": "/api/v1/analytics"
        }
    }

api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(personas.router, prefix="/personas", tags=["personas"])
api_router.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


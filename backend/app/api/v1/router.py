"""
Main API router for v1 endpoints.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import documents, personas, prompts, analytics

api_router = APIRouter()

api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(personas.router, prefix="/personas", tags=["personas"])
api_router.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


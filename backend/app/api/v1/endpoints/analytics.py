"""
Analytics and reporting endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/persona-sets/{persona_set_id}")
async def get_persona_set_analytics(
    persona_set_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get complete analytics report for a persona set."""
    try:
        report = await AnalyticsService.get_analytics_report(db, persona_set_id)
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting analytics: {str(e)}"
        )


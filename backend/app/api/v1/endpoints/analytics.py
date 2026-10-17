"""
Analytics and reporting endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.persona_view import (
    PersonaProfileViewCreate,
    PersonaProfileViewResponse,
    PersonaSetViewTimeSummary,
)
from app.services.analytics_service import AnalyticsService
from app.services.persona_view_service import PersonaViewService

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


@router.post("/profile-views", status_code=status.HTTP_201_CREATED)
async def record_profile_view(
    body: PersonaProfileViewCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Record time spent on a persona profile or the all-profiles page."""
    try:
        recorded = await PersonaViewService.record_view(db, body, user_id=user.id)
        await db.commit()
        if recorded is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        return PersonaProfileViewResponse.model_validate(recorded)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording profile view: {str(e)}",
        )


@router.get(
    "/persona-sets/{persona_set_id}/profile-views",
    response_model=PersonaSetViewTimeSummary,
)
async def get_persona_set_profile_views(
    persona_set_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Summarize recorded view time for a persona set."""
    try:
        return await PersonaViewService.get_set_summary(db, persona_set_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading profile views: {str(e)}",
        )

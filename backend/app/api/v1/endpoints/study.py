"""
User-study endpoints: public enter + study session APIs.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import bearer_scheme, get_current_user, get_current_admin
from app.core.security import decode_access_token
from app.models.user import User
from app.schemas.study import (
    StudyAdminSummary,
    StudyConfigResponse,
    StudyConfigUpdate,
    StudyEnterRequest,
    StudyEnterResponse,
    StudyEventAdminResponse,
    StudyEventCreate,
    StudyEventResponse,
    StudyParticipantAdminInfo,
    StudyPersonaOrderUpdate,
    StudyPublicInfo,
)
from app.services.study_service import StudyService

router = APIRouter()
public_router = APIRouter()


def _study_claims_from_request(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        return {}
    payload = decode_access_token(credentials.credentials) or {}
    if not payload.get("is_study_participant"):
        return {}
    return {
        "study_id": payload.get("study_id"),
        "study_slug": payload.get("study_slug"),
        "participant_id": payload.get("participant_id"),
        "participant_code": payload.get("participant_code"),
        "is_study_participant": True,
    }


# ── Admin console (must be declared before /{slug} routes) ───────────────────


@router.get("/admin/studies", response_model=List[StudyAdminSummary])
async def admin_list_studies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    rows = await StudyService.list_studies(db)
    return [StudyAdminSummary(**r) for r in rows]


@router.get("/admin/studies/{slug}", response_model=StudyConfigResponse)
async def admin_get_study(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    study = await StudyService.get_by_slug(db, slug)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return StudyConfigResponse.model_validate(study)


@router.put("/admin/studies/{slug}", response_model=StudyConfigResponse)
async def admin_update_study(
    slug: str,
    body: StudyConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    try:
        study = await StudyService.update_config(
            db,
            slug,
            name=body.name,
            enabled=body.enabled,
            project_id=body.project_id,
            persona_set_id=body.persona_set_id,
            persona_order=body.persona_order,
            order_rotations=body.order_rotations,
            allow_open_codes=body.allow_open_codes,
            max_participants=body.max_participants,
            welcome_text=body.welcome_text,
            rebuild_rotations=body.rebuild_rotations,
        )
        await db.commit()
        await db.refresh(study)
        return StudyConfigResponse.model_validate(study)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/admin/studies/{slug}/participants",
    response_model=List[StudyParticipantAdminInfo],
)
async def admin_list_participants(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    study = await StudyService.get_by_slug(db, slug)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    rows = await StudyService.list_participants(db, study.id)
    return [StudyParticipantAdminInfo(**r) for r in rows]


@router.get(
    "/admin/studies/{slug}/events",
    response_model=List[StudyEventAdminResponse],
)
async def admin_list_events(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
    participant_code: Optional[str] = None,
    limit: int = 500,
):
    study = await StudyService.get_by_slug(db, slug)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    rows = await StudyService.list_events_admin(
        db, study.id, participant_code=participant_code, limit=limit
    )
    return [StudyEventAdminResponse(**r) for r in rows]


@public_router.get("/{slug}", response_model=StudyPublicInfo)
async def get_study_public(slug: str, db: AsyncSession = Depends(get_db)):
    try:
        return await StudyService.get_public_info(db, slug)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@public_router.post("/{slug}/enter", response_model=StudyEnterResponse)
async def enter_study(
    slug: str,
    body: StudyEnterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await StudyService.enter(db, slug, body.code)
        await db.commit()
        return result
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not enter study: {e}",
        )


@router.get("/{slug}/config", response_model=StudyConfigResponse)
async def get_study_config(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    study = await StudyService.get_by_slug(db, slug)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    return StudyConfigResponse.model_validate(study)


@router.get("/{slug}/personas")
async def get_study_personas_ordered(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    study = await StudyService.get_by_slug(db, slug)
    if not study or not study.enabled:
        raise HTTPException(status_code=404, detail="Study not found or disabled")
    claims = _study_claims_from_request(credentials)
    participant_code = claims.get("participant_code")
    meta = await StudyService.ordered_personas(db, study, participant_code)
    personas = meta["personas"]
    return {
        "study_slug": study.slug,
        "persona_set_id": study.persona_set_id,
        "project_id": study.project_id,
        "persona_order": meta["persona_order"],
        "order_condition": meta.get("order_condition"),
        "order_rotation_index": meta.get("order_rotation_index"),
        "order_groups": meta.get("order_groups"),
        "has_order_rotations": bool(study.order_rotations),
        "participant_code": participant_code,
        "personas": [
            {
                "id": p.id,
                "persona_set_id": p.persona_set_id,
                "name": p.name,
                "persona_data": p.persona_data,
                "image_url": p.image_url,
                "stakeholder_group": (p.persona_data or {}).get("stakeholder_group"),
            }
            for p in personas
        ],
    }


@router.put("/{slug}/persona-order", response_model=StudyConfigResponse)
async def update_persona_order(
    slug: str,
    body: StudyPersonaOrderUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
):
    try:
        study = await StudyService.update_persona_order(db, slug, body.persona_order)
        await db.commit()
        await db.refresh(study)
        return StudyConfigResponse.model_validate(study)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{slug}/events", response_model=StudyEventResponse, status_code=201)
async def record_study_event(
    slug: str,
    body: StudyEventCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    study = await StudyService.get_by_slug(db, slug)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    claims = _study_claims_from_request(credentials)
    if claims.get("study_slug") and claims.get("study_slug") != slug:
        raise HTTPException(status_code=403, detail="Token is for a different study")
    try:
        event = await StudyService.record_event(
            db,
            study_id=study.id,
            event_type=body.event_type,
            path=body.path,
            payload=body.payload,
            participant_id=claims.get("participant_id"),
            user_id=user.id,
        )
        await db.commit()
        await db.refresh(event)
        return StudyEventResponse.model_validate(event)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/events", response_model=List[StudyEventResponse])
async def list_study_events(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin),
    limit: int = 500,
):
    study = await StudyService.get_by_slug(db, slug)
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    from app.models.study import StudyEvent

    result = await db.execute(
        select(StudyEvent)
        .where(StudyEvent.study_id == study.id)
        .order_by(StudyEvent.id.desc())
        .limit(min(limit, 2000))
    )
    return [StudyEventResponse.model_validate(e) for e in result.scalars().all()]

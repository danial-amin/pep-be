"""
Invite-only auth endpoints.

Public: login, accept-invite, invite preview
Protected: me
Admin: create/list invites
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_admin, bearer_scheme
from app.core.security import decode_access_token
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserResponse,
    InviteCreateRequest,
    InviteResponse,
    InvitePreviewResponse,
    AcceptInviteRequest,
)
from app.services.auth_service import AuthService

router = APIRouter()


def _invite_response(invite) -> InviteResponse:
    data = InviteResponse.model_validate(invite)
    data.accept_path = f"/invite/{invite.token}"
    return data


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await AuthService.authenticate(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = AuthService.issue_token(user)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def me(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    data = UserResponse.model_validate(user)
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials) or {}
        if payload.get("is_study_participant"):
            data.is_study_participant = True
            data.study_id = payload.get("study_id")
            data.study_slug = payload.get("study_slug")
            data.participant_code = payload.get("participant_code")
    return data


@router.get("/invites/{token}/preview", response_model=InvitePreviewResponse)
async def preview_invite(token: str, db: AsyncSession = Depends(get_db)):
    invite = await AuthService.get_invite_by_token(db, token)
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    ok, _ = AuthService.invite_is_valid(invite)
    return InvitePreviewResponse(
        email=invite.email,
        expires_at=invite.expires_at,
        note=invite.note,
        valid=ok,
    )


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(request: AcceptInviteRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await AuthService.accept_invite(
            db, token=request.token, name=request.name, password=request.password
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept invite: {e}",
        )

    token = AuthService.issue_token(user)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    request: InviteCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        invite = await AuthService.create_invite(
            session=db,
            email=request.email,
            invited_by=admin,
            note=request.note,
            expires_in_days=request.expires_in_days,
        )
        await db.commit()
        await db.refresh(invite)
        return _invite_response(invite)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create invite: {e}",
        )


@router.get("/invites", response_model=List[InviteResponse])
async def list_invites(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    invites = await AuthService.list_invites(db)
    return [_invite_response(i) for i in invites]

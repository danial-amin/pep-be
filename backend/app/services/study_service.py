"""
Service for user-study mode (participant entry, order, events).
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token, hash_password
from app.models.persona import Persona, PersonaSet
from app.models.study import Study, StudyEvent, StudyParticipant
from app.models.user import User
from app.schemas.study import StudyEnterResponse, StudyParticipantInfo, StudyPublicInfo


_CODE_RE = re.compile(r"^P\d{1,3}$", re.IGNORECASE)


def normalize_participant_code(code: str) -> str:
    raw = (code or "").strip().upper()
    if not raw:
        raise ValueError("Participant code is required")
    # Accept p01 / P01 / 01 → P01
    if raw.isdigit():
        raw = f"P{int(raw):02d}"
    elif raw.startswith("P") and raw[1:].isdigit():
        raw = f"P{int(raw[1:]):02d}"
    if not _CODE_RE.match(raw):
        raise ValueError("Use a participant code like P01, P02, …")
    return raw


class StudyService:
    @staticmethod
    async def get_by_slug(session: AsyncSession, slug: str) -> Optional[Study]:
        result = await session.execute(select(Study).where(Study.slug == slug))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_public_info(session: AsyncSession, slug: str) -> StudyPublicInfo:
        study = await StudyService.get_by_slug(session, slug)
        if not study or not study.enabled:
            raise ValueError("Study not found or disabled")
        return StudyPublicInfo(
            slug=study.slug,
            name=study.name,
            enabled=study.enabled,
            welcome_text=study.welcome_text,
            persona_set_id=study.persona_set_id,
            project_id=study.project_id,
        )

    @staticmethod
    async def enter(
        session: AsyncSession,
        slug: str,
        code: str,
    ) -> StudyEnterResponse:
        study = await StudyService.get_by_slug(session, slug)
        if not study or not study.enabled:
            raise ValueError("Study not found or disabled")

        norm = normalize_participant_code(code)

        result = await session.execute(
            select(StudyParticipant).where(
                StudyParticipant.study_id == study.id,
                StudyParticipant.code == norm,
            )
        )
        participant = result.scalar_one_or_none()

        if not participant:
            if not study.allow_open_codes:
                raise ValueError("Unknown participant code")
            count = (
                await session.execute(
                    select(StudyParticipant).where(StudyParticipant.study_id == study.id)
                )
            ).scalars().all()
            if len(count) >= (study.max_participants or 40):
                raise ValueError("This study has reached its participant limit")
            participant = StudyParticipant(
                study_id=study.id,
                code=norm,
                display_name=norm,
            )
            session.add(participant)
            await session.flush()

        user = None
        if participant.user_id:
            user = (
                await session.execute(select(User).where(User.id == participant.user_id))
            ).scalar_one_or_none()

        if not user:
            email = f"{norm.lower()}@{study.slug}.study.pep.local"
            existing = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if existing:
                user = existing
            else:
                user = User(
                    email=email,
                    name=f"Study {norm}",
                    hashed_password=hash_password(secrets.token_urlsafe(24)),
                    is_admin=False,
                    is_active=True,
                )
                session.add(user)
                await session.flush()
            participant.user_id = user.id

        participant.last_seen_at = datetime.now(timezone.utc)
        await session.flush()

        token = create_access_token(
            str(user.id),
            extra={
                "email": user.email,
                "is_admin": False,
                "is_study_participant": True,
                "study_id": study.id,
                "study_slug": study.slug,
                "participant_id": participant.id,
                "participant_code": participant.code,
            },
        )

        return StudyEnterResponse(
            access_token=token,
            study=StudyPublicInfo(
                slug=study.slug,
                name=study.name,
                enabled=study.enabled,
                welcome_text=study.welcome_text,
                persona_set_id=study.persona_set_id,
                project_id=study.project_id,
            ),
            participant=StudyParticipantInfo.model_validate(participant),
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "is_admin": False,
                "is_active": True,
                "is_study_participant": True,
                "study_id": study.id,
                "study_slug": study.slug,
                "participant_code": participant.code,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
        )

    @staticmethod
    async def ordered_personas(
        session: AsyncSession,
        study: Study,
    ) -> List[Persona]:
        result = await session.execute(
            select(PersonaSet)
            .where(PersonaSet.id == study.persona_set_id)
            .options(selectinload(PersonaSet.personas))
        )
        persona_set = result.scalar_one_or_none()
        if not persona_set:
            return []
        personas = list(persona_set.personas)
        order = study.persona_order or []
        if not order:
            return personas
        by_id = {p.id: p for p in personas}
        ordered = [by_id[i] for i in order if i in by_id]
        # Append any personas not listed in order
        seen = set(order)
        ordered.extend([p for p in personas if p.id not in seen])
        return ordered

    @staticmethod
    async def update_persona_order(
        session: AsyncSession,
        slug: str,
        persona_order: List[int],
    ) -> Study:
        study = await StudyService.get_by_slug(session, slug)
        if not study:
            raise ValueError("Study not found")
        study.persona_order = persona_order
        await session.flush()
        return study

    @staticmethod
    async def record_event(
        session: AsyncSession,
        *,
        study_id: int,
        event_type: str,
        path: Optional[str] = None,
        payload: Optional[dict] = None,
        participant_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> StudyEvent:
        event = StudyEvent(
            study_id=study_id,
            participant_id=participant_id,
            user_id=user_id,
            event_type=event_type[:64],
            path=(path or "")[:512] or None,
            payload=payload,
        )
        session.add(event)
        await session.flush()
        return event

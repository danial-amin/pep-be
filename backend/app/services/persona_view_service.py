"""
Service for recording and summarizing persona profile view times.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.persona import Persona, PersonaSet
from app.models.persona_view import PersonaProfileView
from app.schemas.persona_view import (
    PersonaProfileViewCreate,
    PersonaProfileViewResponse,
    PersonaSetViewTimeSummary,
    PersonaViewTimeTotal,
)

VALID_VIEW_TYPES = {"persona", "set_profiles"}
MIN_DURATION_SECONDS = 1.0


class PersonaViewService:
    @staticmethod
    async def record_view(
        session: AsyncSession,
        data: PersonaProfileViewCreate,
        user_id: Optional[int] = None,
    ) -> Optional[PersonaProfileViewResponse]:
        if data.view_type not in VALID_VIEW_TYPES:
            raise ValueError(f"view_type must be one of {sorted(VALID_VIEW_TYPES)}")

        if data.duration_seconds < MIN_DURATION_SECONDS:
            return None

        if data.view_type == "persona" and data.persona_id is None:
            raise ValueError("persona_id is required when view_type is 'persona'")

        set_result = await session.execute(
            select(PersonaSet).where(PersonaSet.id == data.persona_set_id)
        )
        if not set_result.scalar_one_or_none():
            raise ValueError(f"Persona set {data.persona_set_id} not found")

        if data.persona_id is not None:
            persona_result = await session.execute(
                select(Persona).where(
                    Persona.id == data.persona_id,
                    Persona.persona_set_id == data.persona_set_id,
                )
            )
            if not persona_result.scalar_one_or_none():
                raise ValueError(
                    f"Persona {data.persona_id} not found in set {data.persona_set_id}"
                )

        row = PersonaProfileView(
            user_id=user_id,
            persona_set_id=data.persona_set_id,
            persona_id=data.persona_id if data.view_type == "persona" else None,
            view_type=data.view_type,
            duration_seconds=float(data.duration_seconds),
            started_at=data.started_at,
            ended_at=data.ended_at or datetime.now(timezone.utc),
        )
        session.add(row)
        await session.flush()
        await session.refresh(row)
        return PersonaProfileViewResponse.model_validate(row)

    @staticmethod
    async def get_set_summary(
        session: AsyncSession,
        persona_set_id: int,
    ) -> PersonaSetViewTimeSummary:
        set_result = await session.execute(
            select(PersonaSet)
            .where(PersonaSet.id == persona_set_id)
            .options(selectinload(PersonaSet.personas))
        )
        persona_set = set_result.scalar_one_or_none()
        if not persona_set:
            raise ValueError(f"Persona set {persona_set_id} not found")

        name_by_id = {
            p.id: (p.persona_data or {}).get("name") or p.name
            for p in persona_set.personas
        }

        agg = await session.execute(
            select(
                PersonaProfileView.view_type,
                PersonaProfileView.persona_id,
                func.coalesce(func.sum(PersonaProfileView.duration_seconds), 0.0),
                func.count(PersonaProfileView.id),
            )
            .where(PersonaProfileView.persona_set_id == persona_set_id)
            .group_by(PersonaProfileView.view_type, PersonaProfileView.persona_id)
        )

        totals: list[PersonaViewTimeTotal] = []
        grand = 0.0
        for view_type, persona_id, total_seconds, view_count in agg.all():
            total_f = float(total_seconds or 0)
            grand += total_f
            totals.append(
                PersonaViewTimeTotal(
                    persona_id=persona_id,
                    persona_name=name_by_id.get(persona_id) if persona_id else None,
                    view_type=view_type,
                    total_seconds=total_f,
                    view_count=int(view_count or 0),
                )
            )

        totals.sort(
            key=lambda t: (
                0 if t.view_type == "set_profiles" else 1,
                -(t.total_seconds),
            )
        )
        return PersonaSetViewTimeSummary(
            persona_set_id=persona_set_id,
            totals=totals,
            grand_total_seconds=grand,
        )

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
# Researcher / pilot test codes: PX (default order) or PX1…PX6 (specific rotation)
_TEST_CODE_RE = re.compile(r"^PX([1-6])?$", re.IGNORECASE)

# Short labels for logging / UI (canonical stakeholder_group → study condition code)
GROUP_LABELS = {
    "affected_households": "AH",
    "local_humanitarian_workers": "HW",
    "bisp_programme_representatives": "BISP",
}

# Map free-form / display stakeholder labels onto Latin-square keys
GROUP_ALIASES = {
    "affected_households": "affected_households",
    "affected_household": "affected_households",
    "affected household": "affected_households",
    "local_humanitarian_workers": "local_humanitarian_workers",
    "local_humanitarian_worker": "local_humanitarian_workers",
    "local ngo worker": "local_humanitarian_workers",
    "local_ngo_worker": "local_humanitarian_workers",
    "bisp_programme_representatives": "bisp_programme_representatives",
    "bisp_programme_representative": "bisp_programme_representatives",
    "bisp representative": "bisp_programme_representatives",
    "bisp_representative": "bisp_programme_representatives",
}


def normalize_stakeholder_group(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    key = str(raw).strip().lower().replace("-", " ")
    key = re.sub(r"\s+", " ", key)
    underscored = key.replace(" ", "_")
    return GROUP_ALIASES.get(key) or GROUP_ALIASES.get(underscored) or underscored


def normalize_participant_code(code: str) -> str:
    raw = (code or "").strip().upper()
    if not raw:
        raise ValueError("Participant code is required")
    # Test codes: PX, PX1…PX6
    test_m = _TEST_CODE_RE.match(raw)
    if test_m:
        return raw if raw.startswith("PX") else f"PX{test_m.group(1) or ''}"
    # Accept p01 / P01 / 01 → P01
    if raw.isdigit():
        raw = f"P{int(raw):02d}"
    elif raw.startswith("P") and raw[1:].isdigit():
        raw = f"P{int(raw[1:]):02d}"
    if not _CODE_RE.match(raw):
        raise ValueError("Use a participant code like P01, P02, … (or PX to test)")
    return raw


def is_test_participant_code(code: str) -> bool:
    try:
        return bool(_TEST_CODE_RE.match(normalize_participant_code(code)))
    except ValueError:
        return False


def participant_number(code: str) -> int:
    norm = normalize_participant_code(code)
    if is_test_participant_code(norm):
        # PX → 1 (first rotation); PX3 → 3
        suffix = norm[2:]
        return int(suffix) if suffix.isdigit() else 1
    return int(norm[1:])


def rotation_index_for_code(code: str, rotation_count: int) -> int:
    if rotation_count <= 0:
        return 0
    return (participant_number(code) - 1) % rotation_count


def condition_label(groups: List[str]) -> str:
    return " – ".join(GROUP_LABELS.get(g, g) for g in groups)


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
        is_test = is_test_participant_code(norm)

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
            # Test codes (PX / PX1…) do not consume the participant limit
            if not is_test:
                real_codes = (
                    await session.execute(
                        select(StudyParticipant).where(StudyParticipant.study_id == study.id)
                    )
                ).scalars().all()
                real_count = sum(
                    1 for p in real_codes if not is_test_participant_code(p.code)
                )
                if real_count >= (study.max_participants or 40):
                    raise ValueError("This study has reached its participant limit")
            participant = StudyParticipant(
                study_id=study.id,
                code=norm,
                display_name=f"{norm} (test)" if is_test else norm,
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
                    name=f"Study {norm}" + (" (test)" if is_test else ""),
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
                "is_test_participant": is_test,
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
                "is_test_participant": is_test,
                "study_id": study.id,
                "study_slug": study.slug,
                "participant_code": participant.code,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
        )

    @staticmethod
    def resolve_order_meta(
        study: Study,
        personas: List[Persona],
        participant_code: Optional[str] = None,
    ) -> dict:
        """
        Resolve display order for a participant.

        When study.order_rotations is set, Pn uses rotations[(n-1) % len].
        Otherwise falls back to study.persona_order (persona IDs).
        """
        by_group = {}
        for p in personas:
            g = normalize_stakeholder_group((p.persona_data or {}).get("stakeholder_group"))
            if g and g not in by_group:
                by_group[g] = p
        by_id = {p.id: p for p in personas}
        rotations = study.order_rotations or []
        if isinstance(rotations, str):
            rotations = []

        if rotations and participant_code:
            idx = rotation_index_for_code(participant_code, len(rotations))
            groups = [normalize_stakeholder_group(g) or g for g in (rotations[idx] or [])]
            ordered = [by_group[g] for g in groups if g in by_group]
            seen = {p.id for p in ordered}
            ordered.extend([p for p in personas if p.id not in seen])
            return {
                "personas": ordered,
                "persona_order": [p.id for p in ordered],
                "order_condition": condition_label(groups),
                "order_rotation_index": idx,
                "order_groups": groups,
            }

        order_ids = study.persona_order or []
        if order_ids:
            ordered = [by_id[i] for i in order_ids if i in by_id]
            seen = set(order_ids)
            ordered.extend([p for p in personas if p.id not in seen])
        else:
            ordered = list(personas)
        return {
            "personas": ordered,
            "persona_order": [p.id for p in ordered],
            "order_condition": None,
            "order_rotation_index": None,
            "order_groups": None,
        }

    @staticmethod
    async def ordered_personas(
        session: AsyncSession,
        study: Study,
        participant_code: Optional[str] = None,
    ) -> dict:
        result = await session.execute(
            select(PersonaSet)
            .where(PersonaSet.id == study.persona_set_id)
            .options(selectinload(PersonaSet.personas))
        )
        persona_set = result.scalar_one_or_none()
        if not persona_set:
            return {
                "personas": [],
                "persona_order": [],
                "order_condition": None,
                "order_rotation_index": None,
                "order_groups": None,
            }
        return StudyService.resolve_order_meta(
            study, list(persona_set.personas), participant_code
        )
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
    def _policy_study_rotations(groups_present: set) -> Optional[List[List[str]]]:
        """Build the 6 AH/HW/BISP Latin-square rotations when all three groups exist."""
        ah = "affected_households"
        hw = "local_humanitarian_workers"
        bisp = "bisp_programme_representatives"
        needed = {ah, hw, bisp}
        if not needed.issubset(groups_present):
            return None
        return [
            [ah, hw, bisp],
            [ah, bisp, hw],
            [hw, ah, bisp],
            [hw, bisp, ah],
            [bisp, ah, hw],
            [bisp, hw, ah],
        ]

    @staticmethod
    async def list_studies(session: AsyncSession) -> List[dict]:
        from sqlalchemy import func
        from app.models.study import StudyParticipant, StudyEvent

        studies = (await session.execute(select(Study).order_by(Study.id.desc()))).scalars().all()
        out = []
        for study in studies:
            p_count = (
                await session.execute(
                    select(func.count())
                    .select_from(StudyParticipant)
                    .where(StudyParticipant.study_id == study.id)
                )
            ).scalar() or 0
            e_count = (
                await session.execute(
                    select(func.count())
                    .select_from(StudyEvent)
                    .where(StudyEvent.study_id == study.id)
                )
            ).scalar() or 0
            out.append(
                {
                    "id": study.id,
                    "slug": study.slug,
                    "name": study.name,
                    "enabled": study.enabled,
                    "project_id": study.project_id,
                    "persona_set_id": study.persona_set_id,
                    "participant_count": int(p_count),
                    "event_count": int(e_count),
                }
            )
        return out

    @staticmethod
    async def update_config(
        session: AsyncSession,
        slug: str,
        *,
        name: Optional[str] = None,
        enabled: Optional[bool] = None,
        project_id: Optional[int] = None,
        persona_set_id: Optional[int] = None,
        persona_order: Optional[List[int]] = None,
        order_rotations: Optional[List[List[str]]] = None,
        allow_open_codes: Optional[bool] = None,
        max_participants: Optional[int] = None,
        welcome_text: Optional[str] = None,
        rebuild_rotations: bool = True,
    ) -> Study:
        study = await StudyService.get_by_slug(session, slug)
        if not study:
            raise ValueError("Study not found")

        if name is not None:
            study.name = name
        if enabled is not None:
            study.enabled = enabled
        if project_id is not None:
            study.project_id = project_id
        if allow_open_codes is not None:
            study.allow_open_codes = allow_open_codes
        if max_participants is not None:
            study.max_participants = max_participants
        if welcome_text is not None:
            study.welcome_text = welcome_text
        if order_rotations is not None:
            study.order_rotations = order_rotations
        if persona_order is not None:
            study.persona_order = persona_order

        if persona_set_id is not None and persona_set_id != study.persona_set_id:
            ps = (
                await session.execute(
                    select(PersonaSet)
                    .where(PersonaSet.id == persona_set_id)
                    .options(selectinload(PersonaSet.personas))
                )
            ).scalar_one_or_none()
            if not ps:
                raise ValueError(f"Persona set {persona_set_id} not found")
            study.persona_set_id = persona_set_id
            if study.project_id is None and ps.project_id is not None:
                study.project_id = ps.project_id

            personas = list(ps.personas)
            by_group = {}
            for p in personas:
                g = normalize_stakeholder_group((p.persona_data or {}).get("stakeholder_group"))
                if g and g not in by_group:
                    by_group[g] = p.id
            groups = set(by_group.keys())
            if rebuild_rotations:
                rotations = StudyService._policy_study_rotations(groups)
                study.order_rotations = rotations
                if rotations:
                    study.persona_order = [
                        by_group[g] for g in rotations[0] if g in by_group
                    ]
                else:
                    study.persona_order = [p.id for p in personas]
            elif persona_order is None:
                study.persona_order = [p.id for p in personas]

        await session.flush()
        return study

    @staticmethod
    async def list_participants(session: AsyncSession, study_id: int) -> List[dict]:
        from sqlalchemy import func
        from app.models.study import StudyParticipant, StudyEvent

        participants = (
            await session.execute(
                select(StudyParticipant)
                .where(StudyParticipant.study_id == study_id)
                .order_by(StudyParticipant.code)
            )
        ).scalars().all()
        out = []
        for p in participants:
            e_count = (
                await session.execute(
                    select(func.count())
                    .select_from(StudyEvent)
                    .where(StudyEvent.participant_id == p.id)
                )
            ).scalar() or 0
            out.append(
                {
                    "id": p.id,
                    "code": p.code,
                    "display_name": p.display_name,
                    "user_id": p.user_id,
                    "created_at": p.created_at,
                    "last_seen_at": p.last_seen_at,
                    "event_count": int(e_count),
                    "is_test": is_test_participant_code(p.code),
                }
            )
        return out

    @staticmethod
    async def list_events_admin(
        session: AsyncSession,
        study_id: int,
        *,
        participant_code: Optional[str] = None,
        limit: int = 500,
    ) -> List[dict]:
        from app.models.study import StudyEvent, StudyParticipant

        query = (
            select(StudyEvent, StudyParticipant.code)
            .outerjoin(StudyParticipant, StudyParticipant.id == StudyEvent.participant_id)
            .where(StudyEvent.study_id == study_id)
        )
        if participant_code:
            try:
                norm = normalize_participant_code(participant_code)
            except ValueError:
                norm = participant_code.strip().upper()
            query = query.where(StudyParticipant.code == norm)
        query = query.order_by(StudyEvent.id.desc()).limit(min(limit, 2000))
        rows = (await session.execute(query)).all()
        return [
            {
                "id": e.id,
                "study_id": e.study_id,
                "participant_id": e.participant_id,
                "participant_code": code,
                "user_id": e.user_id,
                "event_type": e.event_type,
                "path": e.path,
                "payload": e.payload,
                "created_at": e.created_at,
            }
            for e, code in rows
        ]

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
        participant_code: Optional[str] = None,
    ) -> StudyEvent:
        enriched: dict = dict(payload or {})
        if participant_id is not None:
            enriched.setdefault("participant_id", participant_id)
        if user_id is not None:
            enriched.setdefault("user_id", user_id)
        if participant_code:
            enriched.setdefault("participant_code", participant_code)

        # Keep participant last_seen fresh for admin visibility
        if participant_id is not None:
            participant = (
                await session.execute(
                    select(StudyParticipant).where(StudyParticipant.id == participant_id)
                )
            ).scalar_one_or_none()
            if participant:
                participant.last_seen_at = datetime.now(timezone.utc)
                if participant.code and "participant_code" not in enriched:
                    enriched["participant_code"] = participant.code

        event = StudyEvent(
            study_id=study_id,
            participant_id=participant_id,
            user_id=user_id,
            event_type=event_type[:64],
            path=(path or "")[:512] or None,
            payload=enriched or None,
        )
        session.add(event)
        await session.flush()
        return event

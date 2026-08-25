#!/usr/bin/env python3
"""Regenerate Policy Study persona set 38 in place (preserve persona IDs)."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.persona import Persona, PersonaSet
from app.services.iterative_generation_service import iterative_generation_service

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("regen_set_38")

TARGET_SET_ID = 38
GROUPS = [
    "affected household",
    "Local Volunteer",
    "BISP Representative",
]
CONTEXT_DETAILS = (
    "All three personas should belong to the town of Hyderabad, Sindh, Pakistan. "
    "Keep goals, frustrations, and quotes locally consistent with Hyderabad / Sindh "
    "and each persona's role scope. Do not treat other provinces' statistics as this "
    "persona's personal lived concerns unless their role is explicitly national. "
    "The affected-household persona should be a widow and head of household. "
    "The local volunteer should be an unpaid community volunteer (not an NGO employee)."
)


def _geo_hits(pd: dict) -> list:
    import re

    blob = json.dumps(pd or {}, ensure_ascii=False)
    return sorted(
        set(
            re.findall(
                r"(?i)baloch\w*|sindh|hyderabad|punjab|karachi|kpk|khyber",
                blob,
            )
        )
    )


async def main() -> None:
    async with AsyncSessionLocal() as session:
        old = (
            await session.execute(
                select(PersonaSet)
                .where(PersonaSet.id == TARGET_SET_ID)
                .options(selectinload(PersonaSet.personas))
            )
        ).scalar_one_or_none()
        if not old:
            raise SystemExit(f"Persona set {TARGET_SET_ID} not found")

        project_id = old.project_id
        old_personas = sorted(list(old.personas), key=lambda p: p.id)
        if len(old_personas) != len(GROUPS):
            raise SystemExit(
                f"Expected {len(GROUPS)} personas on set {TARGET_SET_ID}, found {len(old_personas)}"
            )

        logger.info(
            "Regenerating set %s for project_id=%s (in-place update of IDs %s)",
            TARGET_SET_ID,
            project_id,
            [p.id for p in old_personas],
        )

        new_set, metrics = await iterative_generation_service.generate_persona_set_iterative(
            session=session,
            num_personas=len(GROUPS),
            project_id=project_id,
            stakeholder_groups=GROUPS,
            context_details=CONTEXT_DETAILS,
            interview_topic="Emergency registration and cash assistance / social protection access",
            include_ethical_guardrails=True,
            output_format="json",
            auto_iterate=True,
            rqe_threshold=0.75,
            max_iterations=3,
        )
        await session.flush()

        new_personas = sorted(
            (
                await session.execute(select(Persona).where(Persona.persona_set_id == new_set.id))
            ).scalars().all(),
            key=lambda p: p.id,
        )
        if len(new_personas) != len(old_personas):
            raise SystemExit(
                f"Generated {len(new_personas)} personas, expected {len(old_personas)}"
            )

        # Overwrite existing persona rows so FKs (simulations, chats) keep working
        for old_p, new_p, group in zip(old_personas, new_personas, GROUPS):
            pd = dict(new_p.persona_data or {})
            pd["stakeholder_group"] = pd.get("stakeholder_group") or group
            old_p.name = new_p.name or pd.get("name") or old_p.name
            old_p.persona_data = pd
            # leave image_url as-is unless new has one
            if new_p.image_url:
                old_p.image_url = new_p.image_url

        target = (
            await session.execute(select(PersonaSet).where(PersonaSet.id == TARGET_SET_ID))
        ).scalar_one()
        target.name = "Policy Study stakeholders (Hyderabad)"
        target.description = (
            "Regenerated with place/role grounding rules; "
            f"RQE threshold {new_set.rqe_threshold}"
        )
        target.generation_config = new_set.generation_config
        target.rqe_threshold = new_set.rqe_threshold
        target.max_iterations = new_set.max_iterations
        target.generation_cycle = new_set.generation_cycle
        target.rqe_scores = new_set.rqe_scores
        target.diversity_score = new_set.diversity_score
        target.status = "generated"
        target.project_id = project_id

        # Remove temporary generated set + its persona rows
        for p in new_personas:
            await session.delete(p)
        await session.flush()
        await session.delete(new_set)
        await session.commit()

        final = (
            await session.execute(
                select(PersonaSet)
                .where(PersonaSet.id == TARGET_SET_ID)
                .options(selectinload(PersonaSet.personas))
            )
        ).scalar_one()

        logger.info(
            "Done set=%s rqe=%.3f threshold_met=%s iterations=%s",
            final.id,
            float(metrics.get("rqe_score") or 0),
            metrics.get("threshold_met"),
            metrics.get("iterations_used"),
        )
        for p in sorted(final.personas, key=lambda x: x.id):
            pd = p.persona_data or {}
            dem = pd.get("demographics") if isinstance(pd.get("demographics"), dict) else {}
            summary = {
                "id": p.id,
                "name": p.name,
                "stakeholder_group": pd.get("stakeholder_group"),
                "gender": dem.get("gender") or pd.get("gender"),
                "location": dem.get("location") or pd.get("location"),
                "occupation": dem.get("occupation") or pd.get("occupation"),
                "geo_mentions": _geo_hits(pd),
                "goals": pd.get("goals"),
                "frustrations": pd.get("frustrations"),
                "background": (pd.get("background") or "")[:320],
            }
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            print("---")


if __name__ == "__main__":
    asyncio.run(main())

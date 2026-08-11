#!/usr/bin/env python3
"""Create / update the Policy Study user-study config (slug: policy-study)."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.persona import PersonaSet
from app.models.project import Project
from app.models.study import Study

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_policy_study")

SLUG = "policy-study"

AH = "affected_households"
HW = "local_humanitarian_workers"
BISP = "bisp_programme_representatives"

# Counterbalanced orders for P01, P02, … (cycles every 6)
# P01 AH–HW–BISP, P02 AH–BISP–HW, P03 HW–AH–BISP,
# P04 HW–BISP–AH, P05 BISP–AH–HW, P06 BISP–HW–AH, P07→P01…
ORDER_ROTATIONS = [
    [AH, HW, BISP],
    [AH, BISP, HW],
    [HW, AH, BISP],
    [HW, BISP, AH],
    [BISP, AH, HW],
    [BISP, HW, AH],
]


async def ensure_order_rotations_column(session) -> None:
    await session.execute(
        text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='studies')
                   AND NOT EXISTS (
                       SELECT 1 FROM information_schema.columns
                       WHERE table_name='studies' AND column_name='order_rotations'
                   ) THEN
                    ALTER TABLE studies ADD COLUMN order_rotations JSONB;
                END IF;
            END $$;
            """
        )
    )
    await session.commit()


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await ensure_order_rotations_column(session)

        project = (
            await session.execute(select(Project).where(Project.name == "Policy Study"))
        ).scalar_one_or_none()
        if not project:
            raise SystemExit("Policy Study project not found")

        sets = (
            await session.execute(
                select(PersonaSet)
                .where(PersonaSet.project_id == project.id)
                .options(selectinload(PersonaSet.personas))
                .order_by(PersonaSet.id.desc())
            )
        ).scalars().all()
        if not sets:
            raise SystemExit("No persona sets for Policy Study")

        chosen = None
        for ps in sets:
            cfg = ps.generation_config or {}
            if cfg.get("stakeholder_groups"):
                chosen = ps
                break
        if chosen is None:
            chosen = sets[0]

        # Backfill stakeholder_group when the LLM omitted it.
        # Prefer persona_00N ↔ generation_config.stakeholder_groups[N-1],
        # then fall back to content heuristics.
        cfg_groups = list((chosen.generation_config or {}).get("stakeholder_groups") or [])
        heuristics = [
            (AH, ("flood-affected", "community member navigating", "mother of", "household")),
            (BISP, ("bisp", "programme official", "nser", "social protection")),
            (HW, ("ngo", "humanitarian", "on the ground", "local worker", "community needs", "volunteer")),
        ]
        for p in chosen.personas:
            data = dict(p.persona_data or {})
            if data.get("stakeholder_group") in {AH, HW, BISP}:
                continue
            assigned = None
            pid = str(data.get("persona_id") or "")
            if cfg_groups and pid.startswith("persona_"):
                try:
                    idx = int(pid.split("_")[1]) - 1
                    if 0 <= idx < len(cfg_groups):
                        assigned = cfg_groups[idx]
                except (ValueError, IndexError):
                    assigned = None
            if not assigned:
                blob = " ".join(
                    str(data.get(k) or "")
                    for k in ("tagline", "background", "name")
                ).lower()
                for group, needles in heuristics:
                    if any(n in blob for n in needles):
                        assigned = group
                        break
            if assigned:
                data["stakeholder_group"] = assigned
                p.persona_data = data
                logger.info("Backfilled persona %s → %s", p.id, assigned)

        by_group = {
            (p.persona_data or {}).get("stakeholder_group"): p.id
            for p in chosen.personas
            if (p.persona_data or {}).get("stakeholder_group")
        }
        # Default/fallback order = first rotation (AH–HW–BISP)
        order = [by_group[g] for g in ORDER_ROTATIONS[0] if g in by_group]
        for p in chosen.personas:
            if p.id not in order:
                order.append(p.id)

        missing = [
            g
            for rotation in ORDER_ROTATIONS
            for g in rotation
            if g not in by_group
        ]
        if missing:
            raise SystemExit(f"Missing stakeholder personas for groups: {sorted(set(missing))}")

        welcome = (
            "Welcome to the PEP Policy Study session.\n\n"
            "Enter your participant code (for example P01). No password is needed.\n"
            "You will see three stakeholder personas on one screen; click a card to enlarge."
        )

        existing = (
            await session.execute(select(Study).where(Study.slug == SLUG))
        ).scalar_one_or_none()

        if existing:
            existing.name = "Policy Study"
            existing.enabled = True
            existing.project_id = project.id
            existing.persona_set_id = chosen.id
            existing.persona_order = order
            existing.order_rotations = ORDER_ROTATIONS
            existing.allow_open_codes = True
            existing.max_participants = 40
            existing.welcome_text = welcome
            study = existing
            logger.info("Updated study id=%s slug=%s", study.id, study.slug)
        else:
            study = Study(
                slug=SLUG,
                name="Policy Study",
                enabled=True,
                project_id=project.id,
                persona_set_id=chosen.id,
                persona_order=order,
                order_rotations=ORDER_ROTATIONS,
                allow_open_codes=True,
                max_participants=40,
                welcome_text=welcome,
            )
            session.add(study)
            logger.info("Created study slug=%s", SLUG)

        await session.commit()
        logger.info(
            "Ready: /study/%s  persona_set_id=%s rotations=%s",
            SLUG,
            chosen.id,
            len(ORDER_ROTATIONS),
        )
        for i, rotation in enumerate(ORDER_ROTATIONS):
            labels = " – ".join(
                {"affected_households": "AH", "local_humanitarian_workers": "HW", "bisp_programme_representatives": "BISP"}[g]
                for g in rotation
            )
            logger.info("  P%02d,P%02d,… → %s", i + 1, i + 7, labels)


if __name__ == "__main__":
    asyncio.run(main())

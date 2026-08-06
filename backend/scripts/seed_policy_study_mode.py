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

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.persona import Persona, PersonaSet
from app.models.project import Project
from app.models.study import Study

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_policy_study")

SLUG = "policy-study"
STAKEHOLDER_ORDER = [
    "affected_households",
    "bisp_programme_representatives",
    "local_humanitarian_workers",
]


async def main() -> None:
    async with AsyncSessionLocal() as session:
        project = (
            await session.execute(select(Project).where(Project.name == "Policy Study"))
        ).scalar_one_or_none()
        if not project:
            raise SystemExit("Policy Study project not found")

        # Prefer persona set that has stakeholder_groups in generation_config
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

        # Order personas by stakeholder_group when possible
        by_group = {
            (p.persona_data or {}).get("stakeholder_group"): p.id
            for p in chosen.personas
            if (p.persona_data or {}).get("stakeholder_group")
        }
        order = [by_group[g] for g in STAKEHOLDER_ORDER if g in by_group]
        for p in chosen.personas:
            if p.id not in order:
                order.append(p.id)

        existing = (
            await session.execute(select(Study).where(Study.slug == SLUG))
        ).scalar_one_or_none()

        welcome = (
            "Welcome to the PEP Policy Study session.\n\n"
            "Enter your participant code (for example P01). No password is needed.\n"
            "You will see three stakeholder personas on one screen; click a card to enlarge."
        )

        if existing:
            existing.name = "Policy Study"
            existing.enabled = True
            existing.project_id = project.id
            existing.persona_set_id = chosen.id
            existing.persona_order = order
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
                allow_open_codes=True,
                max_participants=40,
                welcome_text=welcome,
            )
            session.add(study)
            logger.info("Created study slug=%s", SLUG)

        await session.commit()
        logger.info(
            "Ready: /study/%s  persona_set_id=%s order=%s",
            SLUG,
            chosen.id,
            order,
        )


if __name__ == "__main__":
    asyncio.run(main())

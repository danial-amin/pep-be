#!/usr/bin/env python3
"""Generate stakeholder-mapped personas for Policy Study on production."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.project import Project
from app.services.iterative_generation_service import iterative_generation_service

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("gen_policy_stakeholders")

GROUPS = [
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

        logger.info("Generating stakeholder personas for project_id=%s", project.id)
        persona_set, metrics = await iterative_generation_service.generate_persona_set_iterative(
            session=session,
            num_personas=len(GROUPS),
            project_id=project.id,
            stakeholder_groups=GROUPS,
            context_details=(
                "Pakistan social protection / BISP–NSER / emergency cash assistance policy study. "
                "Each persona must map to one required stakeholder group."
            ),
            interview_topic="Emergency registration and cash assistance after floods in Pakistan",
            include_ethical_guardrails=True,
            output_format="json",
            auto_iterate=False,
            max_iterations=1,
        )
        await session.commit()
        logger.info(
            "Created persona_set_id=%s rqe=%.3f personas=%s",
            persona_set.id,
            metrics.get("rqe_score") or 0,
            [
                (
                    p.name,
                    (p.persona_data or {}).get("stakeholder_group"),
                )
                for p in persona_set.personas
            ],
        )


if __name__ == "__main__":
    asyncio.run(main())

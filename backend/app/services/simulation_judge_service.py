"""
Simulation LLM-as-judge evaluation service.

Scores every completed simulation (discussion-level) and every participating
persona with messages (persona-level). Read-only over simulation transcripts.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Set

from openai import AsyncOpenAI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.judge_score import JudgeRun, JudgeScore
from app.models.simulation import Simulation, SimulationMessage
from app.schemas.judge import JudgeLLMOutput, parse_judge_response
from app.services.transcript_builder import (
    build_discussion_transcript,
    build_persona_transcript,
    get_persona_name,
    load_simulation_with_messages,
)
from app.utils.judge_prompts import build_full_prompt
from app.utils.judge_survey_items import ALL_ITEMS, Level

logger = logging.getLogger(__name__)


class SimulationJudgeService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def _persona_ids_with_messages(self, simulation: Simulation) -> Set[int]:
        ids: Set[int] = set()
        for message in simulation.messages:
            if message.persona_id and not message.is_moderator_message:
                ids.add(message.persona_id)
        return ids

    async def _call_judge(
        self,
        model: str,
        level: Level,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> tuple[dict, str]:
        schema = JudgeLLMOutput.json_schema_for_level(level)
        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=16384,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": f"simulation_judge_{level}",
                    "strict": True,
                    "schema": schema,
                },
            },
        )
        content = response.choices[0].message.content or "{}"
        model_version = getattr(response, "model", None) or model
        if hasattr(response, "system_fingerprint") and response.system_fingerprint:
            model_version = f"{model_version}@{response.system_fingerprint}"
        return json.loads(content), model_version

    async def _existing_run(
        self,
        session: AsyncSession,
        judge_model: str,
        level: str,
        simulation_id: int,
        target_id: int,
        pass_number: int,
    ) -> bool:
        result = await session.execute(
            select(JudgeRun.id)
            .where(
                JudgeRun.judge_model == judge_model,
                JudgeRun.level == level,
                JudgeRun.simulation_id == simulation_id,
                JudgeRun.target_id == target_id,
                JudgeRun.pass_number == pass_number,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _clear_existing_run(
        self,
        session: AsyncSession,
        judge_model: str,
        level: str,
        simulation_id: int,
        target_id: int,
        pass_number: int,
    ) -> None:
        result = await session.execute(
            select(JudgeRun.id).where(
                JudgeRun.judge_model == judge_model,
                JudgeRun.level == level,
                JudgeRun.simulation_id == simulation_id,
                JudgeRun.target_id == target_id,
                JudgeRun.pass_number == pass_number,
            )
        )
        run_ids = [row[0] for row in result.all()]
        if not run_ids:
            return
        await session.execute(delete(JudgeScore).where(JudgeScore.judge_run_id.in_(run_ids)))
        await session.execute(delete(JudgeRun).where(JudgeRun.id.in_(run_ids)))

    async def _persist_scores(
        self,
        session: AsyncSession,
        *,
        judge_model: str,
        model_version: str,
        pass_number: int,
        temperature: float,
        level: str,
        simulation_id: int,
        target_id: int,
        system_prompt: str,
        user_prompt: str,
        template_hash: str,
        parsed: dict,
        run_ts: datetime,
    ) -> int:
        judge_run = JudgeRun(
            judge_model=judge_model,
            model_version=model_version,
            pass_number=pass_number,
            temperature=temperature,
            level=level,
            simulation_id=simulation_id,
            target_id=target_id,
            prompt_template_hash=template_hash,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            run_timestamp=run_ts,
        )
        session.add(judge_run)
        await session.flush()

        rows = 0
        for item_name, item_response in parsed.items():
            item_def = ALL_ITEMS[item_name]
            session.add(JudgeScore(
                judge_run_id=judge_run.id,
                judge_model=judge_model,
                model_version=model_version,
                pass_number=pass_number,
                temperature=temperature,
                level=level,
                simulation_id=simulation_id,
                target_id=target_id,
                item=item_name,
                item_type=item_def.item_type,
                response_code=item_response.response_code,
                response_label=item_response.response_label,
                justification=item_response.justification,
                run_timestamp=run_ts,
            ))
            rows += 1
        return rows

    async def _score_persona(
        self,
        session: AsyncSession,
        simulation_id: int,
        persona_id: int,
        judge_model: str,
        pass_number: int,
        temperature: float,
        force: bool,
    ) -> int:
        if await self._existing_run(
            session, judge_model, "persona", simulation_id, persona_id, pass_number
        ):
            if not force:
                logger.info(
                    "Skipping persona sim=%s persona=%s model=%s pass=%s (already scored)",
                    simulation_id, persona_id, judge_model, pass_number,
                )
                return 0
            await self._clear_existing_run(
                session, judge_model, "persona", simulation_id, persona_id, pass_number
            )

        simulation = await load_simulation_with_messages(session, simulation_id)
        persona_name = await get_persona_name(session, persona_id)
        transcript = build_persona_transcript(simulation, persona_id, persona_name)
        system_prompt, user_prompt, template_hash = build_full_prompt("persona", transcript)

        raw, model_version = await self._call_judge(
            judge_model, "persona", system_prompt, user_prompt, temperature
        )
        parsed = parse_judge_response("persona", raw)
        run_ts = datetime.now(timezone.utc)
        rows = await self._persist_scores(
            session,
            judge_model=judge_model,
            model_version=model_version,
            pass_number=pass_number,
            temperature=temperature,
            level="persona",
            simulation_id=simulation_id,
            target_id=persona_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            template_hash=template_hash,
            parsed=parsed,
            run_ts=run_ts,
        )
        logger.info(
            "Scored persona simulation_id=%s persona_id=%s model=%s pass=%s items=%s",
            simulation_id, persona_id, judge_model, pass_number, rows,
        )
        return rows

    async def _score_discussion(
        self,
        session: AsyncSession,
        simulation_id: int,
        judge_model: str,
        pass_number: int,
        temperature: float,
        force: bool,
    ) -> int:
        if await self._existing_run(
            session, judge_model, "discussion", simulation_id, simulation_id, pass_number
        ):
            if not force:
                logger.info(
                    "Skipping discussion sim=%s model=%s pass=%s (already scored)",
                    simulation_id, judge_model, pass_number,
                )
                return 0
            await self._clear_existing_run(
                session, judge_model, "discussion", simulation_id, simulation_id, pass_number
            )

        simulation = await load_simulation_with_messages(session, simulation_id)
        transcript = build_discussion_transcript(simulation)
        system_prompt, user_prompt, template_hash = build_full_prompt("discussion", transcript)

        raw, model_version = await self._call_judge(
            judge_model, "discussion", system_prompt, user_prompt, temperature
        )
        parsed = parse_judge_response("discussion", raw)
        run_ts = datetime.now(timezone.utc)
        rows = await self._persist_scores(
            session,
            judge_model=judge_model,
            model_version=model_version,
            pass_number=pass_number,
            temperature=temperature,
            level="discussion",
            simulation_id=simulation_id,
            target_id=simulation_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            template_hash=template_hash,
            parsed=parsed,
            run_ts=run_ts,
        )
        logger.info(
            "Scored discussion simulation_id=%s model=%s pass=%s items=%s",
            simulation_id, judge_model, pass_number, rows,
        )
        return rows

    async def _get_simulation_or_raise(
        self,
        session: AsyncSession,
        simulation_id: int,
    ) -> Simulation:
        result = await session.execute(
            select(Simulation)
            .where(Simulation.id == simulation_id)
            .options(selectinload(Simulation.participants), selectinload(Simulation.messages))
        )
        simulation = result.scalar_one_or_none()
        if simulation is None:
            raise ValueError(f"Simulation {simulation_id} not found")
        return simulation

    async def evaluate_simulation(
        self,
        session: AsyncSession,
        simulation_id: int,
        *,
        judge_models: Optional[List[str]] = None,
        pass_count: Optional[int] = None,
        temperature: Optional[float] = None,
        force: bool = False,
    ) -> dict:
        """Score one simulation: discussion-level + every participating persona."""
        simulation = await self._get_simulation_or_raise(session, simulation_id)
        if simulation.status not in ("completed", "stopped"):
            raise ValueError(
                "Simulation must be completed or stopped before evaluation. "
                f"Current status: {simulation.status}"
            )
        if not simulation.messages:
            raise ValueError("Cannot evaluate: simulation has no messages yet")

        return await self._run_for_simulations(
            session,
            [simulation],
            judge_models=judge_models,
            pass_count=pass_count,
            temperature=temperature,
            force=force,
        )

    async def get_evaluation_scores(
        self,
        session: AsyncSession,
        simulation_id: int,
    ) -> dict:
        """Return stored judge scores grouped for the simulation detail UI."""
        result = await session.execute(
            select(JudgeScore)
            .where(JudgeScore.simulation_id == simulation_id)
            .order_by(JudgeScore.judge_model, JudgeScore.level, JudgeScore.target_id, JudgeScore.item)
        )
        rows = list(result.scalars().all())
        if not rows:
            return {
                "simulation_id": simulation_id,
                "has_evaluation": False,
                "judge_models": [],
                "scores": [],
            }

        persona_names: dict[int, str] = {}
        try:
            simulation = await load_simulation_with_messages(session, simulation_id)
            for participant in simulation.participants:
                if participant.persona:
                    persona_names[participant.persona_id] = participant.persona.name
        except ValueError:
            pass

        scores = []
        models: set[str] = set()
        last_ts = None
        for row in rows:
            models.add(row.judge_model)
            if last_ts is None or row.run_timestamp > last_ts:
                last_ts = row.run_timestamp
            scores.append({
                "judge_model": row.judge_model,
                "level": row.level,
                "simulation_id": row.simulation_id,
                "target_id": row.target_id,
                "persona_name": persona_names.get(row.target_id) if row.level == "persona" else None,
                "item": row.item,
                "item_type": row.item_type,
                "response_code": row.response_code,
                "response_label": row.response_label,
                "justification": row.justification,
                "run_timestamp": row.run_timestamp.isoformat() if row.run_timestamp else None,
            })

        return {
            "simulation_id": simulation_id,
            "has_evaluation": True,
            "judge_models": sorted(models),
            "last_evaluated_at": last_ts.isoformat() if last_ts else None,
            "scores": scores,
        }

    async def _run_for_simulations(
        self,
        session: AsyncSession,
        simulations: List[Simulation],
        *,
        judge_models: Optional[List[str]] = None,
        pass_count: Optional[int] = None,
        temperature: Optional[float] = None,
        force: bool = False,
    ) -> dict:
        models = judge_models or settings.judge_models_list()
        passes = pass_count or settings.JUDGE_PASS_COUNT
        temp = temperature if temperature is not None else settings.JUDGE_TEMPERATURE

        if not simulations:
            return {
                "simulation_ids": [],
                "judge_models": models,
                "pass_count": passes,
                "temperature": temp,
                "persona_targets": 0,
                "attempted_runs": 0,
                "score_rows_written": 0,
            }

        total_rows = 0
        attempted_runs = 0
        persona_targets = 0
        for sim in simulations:
            persona_ids = self._persona_ids_with_messages(sim)
            persona_targets += len(persona_ids)
            for judge_model in models:
                for pass_number in range(1, passes + 1):
                    total_rows += await self._score_discussion(
                        session, sim.id, judge_model, pass_number, temp, force
                    )
                    attempted_runs += 1
                    for persona_id in sorted(persona_ids):
                        total_rows += await self._score_persona(
                            session, sim.id, persona_id, judge_model, pass_number, temp, force
                        )
                        attempted_runs += 1

        await session.commit()
        return {
            "simulation_ids": [sim.id for sim in simulations],
            "judge_models": models,
            "pass_count": passes,
            "temperature": temp,
            "persona_targets": persona_targets,
            "attempted_runs": attempted_runs,
            "score_rows_written": total_rows,
        }


simulation_judge_service = SimulationJudgeService()

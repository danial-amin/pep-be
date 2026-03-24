"""
Agreement Evaluator Service

An LLM-powered agent that tracks whether simulation personas are converging
toward agreement or remaining in disagreement over time.

At each evaluation point (typically after every complete round) it:
  1. Infers each persona's *initial* stance on the topic from their profile
     (cached in Simulation.initial_persona_stances after the first call).
  2. Extracts each persona's *current* stance from their recent messages.
  3. Computes per-persona drift (how far they have moved from their starting
     position) and pairwise alignment across all personas.
  4. Persists a SimulationAgreementEvaluation snapshot so the front-end can
     render a time-series convergence chart.
"""
from __future__ import annotations

import json
import logging
from statistics import mean
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.persona import Persona
from app.models.simulation import (
    Simulation,
    SimulationAgreementEvaluation,
    SimulationMessage,
)

logger = logging.getLogger(__name__)

# How many of each persona's most-recent messages to use when extracting the
# current stance.  Keeping this small keeps the prompt focused and cheap.
_RECENT_MESSAGES_FOR_STANCE = 4


class AgreementEvaluatorService:
    """LLM-powered agreement evaluation agent for persona simulations."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    async def evaluate_agreement(
        self,
        simulation: Simulation,
        participants: Dict[int, Persona],
        session: AsyncSession,
        turn_number: int,
    ) -> SimulationAgreementEvaluation:
        """
        Run a full agreement evaluation snapshot after *turn_number* and persist it.

        Returns the newly created SimulationAgreementEvaluation ORM object.
        """
        # 1. Ensure initial stances are cached
        initial_stances = await self._ensure_initial_stances(
            simulation, participants, session
        )

        # 2. Extract current stances from messages
        messages = [
            m
            for m in simulation.messages
            if m.persona_id is not None and not getattr(m, "is_human_message", False)
        ]
        current_stances = await self._extract_current_stances(
            messages, participants, simulation.goal
        )

        # 3. Build per-persona analysis with drift and pairwise alignment
        persona_stances, alignment_matrix, reasoning = await self._build_persona_analysis(
            initial_stances, current_stances, participants, simulation.goal
        )

        # 4. Compute overall agreement score (mean of all pairwise scores)
        overall_score = _mean_pairwise(alignment_matrix)

        agreement_reached = overall_score >= simulation.agreement_threshold

        # 5. Persist
        evaluation = SimulationAgreementEvaluation(
            simulation_id=simulation.id,
            turn_number=turn_number,
            overall_agreement_score=round(overall_score, 4),
            agreement_reached=agreement_reached,
            persona_stances=persona_stances,
            evaluation_reasoning=reasoning,
        )
        session.add(evaluation)
        await session.commit()
        await session.refresh(evaluation)

        logger.info(
            "Agreement evaluation saved for simulation %d turn %d: score=%.3f reached=%s",
            simulation.id,
            turn_number,
            overall_score,
            agreement_reached,
        )
        return evaluation

    # ──────────────────────────────────────────────────────────────────────────
    # Initial stance inference
    # ──────────────────────────────────────────────────────────────────────────

    async def _ensure_initial_stances(
        self,
        simulation: Simulation,
        participants: Dict[int, Persona],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Return cached initial stances or infer them if not yet stored.

        Stances are stored as JSON in Simulation.initial_persona_stances keyed
        by str(persona_id) so they are consistent across the simulation's life.
        """
        if simulation.initial_persona_stances:
            return simulation.initial_persona_stances  # already a dict via JSON column

        stances: Dict[str, Any] = {}
        for pid, persona in participants.items():
            try:
                stance = await self._infer_initial_stance(persona, simulation.goal)
            except Exception as exc:
                logger.warning(
                    "Could not infer initial stance for persona %d: %s", pid, exc
                )
                stance = {
                    "stance_summary": "No initial stance available.",
                    "key_positions": [],
                }
            stances[str(pid)] = stance

        simulation.initial_persona_stances = stances
        await session.commit()
        return stances

    async def _infer_initial_stance(self, persona: Persona, goal: str) -> Dict[str, Any]:
        """
        Ask the LLM: given this persona's profile, what would their *initial*
        stance on *goal* be before any discussion has taken place?
        """
        pd = persona.persona_data or {}
        goals_list = pd.get("goals", [])
        frustrations_list = pd.get("frustrations", [])
        motivations_list = pd.get("motivations", [])
        background = pd.get("background", "")
        behaviors = pd.get("behaviors", "")

        prompt = f"""You are analysing a persona to predict their initial stance on a discussion topic
BEFORE any conversation has taken place.

PERSONA PROFILE
===============
Name: {persona.name}
Background: {background}
Goals: {', '.join(goals_list) if goals_list else 'Not specified'}
Frustrations: {', '.join(frustrations_list) if frustrations_list else 'Not specified'}
Motivations: {', '.join(motivations_list) if motivations_list else 'Not specified'}
Behavioural traits: {behaviors}

DISCUSSION TOPIC / GOAL
=======================
{goal}

Based solely on this persona's profile (not any actual conversation), predict their most
likely initial stance on the topic. Return ONLY valid JSON with this exact structure:
{{
  "stance_summary": "<2-3 sentence summary of their likely initial position>",
  "key_positions": ["<position 1>", "<position 2>", "<position 3>"]
}}"""

        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert social scientist skilled at predicting how "
                        "individuals with specific backgrounds will approach a topic."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=300,
        )
        return json.loads(response.choices[0].message.content)

    # ──────────────────────────────────────────────────────────────────────────
    # Current stance extraction
    # ──────────────────────────────────────────────────────────────────────────

    async def _extract_current_stances(
        self,
        messages: List[SimulationMessage],
        participants: Dict[int, Persona],
        goal: str,
    ) -> Dict[str, Any]:
        """
        For each persona, extract their current stance from their most recent
        _RECENT_MESSAGES_FOR_STANCE messages.
        """
        # Group messages per persona (most recent first)
        by_persona: Dict[int, List[str]] = {pid: [] for pid in participants}
        for msg in sorted(messages, key=lambda m: m.id):
            if msg.persona_id in by_persona:
                by_persona[msg.persona_id].append(msg.content)

        current: Dict[str, Any] = {}
        for pid, persona in participants.items():
            recent = by_persona.get(pid, [])[-_RECENT_MESSAGES_FOR_STANCE:]
            if not recent:
                current[str(pid)] = {
                    "stance_summary": "This persona has not spoken yet.",
                    "key_positions": [],
                }
                continue
            try:
                stance = await self._extract_stance_from_messages(
                    persona.name, recent, goal
                )
            except Exception as exc:
                logger.warning(
                    "Could not extract current stance for persona %d: %s", pid, exc
                )
                stance = {
                    "stance_summary": "Unable to extract stance.",
                    "key_positions": [],
                }
            current[str(pid)] = stance
        return current

    async def _extract_stance_from_messages(
        self, persona_name: str, messages: List[str], goal: str
    ) -> Dict[str, Any]:
        """Extract a structured stance from a persona's recent messages."""
        transcript = "\n".join([f"  - {m}" for m in messages])
        prompt = f"""Extract {persona_name}'s current stance on the discussion topic based on their recent messages.

DISCUSSION TOPIC: {goal}

{persona_name}'s RECENT MESSAGES:
{transcript}

Return ONLY valid JSON:
{{
  "stance_summary": "<2-3 sentence summary of their current position>",
  "key_positions": ["<position 1>", "<position 2>", "<position 3>"]
}}"""

        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured stance summaries from conversation fragments.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=250,
        )
        return json.loads(response.choices[0].message.content)

    # ──────────────────────────────────────────────────────────────────────────
    # Drift + pairwise alignment
    # ──────────────────────────────────────────────────────────────────────────

    async def _build_persona_analysis(
        self,
        initial_stances: Dict[str, Any],
        current_stances: Dict[str, Any],
        participants: Dict[int, Persona],
        goal: str,
    ) -> tuple[Dict[str, Any], Dict[str, Dict[str, float]], str]:
        """
        Returns:
          - persona_stances dict (keyed by str(persona_id)) ready for DB storage
          - alignment_matrix {str(pid_a): {str(pid_b): score}} for aggregate scoring
          - reasoning string
        """
        pids = [str(pid) for pid in participants]

        # Compute drift scores for each persona
        drift_tasks = []
        for pid_str in pids:
            init = initial_stances.get(pid_str, {})
            curr = current_stances.get(pid_str, {})
            drift_tasks.append(
                self._score_drift(
                    init.get("stance_summary", ""),
                    curr.get("stance_summary", ""),
                )
            )

        import asyncio
        drift_scores = await asyncio.gather(*drift_tasks, return_exceptions=True)

        # Compute pairwise alignment
        alignment_matrix: Dict[str, Dict[str, float]] = {p: {} for p in pids}
        pairs = [(pids[i], pids[j]) for i in range(len(pids)) for j in range(i + 1, len(pids))]

        async def _pair_score(pa: str, pb: str) -> float:
            curr_a = current_stances.get(pa, {}).get("stance_summary", "")
            curr_b = current_stances.get(pb, {}).get("stance_summary", "")
            try:
                return await self._score_alignment(curr_a, curr_b, goal)
            except Exception:
                return 0.5  # neutral fallback

        pair_scores = await asyncio.gather(*[_pair_score(a, b) for a, b in pairs])

        for (pa, pb), score in zip(pairs, pair_scores):
            alignment_matrix[pa][pb] = round(score, 4)
            alignment_matrix[pb][pa] = round(score, 4)

        # Assemble per-persona output
        persona_stances: Dict[str, Any] = {}
        reasoning_parts: List[str] = []

        for idx, pid_str in enumerate(pids):
            pid = int(pid_str)
            persona = participants[pid]
            init = initial_stances.get(pid_str, {})
            curr = current_stances.get(pid_str, {})

            drift_raw = drift_scores[idx]
            drift = float(drift_raw) if not isinstance(drift_raw, Exception) else 0.5

            persona_stances[pid_str] = {
                "persona_name": persona.name,
                "initial_stance": init.get("stance_summary", ""),
                "current_stance": curr.get("stance_summary", ""),
                "drift_score": round(drift, 4),
                "alignment_scores": alignment_matrix[pid_str],
            }

            avg_align = (
                mean(alignment_matrix[pid_str].values())
                if alignment_matrix[pid_str]
                else 0.5
            )
            reasoning_parts.append(
                f"{persona.name}: drift={drift:.2f}, avg_alignment={avg_align:.2f}"
            )

        reasoning = "Per-persona summary — " + " | ".join(reasoning_parts)
        return persona_stances, alignment_matrix, reasoning

    async def _score_drift(self, initial_stance: str, current_stance: str) -> float:
        """
        Return a drift score 0.0 (no change) – 1.0 (completely different).
        Uses the LLM to compare the two stance summaries semantically.
        """
        if not initial_stance or not current_stance:
            return 0.0

        prompt = f"""Compare these two stance descriptions and rate how much the person's position has CHANGED.

INITIAL STANCE: {initial_stance}

CURRENT STANCE: {current_stance}

Return ONLY valid JSON:
{{
  "drift_score": <float 0.0-1.0>,
  "explanation": "<one sentence>"
}}
Where 0.0 = identical stance, 1.0 = completely opposite/different stance."""

        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You measure semantic similarity between two position statements.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=100,
        )
        data = json.loads(response.choices[0].message.content)
        return float(data.get("drift_score", 0.0))

    async def _score_alignment(
        self, stance_a: str, stance_b: str, goal: str
    ) -> float:
        """
        Return an alignment score 0.0 (complete disagreement) – 1.0 (full agreement)
        between two personas' current stances on the same topic.
        """
        if not stance_a or not stance_b:
            return 0.5

        prompt = f"""Two people are discussing: "{goal}"

Person A's stance: {stance_a}

Person B's stance: {stance_b}

How aligned are these two positions on this topic?

Return ONLY valid JSON:
{{
  "alignment_score": <float 0.0-1.0>,
  "explanation": "<one sentence>"
}}
Where 0.0 = diametrically opposed, 0.5 = partially aligned, 1.0 = fully in agreement."""

        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You measure ideological alignment between two position statements.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=100,
        )
        data = json.loads(response.choices[0].message.content)
        return float(data.get("alignment_score", 0.5))


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _mean_pairwise(matrix: Dict[str, Dict[str, float]]) -> float:
    """Compute the mean of all unique pairwise scores in the alignment matrix."""
    scores: List[float] = []
    seen: set = set()
    for pid_a, row in matrix.items():
        for pid_b, score in row.items():
            key = tuple(sorted([pid_a, pid_b]))
            if key not in seen:
                scores.append(score)
                seen.add(key)
    return mean(scores) if scores else 0.5


# Global service instance
agreement_evaluator_service = AgreementEvaluatorService()

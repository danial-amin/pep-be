"""
Repeated-run stability analysis for user-study interaction modes.

SCI = single-persona chat (PersonaChat)
MPS = multi-persona simulation (Simulation)

Selects the longest and shortest observed persona responses per mode from real
study sessions, then reruns each fixed input N times (default 30) without
changing profiles, config, or participant questions/interventions.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import statistics
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.simulation import Simulation
from app.models.study import Study
from app.services.persona_chat_service import PersonaChatService, persona_chat_service
from app.services.persona_simulation_service import PersonaSimulationService, simulation_service
from app.services.study_knowledge_service import _classify_stance

logger = logging.getLogger(__name__)

REFUSAL_MARKERS = ("i don't know", "i do not know", "i'm not sure", "i am not sure")

# Exclude greeting-only exchanges from SCI shortest selection / stability reruns.
MIN_SCI_USER_INPUT_CHARS = 50
_SCI_GREETING_USER_INPUTS = frozenset({"hi", "hello", "hey", "hi!", "hello!", "hey!"})
_SCI_GREETING_RESPONSE_PREFIXES = (
    "hello",
    "hi,",
    "hi ",
    "hey,",
    "hey ",
    "good morning",
    "good afternoon",
    "good evening",
)


def _is_substantive_sci_exchange(row: Any) -> bool:
    """True when the exchange is policy-relevant (not a greeting opener)."""
    user = (row.get("user_input") or "").strip()
    resp = (row.get("content") or "").strip()
    if len(user) < MIN_SCI_USER_INPUT_CHARS:
        return False
    if user.lower() in _SCI_GREETING_USER_INPUTS:
        return False
    resp_lower = resp.lower()
    if len(resp) < 80 and any(resp_lower.startswith(p) for p in _SCI_GREETING_RESPONSE_PREFIXES):
        return False
    return True


@dataclass
class RoundCandidate:
    mode: str  # "sci" | "mps"
    label: str  # "longest" | "shortest"
    source_message_id: int
    participant_code: str
    persona_id: Optional[int]
    persona_name: Optional[str]
    response_length: int
    original_response: str
    user_input: Optional[str] = None
    session_id: Optional[int] = None
    simulation_id: Optional[int] = None
    turn_number: Optional[int] = None


@dataclass
class StabilityRun:
    iteration: int
    content: str
    refused: bool
    stance: str
    char_length: int


@dataclass
class StabilityResult:
    candidate: RoundCandidate
    runs: List[StabilityRun] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


def _is_refusal(text: str) -> bool:
    stripped = (text or "").strip().lower()
    return any(stripped.startswith(m) for m in REFUSAL_MARKERS)


def _stance_label(text: str) -> str:
    return _classify_stance(text or "")


def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode()).hexdigest()[:16]


async def _pairwise_cosine(embeddings: List[List[float]]) -> List[float]:
    if len(embeddings) < 2:
        return []
    arr = np.array(embeddings)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normed = arr / norms
    sim = np.dot(normed, normed.T)
    pairs = []
    n = sim.shape[0]
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append(float(sim[i, j]))
    return pairs


def compute_stability_metrics(runs: List[StabilityRun]) -> Dict[str, Any]:
    if not runs:
        return {}

    contents = [r.content for r in runs]
    refusals = [r.refused for r in runs]
    stances = [r.stance for r in runs]
    lengths = [r.char_length for r in runs]
    unique_hashes = {_content_hash(c) for c in contents}

    stance_counts: Dict[str, int] = {}
    for s in stances:
        stance_counts[s] = stance_counts.get(s, 0) + 1

    metrics: Dict[str, Any] = {
        "n_runs": len(runs),
        "refusal_rate": sum(refusals) / len(runs),
        "refusal_consistent": len(set(refusals)) == 1,
        "unique_response_count": len(unique_hashes),
        "unique_response_rate": len(unique_hashes) / len(runs),
        "stance_distribution": stance_counts,
        "dominant_stance": max(stance_counts, key=stance_counts.get),
        "stance_consistency": max(stance_counts.values()) / len(runs),
        "char_length_mean": statistics.mean(lengths),
        "char_length_stdev": statistics.pstdev(lengths) if len(lengths) > 1 else 0.0,
        "char_length_min": min(lengths),
        "char_length_max": max(lengths),
    }
    return metrics


async def enrich_with_embeddings(runs: List[StabilityRun], metrics: Dict[str, Any]) -> Dict[str, Any]:
    non_refusal = [r.content for r in runs if r.content.strip() and not r.refused]
    if len(non_refusal) < 2:
        metrics["embedding_pairwise_mean"] = None
        metrics["embedding_pairwise_min"] = None
        return metrics
    try:
        from app.core.llm_service import llm_service

        embeddings = await llm_service.create_embeddings(non_refusal)
        pairs = await _pairwise_cosine(embeddings)
        if pairs:
            metrics["embedding_pairwise_mean"] = float(np.mean(pairs))
            metrics["embedding_pairwise_min"] = float(np.min(pairs))
            metrics["embedding_pairwise_max"] = float(np.max(pairs))
    except Exception as e:
        logger.warning("Embedding stability metrics skipped: %s", e)
        metrics["embedding_error"] = str(e)
    return metrics


class StabilityAnalysisService:
    """Find study rounds and rerun them for generative stability analysis."""

    def __init__(
        self,
        chat_service: PersonaChatService = persona_chat_service,
        sim_service: PersonaSimulationService = simulation_service,
    ):
        self.chat_service = chat_service
        self.sim_service = sim_service

    async def find_sci_candidates(
        self,
        session: AsyncSession,
        study_slug: str = "policy-study",
    ) -> Tuple[Optional[RoundCandidate], Optional[RoundCandidate]]:
        """Longest and shortest assistant replies in study single-persona chats."""
        study = (
            await session.execute(select(Study).where(Study.slug == study_slug))
        ).scalar_one_or_none()
        if not study:
            return None, None

        rows = await session.execute(
            text("""
                SELECT
                    pcm.id AS msg_id,
                    pcm.session_id,
                    pcm.persona_id,
                    p.name AS persona_name,
                    pcm.content,
                    char_length(pcm.content) AS resp_len,
                    sp.code AS participant_code,
                    prev.content AS user_input
                FROM persona_chat_messages pcm
                JOIN persona_chat_sessions pcs ON pcs.id = pcm.session_id
                JOIN study_participants sp ON sp.user_id = pcs.user_id AND sp.study_id = :study_id
                LEFT JOIN personas p ON p.id = pcm.persona_id
                LEFT JOIN LATERAL (
                    SELECT content FROM persona_chat_messages u
                    WHERE u.session_id = pcm.session_id
                      AND u.role = 'user'
                      AND u.id < pcm.id
                    ORDER BY u.id DESC
                    LIMIT 1
                ) prev ON true
                WHERE pcm.role = 'assistant'
                  AND pcs.mode = 'single'
                  AND COALESCE(pcm.refused, false) = false
                ORDER BY resp_len DESC
            """),
            {"study_id": study.id},
        )
        all_rows = rows.mappings().all()
        if not all_rows:
            return None, None

        longest_row = all_rows[0]
        substantive_rows = [r for r in all_rows if _is_substantive_sci_exchange(r)]
        shortest_row = (
            min(substantive_rows, key=lambda r: r["resp_len"]) if substantive_rows else None
        )

        def _to_candidate(row, label: str) -> RoundCandidate:
            return RoundCandidate(
                mode="sci",
                label=label,
                source_message_id=row["msg_id"],
                participant_code=row["participant_code"],
                persona_id=row["persona_id"],
                persona_name=row["persona_name"],
                response_length=row["resp_len"],
                original_response=row["content"],
                user_input=row["user_input"],
                session_id=row["session_id"],
            )

        longest = _to_candidate(longest_row, "longest")
        shortest = _to_candidate(shortest_row, "shortest") if shortest_row else None
        return longest, shortest

    async def find_mps_candidates(
        self,
        session: AsyncSession,
        study_slug: str = "policy-study",
    ) -> Tuple[Optional[RoundCandidate], Optional[RoundCandidate]]:
        """Longest and shortest persona turns in study-linked simulations."""
        study = (
            await session.execute(select(Study).where(Study.slug == study_slug))
        ).scalar_one_or_none()
        if not study:
            return None, None

        rows = await session.execute(
            text("""
                WITH participant_sims AS (
                    SELECT DISTINCT
                        sp.code AS participant_code,
                        (se.payload->>'simulation_id')::int AS simulation_id
                    FROM study_events se
                    JOIN study_participants sp ON sp.id = se.participant_id
                    WHERE se.study_id = :study_id
                      AND se.event_type = 'simulation_create'
                      AND se.payload->>'simulation_id' IS NOT NULL
                )
                SELECT
                    sm.id AS msg_id,
                    sm.simulation_id,
                    sm.persona_id,
                    p.name AS persona_name,
                    sm.content,
                    char_length(sm.content) AS resp_len,
                    sm.turn_number,
                    ps.participant_code,
                    prev.content AS prior_context
                FROM simulation_messages sm
                JOIN participant_sims ps ON ps.simulation_id = sm.simulation_id
                LEFT JOIN personas p ON p.id = sm.persona_id
                LEFT JOIN LATERAL (
                    SELECT content FROM simulation_messages x
                    WHERE x.simulation_id = sm.simulation_id
                      AND x.id < sm.id
                      AND (x.is_human_message OR x.persona_id IS NOT NULL)
                    ORDER BY x.id DESC
                    LIMIT 1
                ) prev ON true
                WHERE sm.persona_id IS NOT NULL
                  AND COALESCE(sm.is_human_message, false) = false
                ORDER BY resp_len DESC
            """),
            {"study_id": study.id},
        )
        all_rows = rows.mappings().all()
        if not all_rows:
            return None, None

        longest_row = all_rows[0]
        shortest_row = min(all_rows, key=lambda r: r["resp_len"])

        def _to_candidate(row, label: str) -> RoundCandidate:
            return RoundCandidate(
                mode="mps",
                label=label,
                source_message_id=row["msg_id"],
                participant_code=row["participant_code"],
                persona_id=row["persona_id"],
                persona_name=row["persona_name"],
                response_length=row["resp_len"],
                original_response=row["content"],
                user_input=row.get("prior_context"),
                simulation_id=row["simulation_id"],
                turn_number=row["turn_number"],
            )

        return _to_candidate(longest_row, "longest"), _to_candidate(shortest_row, "shortest")

    async def rerun_sci(
        self,
        session: AsyncSession,
        candidate: RoundCandidate,
        iterations: int = 30,
        strict_mode: bool = True,
    ) -> StabilityResult:
        if not candidate.session_id:
            raise ValueError("SCI candidate missing session_id")

        chat_session = await self.chat_service.get_session(session, candidate.session_id)
        if not chat_session or not chat_session.persona:
            raise ValueError(f"Chat session {candidate.session_id} not found")

        # Messages strictly before the original assistant reply
        prefix = [
            m for m in sorted(chat_session.messages, key=lambda x: x.id or 0)
            if m.id < candidate.source_message_id
        ]
        user_msg = next((m for m in reversed(prefix) if m.role == "user"), None)
        if not user_msg:
            raise ValueError("No user message found before assistant reply")

        # Ephemeral session view for dry-run generation
        chat_session.messages = prefix
        persona = chat_session.persona
        project_id = chat_session.project_id

        runs: List[StabilityRun] = []
        for i in range(iterations):
            result = await self.chat_service._generate_reply_for_persona(
                session,
                persona,
                user_msg.content,
                chat_session,
                user_msg,
                project_id,
                strict_mode,
                persist=False,
            )
            content = result.get("reply") or ""
            refused = bool(result.get("refused")) or _is_refusal(content)
            runs.append(
                StabilityRun(
                    iteration=i + 1,
                    content=content,
                    refused=refused,
                    stance=_stance_label(content),
                    char_length=len(content),
                )
            )
            if (i + 1) % 5 == 0:
                logger.info("SCI %s rerun %d/%d", candidate.label, i + 1, iterations)

        metrics = compute_stability_metrics(runs)
        metrics = await enrich_with_embeddings(runs, metrics)
        return StabilityResult(candidate=candidate, runs=runs, metrics=metrics)

    async def rerun_mps(
        self,
        session: AsyncSession,
        candidate: RoundCandidate,
        iterations: int = 30,
    ) -> StabilityResult:
        if not candidate.simulation_id or not candidate.persona_id:
            raise ValueError("MPS candidate missing simulation_id or persona_id")

        result = await session.execute(
            select(Simulation)
            .options(
                selectinload(Simulation.participants),
                selectinload(Simulation.messages),
            )
            .where(Simulation.id == candidate.simulation_id)
        )
        simulation = result.scalar_one_or_none()
        if not simulation:
            raise ValueError(f"Simulation {candidate.simulation_id} not found")

        prefix = [
            m for m in self.sim_service._chronological_messages(list(simulation.messages))
            if m.id < candidate.source_message_id
        ]

        runs: List[StabilityRun] = []
        for i in range(iterations):
            content = await self.sim_service.generate_turn_from_state(
                session,
                simulation,
                prefix,
                candidate.persona_id,
            )
            refused = _is_refusal(content)
            runs.append(
                StabilityRun(
                    iteration=i + 1,
                    content=content,
                    refused=refused,
                    stance=_stance_label(content),
                    char_length=len(content),
                )
            )
            if (i + 1) % 5 == 0:
                logger.info("MPS %s rerun %d/%d", candidate.label, i + 1, iterations)

        metrics = compute_stability_metrics(runs)
        metrics = await enrich_with_embeddings(runs, metrics)
        return StabilityResult(candidate=candidate, runs=runs, metrics=metrics)

    async def run_full_analysis(
        self,
        session: AsyncSession,
        study_slug: str = "policy-study",
        iterations: int = 30,
        strict_mode: bool = True,
        include_sci_shortest: bool = False,
    ) -> Dict[str, Any]:
        sci_long, sci_short = await self.find_sci_candidates(session, study_slug)
        mps_long, mps_short = await self.find_mps_candidates(session, study_slug)

        results: Dict[str, Any] = {
            "study_slug": study_slug,
            "iterations": iterations,
            "candidates": {},
            "analyses": {},
        }

        for key, cand in [
            ("sci_longest", sci_long),
            ("sci_shortest", sci_short),
            ("mps_longest", mps_long),
            ("mps_shortest", mps_short),
        ]:
            if cand:
                results["candidates"][key] = asdict(cand)

        tasks = []
        task_keys = []
        if sci_long:
            tasks.append(self.rerun_sci(session, sci_long, iterations, strict_mode))
            task_keys.append("sci_longest")
        if sci_short and include_sci_shortest:
            tasks.append(self.rerun_sci(session, sci_short, iterations, strict_mode))
            task_keys.append("sci_shortest")
        if mps_long:
            tasks.append(self.rerun_mps(session, mps_long, iterations))
            task_keys.append("mps_longest")
        if mps_short:
            tasks.append(self.rerun_mps(session, mps_short, iterations))
            task_keys.append("mps_shortest")

        if tasks:
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            for key, item in zip(task_keys, completed):
                if isinstance(item, Exception):
                    results["analyses"][key] = {"error": str(item)}
                    logger.error("%s failed: %s", key, item)
                else:
                    results["analyses"][key] = {
                        "candidate": asdict(item.candidate),
                        "metrics": item.metrics,
                        "runs": [asdict(r) for r in item.runs],
                    }

        return results


stability_analysis_service = StabilityAnalysisService()

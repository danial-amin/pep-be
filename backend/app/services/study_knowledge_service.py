"""
Assembles project- and persona-set-level study knowledge for persona chat.

Provides aggregate facts (participant stances, document themes, analytics,
simulation outcomes) that a single persona profile cannot answer alone.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any, Optional
import json
import logging
import re

from app.models.persona import Persona, PersonaSet
from app.models.project import Project
from app.models.document import Document, DocumentType, ProcessingStatus
from app.models.simulation import Simulation, SimulationAgreementEvaluation

logger = logging.getLogger(__name__)

_MAX_DOC_CHARS = 2000
_MAX_STUDY_KNOWLEDGE_CHARS = 8000


def _classify_stance(text: str) -> str:
    if not text:
        return "unspecified"
    lower = text.lower()
    if any(k in lower for k in ("restrict", "redirection", "must not", "prohibited", "not permit")):
        return "restrict"
    if any(k in lower for k in ("permit", "direct answer", "full answer", "should be allowed", "provide direct")):
        return "permit"
    if any(k in lower for k in ("regulate", "pilot", "guided", "disclosure", "transparency")):
        return "regulate"
    return "other"


def _persona_stance_text(persona_data: Dict[str, Any]) -> str:
    for key in ("starting_position", "tagline", "background"):
        val = persona_data.get(key)
        if isinstance(val, str) and val.strip():
            return val
    goals = persona_data.get("goals")
    if isinstance(goals, list) and goals:
        return str(goals[0])
    return ""


def _format_analytics_snapshot(persona_set: PersonaSet) -> List[str]:
    lines: List[str] = []

    if persona_set.diversity_score and isinstance(persona_set.diversity_score, dict):
        d = persona_set.diversity_score
        lines.append(
            "Diversity metrics: "
            f"RQE={d.get('rqe_score', 'n/a')}, "
            f"avg similarity={d.get('average_similarity', 'n/a')}, "
            f"num personas={d.get('num_personas', 'n/a')}"
        )

    if persona_set.validation_scores and isinstance(persona_set.validation_scores, dict):
        v = persona_set.validation_scores
        lines.append(
            "Validation: "
            f"overall average similarity={v.get('overall_average', 'n/a')}, "
            f"validated personas={v.get('validated_count', 'n/a')}"
        )
        results = v.get("validation_results")
        if isinstance(results, list):
            for r in results[:8]:
                if isinstance(r, dict):
                    lines.append(
                        f"  - {r.get('persona_name', '?')}: "
                        f"similarity={r.get('average_similarity', 'n/a')}, "
                        f"status={r.get('validation_status', 'n/a')}"
                    )

    if persona_set.evaluation_scores and isinstance(persona_set.evaluation_scores, dict):
        summary = persona_set.evaluation_scores.get("summary")
        if isinstance(summary, dict):
            cov = summary.get("coverage_details") or {}
            topics = cov.get("sample_topics_covered")
            topic_str = ", ".join(topics[:8]) if isinstance(topics, list) else "n/a"
            lines.append(
                "Evaluation summary: "
                f"groundedness={summary.get('overall_groundedness', 'n/a')}, "
                f"topic coverage={summary.get('topic_coverage', 'n/a')}, "
                f"topics covered={topic_str}"
            )

    gen = persona_set.generation_config
    if isinstance(gen, dict):
        for key in ("interview_topic", "user_study_design", "context_details"):
            if gen.get(key):
                lines.append(f"Study design ({key}): {gen[key]}")

    return lines


class StudyKnowledgeService:
    """Build a bounded text digest of study-level facts for persona chat."""

    @staticmethod
    async def build_study_knowledge(
        db: AsyncSession,
        persona: Persona,
        project_id: Optional[int],
    ) -> str:
        sections: List[str] = []
        persona_set = persona.persona_set

        if persona_set:
            result = await db.execute(
                select(PersonaSet)
                .where(PersonaSet.id == persona_set.id)
                .options(selectinload(PersonaSet.personas))
            )
            loaded_set = result.scalar_one_or_none()
            if loaded_set:
                sections.append(StudyKnowledgeService._build_roster_section(loaded_set))
                analytics = _format_analytics_snapshot(loaded_set)
                if analytics:
                    sections.append("ANALYTICS & VALIDATION:\n" + "\n".join(analytics))

        doc_section = await StudyKnowledgeService._build_documents_section(db, project_id)
        if doc_section:
            sections.append(doc_section)

        sim_section = await StudyKnowledgeService._build_simulation_section(db, project_id)
        if sim_section:
            sections.append(sim_section)

        digest = "\n\n".join(s for s in sections if s.strip())
        if len(digest) > _MAX_STUDY_KNOWLEDGE_CHARS:
            digest = digest[:_MAX_STUDY_KNOWLEDGE_CHARS] + "\n...(truncated)"
        return digest

    @staticmethod
    def _build_roster_section(persona_set: PersonaSet) -> str:
        personas = persona_set.personas or []
        if not personas:
            return ""

        lines = [f"STUDY PARTICIPANTS ({len(personas)} personas in set '{persona_set.name}'):"]
        stance_counts: Dict[str, int] = {}
        occupations: Dict[str, int] = {}

        for p in personas:
            data = p.persona_data or {}
            demo = data.get("demographics") or {}
            occupation = demo.get("occupation") if isinstance(demo, dict) else None
            if occupation:
                occupations[str(occupation)] = occupations.get(str(occupation), 0) + 1

            stance_src = _persona_stance_text(data)
            stance = _classify_stance(stance_src)
            stance_counts[stance] = stance_counts.get(stance, 0) + 1

            pos_preview = stance_src[:120] + ("..." if len(stance_src) > 120 else "")
            lines.append(f"  - {p.name} ({occupation or 'role n/a'}): {pos_preview}")

        if stance_counts:
            parts = [f"{k}={v}" for k, v in sorted(stance_counts.items()) if k != "unspecified"]
            unspecified = stance_counts.get("unspecified", 0)
            if parts:
                lines.append(f"Aggregate stance distribution: {', '.join(parts)}")
            if unspecified:
                lines.append(f"Participants without explicit policy stance: {unspecified}")

        if occupations:
            occ_parts = [f"{k} ({v})" for k, v in sorted(occupations.items(), key=lambda x: -x[1])[:6]]
            lines.append(f"Occupation breakdown: {', '.join(occ_parts)}")

        return "\n".join(lines)

    @staticmethod
    async def _build_documents_section(
        db: AsyncSession,
        project_id: Optional[int],
    ) -> str:
        query = select(Document).where(Document.processing_status == ProcessingStatus.COMPLETED)
        if project_id is not None:
            query = query.where(Document.project_id == project_id)
        else:
            query = query.where(Document.project_id.is_(None))

        result = await db.execute(query.order_by(Document.document_type, Document.id))
        documents = list(result.scalars().all())

        if not documents and project_id is not None:
            result = await db.execute(
                select(Document)
                .where(Document.processing_status == ProcessingStatus.COMPLETED)
                .order_by(Document.document_type, Document.id)
            )
            documents = list(result.scalars().all())

        if not documents:
            return ""

        lines = ["STUDY DOCUMENTS & RESEARCH MATERIAL:"]
        total = 0
        for doc in documents:
            body = (doc.processed_content or doc.content or "").strip()
            if not body:
                continue
            excerpt = body[:_MAX_DOC_CHARS]
            if len(body) > _MAX_DOC_CHARS:
                excerpt += "..."
            lines.append(f"[{doc.document_type.value}: {doc.filename}]")
            lines.append(excerpt)
            total += len(excerpt)
            if total >= _MAX_STUDY_KNOWLEDGE_CHARS // 2:
                lines.append("...(additional documents truncated)")
                break

        themes = StudyKnowledgeService._extract_key_themes("\n".join(lines))
        if themes:
            lines.append("Key themes extracted from documents:")
            lines.extend(f"  - {t}" for t in themes)

        return "\n".join(lines)

    @staticmethod
    def _extract_key_themes(text: str) -> List[str]:
        themes: List[str] = []
        for match in re.finditer(r"(?:key themes?|main themes?|themes? from)[:\s]+(.+?)(?:\n\n|\n#|$)", text, re.I | re.S):
            block = match.group(1)
            for line in block.split("\n"):
                line = re.sub(r"^[\s\-*•]+", "", line).strip()
                if line and len(line) > 10:
                    themes.append(line[:200])
        return themes[:10]

    @staticmethod
    async def _build_simulation_section(
        db: AsyncSession,
        project_id: Optional[int],
    ) -> str:
        if project_id is None:
            return ""

        result = await db.execute(
            select(Simulation)
            .where(Simulation.project_id == project_id)
            .where(Simulation.status.in_(["completed", "stopped"]))
            .order_by(desc(Simulation.id))
            .limit(2)
        )
        simulations = list(result.scalars().all())
        if not simulations:
            return ""

        lines = ["SIMULATION OUTCOMES (multi-persona discussions):"]
        for sim in simulations:
            lines.append(f"Simulation '{sim.name}' (goal: {(sim.goal or '')[:200]})")
            if sim.summary:
                summary = sim.summary
                if isinstance(summary, str) and summary.startswith("{"):
                    try:
                        summary = json.dumps(json.loads(summary), indent=0)[:800]
                    except json.JSONDecodeError:
                        summary = summary[:800]
                else:
                    summary = str(summary)[:800]
                lines.append(f"Summary: {summary}")
            if sim.key_insights:
                insights = sim.key_insights
                if isinstance(insights, list):
                    lines.append("Unresolved disagreements / key insights:")
                    for item in insights[:5]:
                        lines.append(f"  - {str(item)[:200]}")
            if sim.action_items and isinstance(sim.action_items, list):
                lines.append("Action items:")
                for item in sim.action_items[:3]:
                    lines.append(f"  - {str(item)[:200]}")

            ev_result = await db.execute(
                select(SimulationAgreementEvaluation)
                .where(SimulationAgreementEvaluation.simulation_id == sim.id)
                .order_by(desc(SimulationAgreementEvaluation.turn_number))
                .limit(1)
            )
            latest_ev = ev_result.scalar_one_or_none()
            if latest_ev:
                lines.append(
                    f"Latest agreement score: {latest_ev.overall_agreement_score:.2f} "
                    f"(reached={latest_ev.agreement_reached}) at turn {latest_ev.turn_number}"
                )
                if latest_ev.persona_stances and isinstance(latest_ev.persona_stances, dict):
                    alignments = []
                    for pid, data in latest_ev.persona_stances.items():
                        if isinstance(data, dict):
                            name = data.get("persona_name", pid)
                            scores = data.get("alignment_scores") or {}
                            if scores:
                                avg_align = sum(scores.values()) / len(scores)
                                alignments.append(f"{name}: avg alignment {avg_align:.2f}")
                    if alignments:
                        lines.append("Persona alignment in simulation: " + "; ".join(alignments[:5]))

        return "\n".join(lines)


study_knowledge_service = StudyKnowledgeService()

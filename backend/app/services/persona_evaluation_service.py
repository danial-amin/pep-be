"""
Persona Evaluation Service — Beyond Cosine Similarity.

Implements the comprehensive evaluation plan from EVALUATION_PLAN.md:
- Groundedness (claim extraction + LLM-as-judge entailment)
- Coverage (topic overlap between personas and source)
- Diversity (demographic, attitudinal, beyond RQE)
- Internal coherence (LLM-as-judge)
- Realism (LLM-as-judge)
- Fairness (LLM-as-judge)
- Simulation adherence (LLM-as-judge)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any, Optional
import logging
import math
import json
from datetime import datetime, timezone

from app.models.persona import PersonaSet, Persona
from app.models.document import Document, DocumentType
from app.models.simulation import Simulation, SimulationMessage, SimulationParticipant
from app.core.llm_service import llm_service
from app.core.vector_db import vector_db
from app.core.config import settings
from app.core.openai_compat import chat_completion_kwargs
from app.utils.rag_filter import get_project_document_filter

logger = logging.getLogger(__name__)

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("scikit-learn not available. Some evaluation features will be limited.")


# Attributes to evaluate for groundedness
EVALUABLE_ATTRIBUTES = [
    "background",
    "goals",
    "frustrations",
    "motivations",
    "behaviors",
    "quote",
    "quotes",
]


class PersonaEvaluationService:
    """Service for comprehensive persona evaluation beyond cosine similarity."""

    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def _llm_judge(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[dict] = None,
        temperature: float = 0.2
    ) -> str:
        """Call LLM for judgment/scoring."""
        kwargs = chat_completion_kwargs(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
        )
        if response_format:
            kwargs["response_format"] = response_format
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def _extract_claims(self, text: str) -> List[str]:
        """Extract atomic claims from text using LLM."""
        if not text or not str(text).strip():
            return []
        text = str(text).strip()
        if len(text) < 20:
            return [text] if text else []
        try:
            content = await self._llm_judge(
                system_prompt="You extract atomic, verifiable claims from text. Each claim should be a single factual statement that can be checked against source material. Return a JSON object with key 'claims' containing a list of strings.",
                user_prompt=f"Extract 2-5 atomic claims from this text:\n\n{text[:1500]}",
                response_format={"type": "json_object"}
            )
            data = json.loads(content)
            claims = data.get("claims", [])
            return [c for c in claims if isinstance(c, str) and len(c.strip()) > 5][:5]
        except Exception as e:
            logger.warning(f"Claim extraction failed: {e}")
            return [text[:200]]

    async def _check_entailment(self, claim: str, source_chunks: List[str]) -> float:
        """Check if claim is entailed by source using LLM-as-judge. Returns 0-1 score."""
        if not source_chunks:
            return 0.0
        source_text = "\n\n---\n\n".join(source_chunks[:5])
        try:
            content = await self._llm_judge(
                system_prompt="You determine if a claim is supported (entailed) by the given source text. Respond with a JSON object: {\"supported\": true/false, \"confidence\": 0.0-1.0}. Supported means the source text provides evidence for the claim. Confidence reflects how strongly the source supports the claim.",
                user_prompt=f"Claim: {claim[:500]}\n\nSource text:\n{source_text[:2000]}",
                response_format={"type": "json_object"}
            )
            data = json.loads(content)
            supported = data.get("supported", False)
            confidence = float(data.get("confidence", 0.0))
            return confidence if supported else 0.0
        except Exception as e:
            logger.warning(f"Entailment check failed: {e}")
            return 0.0

    async def _get_source_chunks_for_claim(
        self,
        session: AsyncSession,
        claim: str,
        project_id: Optional[int],
        n_results: int = 5
    ) -> List[str]:
        """Retrieve relevant source chunks for a claim. Uses document_id filter for project scope."""
        filter_metadata = await get_project_document_filter(session, project_id, "interview")
        try:
            result = await vector_db.query_documents(
                query_texts=[claim],
                n_results=n_results,
                filter_metadata=filter_metadata,
                use_reranking=False
            )
            docs = result.get("documents", [[]])
            return docs[0] if docs and docs[0] else []
        except Exception as e:
            logger.warning(f"Source retrieval failed: {e}")
            return []

    async def evaluate_groundedness(
        self,
        session: AsyncSession,
        persona: Persona,
        project_id: Optional[int],
        max_claims_per_attr: int = 3
    ) -> Dict[str, Any]:
        """Evaluate groundedness: claim extraction + entailment check."""
        persona_data = persona.persona_data or {}
        attribute_scores = {}
        all_claims = []
        all_entailment_scores = []

        for attr in EVALUABLE_ATTRIBUTES:
            val = persona_data.get(attr)
            if not val:
                continue
            text = " ".join(str(x) for x in val) if isinstance(val, list) else str(val)
            if not text.strip():
                continue

            claims = await self._extract_claims(text)
            claims = claims[:max_claims_per_attr]
            if not claims:
                continue

            entailment_scores = []
            for claim in claims:
                chunks = await self._get_source_chunks_for_claim(session, claim, project_id)
                score = await self._check_entailment(claim, chunks)
                entailment_scores.append(score)
                all_claims.append(claim)
                all_entailment_scores.append(score)

            attr_score = sum(entailment_scores) / len(entailment_scores) if entailment_scores else 0.0
            attribute_scores[attr] = {
                "claims_checked": len(claims),
                "entailed_ratio": round(attr_score, 3),
                "per_claim_scores": [round(s, 3) for s in entailment_scores]
            }

        groundedness = sum(all_entailment_scores) / len(all_entailment_scores) if all_entailment_scores else 0.0
        return {
            "groundedness": round(groundedness, 3),
            "total_claims_checked": len(all_claims),
            "attribute_details": attribute_scores
        }

    def _extract_topics_tfidf(self, texts: List[str], max_features: int = 50) -> set:
        """Extract top keywords as topics using TF-IDF."""
        if not HAS_SKLEARN or not texts:
            return set()
        try:
            vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english")
            matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
            # Get top terms across all docs
            sums = matrix.sum(axis=0).A1
            top_indices = sums.argsort()[-max_features:][::-1]
            return {feature_names[i] for i in top_indices if sums[i] > 0}
        except Exception as e:
            logger.warning(f"TF-IDF topic extraction failed: {e}")
            return set()

    async def evaluate_coverage(
        self,
        session: AsyncSession,
        persona_set: PersonaSet,
        source_texts: List[str]
    ) -> Dict[str, Any]:
        """Evaluate topic coverage: overlap between persona topics and source topics."""
        if not source_texts:
            return {"topic_coverage": 0.0, "source_topics_count": 0, "persona_topics_count": 0}

        persona_texts = []
        for p in persona_set.personas:
            pd = p.persona_data or {}
            parts = [
                pd.get("background", ""),
                " ".join(pd.get("goals", []) or []),
                " ".join(pd.get("frustrations", []) or []),
                " ".join(pd.get("motivations", []) or []),
            ]
            persona_texts.append(" ".join(str(x) for x in parts))

        source_topics = self._extract_topics_tfidf(source_texts)
        persona_topics = self._extract_topics_tfidf(persona_texts)

        if not source_topics:
            return {"topic_coverage": 0.0, "source_topics_count": 0, "persona_topics_count": len(persona_topics)}

        overlap = source_topics & persona_topics
        coverage = len(overlap) / len(source_topics)
        return {
            "topic_coverage": round(coverage, 3),
            "source_topics_count": len(source_topics),
            "persona_topics_count": len(persona_topics),
            "overlap_count": len(overlap),
            "sample_topics_covered": list(overlap)[:10]
        }

    def _compute_entropy(self, values: List[str]) -> float:
        """Compute categorical entropy."""
        if not values:
            return 0.0
        from collections import Counter
        counts = Counter(str(v).lower().strip() for v in values if v)
        n = sum(counts.values())
        if n == 0:
            return 0.0
        return -sum((c / n) * math.log2(c / n) for c in counts.values())

    def evaluate_demographic_diversity(self, persona_set: PersonaSet) -> Dict[str, Any]:
        """Evaluate demographic diversity (entropy across dimensions)."""
        personas = persona_set.personas or []
        if len(personas) < 2:
            return {"demographic_diversity": 0.0, "dimensions": {}}

        occupations = []
        locations = []
        age_groups = []
        genders = []

        for p in personas:
            dem = (p.persona_data or {}).get("demographics") or {}
            if dem.get("occupation"):
                occupations.append(str(dem["occupation"]))
            if dem.get("location"):
                loc = dem["location"]
                locations.append(str(loc) if isinstance(loc, str) else f"{loc.get('city','')} {loc.get('country','')}")
            if dem.get("age"):
                age = dem["age"]
                age_groups.append("young" if age < 30 else "mid" if age < 50 else "older")
            if dem.get("gender"):
                genders.append(str(dem["gender"]))

        dims = {}
        if occupations:
            dims["occupation"] = round(self._compute_entropy(occupations) / max(math.log2(len(set(occupations)) or 1), 0.01), 3)
        if locations:
            dims["location"] = round(self._compute_entropy(locations) / max(math.log2(len(set(locations)) or 1), 0.01), 3)
        if age_groups:
            dims["age"] = round(self._compute_entropy(age_groups) / max(math.log2(len(set(age_groups)) or 1), 0.01), 3)
        if genders:
            dims["gender"] = round(self._compute_entropy(genders) / max(math.log2(len(set(genders)) or 1), 0.01), 3)

        avg = sum(dims.values()) / len(dims) if dims else 0.0
        return {
            "demographic_diversity": round(avg, 3),
            "dimensions": dims
        }

    async def evaluate_attitudinal_diversity(
        self,
        persona_set: PersonaSet
    ) -> Dict[str, Any]:
        """Evaluate attitudinal diversity (goals + frustrations spread)."""
        personas = persona_set.personas or []
        if len(personas) < 2:
            return {"attitudinal_diversity": 0.0}

        texts = []
        for p in personas:
            pd = p.persona_data or {}
            g = " ".join(pd.get("goals", []) or [])
            f = " ".join(pd.get("frustrations", []) or [])
            texts.append(f"{g} {f}".strip() or p.name)

        if not any(t.strip() for t in texts):
            return {"attitudinal_diversity": 0.0}

        try:
            embeddings = await llm_service.create_embeddings(texts)
            if HAS_SKLEARN:
                sim = cosine_similarity(embeddings)
                mask = ~np.eye(len(sim), dtype=bool)
                pairwise = sim[mask]
                avg_sim = float(np.mean(pairwise))
                diversity = 1 - avg_sim
                return {"attitudinal_diversity": round(diversity, 3)}
        except Exception as e:
            logger.warning(f"Attitudinal diversity failed: {e}")
        return {"attitudinal_diversity": 0.0}

    async def evaluate_coherence(self, persona: Persona) -> Dict[str, Any]:
        """Evaluate internal coherence using LLM-as-judge."""
        pd = persona.persona_data or {}
        dem = pd.get("demographics") or {}
        background = pd.get("background", "")
        goals = pd.get("goals", []) or []
        frustrations = pd.get("frustrations", []) or []

        summary = f"""
Persona: {persona.name}
Demographics: {dem}
Background: {background}
Goals: {goals}
Frustrations: {frustrations}
"""
        try:
            content = await self._llm_judge(
                system_prompt="You rate persona internal consistency. Consider: Do goals align with frustrations? Is background consistent with demographics? Any contradictions? Respond with JSON: {\"score\": 1-5, \"reasoning\": \"brief explanation\"}. 1=contradictory, 5=fully coherent.",
                user_prompt=f"Rate this persona's internal coherence:\n{summary[:2000]}",
                response_format={"type": "json_object"}
            )
            data = json.loads(content)
            score = int(data.get("score", 3))
            score = max(1, min(5, score))
            return {"coherence": score, "reasoning": data.get("reasoning", "")}
        except Exception as e:
            logger.warning(f"Coherence evaluation failed: {e}")
            return {"coherence": 3, "reasoning": "Evaluation failed"}

    async def evaluate_realism(self, persona: Persona) -> Dict[str, Any]:
        """Evaluate realism/plausibility using LLM-as-judge."""
        pd = persona.persona_data or {}
        summary = str(pd)[:1500]
        try:
            content = await self._llm_judge(
                system_prompt="You rate how plausible this persona is as a real person. Consider demographics, goals, frustrations, background. Respond with JSON: {\"score\": 1-5, \"reasoning\": \"brief\"}. 1=implausible, 5=very plausible.",
                user_prompt=f"Rate this persona's realism:\n{summary}",
                response_format={"type": "json_object"}
            )
            data = json.loads(content)
            score = int(data.get("score", 3))
            score = max(1, min(5, score))
            return {"realism": score, "reasoning": data.get("reasoning", "")}
        except Exception as e:
            logger.warning(f"Realism evaluation failed: {e}")
            return {"realism": 3, "reasoning": "Evaluation failed"}

    async def evaluate_fairness(self, persona: Persona) -> Dict[str, Any]:
        """Evaluate fairness: stereotype check using LLM-as-judge."""
        pd = persona.persona_data or {}
        summary = str(pd)[:1500]
        try:
            content = await self._llm_judge(
                system_prompt="Does this persona rely on harmful stereotypes (e.g., gender-occupation, age-ability)? Respond with JSON: {\"flagged\": true/false, \"reasoning\": \"brief\"}. Flag only if there are concerning stereotypes.",
                user_prompt=f"Check this persona for stereotypes:\n{summary}",
                response_format={"type": "json_object"}
            )
            data = json.loads(content)
            flagged = bool(data.get("flagged", False))
            return {"fairness_flag": flagged, "reasoning": data.get("reasoning", "")}
        except Exception as e:
            logger.warning(f"Fairness evaluation failed: {e}")
            return {"fairness_flag": False, "reasoning": "Evaluation failed"}

    async def evaluate_simulation_adherence(
        self,
        session: AsyncSession,
        simulation_id: int,
        sample_size: int = 5
    ) -> Dict[str, Any]:
        """Evaluate how well simulation messages adhere to personas."""
        result = await session.execute(
            select(Simulation)
            .options(
                selectinload(Simulation.messages),
                selectinload(Simulation.participants).selectinload(SimulationParticipant.persona)
            )
            .where(Simulation.id == simulation_id)
        )
        sim = result.scalar_one_or_none()
        if not sim or not sim.messages:
            return {"mean_adherence": 0.0, "messages_evaluated": 0}

        persona_messages = [m for m in sim.messages if m.persona_id and not m.is_human_message]
        if not persona_messages:
            return {"mean_adherence": 0.0, "messages_evaluated": 0}

        # Sample messages
        step = max(1, len(persona_messages) // sample_size)
        sampled = persona_messages[::step][:sample_size]

        persona_map = {p.persona_id: p for p in sim.participants if p.persona}
        scores = []
        for msg in sampled:
            persona = persona_map.get(msg.persona_id) and persona_map[msg.persona_id].persona
            if not persona:
                continue
            pd = (persona.persona_data or {})
            attr_summary = f"Background: {pd.get('background','')[:300]}. Goals: {pd.get('goals',[])}. Frustrations: {pd.get('frustrations',[])}"
            try:
                content = await self._llm_judge(
                    system_prompt="Rate how well a response fits a persona. 1=completely off-character, 5=perfectly in character. Respond with JSON: {\"score\": 1-5}.",
                    user_prompt=f"Persona attributes:\n{attr_summary}\n\nResponse: {msg.content[:500]}\n\nScore:",
                    response_format={"type": "json_object"}
                )
                data = json.loads(content)
                s = int(data.get("score", 3))
                scores.append(max(1, min(5, s)))
            except Exception as e:
                logger.warning(f"Adherence check failed: {e}")

        mean_adherence = sum(scores) / len(scores) if scores else 0.0
        return {
            "mean_adherence": round(mean_adherence, 2),
            "messages_evaluated": len(scores),
            "sample_size": len(sampled)
        }

    async def evaluate_persona_set(
        self,
        session: AsyncSession,
        persona_set_id: int,
        include_groundedness: bool = True,
        include_coverage: bool = True,
        include_diversity_extended: bool = True,
        include_coherence: bool = True,
        include_realism: bool = True,
        include_fairness: bool = True,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Run full evaluation on a persona set.
        Returns comprehensive evaluation report.
        """
        result = await session.execute(
            select(PersonaSet)
            .where(PersonaSet.id == persona_set_id)
            .options(selectinload(PersonaSet.personas))
        )
        persona_set = result.scalar_one_or_none()
        if not persona_set:
            raise ValueError(f"Persona set {persona_set_id} not found")
        if not persona_set.personas:
            raise ValueError("Persona set has no personas")

        project_id = persona_set.project_id

        # Get source documents for coverage
        source_texts = []
        doc_query = select(Document).where(Document.document_type == DocumentType.INTERVIEW)
        if project_id is not None:
            doc_query = doc_query.where(Document.project_id == project_id)
        doc_result = await session.execute(doc_query)
        for doc in doc_result.scalars().all():
            if doc.content:
                source_texts.append(doc.content)
            if doc.processed_content:
                source_texts.append(doc.processed_content)

        # Chunk source if very long (for topic extraction)
        chunked = []
        for t in source_texts:
            for i in range(0, len(t), 2000):
                chunked.append(t[i:i + 2000])
        source_texts = chunked if chunked else source_texts

        per_persona = []
        summary = {
            "overall_groundedness": 0.0,
            "topic_coverage": 0.0,
            "diversity_rqe": (persona_set.diversity_score or {}).get("rqe_score"),
            "diversity_demographic": 0.0,
            "diversity_attitudinal": 0.0,
            "mean_coherence": 0.0,
            "mean_realism": 0.0,
            "fairness_flags": 0
        }

        # Per-persona evaluations
        for persona in persona_set.personas:
            p_result = {
                "persona_id": persona.id,
                "name": persona.name,
                "groundedness": None,
                "coherence": None,
                "realism": None,
                "fairness_flag": False,
                "attribute_details": {}
            }

            if include_groundedness:
                g = await self.evaluate_groundedness(session, persona, project_id)
                p_result["groundedness"] = g["groundedness"]
                p_result["attribute_details"]["groundedness"] = g
                summary["overall_groundedness"] = summary["overall_groundedness"] or 0
                # Will aggregate at end

            if include_coherence:
                c = await self.evaluate_coherence(persona)
                p_result["coherence"] = c["coherence"]
                p_result["coherence_reasoning"] = c.get("reasoning", "")

            if include_realism:
                r = await self.evaluate_realism(persona)
                p_result["realism"] = r["realism"]
                p_result["realism_reasoning"] = r.get("reasoning", "")

            if include_fairness:
                f = await self.evaluate_fairness(persona)
                p_result["fairness_flag"] = f["fairness_flag"]
                p_result["fairness_reasoning"] = f.get("reasoning", "")
                if f["fairness_flag"]:
                    summary["fairness_flags"] += 1

            per_persona.append(p_result)

        # Aggregate groundedness
        grounded = [p["groundedness"] for p in per_persona if p["groundedness"] is not None]
        if grounded:
            summary["overall_groundedness"] = round(sum(grounded) / len(grounded), 3)

        # Coverage
        if include_coverage and source_texts:
            cov = await self.evaluate_coverage(session, persona_set, source_texts)
            summary["topic_coverage"] = cov.get("topic_coverage", 0.0)
            summary["coverage_details"] = cov

        # Extended diversity
        if include_diversity_extended:
            demo_div = self.evaluate_demographic_diversity(persona_set)
            summary["diversity_demographic"] = demo_div.get("demographic_diversity", 0.0)
            summary["diversity_demographic_details"] = demo_div.get("dimensions", {})

            att_div = await self.evaluate_attitudinal_diversity(persona_set)
            summary["diversity_attitudinal"] = att_div.get("attitudinal_diversity", 0.0)

        # Coherence and realism aggregates
        coherences = [p["coherence"] for p in per_persona if p["coherence"] is not None]
        realisms = [p["realism"] for p in per_persona if p["realism"] is not None]
        if coherences:
            summary["mean_coherence"] = round(sum(coherences) / len(coherences), 2)
        if realisms:
            summary["mean_realism"] = round(sum(realisms) / len(realisms), 2)

        report = {
            "persona_set_id": persona_set_id,
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "per_persona": per_persona
        }

        # Persist to persona set
        persona_set.evaluation_scores = report
        await session.flush()

        return report


persona_evaluation_service = PersonaEvaluationService()

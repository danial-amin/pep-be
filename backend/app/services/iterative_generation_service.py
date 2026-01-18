"""
Iterative persona generation service implementing the PEP paper methodology.

This service implements the core PEP (Persona Engineering Process) algorithm:
1. Generate initial persona set
2. Calculate RQE (Rao's Quadratic Entropy) for diversity
3. If RQE < threshold, regenerate with prompt refinement hints
4. Iterate until threshold met or max iterations reached
5. Return final set with metrics and iteration history
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime

from app.models.persona import PersonaSet, Persona
from app.models.document import Document, DocumentType
from app.core.llm_service import llm_service
from app.core.vector_db import vector_db
from app.utils.persona_normalizer import normalize_persona_to_nested

logger = logging.getLogger(__name__)

# Default thresholds from PEP paper
DEFAULT_RQE_THRESHOLD = 0.75  # Paper recommends >= 0.75 for good diversity
DEFAULT_CS_THRESHOLD = 0.80   # Cosine similarity threshold for validation
DEFAULT_MAX_ITERATIONS = 3


class IterativeGenerationService:
    """
    Service for iterative persona generation following PEP paper methodology.

    Key features:
    - Iterative generation until RQE threshold is met
    - Prompt refinement hints based on diversity gaps
    - Source traceability for generated personas
    - Comprehensive metrics tracking
    """

    @staticmethod
    async def generate_persona_set_iterative(
        session: AsyncSession,
        num_personas: int = 5,
        rqe_threshold: float = DEFAULT_RQE_THRESHOLD,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        auto_iterate: bool = True,
        cs_threshold: float = DEFAULT_CS_THRESHOLD,
        context_details: Optional[str] = None,
        interview_topic: Optional[str] = None,
        user_study_design: Optional[str] = None,
        include_ethical_guardrails: bool = True,
        output_format: str = "json",
        document_ids: Optional[List[int]] = None,
        project_id: Optional[str] = None
    ) -> Tuple[PersonaSet, Dict[str, Any]]:
        """
        Generate persona set with iterative refinement until RQE threshold is met.

        Implements the PEP paper's iterative generation algorithm:
        1. Generate initial persona set
        2. Calculate RQE diversity score
        3. If RQE < threshold and iterations < max:
           - Generate diversity hints based on similarity analysis
           - Regenerate with hints emphasizing needed differentiation
        4. Track all iterations and metrics
        5. Return final set with comprehensive metrics

        Args:
            session: Database session
            num_personas: Number of personas to generate (paper recommends 4-6)
            rqe_threshold: Target RQE score (>= 0.75 recommended)
            max_iterations: Maximum generation attempts
            auto_iterate: If True, automatically iterate until threshold met
            cs_threshold: Cosine similarity threshold for validation
            context_details: Additional context about research/market
            interview_topic: Focus topic for interviews
            user_study_design: Study design methodology
            include_ethical_guardrails: Include ethical considerations
            output_format: Output format (json, profile, etc.)
            document_ids: Specific document IDs to use
            project_id: Project ID for scoping

        Returns:
            Tuple of (PersonaSet, metrics_dict) with iteration history
        """
        # Retrieve documents for generation
        interview_texts, context_texts = await IterativeGenerationService._get_documents(
            session, document_ids, project_id
        )

        if not interview_texts and not context_texts:
            raise ValueError("No documents found. Please process at least one interview or context document first.")

        # Store generation configuration
        generation_config = {
            "num_personas": num_personas,
            "rqe_threshold": rqe_threshold,
            "max_iterations": max_iterations,
            "cs_threshold": cs_threshold,
            "auto_iterate": auto_iterate,
            "output_format": output_format,
            "context_details": context_details,
            "interview_topic": interview_topic,
            "user_study_design": user_study_design,
            "include_ethical_guardrails": include_ethical_guardrails,
            "document_ids": document_ids,
            "project_id": project_id
        }

        # Iteration tracking
        iteration_history = []
        current_iteration = 0
        current_rqe = 0.0
        threshold_met = False
        diversity_hints = None

        # Create initial persona set record
        persona_set = PersonaSet(
            name=f"Persona Set (Iterative)",
            description=f"Generated with RQE threshold {rqe_threshold}",
            project_id=project_id,
            generation_config=generation_config,
            rqe_threshold=rqe_threshold,
            max_iterations=max_iterations,
            generation_cycle=1,
            status="generating"
        )
        session.add(persona_set)
        await session.flush()

        # Iterative generation loop
        while current_iteration < max_iterations:
            current_iteration += 1
            logger.info(f"Generation iteration {current_iteration}/{max_iterations}")

            # Generate personas (with diversity hints if not first iteration)
            persona_data_list = await IterativeGenerationService._generate_personas(
                interview_texts=interview_texts,
                context_texts=context_texts,
                num_personas=num_personas,
                context_details=context_details,
                interview_topic=interview_topic,
                user_study_design=user_study_design,
                include_ethical_guardrails=include_ethical_guardrails,
                output_format=output_format,
                diversity_hints=diversity_hints
            )

            # Clear existing personas for this set (if iterating)
            if current_iteration > 1:
                for persona in persona_set.personas:
                    await session.delete(persona)
                await session.flush()

            # Create persona records
            for persona_data in persona_data_list:
                normalized_data = normalize_persona_to_nested(persona_data)
                persona = Persona(
                    persona_set_id=persona_set.id,
                    name=normalized_data.get("name", "Unknown"),
                    persona_data=normalized_data
                )
                session.add(persona)

            await session.flush()
            await session.refresh(persona_set)

            # Calculate RQE diversity score
            rqe_metrics = await IterativeGenerationService._calculate_rqe(persona_set)
            current_rqe = rqe_metrics["rqe_score"]

            # Record iteration
            iteration_record = {
                "iteration": current_iteration,
                "rqe_score": current_rqe,
                "threshold": rqe_threshold,
                "threshold_met": current_rqe >= rqe_threshold,
                "num_personas": len(persona_set.personas),
                "diversity_hints_used": diversity_hints is not None,
                "timestamp": datetime.utcnow().isoformat()
            }
            iteration_history.append(iteration_record)

            # Check if threshold is met
            if current_rqe >= rqe_threshold:
                threshold_met = True
                logger.info(f"RQE threshold met! Score: {current_rqe:.3f} >= {rqe_threshold}")
                break

            # If not auto-iterating, stop after first generation
            if not auto_iterate:
                logger.info(f"Auto-iterate disabled. RQE: {current_rqe:.3f} (threshold: {rqe_threshold})")
                break

            # Generate diversity hints for next iteration
            if current_iteration < max_iterations:
                diversity_hints = await IterativeGenerationService._generate_diversity_hints(
                    persona_set, rqe_metrics
                )
                logger.info(f"Generated diversity hints for iteration {current_iteration + 1}")

        # Update persona set with final metrics
        persona_set.generation_cycle = current_iteration
        persona_set.status = "generated"
        persona_set.rqe_scores = iteration_history
        persona_set.diversity_score = {
            "final_rqe": current_rqe,
            "threshold": rqe_threshold,
            "threshold_met": threshold_met,
            "iterations_used": current_iteration
        }

        await session.flush()
        await session.refresh(persona_set)

        # Build metrics response
        metrics = {
            "rqe_score": current_rqe,
            "rqe_threshold": rqe_threshold,
            "threshold_met": threshold_met,
            "iterations_used": current_iteration,
            "max_iterations": max_iterations,
            "iteration_history": iteration_history,
            "num_personas": len(persona_set.personas)
        }

        return persona_set, metrics

    @staticmethod
    async def _get_documents(
        session: AsyncSession,
        document_ids: Optional[List[int]] = None,
        project_id: Optional[str] = None
    ) -> Tuple[List[str], List[str]]:
        """Retrieve documents for persona generation using RAG."""
        # Build query filter for documents
        document_query = select(Document)

        if document_ids:
            document_query = document_query.where(Document.id.in_(document_ids))
        elif project_id:
            document_query = document_query.where(Document.project_id == project_id)

        # Get interview documents
        interview_query = document_query.where(Document.document_type == DocumentType.INTERVIEW)
        interview_result = await session.execute(interview_query)
        interviews = list(interview_result.scalars().all())

        # Get context documents
        context_query_db = select(Document)
        if document_ids:
            context_query_db = context_query_db.where(Document.id.in_(document_ids))
        elif project_id:
            context_query_db = context_query_db.where(Document.project_id == project_id)
        context_query_db = context_query_db.where(Document.document_type == DocumentType.CONTEXT)
        context_result = await session.execute(context_query_db)
        contexts = list(context_result.scalars().all())

        interview_texts = []
        context_texts = []

        # Use RAG to retrieve relevant chunks
        if interviews:
            interview_doc_ids = [str(doc.id) for doc in interviews]
            interview_filter = {"document_type": "interview"}
            if len(interview_doc_ids) == 1:
                interview_filter["document_id"] = interview_doc_ids[0]
            elif len(interview_doc_ids) > 1:
                interview_filter["document_id"] = {"$in": interview_doc_ids}

            interview_results = await vector_db.query_documents(
                query_texts=["user interviews, user research, interview transcripts, user feedback, user needs, behaviors, patterns"],
                n_results=15,  # Get more chunks for iterative generation
                filter_metadata=interview_filter
            )

            if interview_results.get("documents") and len(interview_results["documents"]) > 0:
                for doc_list in interview_results["documents"]:
                    interview_texts.extend(doc_list)

            if not interview_texts:
                interview_texts = [interview.content for interview in interviews]

        if contexts:
            context_doc_ids = [str(doc.id) for doc in contexts]
            context_filter = {"document_type": "context"}
            if len(context_doc_ids) == 1:
                context_filter["document_id"] = context_doc_ids[0]
            elif len(context_doc_ids) > 1:
                context_filter["document_id"] = {"$in": context_doc_ids}

            context_results = await vector_db.query_documents(
                query_texts=["research context, background information, market research, user behavior, demographics, domain knowledge"],
                n_results=15,
                filter_metadata=context_filter
            )

            if context_results.get("documents") and len(context_results["documents"]) > 0:
                for doc_list in context_results["documents"]:
                    context_texts.extend(doc_list)

            if not context_texts:
                context_texts = [context.content for context in contexts]

        logger.info(f"Retrieved {len(interview_texts)} interview chunks and {len(context_texts)} context chunks")
        return interview_texts, context_texts

    @staticmethod
    async def _generate_personas(
        interview_texts: List[str],
        context_texts: List[str],
        num_personas: int,
        context_details: Optional[str],
        interview_topic: Optional[str],
        user_study_design: Optional[str],
        include_ethical_guardrails: bool,
        output_format: str,
        diversity_hints: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate personas using LLM with optional diversity hints."""
        # Add diversity hints to context if provided
        enhanced_context = context_details or ""
        if diversity_hints:
            enhanced_context = f"{enhanced_context}\n\nDIVERSITY REQUIREMENTS:\n{diversity_hints}"

        has_interviews = len(interview_texts) > 0
        has_context = len(context_texts) > 0

        persona_set_data = await llm_service.generate_persona_set(
            interview_documents=interview_texts if has_interviews else [],
            context_documents=context_texts if has_context else [],
            num_personas=num_personas,
            context_details=enhanced_context if enhanced_context else None,
            interview_topic=interview_topic,
            user_study_design=user_study_design,
            include_ethical_guardrails=include_ethical_guardrails,
            output_format=output_format,
            has_interviews=has_interviews,
            has_context=has_context
        )

        # Extract personas from response
        personas_data = persona_set_data.get("personas", [])
        if not isinstance(personas_data, list):
            personas_data = [personas_data] if personas_data else []

        return [p for p in personas_data if isinstance(p, dict)]

    @staticmethod
    async def _calculate_rqe(persona_set: PersonaSet) -> Dict[str, Any]:
        """
        Calculate RQE (Rao's Quadratic Entropy) for persona set diversity.

        RQE measures the overall differentiation across all personas:
        - 0 = identical personas
        - 1 = maximally diverse

        Per PEP paper:
        - RQE >= 0.75 = good diversity
        - RQE 0.60-0.74 = moderate diversity
        - RQE < 0.60 = insufficient differentiation
        """
        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            logger.warning("scikit-learn not available. Using fallback RQE calculation.")
            return {"rqe_score": 0.7, "method": "fallback"}

        if not persona_set.personas or len(persona_set.personas) < 2:
            return {"rqe_score": 1.0, "num_personas": len(persona_set.personas) if persona_set.personas else 0}

        # Create text representations of personas
        persona_texts = []
        for persona in persona_set.personas:
            data = persona.persona_data
            text_parts = [
                persona.name,
                str(data.get("background", "")),
                " ".join(data.get("goals", [])) if isinstance(data.get("goals"), list) else str(data.get("goals", "")),
                " ".join(data.get("frustrations", [])) if isinstance(data.get("frustrations"), list) else str(data.get("frustrations", "")),
                str(data.get("behaviors", "")),
                str(data.get("demographics", {}).get("occupation", "")) if isinstance(data.get("demographics"), dict) else str(data.get("occupation", ""))
            ]
            persona_texts.append(" ".join(filter(None, text_parts)))

        # Generate embeddings
        persona_embeddings = await llm_service.create_embeddings(persona_texts)
        embeddings_array = np.array(persona_embeddings)

        # Calculate pairwise cosine similarities
        similarity_matrix = cosine_similarity(embeddings_array)

        # RQE: 1 - average pairwise similarity (excluding self-similarity)
        mask = ~np.eye(similarity_matrix.shape[0], dtype=bool)
        pairwise_similarities = similarity_matrix[mask]

        avg_similarity = float(np.mean(pairwise_similarities))
        rqe_score = 1 - avg_similarity

        # Additional metrics
        min_similarity = float(np.min(pairwise_similarities))
        max_similarity = float(np.max(pairwise_similarities))

        return {
            "rqe_score": rqe_score,
            "average_similarity": avg_similarity,
            "min_similarity": min_similarity,
            "max_similarity": max_similarity,
            "num_personas": len(persona_set.personas),
            "similarity_matrix": similarity_matrix.tolist()
        }

    @staticmethod
    async def _generate_diversity_hints(
        persona_set: PersonaSet,
        rqe_metrics: Dict[str, Any]
    ) -> str:
        """
        Generate diversity hints based on similarity analysis.

        Analyzes which personas are too similar and generates specific
        guidance for the next iteration to increase differentiation.
        """
        try:
            import numpy as np
        except ImportError:
            return "Please ensure personas are distinctly different from each other in demographics, goals, and behaviors."

        similarity_matrix = rqe_metrics.get("similarity_matrix")
        if similarity_matrix is None:
            return "Ensure each persona has unique demographics, distinct goals, and different behavioral patterns."

        similarity_matrix = np.array(similarity_matrix)
        n_personas = len(persona_set.personas)

        # Find most similar pairs
        similar_pairs = []
        for i in range(n_personas):
            for j in range(i + 1, n_personas):
                if similarity_matrix[i][j] > 0.7:  # High similarity threshold
                    similar_pairs.append({
                        "persona1": persona_set.personas[i].name,
                        "persona2": persona_set.personas[j].name,
                        "similarity": float(similarity_matrix[i][j])
                    })

        # Sort by similarity (most similar first)
        similar_pairs.sort(key=lambda x: x["similarity"], reverse=True)

        # Generate hints
        hints = []
        hints.append("IMPORTANT: The following personas are too similar and need more differentiation:")

        for pair in similar_pairs[:3]:  # Top 3 most similar pairs
            hints.append(f"- {pair['persona1']} and {pair['persona2']} are {pair['similarity']:.0%} similar")

        hints.append("\nTo increase diversity, please:")
        hints.append("1. Vary demographics more (age ranges, locations, occupations)")
        hints.append("2. Create contrasting goals and motivations")
        hints.append("3. Differentiate technology comfort levels and behaviors")
        hints.append("4. Include personas with opposing frustrations or pain points")
        hints.append("5. Vary educational backgrounds and experience levels")

        return "\n".join(hints)


# Global service instance
iterative_generation_service = IterativeGenerationService()

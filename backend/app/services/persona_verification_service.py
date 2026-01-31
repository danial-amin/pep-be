"""
Persona Verification Service for semantic similarity validation.

Implements verification through reverse querying the vector database:
1. Direct similarity: Query each persona attribute against source data
2. Indirect similarity: Multi-hop semantic relationships through intermediate concepts
3. Filtering: Retain only items with similarity >= threshold (default 80%)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Similarity thresholds
DEFAULT_SIMILARITY_THRESHOLD = 0.80  # 80% threshold as requested
INDIRECT_SIMILARITY_THRESHOLD = 0.70  # Lower threshold for indirect matches
INDIRECT_HOP_DECAY = 0.15  # Decay factor for each hop in indirect similarity

try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("numpy/scikit-learn not available. Verification features will be limited.")

from app.models.persona import PersonaSet, Persona
from app.core.llm_service import llm_service
from app.core.vector_db import vector_db


class PersonaVerificationService:
    """
    Service for verifying persona attributes against source data in vector DB.

    Implements the PEP paper verification methodology with extensions:
    - Direct similarity: Cosine similarity between persona attribute and source chunks
    - Indirect similarity: Multi-hop semantic relationships through related concepts
    - Filtering: Removes attributes that don't meet the similarity threshold
    """

    # Attributes that can be verified against source data
    VERIFIABLE_ATTRIBUTES = [
        "background",
        "goals",
        "frustrations",
        "motivations",
        "behaviors",
        "quote",
        "quotes",
        "technology_profile",
        "other_information"
    ]

    # Attributes that represent core persona identity (not filtered, only flagged)
    CORE_ATTRIBUTES = ["name", "demographics"]

    @staticmethod
    async def verify_persona_similarity(
        session: AsyncSession,
        persona_id: int,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        use_indirect_similarity: bool = True,
        filter_low_similarity: bool = True,
        project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify a persona's attributes against source data using semantic similarity.

        Performs reverse querying of the vector DB for each persona attribute:
        1. Calculate direct similarity (attribute text -> source chunks)
        2. Calculate indirect similarity if direct is below threshold
        3. Combine scores using weighted approach
        4. Filter out low-similarity items if requested

        Args:
            session: Database session
            persona_id: ID of persona to verify
            similarity_threshold: Minimum similarity to retain (default 0.80)
            use_indirect_similarity: Whether to calculate indirect similarity
            filter_low_similarity: Whether to remove low-similarity items
            project_id: Optional project ID for scoping vector DB queries

        Returns:
            Dictionary with verification results, filtered persona, and metrics
        """
        # Load persona
        result = await session.execute(
            select(Persona).where(Persona.id == persona_id)
        )
        persona = result.scalar_one_or_none()

        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        # Build metadata filter for vector DB
        metadata_filter = {"document_type": "interview"}
        if project_id:
            metadata_filter["project_id"] = str(project_id)

        # Verify each attribute
        verification_results = {}
        filtered_persona_data = dict(persona.persona_data)
        source_references = {}

        total_direct_similarity = 0.0
        total_indirect_similarity = 0.0
        verified_count = 0
        filtered_count = 0

        for attr_name in PersonaVerificationService.VERIFIABLE_ATTRIBUTES:
            attr_value = persona.persona_data.get(attr_name)
            if not attr_value:
                continue

            # Convert to text for embedding
            attr_text = PersonaVerificationService._attribute_to_text(attr_value)
            if not attr_text.strip():
                continue

            # Calculate direct similarity
            direct_result = await PersonaVerificationService._calculate_direct_similarity(
                attr_text=attr_text,
                metadata_filter=metadata_filter,
                top_k=5
            )

            # Calculate indirect similarity if enabled and direct is below threshold
            indirect_result = None
            if use_indirect_similarity and direct_result["similarity"] < similarity_threshold:
                indirect_result = await PersonaVerificationService._calculate_indirect_similarity(
                    attr_text=attr_text,
                    metadata_filter=metadata_filter,
                    max_hops=2
                )

            # Combine similarities
            combined_similarity = PersonaVerificationService._combine_similarities(
                direct_similarity=direct_result["similarity"],
                indirect_similarity=indirect_result["similarity"] if indirect_result else 0.0,
                indirect_path=indirect_result.get("path") if indirect_result else None
            )

            # Determine if attribute passes verification
            is_verified = combined_similarity >= similarity_threshold

            verification_results[attr_name] = {
                "direct_similarity": round(direct_result["similarity"], 4),
                "indirect_similarity": round(indirect_result["similarity"], 4) if indirect_result else None,
                "combined_similarity": round(combined_similarity, 4),
                "verified": is_verified,
                "threshold": similarity_threshold,
                "source_chunks": direct_result.get("source_chunks", [])[:3],
                "indirect_path": indirect_result.get("path") if indirect_result else None
            }

            # Track metrics
            total_direct_similarity += direct_result["similarity"]
            if indirect_result:
                total_indirect_similarity += indirect_result["similarity"]

            if is_verified:
                verified_count += 1
                # Store source references for traceability
                source_references[attr_name] = [
                    {"text": chunk[:200], "similarity": direct_result["similarity"]}
                    for chunk in direct_result.get("source_chunks", [])[:2]
                ]
            else:
                filtered_count += 1
                # Filter out low-similarity attribute if requested
                if filter_low_similarity:
                    if isinstance(attr_value, list):
                        # For lists, filter individual items
                        filtered_items = await PersonaVerificationService._filter_list_items(
                            items=attr_value,
                            metadata_filter=metadata_filter,
                            threshold=similarity_threshold
                        )
                        if filtered_items:
                            filtered_persona_data[attr_name] = filtered_items
                        else:
                            # Remove attribute entirely if no items pass
                            filtered_persona_data.pop(attr_name, None)
                    else:
                        # For scalar values, remove if below threshold
                        filtered_persona_data.pop(attr_name, None)

        # Calculate overall metrics
        num_attributes = len(verification_results)
        avg_direct_similarity = total_direct_similarity / num_attributes if num_attributes > 0 else 0.0
        avg_indirect_similarity = total_indirect_similarity / num_attributes if num_attributes > 0 else 0.0
        verification_rate = verified_count / num_attributes if num_attributes > 0 else 0.0

        # Update persona with verification results
        persona.attribute_validation = verification_results
        persona.source_references = source_references
        persona.similarity_score = {
            "average_direct": round(avg_direct_similarity, 4),
            "average_indirect": round(avg_indirect_similarity, 4),
            "verification_rate": round(verification_rate, 4),
            "verified_count": verified_count,
            "filtered_count": filtered_count
        }
        persona.validation_status = "verified" if verification_rate >= 0.7 else "partial"

        await session.flush()

        return {
            "persona_id": persona_id,
            "persona_name": persona.name,
            "verification_results": verification_results,
            "original_persona_data": persona.persona_data,
            "filtered_persona_data": filtered_persona_data if filter_low_similarity else persona.persona_data,
            "metrics": {
                "average_direct_similarity": round(avg_direct_similarity, 4),
                "average_indirect_similarity": round(avg_indirect_similarity, 4),
                "verification_rate": round(verification_rate, 4),
                "verified_attributes": verified_count,
                "filtered_attributes": filtered_count,
                "total_attributes": num_attributes,
                "threshold": similarity_threshold
            },
            "source_references": source_references,
            "validation_status": persona.validation_status
        }

    @staticmethod
    async def verify_persona_set(
        session: AsyncSession,
        persona_set_id: int,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        use_indirect_similarity: bool = True,
        filter_low_similarity: bool = True,
        project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify all personas in a set and return aggregated results.

        Args:
            session: Database session
            persona_set_id: ID of persona set to verify
            similarity_threshold: Minimum similarity threshold (default 0.80)
            use_indirect_similarity: Whether to use indirect similarity
            filter_low_similarity: Whether to filter low-similarity items
            project_id: Optional project ID for scoping

        Returns:
            Dictionary with per-persona results and aggregate metrics
        """
        # Load persona set with personas
        result = await session.execute(
            select(PersonaSet)
            .where(PersonaSet.id == persona_set_id)
            .options(selectinload(PersonaSet.personas))
        )
        persona_set = result.scalar_one_or_none()

        if not persona_set:
            raise ValueError(f"Persona set {persona_set_id} not found")

        if not persona_set.personas:
            raise ValueError("Persona set has no personas to verify")

        # Use project_id from persona_set if not provided
        effective_project_id = project_id or persona_set.project_id

        # Verify each persona
        persona_results = []
        total_verification_rate = 0.0
        total_direct_similarity = 0.0
        fully_verified_count = 0

        for persona in persona_set.personas:
            try:
                result = await PersonaVerificationService.verify_persona_similarity(
                    session=session,
                    persona_id=persona.id,
                    similarity_threshold=similarity_threshold,
                    use_indirect_similarity=use_indirect_similarity,
                    filter_low_similarity=filter_low_similarity,
                    project_id=effective_project_id
                )
                persona_results.append(result)

                # Aggregate metrics
                metrics = result["metrics"]
                total_verification_rate += metrics["verification_rate"]
                total_direct_similarity += metrics["average_direct_similarity"]

                if metrics["verification_rate"] >= 0.8:
                    fully_verified_count += 1

            except Exception as e:
                logger.error(f"Error verifying persona {persona.id}: {e}")
                persona_results.append({
                    "persona_id": persona.id,
                    "persona_name": persona.name,
                    "error": str(e)
                })

        # Calculate aggregate metrics
        num_personas = len(persona_set.personas)
        avg_verification_rate = total_verification_rate / num_personas if num_personas > 0 else 0.0
        avg_direct_similarity = total_direct_similarity / num_personas if num_personas > 0 else 0.0

        # Update persona set status
        persona_set.validation_scores = [
            {
                "persona_id": r["persona_id"],
                "verification_rate": r.get("metrics", {}).get("verification_rate", 0),
                "status": r.get("validation_status", "error")
            }
            for r in persona_results
        ]
        persona_set.status = "verified"

        await session.flush()

        return {
            "persona_set_id": persona_set_id,
            "persona_results": persona_results,
            "aggregate_metrics": {
                "average_verification_rate": round(avg_verification_rate, 4),
                "average_direct_similarity": round(avg_direct_similarity, 4),
                "fully_verified_personas": fully_verified_count,
                "partially_verified_personas": num_personas - fully_verified_count,
                "total_personas": num_personas,
                "threshold": similarity_threshold
            },
            "status": "verified",
            "verified_at": datetime.utcnow().isoformat()
        }

    @staticmethod
    async def get_verified_persona(
        session: AsyncSession,
        persona_id: int,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get a verified and filtered persona with only high-similarity attributes.

        This returns the persona with low-similarity items removed,
        suitable for production use where only validated data is needed.

        Args:
            session: Database session
            persona_id: ID of persona to get
            similarity_threshold: Minimum similarity for inclusion
            project_id: Optional project ID for scoping

        Returns:
            Filtered persona data with verification metadata
        """
        result = await PersonaVerificationService.verify_persona_similarity(
            session=session,
            persona_id=persona_id,
            similarity_threshold=similarity_threshold,
            use_indirect_similarity=True,
            filter_low_similarity=True,
            project_id=project_id
        )

        return {
            "persona_id": persona_id,
            "persona_name": result["persona_name"],
            "verified_persona_data": result["filtered_persona_data"],
            "verification_rate": result["metrics"]["verification_rate"],
            "threshold": similarity_threshold,
            "source_references": result["source_references"]
        }

    @staticmethod
    async def _calculate_direct_similarity(
        attr_text: str,
        metadata_filter: Dict[str, Any],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Calculate direct semantic similarity between attribute text and source chunks.

        Queries the vector DB and returns cosine similarity scores.
        """
        try:
            # Query vector DB for similar source chunks
            query_results = await vector_db.query_documents(
                query_texts=[attr_text],
                n_results=top_k,
                filter_metadata=metadata_filter
            )

            # Extract similarities from distances
            similarities = []
            source_chunks = []

            if query_results.get("distances") and len(query_results["distances"]) > 0:
                scores = query_results["distances"][0]
                # Pinecone returns cosine similarity (higher = more similar). Handle None.
                for s in scores:
                    if s is None:
                        similarities.append(0.0)
                    elif s > 1:
                        # Likely a distance metric (e.g. from ChromaDB)
                        similarities.append(max(0.0, 1.0 - float(s)))
                    else:
                        similarities.append(float(s))

            if query_results.get("documents") and len(query_results["documents"]) > 0:
                source_chunks = query_results["documents"][0]

            # Use relevance scores from reranker if available
            if query_results.get("relevance_scores") and len(query_results["relevance_scores"]) > 0:
                similarities = query_results["relevance_scores"][0]

            # Calculate average similarity
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
            max_similarity = max(similarities) if similarities else 0.0

            return {
                "similarity": max(avg_similarity, max_similarity * 0.9),  # Weighted towards max
                "average_similarity": avg_similarity,
                "max_similarity": max_similarity,
                "all_similarities": similarities,
                "source_chunks": source_chunks,
                "num_matches": len(similarities)
            }

        except Exception as e:
            logger.error(f"Error calculating direct similarity: {e}")
            return {
                "similarity": 0.0,
                "error": str(e),
                "source_chunks": []
            }

    @staticmethod
    async def _calculate_indirect_similarity(
        attr_text: str,
        metadata_filter: Dict[str, Any],
        max_hops: int = 2
    ) -> Dict[str, Any]:
        """
        Calculate indirect/conceptual semantic similarity.

        Uses multiple strategies to find conceptual relationships:
        1. Semantic expansion: Extract key themes and search for each
        2. Synonym/related term search: Find semantically similar concepts
        3. Contextual matching: Look for broader context that implies the attribute

        This ensures we find conceptual relationships even when direct text
        matching fails.
        """
        if not HAS_NUMPY:
            return {"similarity": 0.0, "path": [], "error": "numpy not available"}

        try:
            best_indirect_similarity = 0.0
            best_path = []
            all_concept_scores = []

            # Strategy 1: Search with semantic variations of the attribute
            semantic_queries = PersonaVerificationService._generate_semantic_queries(attr_text)

            for query_variant in semantic_queries:
                try:
                    variant_results = await vector_db.query_documents(
                        query_texts=[query_variant],
                        n_results=5,
                        filter_metadata=metadata_filter
                    )

                    if variant_results.get("distances") and variant_results["distances"][0]:
                        scores = variant_results["distances"][0]
                        max_score = max(scores) if scores else 0.0
                        if max_score > 0:
                            all_concept_scores.append({
                                "query": query_variant[:50],
                                "similarity": max_score,
                                "source": variant_results.get("documents", [[]])[0][:1]
                            })
                except Exception as e:
                    logger.debug(f"Semantic query failed: {e}")
                    continue

            # Strategy 2: Break into key concepts and search individually
            key_concepts = PersonaVerificationService._extract_key_concepts(attr_text)
            concept_similarities = []

            for concept in key_concepts[:5]:  # Limit to top 5 concepts
                try:
                    concept_results = await vector_db.query_documents(
                        query_texts=[concept],
                        n_results=3,
                        filter_metadata=metadata_filter
                    )

                    if concept_results.get("distances") and concept_results["distances"][0]:
                        scores = concept_results["distances"][0]
                        concept_sim = max(scores) if scores else 0.0
                        if concept_sim > 0.3:  # Only count meaningful matches
                            concept_similarities.append(concept_sim)
                            all_concept_scores.append({
                                "query": f"concept: {concept}",
                                "similarity": concept_sim,
                                "source": concept_results.get("documents", [[]])[0][:1]
                            })
                except Exception as e:
                    logger.debug(f"Concept search failed for '{concept}': {e}")
                    continue

            # Strategy 3: Broader contextual search
            context_query = f"user research data about {attr_text[:100]}"
            try:
                context_results = await vector_db.query_documents(
                    query_texts=[context_query],
                    n_results=5,
                    filter_metadata=metadata_filter
                )

                if context_results.get("distances") and context_results["distances"][0]:
                    scores = context_results["distances"][0]
                    context_sim = max(scores) if scores else 0.0
                    if context_sim > 0.3:
                        all_concept_scores.append({
                            "query": "contextual",
                            "similarity": context_sim,
                            "source": context_results.get("documents", [[]])[0][:1]
                        })
            except Exception as e:
                logger.debug(f"Context search failed: {e}")

            # Calculate best indirect similarity from all strategies
            if all_concept_scores:
                # Sort by similarity
                all_concept_scores.sort(key=lambda x: x["similarity"], reverse=True)

                # Use weighted average of top matches
                top_scores = [s["similarity"] for s in all_concept_scores[:3]]
                if top_scores:
                    # Weighted: best score counts more
                    weights = [0.5, 0.3, 0.2][:len(top_scores)]
                    best_indirect_similarity = sum(s * w for s, w in zip(top_scores, weights))

                    # Build path for explanation
                    best_path = [
                        {
                            "hop": i + 1,
                            "query": score["query"],
                            "similarity": round(score["similarity"], 4),
                            "matched_text": score["source"][0][:100] if score["source"] else ""
                        }
                        for i, score in enumerate(all_concept_scores[:3])
                    ]

            # If concept-level matching found results, boost the score
            if concept_similarities:
                avg_concept_sim = sum(concept_similarities) / len(concept_similarities)
                coverage = len(concept_similarities) / max(len(key_concepts), 1)

                # Conceptual coverage bonus
                concept_based_score = avg_concept_sim * (0.7 + 0.3 * coverage)
                if concept_based_score > best_indirect_similarity:
                    best_indirect_similarity = concept_based_score
                    best_path.append({
                        "hop": len(best_path) + 1,
                        "method": "concept_coverage",
                        "concepts_matched": len(concept_similarities),
                        "total_concepts": len(key_concepts),
                        "similarity": round(concept_based_score, 4)
                    })

            return {
                "similarity": round(best_indirect_similarity, 4),
                "path": best_path,
                "method": "conceptual_multi_strategy",
                "strategies_used": len(all_concept_scores)
            }

        except Exception as e:
            logger.error(f"Error calculating indirect similarity: {e}")
            return {"similarity": 0.0, "path": [], "error": str(e)}

    @staticmethod
    def _generate_semantic_queries(text: str) -> List[str]:
        """Generate semantic variations of the query text."""
        queries = []
        text_lower = text.lower()

        # Original text (shortened if needed)
        queries.append(text[:300])

        # Rephrase as user need/want
        if len(text) < 200:
            queries.append(f"user wants to {text}")
            queries.append(f"user needs {text}")
            queries.append(f"user looking for {text}")

        # Extract action-oriented rephrasing
        if "goal" in text_lower or "want" in text_lower:
            queries.append(f"motivation: {text[:150]}")

        if "frustrat" in text_lower or "pain" in text_lower or "problem" in text_lower:
            queries.append(f"user challenge: {text[:150]}")
            queries.append(f"difficulty with {text[:150]}")

        if "behavior" in text_lower or "habit" in text_lower:
            queries.append(f"user typically {text[:150]}")

        # Generic semantic expansions
        queries.append(f"research finding about {text[:100]}")
        queries.append(f"interview insight: {text[:100]}")

        return queries[:6]  # Limit to 6 variations

    @staticmethod
    def _extract_key_concepts(text: str) -> List[str]:
        """Extract key concepts/themes from text for granular matching."""
        import re

        # Remove common words and extract meaningful phrases
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'it', 'its', 'this', 'that', 'these', 'those', 'i', 'me', 'my',
            'we', 'our', 'you', 'your', 'he', 'she', 'they', 'them', 'their',
            'what', 'which', 'who', 'whom', 'when', 'where', 'why', 'how',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'not', 'only', 'same', 'so', 'than', 'too',
            'very', 'just', 'also', 'now', 'here', 'there', 'then', 'once'
        }

        # Clean and tokenize
        text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text_clean.split()

        # Extract meaningful words
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]

        # Create concept phrases (bigrams and key words)
        concepts = []

        # Add individual key words
        for word in meaningful_words[:10]:
            concepts.append(word)

        # Add bigrams (consecutive meaningful words)
        for i in range(len(words) - 1):
            if words[i] not in stop_words and words[i+1] not in stop_words:
                bigram = f"{words[i]} {words[i+1]}"
                if len(bigram) > 5:
                    concepts.append(bigram)

        # Deduplicate while preserving order
        seen = set()
        unique_concepts = []
        for c in concepts:
            if c not in seen:
                seen.add(c)
                unique_concepts.append(c)

        return unique_concepts[:8]  # Return top 8 concepts

    @staticmethod
    def _combine_similarities(
        direct_similarity: float,
        indirect_similarity: float,
        indirect_path: Optional[List[Dict]] = None
    ) -> float:
        """
        Combine direct and indirect similarities into a final score.

        Strategy:
        - If direct similarity >= threshold, use direct only
        - If direct is moderate (0.5-0.8), blend with indirect
        - If direct is low but indirect is strong, indirect can contribute significantly
        - Use adaptive weighting based on the strength of each signal
        """
        # If direct is already good, use it
        if direct_similarity >= DEFAULT_SIMILARITY_THRESHOLD:
            return direct_similarity

        # If no indirect similarity, return direct
        if indirect_similarity <= 0:
            return direct_similarity

        # Adaptive weighting based on signal strengths
        # When direct is very low, give more weight to indirect
        if direct_similarity < 0.3:
            # Direct is weak, lean more on indirect
            direct_weight = 0.4
            indirect_weight = 0.6
        elif direct_similarity < 0.5:
            # Direct is moderate-low
            direct_weight = 0.5
            indirect_weight = 0.5
        else:
            # Direct is moderate, still prefer it but consider indirect
            direct_weight = 0.6
            indirect_weight = 0.4

        # Calculate weighted combination
        combined = (direct_similarity * direct_weight) + (indirect_similarity * indirect_weight)

        # Boost if we have strong evidence from both sources
        if direct_similarity > 0.4 and indirect_similarity > 0.5:
            combined = min(1.0, combined * 1.15)

        # Additional boost if indirect path has multiple strong matches
        if indirect_path and len(indirect_path) >= 2:
            path_scores = [p.get("similarity", 0) for p in indirect_path if isinstance(p.get("similarity"), (int, float))]
            if path_scores and min(path_scores) > 0.4:
                combined = min(1.0, combined * 1.1)

        return round(combined, 4)

    @staticmethod
    async def _filter_list_items(
        items: List[Any],
        metadata_filter: Dict[str, Any],
        threshold: float
    ) -> List[Any]:
        """
        Filter individual items in a list based on similarity threshold.

        Used for attributes that are lists (goals, frustrations, etc.)
        to retain only items that pass the similarity threshold.
        """
        if not items:
            return []

        filtered_items = []

        for item in items:
            item_text = str(item) if not isinstance(item, str) else item
            if not item_text.strip():
                continue

            # Check similarity for this item
            result = await PersonaVerificationService._calculate_direct_similarity(
                attr_text=item_text,
                metadata_filter=metadata_filter,
                top_k=3
            )

            if result["similarity"] >= threshold:
                filtered_items.append(item)
            else:
                logger.debug(f"Filtered out item with similarity {result['similarity']}: {item_text[:50]}...")

        return filtered_items

    @staticmethod
    def _attribute_to_text(value: Any) -> str:
        """Convert an attribute value to searchable text."""
        if isinstance(value, str):
            return value
        elif isinstance(value, list):
            return " ".join(str(item) for item in value)
        elif isinstance(value, dict):
            # For nested objects like technology_profile
            parts = []
            for k, v in value.items():
                if isinstance(v, list):
                    parts.append(f"{k}: {', '.join(str(i) for i in v)}")
                else:
                    parts.append(f"{k}: {v}")
            return " ".join(parts)
        else:
            return str(value)

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not HAS_NUMPY:
            # Fallback calculation
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = sum(a * a for a in vec1) ** 0.5
            norm2 = sum(b * b for b in vec2) ** 0.5
            return dot_product / (norm1 * norm2) if norm1 * norm2 > 0 else 0.0

        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        return float(np.dot(vec1_np, vec2_np) / (np.linalg.norm(vec1_np) * np.linalg.norm(vec2_np)))


# Global service instance
persona_verification_service = PersonaVerificationService()

"""
Persona generation and management service.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any

from app.models.persona import PersonaSet, Persona
from app.models.document import Document, DocumentType
from app.core.llm_service import llm_service
from app.core.vector_db import vector_db
from app.schemas.persona import PersonaBasic
from app.utils.persona_normalizer import normalize_persona_to_nested
import logging

logger = logging.getLogger(__name__)


class PersonaService:
    """Service for persona generation and management."""
    
    @staticmethod
    async def generate_persona_set(
        session: AsyncSession,
        num_personas: int = 3,
        context_details: Optional[str] = None,
        interview_topic: Optional[str] = None,
        user_study_design: Optional[str] = None,
        include_ethical_guardrails: bool = True,
        output_format: str = "json",
        document_ids: Optional[List[int]] = None,
        project_id: Optional[int] = None
    ) -> PersonaSet:
        """
        Generate initial persona set with basic demographics using RAG.
        
        Uses vector database to retrieve relevant document chunks instead of
        loading all documents, making it more efficient and scalable.
        
        Args:
            document_ids: Optional list of document IDs to filter by (for session isolation)
            project_id: Optional project ID to filter documents by project
        """
        # Build query filter for documents
        document_query = select(Document)
        
        # Filter by document_ids if provided (for session isolation)
        if document_ids:
            document_query = document_query.where(Document.id.in_(document_ids))
        # Or filter by project_id if provided
        elif project_id:
            document_query = document_query.where(Document.project_id == project_id)
        
        # Check if we have any interview documents
        interview_query = document_query.where(Document.document_type == DocumentType.INTERVIEW)
        interview_result = await session.execute(interview_query)
        interviews = list(interview_result.scalars().all())
        
        # Check if we have any context documents
        context_query_db = document_query.where(Document.document_type == DocumentType.CONTEXT)
        context_result = await session.execute(context_query_db)
        contexts = list(context_result.scalars().all())
        
        # Validate that we have at least one type of document
        if not interviews and not contexts:
            raise ValueError("No documents found. Please process at least one interview or context document first.")
        
        interview_texts = []
        context_texts = []
        
        # Process interviews if available
        if interviews:
            # Get interview document IDs for vector DB filtering
            interview_doc_ids = [str(doc.id) for doc in interviews] if (document_ids or project_id) else None
            
            # Use RAG to retrieve relevant chunks for persona generation
            interview_query_text = "user interviews, user research, interview transcripts, user feedback, user needs"
            interview_filter = {"document_type": "interview"}
            if project_id:
                # Filter by project_id for project isolation
                interview_filter["project_id"] = str(project_id)
            elif interview_doc_ids and len(interview_doc_ids) > 0:
                # Filter by document IDs for session isolation
                if len(interview_doc_ids) == 1:
                    interview_filter["document_id"] = interview_doc_ids[0]
                else:
                    interview_filter["document_id"] = {"$in": interview_doc_ids}
            
            interview_results = await vector_db.query_documents(
                query_texts=[interview_query_text],
                n_results=10,  # Get top 10 relevant chunks
                filter_metadata=interview_filter
            )
            
            # Extract document texts from vector DB results
            if interview_results.get("documents") and len(interview_results["documents"]) > 0:
                # Flatten the results (ChromaDB returns lists of lists)
                for doc_list in interview_results["documents"]:
                    interview_texts.extend(doc_list)
            
            # If no results from vector DB, fall back to full documents (for backward compatibility)
            if not interview_texts:
                logger.warning("No interview chunks found in vector DB, falling back to full documents")
                interview_texts = [interview.content for interview in interviews]
        
        # Process context if available
        if contexts:
            context_query_text = "research context, background information, market research, user behavior, demographics"
            context_doc_ids = [str(doc.id) for doc in contexts] if document_ids or project_id else None
            
            context_filter = {"document_type": "context"}
            if project_id:
                # Filter by project_id for project isolation
                context_filter["project_id"] = str(project_id)
            elif context_doc_ids and len(context_doc_ids) > 0:
                # Filter by document IDs for session isolation
                if len(context_doc_ids) == 1:
                    context_filter["document_id"] = context_doc_ids[0]
                else:
                    context_filter["document_id"] = {"$in": context_doc_ids}
            
            context_results = await vector_db.query_documents(
                query_texts=[context_query_text],
                n_results=10,  # Get top 10 relevant chunks
                filter_metadata=context_filter
            )
            
            # Extract document texts from vector DB results
            if context_results.get("documents") and len(context_results["documents"]) > 0:
                for doc_list in context_results["documents"]:
                    context_texts.extend(doc_list)
            
            # If no results from vector DB, fall back to full documents
            if not context_texts:
                logger.warning("No context chunks found in vector DB, falling back to full documents")
                context_texts = [context.content for context in contexts]
        
        logger.info(f"Using {len(interview_texts)} interview chunks and {len(context_texts)} context chunks for persona generation")
        
        # Determine generation mode based on available documents
        has_interviews = len(interview_texts) > 0
        has_context = len(context_texts) > 0
        
        # Generate persona set using LLM with retrieved chunks and advanced options
        persona_set_data = await llm_service.generate_persona_set(
            interview_documents=interview_texts if has_interviews else [],
            context_documents=context_texts if has_context else [],
            num_personas=num_personas,
            context_details=context_details,
            interview_topic=interview_topic,
            user_study_design=user_study_design,
            include_ethical_guardrails=include_ethical_guardrails,
            output_format=output_format,
            has_interviews=has_interviews,
            has_context=has_context
        )
        
        # Create persona set
        persona_set = PersonaSet(
            name=f"Persona Set {len(await PersonaService._get_all_persona_sets(session)) + 1}",
            description=persona_set_data.get("description", "Generated persona set"),
            project_id=project_id,  # Link to project
            status="generated",
            generation_cycle=1
        )
        session.add(persona_set)
        await session.flush()
        
        # Create basic personas
        # Handle different output formats
        if output_format == "json":
            personas_data = persona_set_data.get("personas", [])
            if not isinstance(personas_data, list):
                # If personas is not a list, try to extract it
                personas_data = [personas_data] if personas_data else []
            
            for persona_data in personas_data:
                if isinstance(persona_data, dict):
                    # Normalize to standard nested structure
                    normalized_data = normalize_persona_to_nested(persona_data)
                    persona = Persona(
                        persona_set_id=persona_set.id,
                        name=normalized_data.get("name", "Unknown"),
                        persona_data=normalized_data
                    )
                else:
                    persona = Persona(
                        persona_set_id=persona_set.id,
                        name="Persona",
                        persona_data={"content": str(persona_data)}
                    )
                session.add(persona)
        else:
            # For non-JSON formats, store the formatted content
            # The LLM returns content in the "personas" field as formatted text
            formatted_content = persona_set_data.get("personas", "")
            if not formatted_content:
                formatted_content = persona_set_data.get("content", "No personas generated")
            
            # Store as a single persona entry with the formatted content
            persona = Persona(
                persona_set_id=persona_set.id,
                name=f"Persona Set {persona_set.id} - {output_format}",
                persona_data={
                    "format": output_format,
                    "content": str(formatted_content),
                    "num_personas": num_personas
                }
            )
            session.add(persona)
        
        await session.flush()
        await session.refresh(persona_set)
        
        return persona_set
    
    @staticmethod
    async def expand_persona(
        session: AsyncSession,
        persona_id: int
    ) -> Persona:
        """
        Expand a basic persona into a full-fledged persona using RAG.
        
        Uses vector database to retrieve relevant context chunks based on
        the persona's characteristics, making it more targeted and efficient.
        """
        result = await session.execute(
            select(Persona).where(Persona.id == persona_id)
        )
        persona = result.scalar_one_or_none()
        
        if not persona:
            raise ValueError(f"Persona with ID {persona_id} not found")
        
        # Build a query based on persona characteristics for better retrieval
        persona_name = persona.persona_data.get("name", "")
        persona_occupation = persona.persona_data.get("occupation", "")
        persona_description = persona.persona_data.get("basic_description", "")
        
        # Create a semantic query from persona characteristics
        query = f"{persona_name} {persona_occupation} {persona_description} demographics psychographics behaviors goals challenges"
        
        # Get persona set to check for project_id
        persona_set = persona.persona_set
        
        # Use RAG to retrieve relevant context chunks
        context_filter = {"document_type": "context"}
        if persona_set and persona_set.project_id:
            context_filter["project_id"] = str(persona_set.project_id)
        
        context_results = await vector_db.query_documents(
            query_texts=[query],
            n_results=8,  # Get top 8 relevant chunks
            filter_metadata=context_filter
        )
        
        # Extract document texts from vector DB results
        context_texts = []
        if context_results.get("documents") and len(context_results["documents"]) > 0:
            for doc_list in context_results["documents"]:
                context_texts.extend(doc_list)
        
        # Fall back to full documents if no chunks found
        if not context_texts:
            logger.warning("No context chunks found in vector DB, falling back to full documents")
            context_query = select(Document).where(Document.document_type == DocumentType.CONTEXT)
            if persona_set and persona_set.project_id:
                context_query = context_query.where(Document.project_id == persona_set.project_id)
            context_result = await session.execute(context_query)
            contexts = list(context_result.scalars().all())
            context_texts = [context.content for context in contexts]
        
        logger.info(f"Using {len(context_texts)} context chunks for persona expansion")
        
        # Expand persona using LLM with retrieved chunks
        expanded_data = await llm_service.expand_persona(
            persona_basic=persona.persona_data,
            context_documents=context_texts
        )
        
        # Demographic fields that must NEVER be changed (flat structure)
        DEMOGRAPHIC_FIELDS = {
            'name', 'age', 'gender', 'nationality', 'education_level', 'income_bracket',
            'relationship_status', 'occupation', 'location', 'persona_id', 'tagline',
            'social_media_usage', 'role'  # These are also demographic/descriptive, not behavioral
        }
        
        # Fields that should be expanded (behavioral/psychographic)
        EXPANDABLE_FIELDS = {
            'behaviors', 'goals', 'motivations', 'frustrations', 'pain_points', 'quotes',
            'quote', 'other_information', 'background', 'personal_history', 'detailed_description',
            'technology_profile', 'interaction_preferences', 'technology_usage', 'digital_literacy',
            'behaviors_and_preferences', 'goals_and_motivations', 'pain_points_and_frustrations',
            'background_and_personal_history', 'technology_usage_and_digital_literacy',
            'needs_and_interaction_with_product_service', 'interaction_with_product_service'
        }
        
        # Normalize both original and expanded to nested structure first
        original_normalized = normalize_persona_to_nested(persona.persona_data)
        expanded_normalized = normalize_persona_to_nested(expanded_data)
        
        # Strict merge: Only keep fields that exist in the original, remove any new fields
        # Preserve demographic fields exactly, only expand behavioral fields
        def strict_deep_merge(original: dict, expanded: dict) -> dict:
            """Strict deep merge: Preserve demographics exactly, only expand behavioral fields."""
            result = original.copy()
            
            # First, identify all keys in original to detect structure changes
            original_keys = set(original.keys())
            expanded_keys = set(expanded.keys())
            
            # Log any new fields that were added
            new_fields = expanded_keys - original_keys
            if new_fields:
                logger.warning(f"Expansion added new fields {new_fields} which don't exist in original. These will be ignored.")
            
            for key in original_keys:
                # If key doesn't exist in expanded, keep original (shouldn't happen, but be safe)
                if key not in expanded:
                    result[key] = original[key]
                    continue
                
                value = expanded[key]
                
                # CRITICAL: Demographic fields must remain EXACTLY as they are
                if key in DEMOGRAPHIC_FIELDS:
                    # Keep original value for demographic fields - do NOT change them
                    logger.debug(f"Preserving demographic field '{key}' exactly as original")
                    result[key] = original[key]  # Use original, ignore expanded
                    continue
                
                # Check if it's a nested demographics object - preserve it entirely
                if key == 'demographics' and isinstance(original.get(key), dict):
                    # Preserve entire demographics object exactly - do not merge
                    logger.debug(f"Preserving demographics object exactly as original")
                    result[key] = original[key]
                    continue
                
                # CRITICAL: Preserve structure - if original is flat, don't allow nested
                # If original has flat demographics, don't allow nested demographics object
                if key == 'demographics' and not isinstance(original.get(key), dict) and isinstance(value, dict):
                    logger.warning(f"Expansion tried to add nested 'demographics' object but original has flat structure. Preserving original structure.")
                    # Don't add nested structure if original was flat
                    continue
                
                # For expandable fields, allow expansion
                if key in EXPANDABLE_FIELDS:
                    if isinstance(result[key], dict) and isinstance(value, dict):
                        # Recursively merge nested dictionaries for behavioral fields
                        result[key] = strict_deep_merge(result[key], value)
                    elif isinstance(result[key], list) and isinstance(value, list):
                        # For arrays, prefer expanded version if it has more content
                        result[key] = value if len(value) > len(result[key]) else result[key]
                    else:
                        # Use expanded value for behavioral fields
                        if value is not None and value != "":
                            result[key] = value
                else:
                    # For unknown fields, preserve original to be safe
                    # This includes fields like 'social_media_usage', 'role' which are descriptive
                    logger.debug(f"Preserving field '{key}' as original (not in expandable list)")
                    result[key] = original[key]
            
            return result
        
        # Strict merge: Only expand existing fields, remove any new fields
        merged_data = strict_deep_merge(original_normalized, expanded_normalized)
        
        # Final validation: Ensure structure matches original
        # If original had flat structure, ensure merged doesn't have nested demographics
        original_has_flat_demographics = all(
            key in persona.persona_data for key in ['age', 'gender', 'occupation']
        ) and 'demographics' not in persona.persona_data
        
        if original_has_flat_demographics and 'demographics' in merged_data:
            logger.warning("Expansion tried to add nested 'demographics' but original has flat structure. Removing nested structure.")
            # Remove nested demographics and keep flat structure
            if isinstance(merged_data['demographics'], dict):
                # Extract flat fields from nested demographics if they exist
                nested_demo = merged_data.pop('demographics')
                # But don't add them back - keep original flat structure
                logger.info("Removed nested demographics structure to preserve original flat structure")
        
        # Update persona with merged data
        persona.persona_data = merged_data
        
        # Update persona set status if all personas are expanded
        persona_set = persona.persona_set
        if persona_set:
            all_expanded = all(
                p.persona_data.get("detailed_description") or p.persona_data.get("personal_background")
                for p in persona_set.personas
            )
            if all_expanded:
                persona_set.status = "expanded"
        
        await session.flush()
        await session.refresh(persona)
        
        return persona
    
    @staticmethod
    async def generate_persona_image(
        session: AsyncSession,
        persona_id: int
    ) -> Persona:
        """Generate an image for a persona."""
        from app.utils.image_utils import download_and_save_image
        
        result = await session.execute(
            select(Persona).where(Persona.id == persona_id)
        )
        persona = result.scalar_one_or_none()
        
        if not persona:
            raise ValueError(f"Persona with ID {persona_id} not found")
        
        # Generate image prompt
        image_prompt = await llm_service.generate_persona_image_prompt(persona.persona_data)
        
        # Generate image (returns temporary DALL-E URL)
        dall_e_url = await llm_service.generate_image(image_prompt)
        
        # Download and save the image locally
        local_image_path = await download_and_save_image(dall_e_url, persona_id)
        
        if not local_image_path:
            logger.warning(f"Failed to download image for persona {persona_id}, using DALL-E URL")
            local_image_path = dall_e_url
        
        # Update persona with local image path
        persona.image_url = local_image_path
        persona.image_prompt = image_prompt
        await session.commit()
        await session.refresh(persona)
        
        return persona
    
    @staticmethod
    async def save_persona_set(
        session: AsyncSession,
        persona_set_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> PersonaSet:
        """Save/update a persona set."""
        result = await session.execute(
            select(PersonaSet).where(PersonaSet.id == persona_set_id)
        )
        persona_set = result.scalar_one_or_none()
        
        if not persona_set:
            raise ValueError(f"Persona set with ID {persona_set_id} not found")
        
        if name:
            persona_set.name = name
        if description:
            persona_set.description = description
        
        await session.flush()
        await session.refresh(persona_set)
        
        return persona_set
    
    @staticmethod
    async def get_persona_set(
        session: AsyncSession,
        persona_set_id: int
    ) -> Optional[PersonaSet]:
        """Get a persona set by ID."""
        from sqlalchemy.orm import selectinload
        result = await session.execute(
            select(PersonaSet)
            .where(PersonaSet.id == persona_set_id)
            .options(selectinload(PersonaSet.personas))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_persona_sets(
        session: AsyncSession
    ) -> List[PersonaSet]:
        """Get all persona sets."""
        from sqlalchemy.orm import selectinload
        result = await session.execute(
            select(PersonaSet).options(selectinload(PersonaSet.personas))
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def _get_all_persona_sets(
        session: AsyncSession
    ) -> List[PersonaSet]:
        """Internal method to get all persona sets."""
        result = await session.execute(select(PersonaSet))
        return list(result.scalars().all())


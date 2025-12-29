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
import logging

logger = logging.getLogger(__name__)


class PersonaService:
    """Service for persona generation and management."""
    
    @staticmethod
    async def generate_persona_set(
        session: AsyncSession,
        num_personas: int = 3
    ) -> PersonaSet:
        """
        Generate initial persona set with basic demographics using RAG.
        
        Uses vector database to retrieve relevant document chunks instead of
        loading all documents, making it more efficient and scalable.
        """
        # Check if we have any interview documents
        interview_result = await session.execute(
            select(Document).where(Document.document_type == DocumentType.INTERVIEW)
        )
        interviews = list(interview_result.scalars().all())
        
        if not interviews:
            raise ValueError("No interview documents found. Please process interview documents first.")
        
        # Use RAG to retrieve relevant chunks for persona generation
        # Query for interview-related content
        interview_query = "user interviews, user research, interview transcripts, user feedback, user needs"
        interview_results = await vector_db.query_documents(
            query_texts=[interview_query],
            n_results=10,  # Get top 10 relevant chunks
            filter_metadata={"document_type": "interview"}
        )
        
        # Query for context-related content
        context_query = "research context, background information, market research, user behavior, demographics"
        context_results = await vector_db.query_documents(
            query_texts=[context_query],
            n_results=10,  # Get top 10 relevant chunks
            filter_metadata={"document_type": "context"}
        )
        
        # Extract document texts from vector DB results
        interview_texts = []
        if interview_results.get("documents") and len(interview_results["documents"]) > 0:
            # Flatten the results (ChromaDB returns lists of lists)
            for doc_list in interview_results["documents"]:
                interview_texts.extend(doc_list)
        
        context_texts = []
        if context_results.get("documents") and len(context_results["documents"]) > 0:
            for doc_list in context_results["documents"]:
                context_texts.extend(doc_list)
        
        # If no results from vector DB, fall back to full documents (for backward compatibility)
        if not interview_texts:
            logger.warning("No interview chunks found in vector DB, falling back to full documents")
            interview_texts = [interview.content for interview in interviews]
        
        if not context_texts:
            logger.warning("No context chunks found in vector DB, falling back to full documents")
            context_result = await session.execute(
                select(Document).where(Document.document_type == DocumentType.CONTEXT)
            )
            contexts = list(context_result.scalars().all())
            context_texts = [context.content for context in contexts]
        
        logger.info(f"Using {len(interview_texts)} interview chunks and {len(context_texts)} context chunks for persona generation")
        
        # Generate persona set using LLM with retrieved chunks
        persona_set_data = await llm_service.generate_persona_set(
            interview_documents=interview_texts,
            context_documents=context_texts,
            num_personas=num_personas
        )
        
        # Create persona set
        persona_set = PersonaSet(
            name=f"Persona Set {len(await PersonaService._get_all_persona_sets(session)) + 1}",
            description=persona_set_data.get("description", "Generated persona set")
        )
        session.add(persona_set)
        await session.flush()
        
        # Create basic personas
        personas_data = persona_set_data.get("personas", [])
        for persona_data in personas_data:
            persona = Persona(
                persona_set_id=persona_set.id,
                name=persona_data.get("name", "Unknown"),
                persona_data=persona_data
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
        
        # Use RAG to retrieve relevant context chunks
        context_results = await vector_db.query_documents(
            query_texts=[query],
            n_results=8,  # Get top 8 relevant chunks
            filter_metadata={"document_type": "context"}
        )
        
        # Extract document texts from vector DB results
        context_texts = []
        if context_results.get("documents") and len(context_results["documents"]) > 0:
            for doc_list in context_results["documents"]:
                context_texts.extend(doc_list)
        
        # Fall back to full documents if no chunks found
        if not context_texts:
            logger.warning("No context chunks found in vector DB, falling back to full documents")
            context_result = await session.execute(
                select(Document).where(Document.document_type == DocumentType.CONTEXT)
            )
            contexts = list(context_result.scalars().all())
            context_texts = [context.content for context in contexts]
        
        logger.info(f"Using {len(context_texts)} context chunks for persona expansion")
        
        # Expand persona using LLM with retrieved chunks
        expanded_data = await llm_service.expand_persona(
            persona_basic=persona.persona_data,
            context_documents=context_texts
        )
        
        # Update persona
        persona.persona_data = expanded_data
        await session.flush()
        await session.refresh(persona)
        
        return persona
    
    @staticmethod
    async def generate_persona_image(
        session: AsyncSession,
        persona_id: int
    ) -> Persona:
        """Generate an image for a persona."""
        result = await session.execute(
            select(Persona).where(Persona.id == persona_id)
        )
        persona = result.scalar_one_or_none()
        
        if not persona:
            raise ValueError(f"Persona with ID {persona_id} not found")
        
        # Generate image prompt
        image_prompt = await llm_service.generate_persona_image_prompt(persona.persona_data)
        
        # Generate image
        image_url = await llm_service.generate_image(image_prompt)
        
        # Update persona
        persona.image_url = image_url
        persona.image_prompt = image_prompt
        await session.flush()
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
        result = await session.execute(
            select(PersonaSet).where(PersonaSet.id == persona_set_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_persona_sets(
        session: AsyncSession
    ) -> List[PersonaSet]:
        """Get all persona sets."""
        result = await session.execute(select(PersonaSet))
        return list(result.scalars().all())
    
    @staticmethod
    async def _get_all_persona_sets(
        session: AsyncSession
    ) -> List[PersonaSet]:
        """Internal method to get all persona sets."""
        result = await session.execute(select(PersonaSet))
        return list(result.scalars().all())


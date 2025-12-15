"""
Persona generation and management service.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any

from app.models.persona import PersonaSet, Persona
from app.models.document import Document, DocumentType
from app.core.llm_service import llm_service
from app.schemas.persona import PersonaBasic


class PersonaService:
    """Service for persona generation and management."""
    
    @staticmethod
    async def generate_persona_set(
        session: AsyncSession,
        num_personas: int = 3
    ) -> PersonaSet:
        """Generate initial persona set with basic demographics."""
        # Get interview and context documents
        interview_result = await session.execute(
            select(Document).where(Document.document_type == DocumentType.INTERVIEW)
        )
        interviews = list(interview_result.scalars().all())
        
        context_result = await session.execute(
            select(Document).where(Document.document_type == DocumentType.CONTEXT)
        )
        contexts = list(context_result.scalars().all())
        
        if not interviews:
            raise ValueError("No interview documents found. Please process interview documents first.")
        
        # Extract content
        interview_texts = [interview.content for interview in interviews]
        context_texts = [context.content for context in contexts]
        
        # Generate persona set using LLM
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
        """Expand a basic persona into a full-fledged persona."""
        result = await session.execute(
            select(Persona).where(Persona.id == persona_id)
        )
        persona = result.scalar_one_or_none()
        
        if not persona:
            raise ValueError(f"Persona with ID {persona_id} not found")
        
        # Get context documents
        context_result = await session.execute(
            select(Document).where(Document.document_type == DocumentType.CONTEXT)
        )
        contexts = list(context_result.scalars().all())
        context_texts = [context.content for context in contexts]
        
        # Expand persona using LLM
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


"""
Persona generation and management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.persona import (
    PersonaSetCreateRequest,
    PersonaSetResponse,
    PersonaSetGenerateResponse,
    PersonaExpandResponse,
    PersonaImageResponse,
    PersonaResponse
)
from app.services.persona_service import PersonaService

router = APIRouter()


@router.post("/generate-set", response_model=PersonaSetGenerateResponse, status_code=status.HTTP_201_CREATED)
async def generate_persona_set(
    request: PersonaSetCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 1: Generate initial persona set with basic demographics.
    
    Creates a persona set based on processed interview documents.
    Returns basic personas with demographics.
    """
    try:
        persona_set = await PersonaService.generate_persona_set(
            session=db,
            num_personas=request.num_personas
        )
        
        # Convert to response format
        personas_basic = [
            PersonaBasic(**persona.persona_data)
            for persona in persona_set.personas
        ]
        
        return PersonaSetGenerateResponse(
            persona_set_id=persona_set.id,
            personas=personas_basic,
            status="created"
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating persona set: {str(e)}"
        )


@router.post("/{persona_set_id}/expand", response_model=List[PersonaExpandResponse])
async def expand_personas(
    persona_set_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 2: Expand all personas in a set into full-fledged personas.
    
    Takes basic personas and expands them with detailed information:
    - Personal background
    - Psychographics
    - Behaviors
    - Goals and challenges
    - Technology usage
    - Communication preferences
    """
    try:
        persona_set = await PersonaService.get_persona_set(db, persona_set_id)
        
        if not persona_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona set with ID {persona_set_id} not found"
            )
        
        expanded_personas = []
        for persona in persona_set.personas:
            expanded = await PersonaService.expand_persona(db, persona.id)
            expanded_personas.append(
                PersonaExpandResponse(
                    persona_id=expanded.id,
                    persona_data=expanded.persona_data,
                    status="expanded"
                )
            )
        
        return expanded_personas
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error expanding personas: {str(e)}"
        )


@router.post("/{persona_set_id}/generate-images", response_model=List[PersonaImageResponse])
async def generate_persona_images(
    persona_set_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 3: Generate images for all personas in a set.
    
    Creates AI-generated images for each persona based on their characteristics.
    """
    try:
        persona_set = await PersonaService.get_persona_set(db, persona_set_id)
        
        if not persona_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona set with ID {persona_set_id} not found"
            )
        
        image_responses = []
        for persona in persona_set.personas:
            updated = await PersonaService.generate_persona_image(db, persona.id)
            image_responses.append(
                PersonaImageResponse(
                    persona_id=updated.id,
                    image_url=updated.image_url,
                    image_prompt=updated.image_prompt,
                    status="image_generated"
                )
            )
        
        return image_responses
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating images: {str(e)}"
        )


@router.post("/{persona_set_id}/save", response_model=PersonaSetResponse)
async def save_persona_set(
    persona_set_id: int,
    name: str = None,
    description: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Save/update a persona set in the database.
    
    Persists the generated persona set with optional name and description updates.
    """
    try:
        persona_set = await PersonaService.save_persona_set(
            session=db,
            persona_set_id=persona_set_id,
            name=name,
            description=description
        )
        
        return PersonaSetResponse.model_validate(persona_set)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving persona set: {str(e)}"
        )


@router.get("/sets", response_model=List[PersonaSetResponse])
async def get_all_persona_sets(
    db: AsyncSession = Depends(get_db)
):
    """Get all saved persona sets."""
    persona_sets = await PersonaService.get_all_persona_sets(db)
    return [PersonaSetResponse.model_validate(ps) for ps in persona_sets]


@router.get("/sets/{persona_set_id}", response_model=PersonaSetResponse)
async def get_persona_set(
    persona_set_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific persona set by ID."""
    persona_set = await PersonaService.get_persona_set(db, persona_set_id)
    
    if not persona_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona set with ID {persona_set_id} not found"
        )
    
    return PersonaSetResponse.model_validate(persona_set)


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific persona by ID."""
    from sqlalchemy import select
    from app.models.persona import Persona
    
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona with ID {persona_id} not found"
        )
    
    return PersonaResponse.model_validate(persona)


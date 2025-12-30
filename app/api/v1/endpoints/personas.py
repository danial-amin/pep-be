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
from app.services.analytics_service import AnalyticsService

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
            num_personas=request.num_personas,
            context_details=request.context_details,
            interview_topic=request.interview_topic,
            user_study_design=request.user_study_design,
            include_ethical_guardrails=request.include_ethical_guardrails,
            output_format=request.output_format.value
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


@router.post("/persona/{persona_id}/generate-image", response_model=PersonaImageResponse)
async def generate_single_persona_image(
    persona_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate an image for a single persona.
    
    Creates an AI-generated image for the specified persona based on their characteristics.
    """
    try:
        updated = await PersonaService.generate_persona_image(db, persona_id)
        
        return PersonaImageResponse(
            persona_id=updated.id,
            image_url=updated.image_url,
            image_prompt=updated.image_prompt,
            status="image_generated"
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating image: {str(e)}"
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


@router.post("/load-default-personas", response_model=PersonaSetResponse)
async def load_default_personas(
    db: AsyncSession = Depends(get_db)
):
    """Load default personas from JSON file into a new persona set."""
    from app.utils.load_default_personas import load_default_personas, convert_persona_to_db_format
    from app.models.persona import PersonaSet, Persona
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    
    try:
        # Check if default persona set already exists (handle multiple results)
        result = await db.execute(
            select(PersonaSet)
            .where(PersonaSet.name == "Default Persona Set")
            .limit(1)
            .options(selectinload(PersonaSet.personas))
        )
        existing_set = result.scalar_one_or_none()
        
        if existing_set:
            # Return existing set with relationships already loaded
            return PersonaSetResponse.model_validate(existing_set)
        
        # Load personas from JSON
        default_data = load_default_personas()
        personas_data = default_data.get("personas", [])
        
        if not personas_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No default personas found in JSON file"
            )
        
        # Create persona set
        persona_set = PersonaSet(
            name="Default Persona Set",
            description=default_data.get("metadata", {}).get("context", "Default personas loaded from JSON"),
            status="generated",
            generation_cycle=1
        )
        db.add(persona_set)
        await db.flush()
        
        # Create personas
        for persona_data in personas_data:
            db_persona_data = convert_persona_to_db_format(persona_data)
            persona = Persona(
                persona_set_id=persona_set.id,
                name=db_persona_data["name"],
                persona_data=db_persona_data
            )
            db.add(persona)
        
        await db.commit()
        
        # Reload with relationships
        result = await db.execute(
            select(PersonaSet)
            .where(PersonaSet.id == persona_set.id)
            .options(selectinload(PersonaSet.personas))
        )
        persona_set = result.scalar_one()
        
        return PersonaSetResponse.model_validate(persona_set)
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading default personas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading default personas: {str(e)}"
        )


@router.post("/{persona_set_id}/measure-diversity")
async def measure_diversity(
    persona_set_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 2: Measure diversity of the persona set using RQE (Representation Quality Evaluation).
    
    Calculates how diverse the personas are and stores RQE scores.
    """
    try:
        metrics = await AnalyticsService.calculate_diversity(db, persona_set_id)
        return {
            "persona_set_id": persona_set_id,
            "metrics": metrics,
            "status": "diversity_measured"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error measuring diversity: {str(e)}"
        )


@router.post("/{persona_set_id}/validate")
async def validate_personas(
    persona_set_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Step 4: Validate personas against actual interview transcripts.
    
    Calculates cosine similarity between personas and real interview data.
    """
    try:
        validation = await AnalyticsService.validate_personas(db, persona_set_id)
        return validation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating personas: {str(e)}"
        )


@router.get("/{persona_set_id}/analytics")
async def get_analytics(
    persona_set_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get complete analytics report for a persona set."""
    try:
        report = await AnalyticsService.get_analytics_report(db, persona_set_id)
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting analytics: {str(e)}"
        )


@router.get("/{persona_set_id}/download")
async def download_personas_json(
    persona_set_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Download persona set as JSON."""
    from fastapi.responses import JSONResponse
    
    try:
        report = await AnalyticsService.get_analytics_report(db, persona_set_id)
        return JSONResponse(
            content=report,
            headers={
                "Content-Disposition": f"attachment; filename=persona_set_{persona_set_id}.json"
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading personas: {str(e)}"
        )


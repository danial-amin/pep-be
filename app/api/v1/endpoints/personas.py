"""
Persona generation and management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pathlib import Path

from app.core.database import get_db
from app.schemas.persona import (
    PersonaSetCreateRequest,
    PersonaSetResponse,
    PersonaSetGenerateResponse,
    PersonaExpandResponse,
    PersonaImageResponse,
    PersonaResponse,
    PersonaBasic
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
            output_format=request.output_format.value,
            document_ids=request.document_ids,
            project_id=request.project_id
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


@router.post("/{persona_set_id}/expand", response_model=List[PersonaResponse])
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
            # Return full PersonaResponse instead of just PersonaExpandResponse
            # This ensures image_url and image_prompt are included
            expanded_personas.append(
                PersonaResponse(
                    id=expanded.id,
                    persona_set_id=expanded.persona_set_id,
                    name=expanded.name,
                    persona_data=expanded.persona_data,
                    image_url=expanded.image_url,
                    image_prompt=expanded.image_prompt,
                    similarity_score=expanded.similarity_score,
                    validation_status=expanded.validation_status,
                    created_at=expanded.created_at,
                    updated_at=expanded.updated_at
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
    """
    Get all saved persona sets.
    
    Returns all persona sets in the database, including:
    - Generated persona sets
    - Loaded default persona sets (from JSON files)
    - Each set appears as a separate, distinct entry with its own ID, name, and personas
    """
    persona_sets = await PersonaService.get_all_persona_sets(db)
    # Sort by created_at (newest first) so recently loaded sets appear first
    persona_sets.sort(key=lambda x: x.created_at if x.created_at else x.id, reverse=True)
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
    set_name: str = Query(None, description="Name of the persona set to load (e.g., 'finland', 'CB')"),
    file_path: str = Query(None, description="Specific file path to load from"),
    persona_set_name: str = Query(None, description="Custom name for the persona set in the database"),
    overwrite: bool = Query(False, description="If True, overwrite existing persona set with same name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Load default personas from JSON file into a persona set.
    
    Args:
        set_name: Optional name of the persona set to load (e.g., "set1", "set2").
                  Looks for files like "default_personas_set1.json"
        file_path: Optional specific file path to load from
        persona_set_name: Optional custom name for the persona set in the database.
                         If not provided, uses metadata from JSON or generates a name.
        overwrite: If True and a persona set with the same name exists, overwrite it.
                  If False (default), returns existing set if found.
    """
    from app.utils.load_default_personas import load_default_personas, convert_persona_to_db_format, list_available_persona_sets
    from app.models.persona import PersonaSet, Persona
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    
    try:
        # Load personas from JSON
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Loading personas with set_name={set_name}, file_path={file_path}")
        
        # If no set_name provided, try to load all available sets
        if not set_name and not file_path:
            available_sets = list_available_persona_sets()
            if not available_sets:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No persona set files found. Please specify a set_name or file_path."
                )
            
            # Load all available sets
            loaded_sets = []
            for available_set in available_sets:
                try:
                    set_name_to_load = available_set['name']
                    logger.info(f"Loading persona set: {set_name_to_load}")
                    
                    default_data = load_default_personas(set_name=set_name_to_load)
                    personas_data = default_data.get("personas", [])
                    
                    if not personas_data:
                        logger.warning(f"No personas found in set '{set_name_to_load}', skipping")
                        continue
                    
                    # Determine persona set name
                    if persona_set_name and len(available_sets) == 1:
                        final_set_name = persona_set_name
                    else:
                        metadata_name = default_data.get("metadata", {}).get("name")
                        if metadata_name:
                            final_set_name = metadata_name
                        elif set_name_to_load and set_name_to_load != "default":
                            final_set_name = f"{set_name_to_load.replace('_', ' ').title()} Persona Set"
                        else:
                            final_set_name = "Default Persona Set"
                    
                    # Build description
                    base_description = default_data.get("metadata", {}).get("context", "")
                    source_info = [f"Loaded from set: {set_name_to_load}"]
                    source_text = " | ".join(source_info)
                    final_description = f"{base_description} ({source_text})" if base_description else source_text
                    
                    # Check if persona set already exists
                    result = await db.execute(
                        select(PersonaSet)
                        .where(PersonaSet.name == final_set_name)
                        .limit(1)
                        .options(selectinload(PersonaSet.personas))
                    )
                    existing_set = result.scalar_one_or_none()
                    
                    if existing_set:
                        if overwrite:
                            # Delete existing personas
                            for persona in existing_set.personas:
                                await db.delete(persona)
                            await db.flush()
                            existing_set.description = final_description
                            persona_set = existing_set
                        else:
                            # Return existing set
                            loaded_sets.append(PersonaSetResponse.model_validate(existing_set))
                            continue
                    else:
                        # Create new persona set
                        persona_set = PersonaSet(
                            name=final_set_name,
                            description=final_description,
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
                    
                    await db.flush()
                    
                    # Reload with relationships
                    result = await db.execute(
                        select(PersonaSet)
                        .where(PersonaSet.id == persona_set.id)
                        .options(selectinload(PersonaSet.personas))
                    )
                    persona_set = result.scalar_one()
                    loaded_sets.append(PersonaSetResponse.model_validate(persona_set))
                    
                except Exception as e:
                    logger.warning(f"Error loading set '{available_set['name']}': {e}", exc_info=True)
                    continue
            
            await db.commit()
            
            if not loaded_sets:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Could not load any persona sets. Available sets: {[s['name'] for s in available_sets]}"
                )
            
            # Return the first loaded set (or last if multiple)
            logger.info(f"Successfully loaded {len(loaded_sets)} persona set(s)")
            return loaded_sets[-1]  # Return the last loaded set
        
        # Single set loading (when set_name or file_path is provided)
        default_data = load_default_personas(file_path=file_path, set_name=set_name)
        personas_data = default_data.get("personas", [])
        
        logger.info(f"Loaded data keys: {list(default_data.keys())}, personas count: {len(personas_data)}")
        
        if not personas_data:
            available_sets = list_available_persona_sets()
            logger.warning(f"No personas found in loaded data. Available sets: {[s['name'] for s in available_sets]}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No personas found in set '{set_name or 'default'}'. Available sets: {[s['name'] for s in available_sets]}. Make sure the JSON file has a 'personas' array with persona objects."
            )
        
        # Determine persona set name - make it clear this is a distinct set
        if persona_set_name:
            final_set_name = persona_set_name
        else:
            # Use metadata name, or set_name, or default
            metadata_name = default_data.get("metadata", {}).get("name")
            if metadata_name:
                final_set_name = metadata_name
            elif set_name and set_name != "default":
                # Make it clear this is a separate set (e.g., "Set 1", "Research Set")
                final_set_name = f"{set_name.replace('_', ' ').title()} Persona Set"
            else:
                final_set_name = "Default Persona Set"
        
        # Build description with source information
        base_description = default_data.get("metadata", {}).get("context", "")
        source_info = []
        if set_name:
            source_info.append(f"Loaded from set: {set_name}")
        if file_path:
            source_info.append(f"File: {Path(file_path).name}")
        if source_info:
            source_text = " | ".join(source_info)
            final_description = f"{base_description} ({source_text})" if base_description else source_text
        else:
            final_description = base_description or "Default personas loaded from JSON"
        
        # Check if persona set with this name already exists
        result = await db.execute(
            select(PersonaSet)
            .where(PersonaSet.name == final_set_name)
            .limit(1)
            .options(selectinload(PersonaSet.personas))
        )
        existing_set = result.scalar_one_or_none()
        
        if existing_set:
            if overwrite:
                # Delete existing personas
                for persona in existing_set.personas:
                    await db.delete(persona)
                await db.flush()
                # Update set metadata
                existing_set.description = default_data.get("metadata", {}).get("context", f"Personas loaded from {set_name or 'default'}")
            else:
                # Return existing set
                return PersonaSetResponse.model_validate(existing_set)
        
        # Create or update persona set
        if existing_set and overwrite:
            persona_set = existing_set
            persona_set.name = final_set_name  # Update name in case it changed
            persona_set.description = final_description
        else:
            persona_set = PersonaSet(
                name=final_set_name,
                description=final_description,
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


@router.get("/available-persona-sets")
async def get_available_persona_sets():
    """Get list of available persona set files that can be loaded."""
    from app.utils.load_default_personas import list_available_persona_sets
    
    try:
        sets = list_available_persona_sets()
        return {
            "available_sets": sets,
            "count": len(sets)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing available persona sets: {str(e)}"
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


@router.post("/migrate-to-nested")
async def migrate_personas_to_nested(
    db: AsyncSession = Depends(get_db)
):
    """
    Migrate all personas in the database to the standard nested structure.
    
    This endpoint normalizes all existing personas to use the nested structure
    with a demographics object and arrays for goals/frustrations.
    """
    from app.utils.migrate_personas_to_nested import migrate_all_personas_to_nested
    
    try:
        migrated_count = await migrate_all_personas_to_nested()
        return {
            "message": f"Migration completed successfully",
            "personas_migrated": migrated_count
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error during migration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error migrating personas: {str(e)}"
        )


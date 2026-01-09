"""
Migration script to convert all existing personas to the standard nested structure.

Run this script to normalize all personas in the database to the nested format.
"""
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.persona import Persona
from app.utils.persona_normalizer import normalize_persona_to_nested
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


async def migrate_all_personas_to_nested():
    """
    Migrate all personas in the database to the standard nested structure.
    
    This function:
    1. Loads all personas from the database
    2. Normalizes each persona to nested structure
    3. Updates the persona_data in the database
    """
    async with AsyncSessionLocal() as session:
        try:
            # Get all personas
            result = await session.execute(select(Persona))
            personas = result.scalars().all()
            
            logger.info(f"Found {len(personas)} personas to migrate")
            
            migrated_count = 0
            for persona in personas:
                try:
                    # Check if already in nested format (has demographics object)
                    if isinstance(persona.persona_data, dict):
                        has_demographics = "demographics" in persona.persona_data
                        has_flat_demographics = any(key in persona.persona_data for key in ["age", "gender", "occupation"])
                        
                        # Only migrate if it's flat structure
                        if has_flat_demographics and not has_demographics:
                            # Normalize to nested structure
                            normalized_data = normalize_persona_to_nested(persona.persona_data)
                            persona.persona_data = normalized_data
                            migrated_count += 1
                            logger.info(f"Migrated persona {persona.id}: {persona.name}")
                        elif has_demographics:
                            # Already nested, but ensure it's fully normalized
                            normalized_data = normalize_persona_to_nested(persona.persona_data)
                            # Only update if there were changes
                            if normalized_data != persona.persona_data:
                                persona.persona_data = normalized_data
                                migrated_count += 1
                                logger.info(f"Normalized persona {persona.id}: {persona.name}")
                except Exception as e:
                    logger.error(f"Error migrating persona {persona.id}: {e}", exc_info=True)
                    continue
            
            await session.commit()
            logger.info(f"Migration complete: {migrated_count} personas migrated/normalized")
            return migrated_count
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error during migration: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    asyncio.run(migrate_all_personas_to_nested())

"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Add new columns if they don't exist (for existing databases)
        # This is a fallback if migrations haven't been run
        try:
            from sqlalchemy import text
            # PostgreSQL doesn't support IF NOT EXISTS for ADD COLUMN, so we'll use DO blocks
            await conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='persona_sets' AND column_name='rqe_scores') THEN
                        ALTER TABLE persona_sets ADD COLUMN rqe_scores JSONB;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='persona_sets' AND column_name='diversity_score') THEN
                        ALTER TABLE persona_sets ADD COLUMN diversity_score JSONB;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='persona_sets' AND column_name='validation_scores') THEN
                        ALTER TABLE persona_sets ADD COLUMN validation_scores JSONB;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='persona_sets' AND column_name='generation_cycle') THEN
                        ALTER TABLE persona_sets ADD COLUMN generation_cycle INTEGER DEFAULT 1;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='persona_sets' AND column_name='status') THEN
                        ALTER TABLE persona_sets ADD COLUMN status VARCHAR(50) DEFAULT 'generated';
                    END IF;
                END $$;
            """))
            await conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='personas' AND column_name='similarity_score') THEN
                        ALTER TABLE personas ADD COLUMN similarity_score JSONB;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='personas' AND column_name='validation_status') THEN
                        ALTER TABLE personas ADD COLUMN validation_status VARCHAR(50);
                    END IF;
                END $$;
            """))
            await conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='documents' AND column_name='project_id') THEN
                        ALTER TABLE documents ADD COLUMN project_id VARCHAR(255);
                        CREATE INDEX IF NOT EXISTS ix_documents_project_id ON documents(project_id);
                    END IF;
                END $$;
            """))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not add columns automatically: {e}. Run migrations manually if needed.", exc_info=True)
    
    # Create default documents
    try:
        from app.core.database import AsyncSessionLocal
        from app.utils.default_documents import create_default_documents
        async with AsyncSessionLocal() as session:
            await create_default_documents(session)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not create default documents: {e}", exc_info=True)
    
    # Load default personas if they don't exist
    from app.utils.load_default_personas import load_default_personas, convert_persona_to_db_format
    from app.models.persona import PersonaSet, Persona
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        # Check if default persona set already exists (handle multiple results)
        result = await session.execute(
            select(PersonaSet).where(PersonaSet.name == "Default Persona Set").limit(1)
        )
        existing_set = result.scalar_one_or_none()
        
        if not existing_set:
            try:
                # Load personas from JSON
                default_data = load_default_personas()
                personas_data = default_data.get("personas", [])
                
                if personas_data:
                    # Create persona set
                    persona_set = PersonaSet(
                        name="Default Persona Set",
                        description=default_data.get("metadata", {}).get("context", "Default personas loaded from JSON"),
                        status="generated",
                        generation_cycle=1
                    )
                    session.add(persona_set)
                    await session.flush()
                    
                    # Create personas
                    for persona_data in personas_data:
                        db_persona_data = convert_persona_to_db_format(persona_data)
                        persona = Persona(
                            persona_set_id=persona_set.id,
                            name=db_persona_data["name"],
                            persona_data=db_persona_data
                        )
                        session.add(persona)
                    
                    await session.commit()
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Loaded {len(personas_data)} default personas on startup")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not load default personas on startup: {e}", exc_info=True)
                await session.rollback()
    
    yield
    # Shutdown
    pass


app = FastAPI(
    title="PEP - Persona Generator API",
    description="Automatic persona generator from unstructured data",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
# The field_validator in Settings already parses CORS_ORIGINS to a list
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Mount static files for persona images
static_dir = Path("/app/static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PEP - Persona Generator API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/healthcheck")
async def health_check_alias():
    """Health check endpoint (alias for /health)."""
    return {"status": "healthy"}


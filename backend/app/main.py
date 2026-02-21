"""
Main FastAPI application entry point.
"""
import asyncio
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)


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
                                   WHERE table_name='persona_sets' AND column_name='generation_config') THEN
                        ALTER TABLE persona_sets ADD COLUMN generation_config JSONB;
                    END IF;
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
                                   WHERE table_name='persona_sets' AND column_name='max_iterations') THEN
                        ALTER TABLE persona_sets ADD COLUMN max_iterations INTEGER DEFAULT 3;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='persona_sets' AND column_name='rqe_threshold') THEN
                        ALTER TABLE persona_sets ADD COLUMN rqe_threshold DOUBLE PRECISION DEFAULT 0.75;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='persona_sets' AND column_name='status') THEN
                        ALTER TABLE persona_sets ADD COLUMN status VARCHAR(50) DEFAULT 'generated';
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='persona_sets' AND column_name='evaluation_scores') THEN
                        ALTER TABLE persona_sets ADD COLUMN evaluation_scores JSONB;
                    END IF;
                END $$;
            """))
            # Human intervention support on simulation_messages
            await conn.execute(text("""
                DO $$ 
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='simulation_messages') THEN
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                       WHERE table_name='simulation_messages' AND column_name='is_human_message') THEN
                            ALTER TABLE simulation_messages ADD COLUMN is_human_message BOOLEAN DEFAULT false;
                        END IF;
                        IF EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='simulation_messages' AND column_name='persona_id'
                                   AND is_nullable = 'NO') THEN
                            ALTER TABLE simulation_messages ALTER COLUMN persona_id DROP NOT NULL;
                        END IF;
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
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='personas' AND column_name='source_references') THEN
                        ALTER TABLE personas ADD COLUMN source_references JSONB;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='personas' AND column_name='attribute_validation') THEN
                        ALTER TABLE personas ADD COLUMN attribute_validation JSONB;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='personas' AND column_name='image_data') THEN
                        ALTER TABLE personas ADD COLUMN image_data TEXT;
                    END IF;
                END $$;
            """))
            # Create projects table first (before adding foreign keys)
            await conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.tables 
                                   WHERE table_name='projects') THEN
                        CREATE TABLE projects (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            field_of_study VARCHAR(255),
                            core_objective TEXT,
                            includes_context BOOLEAN DEFAULT true,
                            includes_interviews BOOLEAN DEFAULT true,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                            updated_at TIMESTAMP WITH TIME ZONE
                        );
                        CREATE INDEX IF NOT EXISTS ix_projects_id ON projects(id);
                    END IF;
                END $$;
            """))
            # Handle documents.project_id - add if missing, or convert from VARCHAR to INTEGER if exists
            await conn.execute(text("""
                DO $$ 
                DECLARE
                    col_type text;
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='documents' AND column_name='project_id') THEN
                        ALTER TABLE documents ADD COLUMN project_id INTEGER;
                        CREATE INDEX IF NOT EXISTS ix_documents_project_id ON documents(project_id);
                    ELSE
                        -- Check if column is VARCHAR and convert to INTEGER
                        SELECT data_type INTO col_type 
                        FROM information_schema.columns 
                        WHERE table_name='documents' AND column_name='project_id';
                        
                        IF col_type = 'character varying' THEN
                            -- Convert VARCHAR to INTEGER (set NULL for non-numeric values first)
                            UPDATE documents SET project_id = NULL WHERE project_id !~ '^[0-9]+$';
                            ALTER TABLE documents ALTER COLUMN project_id TYPE INTEGER USING project_id::INTEGER;
                        END IF;
                    END IF;
                END $$;
            """))
            # Add project_id to persona_sets if it doesn't exist
            await conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='persona_sets' AND column_name='project_id') THEN
                        ALTER TABLE persona_sets ADD COLUMN project_id INTEGER;
                        CREATE INDEX IF NOT EXISTS ix_persona_sets_project_id ON persona_sets(project_id);
                        -- Add foreign key constraint (projects table should exist by now)
                        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='projects') THEN
                            ALTER TABLE persona_sets 
                            ADD CONSTRAINT fk_persona_sets_project_id 
                            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL;
                        END IF;
                    END IF;
                END $$;
            """))
            # Document background processing: file_path, processing_status, processing_error; content nullable
            await conn.execute(text("""
                DO $$ 
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='documents') THEN
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                       WHERE table_name='documents' AND column_name='file_path') THEN
                            ALTER TABLE documents ADD COLUMN file_path VARCHAR(512);
                        END IF;
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                       WHERE table_name='documents' AND column_name='processing_status') THEN
                            ALTER TABLE documents ADD COLUMN processing_status VARCHAR(20) NOT NULL DEFAULT 'completed';
                        END IF;
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                       WHERE table_name='documents' AND column_name='processing_error') THEN
                            ALTER TABLE documents ADD COLUMN processing_error TEXT;
                        END IF;
                        ALTER TABLE documents ALTER COLUMN content DROP NOT NULL;
                    END IF;
                END $$;
            """))
        except Exception as e:
            logger.warning(f"Could not add columns automatically: {e}. Run migrations manually if needed.", exc_info=True)
    
    # Create default documents
    try:
        from app.core.database import AsyncSessionLocal
        from app.utils.default_documents import create_default_documents
        async with AsyncSessionLocal() as session:
            await create_default_documents(session)
    except Exception as e:
        logger.warning(f"Could not create default documents: {e}", exc_info=True)
    
    # Load default persona sets from default_personas/ (e.g. CB, finland, molt) — idempotent; you can attach sets to projects yourself
    from app.utils.load_default_personas import (
        load_default_personas,
        list_available_persona_sets,
        convert_persona_to_db_format,
    )
    from app.models.persona import PersonaSet, Persona
    from sqlalchemy import select

    # Only load from default_personas/*.json (e.g. CB, finland, molt); do not fall back to default_personas.json
    available_sets = list_available_persona_sets()
    async with AsyncSessionLocal() as session:
        for set_info in available_sets:
            set_name = set_info.get("name") or set_info.get("filename", "").replace(".json", "")
            if not set_name or set_name == "default" or set_name == "Default Persona Set":
                continue
            # Idempotent: skip if a persona set with this name already exists
            result = await session.execute(
                select(PersonaSet).where(PersonaSet.name == set_name).limit(1)
            )
            if result.scalar_one_or_none():
                continue
            try:
                default_data = load_default_personas(set_name=set_name)
                personas_data = default_data.get("personas", [])
                if not personas_data:
                    continue
                description = default_data.get("metadata", {}).get("context") or f"Default personas from {set_name}"
                persona_set = PersonaSet(
                    name=set_name,
                    description=description,
                    status="generated",
                    generation_cycle=1,
                    project_id=None,
                )
                session.add(persona_set)
                await session.flush()
                for persona_data in personas_data:
                    db_persona_data = convert_persona_to_db_format(persona_data)
                    raw = persona_data if isinstance(persona_data, dict) else {}
                    persona = Persona(
                        persona_set_id=persona_set.id,
                        name=db_persona_data["name"],
                        persona_data=db_persona_data,
                        image_url=raw.get("image_url"),
                        image_data=raw.get("image_data"),
                    )
                    session.add(persona)
                await session.commit()
                logger.info("Loaded default persona set %s (%d personas); attach to a project in the UI if needed", set_name, len(personas_data))
            except Exception as e:
                logger.warning("Could not load default persona set %s: %s", set_name, e, exc_info=True)
                await session.rollback()

    # Re-enqueue any documents that were pending when the server was last stopped
    async def re_enqueue_pending_documents_on_startup():
        try:
            from sqlalchemy import select
            from app.models.document import Document, ProcessingStatus
            from app.core.database import AsyncSessionLocal
            from app.core.queue import enqueue_document_job
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Document).where(
                        Document.processing_status == ProcessingStatus.PENDING,
                        Document.file_path.isnot(None),
                    )
                )
                pending = list(result.scalars().all())
            for doc in pending:
                try:
                    await enqueue_document_job(doc.id)
                except Exception as e:
                    logger.warning("Could not enqueue document %s: %s", doc.id, e)
            if pending:
                logger.info("Re-enqueued %d pending document(s) for worker processing", len(pending))
        except Exception as e:
            logger.warning("Could not re-enqueue pending documents on startup: %s", e, exc_info=True)

    asyncio.create_task(re_enqueue_pending_documents_on_startup())

    # Automatically reprocess documents that have content but no vectors (old records → vectors)
    async def reprocess_documents_on_startup():
        import logging as _logging
        _log = _logging.getLogger(__name__)
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.document_service import DocumentService
            async with AsyncSessionLocal() as session:
                result = await DocumentService.reprocess_documents(
                    session, document_ids=None, force=False
                )
                await session.commit()
            processed, skipped, errors = result["processed"], result["skipped"], result["errors"]
            if processed or errors:
                _log.info(
                    "Startup reprocess: %d processed, %d skipped, %d errors",
                    len(processed),
                    len(skipped),
                    len(errors),
                )
                for e in errors:
                    _log.warning("Reprocess error document_id=%s: %s", e["document_id"], e["error"])
        except Exception as e:
            _log.warning("Could not reprocess documents on startup: %s", e, exc_info=True)

    asyncio.create_task(reprocess_documents_on_startup())

    yield
    # Shutdown
    pass


app = FastAPI(
    title="PEP - Persona Generator API",
    description="Automatic persona generator from unstructured data",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - must allow frontend origin in production
# Use CORS_ORIGINS env var: "*" or "https://frontend-production-eae1.up.railway.app" or comma-separated list
_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
if not _origins or (len(_origins) == 1 and not _origins[0].strip()):
    _origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def _cors_headers(origin: str | None = None) -> dict:
    """Build CORS headers so error responses don't trigger browser CORS errors."""
    origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
    if not origins or (len(origins) == 1 and not str(origins[0]).strip()):
        origins = ["*"]
    if origins == ["*"]:
        allow_origin = origin or "*"
    else:
        allow_origin = (origin if origin in origins else (origins[0] if origins else "*"))
    return {
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure 500 and other unhandled errors return JSON with CORS headers so browser shows real error."""
    logger.exception("Unhandled exception: %s", exc)
    origin = request.headers.get("origin")
    headers = _cors_headers(origin)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers,
    )

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Mount static files for persona images (use STATIC_DIR so volume e.g. /data/static can be used)
static_dir = Path(settings.STATIC_DIR)
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


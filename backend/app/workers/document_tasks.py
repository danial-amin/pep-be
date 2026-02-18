"""
ARQ worker tasks for document processing.

Worker fetches job from Redis, loads document from storage, parses, and upserts to vector DB.
"""
import logging
from pathlib import Path

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.storage import fetch_to_temp_file, delete_file, S3_KEY_PREFIX
from app.models.document import Document, ProcessingStatus
from app.services.document_service import DocumentService
from app.utils.file_processing import extract_text_from_file

logger = logging.getLogger(__name__)


async def process_document_task(ctx: dict, document_id: int) -> None:
    """
    ARQ task: process a document (parse, chunk, embed, upsert to vector DB).
    """
    storage_location: str | None = None
    temp_path: str | None = None
    filename: str = ""

    async with AsyncSessionLocal() as session:
        try:
            document = await DocumentService.get_document(session, document_id)
            if not document:
                logger.error("Document %s not found", document_id)
                return
            if document.processing_status != ProcessingStatus.PENDING:
                logger.info("Document %s not pending (status=%s), skipping", document_id, document.processing_status)
                return
            if not document.file_path:
                logger.error("Document %s has no file_path/storage_location", document_id)
                document.processing_status = ProcessingStatus.FAILED
                document.processing_error = "No storage location for pending document"
                await session.commit()
                return

            storage_location = document.file_path
            filename = document.filename
            document.processing_status = ProcessingStatus.PROCESSING
            await session.commit()
        except Exception as e:
            logger.exception("Error loading document %s: %s", document_id, e)
            return

    # Fetch file to temp path (works for both local and S3)
    try:
        if storage_location.startswith(S3_KEY_PREFIX):
            suffix = Path(filename).suffix if filename else ""
            temp_path = await fetch_to_temp_file(storage_location, suffix=suffix)
        else:
            # Local path - file already on disk
            temp_path = storage_location
            if not Path(temp_path).exists():
                async with AsyncSessionLocal() as session:
                    doc = await DocumentService.get_document(session, document_id)
                    if doc:
                        doc.processing_status = ProcessingStatus.FAILED
                        doc.processing_error = "Stored file not found"
                        await session.commit()
                return

        file_ext = Path(filename).suffix.lower()
        content = await extract_text_from_file(temp_path, file_ext)
    except Exception as e:
        logger.exception("Error fetching/extracting document %s: %s", document_id, e)
        async with AsyncSessionLocal() as session:
            doc = await DocumentService.get_document(session, document_id)
            if doc:
                doc.processing_status = ProcessingStatus.FAILED
                doc.processing_error = str(e)
                await session.commit()
        return
    finally:
        # Only delete temp file if we created one (S3 fetch)
        if temp_path and storage_location and storage_location.startswith(S3_KEY_PREFIX) and temp_path != storage_location:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except OSError:
                pass

    if not content or not content.strip():
        async with AsyncSessionLocal() as session:
            doc = await DocumentService.get_document(session, document_id)
            if doc:
                doc.processing_status = ProcessingStatus.FAILED
                doc.processing_error = "No text extracted from file"
                await session.commit()
        return

    # Process and upsert
    try:
        async with AsyncSessionLocal() as session:
            document = await DocumentService.get_document(session, document_id)
            if not document or document.processing_status != ProcessingStatus.PROCESSING:
                return
            await DocumentService.process_document_content_into_existing(session, document, content)
            document.processing_status = ProcessingStatus.COMPLETED
            document.processing_error = None
            document.file_path = None  # Clear storage ref after successful processing
            await session.commit()
        logger.info("Document %s processed successfully", document_id)
        # Delete stored file only on success (keep on failure so user can retry)
        if storage_location:
            await delete_file(storage_location)
    except Exception as e:
        logger.exception("Processing failed for document %s: %s", document_id, e)
        async with AsyncSessionLocal() as session:
            doc = await DocumentService.get_document(session, document_id)
            if doc:
                doc.processing_status = ProcessingStatus.FAILED
                doc.processing_error = str(e)
                # Keep file_path so user can retry via /retry endpoint
                await session.commit()
        return


def _get_redis_settings():
    """Parse REDIS_URL into ARQ RedisSettings."""
    import urllib.parse
    url = settings.REDIS_URL
    parsed = urllib.parse.urlparse(url)
    from arq.connections import RedisSettings
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/")) if parsed.path else 0,
    )


class WorkerSettings:
    """ARQ worker configuration. Run with: arq app.workers.document_tasks.WorkerSettings"""
    redis_settings = None  # Set below after config load
    functions = [process_document_task]
    queue_name = "arq:document_queue"
    max_jobs = 5
    job_timeout = 600  # 10 min per document
    max_tries = 3
    retry_delay = 60


# Set redis_settings at module load (config is already loaded)
WorkerSettings.redis_settings = _get_redis_settings()

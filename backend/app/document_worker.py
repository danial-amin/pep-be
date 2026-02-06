"""
Document processing worker for Railway (no Celery).

Polls for PENDING documents and processes them into vectors. Run as a separate
Railway service so uploads get processed even when the web process doesn't
complete BackgroundTasks (e.g. request timeout, restart).

Usage:
  python -m app.document_worker

Environment:
  Same as the API: DATABASE_URL, OPENAI_API_KEY, PINECONE_*, UPLOAD_DIR (use a
  Railway Volume path like /data/uploads so the worker can read files written by the web service).
"""
import asyncio
import logging
import os
import sys

# Ensure backend app is on path when run as python -m app.document_worker from repo root
if __name__ == "__main__" and os.path.basename(os.getcwd()) != "app":
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("document_worker")

POLL_INTERVAL_SECONDS = int(os.environ.get("DOCUMENT_WORKER_POLL_SECONDS", "20"))
BATCH_DELAY_SECONDS = float(os.environ.get("DOCUMENT_WORKER_BATCH_DELAY", "2.0"))


async def run_worker() -> None:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.document import Document, ProcessingStatus
    from app.services.document_service import DocumentService

    logger.info(
        "Document worker started (poll every %ss, batch delay %ss)",
        POLL_INTERVAL_SECONDS,
        BATCH_DELAY_SECONDS,
    )
    while True:
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Document).where(
                        Document.processing_status == ProcessingStatus.PENDING,
                        Document.file_path.isnot(None),
                    )
                )
                pending = list(result.scalars().all())
            if not pending:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue
            logger.info("Processing %d pending document(s)", len(pending))
            for doc in pending:
                try:
                    await DocumentService.process_document_background(doc.id)
                except Exception as e:
                    logger.exception("Failed to process document %s: %s", doc.id, e)
                await asyncio.sleep(BATCH_DELAY_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Worker loop error: %s", e)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

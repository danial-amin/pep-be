"""
Redis queue for document processing using ARQ.

Enqueue jobs from the API; worker processes them reliably.
"""
import logging
import urllib.parse

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)


def _parse_redis_url(url: str) -> RedisSettings:
    """Parse REDIS_URL into RedisSettings."""
    parsed = urllib.parse.urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/")) if parsed.path else 0,
    )


async def enqueue_document_job(document_id: int) -> None:
    """
    Enqueue a document processing job.
    Call this after storing the file and creating the pending document record.
    """
    redis_settings = _parse_redis_url(settings.REDIS_URL)
    # IMPORTANT: Ensure the enqueue queue matches the worker queue name.
    # The worker listens on "arq:document_queue" (see app/workers/document_tasks.py).
    redis = await create_pool(
        redis_settings,
        default_queue_name="arq:document_queue",
    )
    try:
        job = await redis.enqueue_job(
            "process_document_task",
            document_id,
            _queue_name="arq:document_queue",
        )
        logger.info("Enqueued document job %s for document_id=%s", job and job.job_id, document_id)
    finally:
        await redis.close()

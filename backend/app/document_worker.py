"""
Document processing worker - ARQ (Redis queue).

Runs ARQ worker that processes jobs from Redis. Use this instead of the old
polling worker for reliable document processing.

Usage:
  python -m app.document_worker

Or directly:
  arq app.workers.document_tasks.WorkerSettings

Environment:
  Same as API: DATABASE_URL, OPENAI_API_KEY, PINECONE_*, REDIS_URL.
  Storage: UPLOAD_DIR (local) or S3_* (Railway Storage Buckets).
"""
import logging
import os
import sys

if __name__ == "__main__" and os.path.basename(os.getcwd()) != "app":
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("document_worker")


def main() -> None:
    from arq import run_worker
    from app.workers.document_tasks import WorkerSettings

    logger.info("Starting ARQ document worker (Redis queue)")
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()

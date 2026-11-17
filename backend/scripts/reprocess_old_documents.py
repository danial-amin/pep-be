"""
Reprocess old documents: convert content → vectors, and list those that need re-upload.

Use when documents were uploaded but never processed into vectors (e.g. on Railway
before adding the worker). Documents that have content in the DB are reprocessed
into vectors; documents with no content (file lost) are listed so you can re-upload.

Usage (from backend/):
  python scripts/reprocess_old_documents.py
  python scripts/reprocess_old_documents.py --project-id 1
  python scripts/reprocess_old_documents.py --force   # re-vector even if vector_id exists
"""
import argparse
import asyncio
import logging
import os
import sys

# Ensure backend app is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reprocess old documents (content → vectors) and list need-reupload."
    )
    parser.add_argument("--project-id", type=int, default=None, help="Filter by project ID.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-vector even when vector_id exists (replaces existing vectors).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list need-reupload and candidates; do not reprocess.",
    )
    return parser.parse_args()


async def main() -> None:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.document import Document, ProcessingStatus
    from app.services.document_service import DocumentService

    args = _parse_args()

    async with AsyncSessionLocal() as session:
        # 1. List documents that need re-upload (no content, pending/failed)
        need_reupload = await DocumentService.get_need_reupload(
            session, project_id=args.project_id
        )
        if need_reupload:
            logger.info(
                "Documents that need RE-UPLOAD (%d): file was lost or never processed",
                len(need_reupload),
            )
            for doc in need_reupload:
                logger.info(
                    "  id=%s filename=%s status=%s error=%s",
                    doc.id,
                    doc.filename,
                    doc.processing_status,
                    (doc.processing_error or "")[:80],
                )
        else:
            logger.info("No documents need re-upload.")

        if args.dry_run:
            # Show how many would be reprocessed
            query = select(Document).where(
                Document.content.isnot(None),
                Document.content != "",
            )
            if args.project_id is not None:
                query = query.where(Document.project_id == args.project_id)
            if not args.force:
                query = query.where(Document.vector_id.is_(None))
            result = await session.execute(query)
            candidates = list(result.scalars().all())
            logger.info(
                "Would reprocess %d document(s) (content → vectors). Run without --dry-run to apply.",
                len(candidates),
            )
            return

        # 2. Reprocess documents that have content but no/missing vectors
        document_ids = None
        if args.project_id is not None:
            result = await session.execute(
                select(Document.id).where(Document.project_id == args.project_id)
            )
            document_ids = [r[0] for r in result.fetchall()]
        result = await DocumentService.reprocess_documents(
            session,
            document_ids=document_ids,
            force=args.force,
        )
        await session.commit()

        logger.info(
            "Reprocessed: %s, skipped: %s, errors: %s",
            result["processed"],
            result["skipped"],
            len(result["errors"]),
        )
        for err in result["errors"]:
            logger.warning("  document_id=%s error=%s", err["document_id"], err["error"])


if __name__ == "__main__":
    asyncio.run(main())

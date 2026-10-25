"""
Normalize PDF-derived document content already stored in the DB.

Usage:
  python backend/scripts/normalize_document_content.py --project-id 10
  python backend/scripts/normalize_document_content.py --all
"""
import argparse
import asyncio
import logging
from typing import Optional

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.document import Document
from app.utils.file_processing import _clean_pdf_text

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize PDF-derived document content.")
    parser.add_argument("--project-id", type=int, default=None, help="Optional project ID filter.")
    parser.add_argument("--all", action="store_true", help="Process all documents (not just PDFs).")
    return parser.parse_args()


def _looks_like_pdf(doc: Document) -> bool:
    filename = (doc.filename or "").lower()
    return filename.endswith(".pdf")


async def _normalize(project_id: Optional[int], process_all: bool) -> None:
    async with AsyncSessionLocal() as session:
        query = select(Document)
        if project_id is not None:
            query = query.where(Document.project_id == project_id)

        result = await session.execute(query)
        documents = list(result.scalars().all())

        if not documents:
            logger.info("No documents found.")
            return

        updated = 0
        for doc in documents:
            if not process_all and not _looks_like_pdf(doc):
                continue
            if not doc.content:
                continue

            cleaned = _clean_pdf_text(doc.content)
            if cleaned and cleaned != doc.content:
                doc.content = cleaned
                session.add(doc)
                updated += 1

        if updated:
            await session.commit()
        logger.info("Normalized %d documents.", updated)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    asyncio.run(_normalize(args.project_id, args.all))


if __name__ == "__main__":
    main()

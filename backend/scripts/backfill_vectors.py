"""
Backfill vector embeddings for existing documents.

Usage:
  python backend/scripts/backfill_vectors.py --project-id 10
  python backend/scripts/backfill_vectors.py --document-type interview --force
"""
import argparse
import asyncio
import logging
from typing import Optional

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.vector_db import vector_db
from app.models.document import Document, DocumentType
from app.utils.token_utils import chunk_text_by_tokens

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill vector embeddings.")
    parser.add_argument("--project-id", type=int, default=None, help="Optional project ID filter.")
    parser.add_argument(
        "--document-type",
        type=str,
        default=None,
        choices=[dt.value for dt in DocumentType],
        help="Optional document type filter (context/interview).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reindex even if vector_id already exists.",
    )
    return parser.parse_args()


async def _backfill(
    project_id: Optional[int],
    document_type: Optional[str],
    force: bool,
) -> None:
    async with AsyncSessionLocal() as session:
        query = select(Document)
        if project_id is not None:
            query = query.where(Document.project_id == project_id)
        if document_type is not None:
            query = query.where(Document.document_type == DocumentType(document_type))

        result = await session.execute(query)
        documents = list(result.scalars().all())

        if not documents:
            logger.info("No documents found for given filters.")
            return

        logger.info("Found %d documents to process.", len(documents))

        for doc in documents:
            if doc.vector_id and not force:
                logger.info("Skipping document %s (vector_id exists).", doc.id)
                continue

            content = doc.content or ""
            if not content.strip():
                logger.warning("Skipping document %s (empty content).", doc.id)
                continue

            chunks = chunk_text_by_tokens(
                content,
                max_tokens=8000,
                overlap_tokens=200,
            )
            if not chunks:
                logger.warning("Skipping document %s (no chunks).", doc.id)
                continue

            metadata_base = {
                "document_type": doc.document_type.value,
                "filename": doc.filename,
                "document_id": str(doc.id),
            }
            if doc.project_id is not None:
                metadata_base["project_id"] = str(doc.project_id)

            metadatas = [
                {**metadata_base, "chunk_index": i, "text_content": chunks[i]}
                for i in range(len(chunks))
            ]

            vector_ids = await vector_db.add_documents(
                documents=chunks,
                metadatas=metadatas,
            )

            doc.vector_id = vector_ids[0] if vector_ids else None
            session.add(doc)
            await session.commit()

            logger.info(
                "Indexed document %s (%d chunks).",
                doc.id,
                len(vector_ids),
            )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    asyncio.run(_backfill(args.project_id, args.document_type, args.force))


if __name__ == "__main__":
    main()

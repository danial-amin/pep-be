"""
RAG filter utilities for project-scoped vector DB queries.

Use document_id instead of project_id when filtering, because:
- document_id is always stored in vector metadata when indexing
- project_id may be missing for older documents or if indexing failed to set it
- Using document_id ensures we only retrieve chunks from the project's actual documents
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any, List

from app.models.document import Document, DocumentType


async def get_project_document_filter(
    session: AsyncSession,
    project_id: Optional[int],
    document_type: str = "interview",
) -> Dict[str, Any]:
    """
    Build vector DB filter metadata that scopes to a project's documents.

    Uses document_id (always in vector metadata) instead of project_id (may be missing).
    This ensures RAG and validation only use chunks from the correct project's files.

    Args:
        session: Database session
        project_id: Project ID to scope to (None = no project scope)
        document_type: "interview" or "context"

    Returns:
        filter_metadata dict for vector_db.query_documents, e.g.:
        {"document_type": "interview", "document_id": {"$in": ["1", "2", "3"]}}
    """
    filter_metadata: Dict[str, Any] = {"document_type": document_type}

    if project_id is None:
        return filter_metadata

    # Get document IDs for this project from DB (source of truth)
    doc_type_enum = DocumentType.INTERVIEW if document_type == "interview" else DocumentType.CONTEXT
    result = await session.execute(
        select(Document.id).where(
            Document.project_id == project_id,
            Document.document_type == doc_type_enum,
        )
    )
    doc_ids = [str(row[0]) for row in result.fetchall() if row[0] is not None]

    if not doc_ids:
        # No documents in project - still use project_id as fallback for any vectors that have it
        filter_metadata["project_id"] = str(project_id)
        return filter_metadata

    if len(doc_ids) == 1:
        filter_metadata["document_id"] = doc_ids[0]
    else:
        filter_metadata["document_id"] = {"$in": doc_ids}

    return filter_metadata


async def get_project_document_ids(
    session: AsyncSession,
    project_id: Optional[int],
    document_type: Optional[str] = None,
) -> List[int]:
    """
    Get document IDs belonging to a project, optionally filtered by type.

    Returns:
        List of document IDs (integers)
    """
    if project_id is None:
        return []

    query = select(Document.id).where(Document.project_id == project_id)
    if document_type:
        doc_type_enum = (
            DocumentType.INTERVIEW if document_type == "interview" else DocumentType.CONTEXT
        )
        query = query.where(Document.document_type == doc_type_enum)

    result = await session.execute(query)
    return [row[0] for row in result.fetchall() if row[0] is not None]

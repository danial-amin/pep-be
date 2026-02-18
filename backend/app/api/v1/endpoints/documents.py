"""
Document processing endpoints.

Upload returns immediately: file stored (local or S3), job enqueued to Redis.
Worker polls Redis, parses document, upserts to vector DB.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from pathlib import Path
import logging

from app.core.database import get_db
from app.core.config import settings
from app.core.vector_db import vector_db
from app.core.storage import store_file
from app.core.queue import enqueue_document_job
from app.models.document import Document, DocumentType, ProcessingStatus
from app.schemas.document import (
    DocumentProcessResponse,
    DocumentResponse,
    ReprocessRequest,
    ReprocessResponse,
    ReprocessErrorItem,
    NeedReuploadResponse,
    NeedReuploadItem,
)
from app.services.document_service import DocumentService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/process", response_model=DocumentProcessResponse, status_code=status.HTTP_201_CREATED)
async def process_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    project_id: int = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document (context or interview). Returns immediately after storing the file.

    File is stored in Railway Storage (S3) or local Volume. A job is enqueued to Redis.
    Worker polls Redis, parses the document, and upserts to vector DB.
    Poll GET /documents or GET /documents/{id} to check processing_status (pending | processing | completed | failed).
    """
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    file_content = await file.read()
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )

    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}_{file.filename}"

    try:
        storage_location = await store_file(content=file_content, object_key=stored_name)
    except Exception as e:
        logger.exception("Failed to store file: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store file: {str(e)}"
        )

    try:
        document = await DocumentService.create_pending_document(
            session=db,
            file_path=storage_location,
            filename=file.filename,
            document_type=document_type,
            project_id=project_id,
        )
        await db.commit()
        await db.refresh(document)
    except Exception as e:
        try:
            from app.core.storage import delete_file
            await delete_file(storage_location)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document record: {str(e)}"
        )

    try:
        await enqueue_document_job(document.id)
    except Exception as e:
        logger.exception("Failed to enqueue document job: %s", e)
        # Document is pending; worker can poll for it as fallback, or we keep it pending
        # User can retry via /retry endpoint

    return DocumentProcessResponse(
        id=document.id,
        filename=document.filename,
        document_type=document.document_type,
        processed=False,
        processing_status=document.processing_status,
        processing_error=document.processing_error,
        vector_id=document.vector_id,
        created_at=document.created_at,
    )


@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    project_id: int = None,
    document_type: DocumentType = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all documents, optionally filtered by project and type."""
    from sqlalchemy import select

    query = select(Document)
    if project_id:
        query = query.where(Document.project_id == project_id)
    if document_type:
        query = query.where(Document.document_type == document_type)

    result = await db.execute(query)
    documents = result.scalars().all()
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get("/need-reupload", response_model=NeedReuploadResponse)
async def get_need_reupload(
    project_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List documents that need to be re-uploaded (pending/failed with no content; file was lost).
    Use this to see which old uploads cannot be converted and must be re-uploaded.
    """
    docs = await DocumentService.get_need_reupload(db, project_id=project_id)
    return NeedReuploadResponse(
        documents=[
            NeedReuploadItem(
                id=doc.id,
                filename=doc.filename,
                document_type=doc.document_type,
                processing_status=doc.processing_status,
                processing_error=doc.processing_error,
            )
            for doc in docs
        ]
    )


@router.get("/vector-stats")
async def get_vector_stats():
    """
    Return vector index stats (total_vector_count, etc.) so you can verify upserts.
    Pinecone stats can take a few seconds to reflect new vectors after upsert.
    """
    stats = vector_db.get_index_stats() if hasattr(vector_db, "get_index_stats") else None
    if stats is None:
        return {"detail": "Vector DB does not expose stats or stats unavailable"}
    return stats


@router.post("/reprocess", response_model=ReprocessResponse)
async def reprocess_documents(
    body: ReprocessRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reprocess documents that have content but no/missing vectors (content → chunks → vector DB).
    Use for old documents that were processed but vectors were lost or never stored.
    - Omit document_ids to reprocess all documents that have content and no vector_id.
    - Set force=true to re-vector even when vector_id exists (replaces existing vectors).
    """
    result = await DocumentService.reprocess_documents(
        db,
        document_ids=body.document_ids,
        force=body.force,
    )
    await db.commit()
    return ReprocessResponse(
        processed=result["processed"],
        skipped=result["skipped"],
        errors=[ReprocessErrorItem(**e) for e in result["errors"]],
    )


@router.post("/{document_id}/retry", response_model=DocumentResponse)
async def retry_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retry processing for a document stuck in pending/processing.
    Re-extracts text from the stored file (pdfplumber for PDF), then chunks and upserts to the vector DB.
    Use when a document never completes; requires the file to still exist (e.g. on a Volume).
    """
    err = await DocumentService.retry_document_processing(db, document_id)
    if err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err,
        )
    await db.commit()
    document = await DocumentService.get_document(db, document_id)
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document and its vectors from the vector DB."""
    success = await DocumentService.delete_document(db, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific document by ID."""
    document = await DocumentService.get_document(db, document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found"
        )
    
    return DocumentResponse.model_validate(document)


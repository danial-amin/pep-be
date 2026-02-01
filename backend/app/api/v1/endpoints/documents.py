"""
Document processing endpoints.

Upload returns immediately; chunking, LLM processing, and vector storage run in the background.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from pathlib import Path
import aiofiles

from app.core.database import get_db
from app.core.config import settings
from app.models.document import Document, DocumentType, ProcessingStatus
from app.schemas.document import DocumentProcessResponse, DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter()

# Create uploads directory if it doesn't exist (persisted until background processing completes)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/process", response_model=DocumentProcessResponse, status_code=status.HTTP_201_CREATED)
async def process_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    project_id: int = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document (context or interview). Returns immediately after storing the file.

    Post-processing (text extraction, LLM processing, chunking, embeddings) runs in the background.
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

    # Create pending document first so we have an id for the stored file path
    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / stored_name

    try:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store file: {str(e)}"
        )

    try:
        document = await DocumentService.create_pending_document(
            session=db,
            file_path=str(file_path),
            filename=file.filename,
            document_type=document_type,
            project_id=project_id,
        )
        await db.commit()
        await db.refresh(document)
    except Exception as e:
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document record: {str(e)}"
        )

    background_tasks.add_task(DocumentService.process_document_background, document.id)

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


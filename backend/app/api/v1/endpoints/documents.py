"""
Document processing endpoints.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import os
import uuid
from pathlib import Path
import aiofiles

from app.core.database import get_db
from app.core.config import settings
from app.models.document import Document, DocumentType
from app.schemas.document import DocumentProcessRequest, DocumentProcessResponse, DocumentResponse
from app.services.document_service import DocumentService
from app.utils.file_processing import extract_text_from_file

router = APIRouter()

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/process", response_model=DocumentProcessResponse, status_code=status.HTTP_201_CREATED)
async def process_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    project_id: int = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a document (context or interview).
    
    - Uploads the file
    - Extracts text content
    - Processes with LLM
    - Creates embeddings and stores in vector DB
    - Saves document metadata in database
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Validate file size
    file_content = await file.read()
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    # Save file temporarily
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    
    try:
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        # Extract text from file based on type
        try:
            content = await extract_text_from_file(str(file_path), file_ext)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # Process document
        document = await DocumentService.process_document(
            session=db,
            file_path=str(file_path),
            filename=file.filename,
            document_type=document_type,
            content=content,
            project_id=project_id
        )
        
        return DocumentProcessResponse(
            id=document.id,
            filename=document.filename,
            document_type=document.document_type,
            processed=True,
            vector_id=document.vector_id,
            created_at=document.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )
    
    finally:
        # Clean up temporary file
        if file_path.exists():
            file_path.unlink()


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


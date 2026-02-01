"""
Document schemas for API requests/responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.document import DocumentType


class DocumentProcessRequest(BaseModel):
    """Request schema for document processing."""
    document_type: DocumentType = Field(..., description="Type of document: context or interview")
    filename: str = Field(..., description="Name of the document file")


class DocumentProcessResponse(BaseModel):
    """Response schema for document processing (upload returns immediately; processing runs in background)."""
    id: int
    filename: str
    document_type: DocumentType
    processed: bool  # True when processing_status is completed
    processing_status: str = "pending"  # pending | processing | completed | failed
    processing_error: Optional[str] = None
    vector_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """Document response schema."""
    id: int
    filename: str
    document_type: DocumentType
    content: Optional[str] = None  # None until background processing completes
    processed_content: Optional[str] = None
    vector_id: Optional[str] = None
    processing_status: str = "completed"
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


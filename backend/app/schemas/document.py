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
    """Response schema for document processing."""
    id: int
    filename: str
    document_type: DocumentType
    processed: bool
    vector_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """Document response schema."""
    id: int
    filename: str
    document_type: DocumentType
    content: str
    processed_content: Optional[str] = None
    vector_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


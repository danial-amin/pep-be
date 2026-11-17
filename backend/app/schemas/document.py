"""
Document schemas for API requests/responses.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
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


class ReprocessRequest(BaseModel):
    """Request to reprocess documents that have content but no/missing vectors."""
    document_ids: Optional[List[int]] = Field(
        None,
        description="Specific document IDs to reprocess; omit to reprocess all that have content and no vector_id",
    )
    force: bool = Field(
        False,
        description="If true, re-vector even when vector_id exists (replaces existing vectors)",
    )


class ReprocessErrorItem(BaseModel):
    document_id: int
    error: str


class ReprocessResponse(BaseModel):
    """Response after reprocessing documents (content → vectors)."""
    processed: List[int] = Field(description="Document IDs that were successfully reprocessed")
    skipped: List[int] = Field(description="Document IDs skipped (e.g. no content or already has vectors)")
    errors: List[ReprocessErrorItem] = Field(description="Document IDs that failed with error message")


class NeedReuploadItem(BaseModel):
    """Document that has no content and cannot be reprocessed; user should re-upload."""
    id: int
    filename: str
    document_type: DocumentType
    processing_status: str
    processing_error: Optional[str] = None


class NeedReuploadResponse(BaseModel):
    """List of documents that need to be re-uploaded (file was lost or never processed)."""
    documents: List[NeedReuploadItem]


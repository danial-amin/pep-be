"""
Document model for storing processed documents.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class DocumentType(str, enum.Enum):
    """Document type enumeration."""
    CONTEXT = "context"
    INTERVIEW = "interview"


class ProcessingStatus:
    """Document processing status."""
    PENDING = "pending"      # Uploaded, waiting for background processing
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """Document model."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    content = Column(Text, nullable=True)  # Nullable until background processing completes
    processed_content = Column(Text, nullable=True)  # LLM processed summary
    vector_id = Column(String(255), nullable=True)  # ID in vector DB
    project_id = Column(Integer, nullable=True, index=True)  # Link to project for isolation
    # Background processing: file stored on disk until processing completes
    file_path = Column(String(512), nullable=True)
    processing_status = Column(String(20), nullable=False, default=ProcessingStatus.COMPLETED)
    processing_error = Column(Text, nullable=True)  # Error message if status is failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


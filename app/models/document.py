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


class Document(Base):
    """Document model."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    content = Column(Text, nullable=False)
    processed_content = Column(Text, nullable=True)  # LLM processed summary
    vector_id = Column(String(255), nullable=True)  # ID in vector DB
    project_id = Column(String(255), nullable=True, index=True)  # Optional project/session identifier for isolation
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


"""
Project model for organizing persona generation workflows.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Project(Base):
    """Project model - organizes documents and persona sets."""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    field_of_study = Column(String(255), nullable=True)  # e.g., "Electric Vehicle Transition", "Healthcare AI"
    core_objective = Column(Text, nullable=True)  # Main objective for persona generation
    includes_context = Column(Boolean, default=True)  # Whether project uses context documents
    includes_interviews = Column(Boolean, default=True)  # Whether project uses interview documents
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships - using string reference to avoid circular import
    persona_sets = relationship("PersonaSet", back_populates="project", cascade="all, delete-orphan")

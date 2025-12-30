"""
Persona models for storing generated personas.
"""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class PersonaSet(Base):
    """Persona set model - collection of personas."""
    __tablename__ = "persona_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # Metrics and analytics
    rqe_scores = Column(JSON, nullable=True)  # RQE scores over cycles: [{"cycle": 1, "score": 0.85}, ...]
    diversity_score = Column(JSON, nullable=True)  # Diversity metrics
    validation_scores = Column(JSON, nullable=True)  # Validation scores: [{"persona_id": 1, "similarity": 0.92}, ...]
    generation_cycle = Column(Integer, default=1)  # Current generation cycle
    status = Column(String(50), default="generated")  # generated, expanded, validated
    personas = relationship("Persona", back_populates="persona_set", cascade="all, delete-orphan")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Persona(Base):
    """Persona model - individual persona."""
    __tablename__ = "personas"
    
    id = Column(Integer, primary_key=True, index=True)
    persona_set_id = Column(Integer, ForeignKey("persona_sets.id"), nullable=False)
    name = Column(String(255), nullable=False)
    persona_data = Column(JSON, nullable=False)  # Full persona JSON
    image_url = Column(String(500), nullable=True)
    image_prompt = Column(Text, nullable=True)
    # Validation metrics
    similarity_score = Column(JSON, nullable=True)  # Cosine similarity scores with transcripts
    validation_status = Column(String(50), nullable=True)  # validated, pending, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    persona_set = relationship("PersonaSet", back_populates="personas")


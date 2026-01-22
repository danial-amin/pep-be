"""
Persona models for storing generated personas.

Implements the persona storage from the PEP paper methodology:
- PersonaSet: Collection of personas with generation config and metrics
- Persona: Individual persona with validation scores and source traceability
"""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class PersonaSet(Base):
    """
    Persona set model - collection of personas.

    Tracks generation configuration, iteration cycles, and quality metrics
    following the PEP paper methodology.
    """
    __tablename__ = "persona_sets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Project scoping - allows multiple projects with separate persona sets
    project_id = Column(String(255), nullable=True, index=True)

    # Generation configuration - stores user-provided parameters
    # Includes: rqe_threshold, max_iterations, num_personas, output_format, etc.
    generation_config = Column(JSON, nullable=True)

    # Metrics and analytics (per PEP paper)
    rqe_scores = Column(JSON, nullable=True)  # RQE scores over cycles: [{"cycle": 1, "score": 0.85}, ...]
    diversity_score = Column(JSON, nullable=True)  # Current diversity metrics
    validation_scores = Column(JSON, nullable=True)  # Validation scores: [{"persona_id": 1, "similarity": 0.92}, ...]

    # Generation tracking
    generation_cycle = Column(Integer, default=1)  # Current generation cycle
    max_iterations = Column(Integer, default=3)  # Maximum iterations for RQE threshold
    rqe_threshold = Column(Float, default=0.75)  # Target RQE score (paper recommends >= 0.75)

    # Status tracking
    status = Column(String(50), default="generated")  # generated, expanded, validated

    # Relationships
    personas = relationship("Persona", back_populates="persona_set", cascade="all, delete-orphan")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Persona(Base):
    """
    Persona model - individual persona.

    Each persona includes:
    - Full persona data (demographics, goals, behaviors, etc.)
    - Source traceability (links to source document chunks)
    - Validation metrics (cosine similarity scores)
    """
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, index=True)
    persona_set_id = Column(Integer, ForeignKey("persona_sets.id"), nullable=False)
    name = Column(String(255), nullable=False)
    persona_data = Column(JSON, nullable=False)  # Full persona JSON

    # Image generation
    image_url = Column(String(500), nullable=True)
    image_prompt = Column(Text, nullable=True)

    # Source traceability - links persona attributes to source chunks
    # Format: {"attribute_name": [{"chunk_id": "...", "text": "...", "similarity": 0.85}, ...]}
    source_references = Column(JSON, nullable=True)

    # Validation metrics (per PEP paper)
    similarity_score = Column(JSON, nullable=True)  # Overall cosine similarity scores with transcripts
    attribute_validation = Column(JSON, nullable=True)  # Per-attribute CS scores: {"goals": 0.82, "frustrations": 0.78, ...}
    validation_status = Column(String(50), nullable=True)  # validated, pending, failed

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    persona_set = relationship("PersonaSet", back_populates="personas")


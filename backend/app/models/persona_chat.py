"""
Persona chat models for controlled persona conversations.

Supports:
  - single mode: 1:1 with one persona
  - set mode: chat with an entire persona set (@mention one, or all if unaddressed)
"""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class PersonaChatSession(Base):
    """Chat session — either one persona or a full persona set."""
    __tablename__ = "persona_chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    # Single-persona mode
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=True, index=True)
    # Set mode
    persona_set_id = Column(Integer, ForeignKey("persona_sets.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    # Display name: persona name (single) or set name (set)
    persona_name = Column(String(255), nullable=False)
    # "single" | "set"
    mode = Column(String(32), nullable=False, default="single")

    messages = relationship(
        "PersonaChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PersonaChatMessage.id",
    )
    persona = relationship("Persona")
    persona_set = relationship("PersonaSet")
    project = relationship("Project")
    user = relationship("User")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PersonaChatMessage(Base):
    """Single message in a persona chat session."""
    __tablename__ = "persona_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("persona_chat_sessions.id"), nullable=False, index=True)
    role = Column(String(32), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)

    # Which persona spoke (assistant messages in set mode)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=True, index=True)
    persona_name = Column(String(255), nullable=True)

    refused = Column(Boolean, default=False)
    retrieval_score = Column(Float, nullable=True)
    sources_used = Column(JSON, nullable=True)  # [{chunk_id, score, preview}]
    refusal_reason = Column(String(64), nullable=True)

    session = relationship("PersonaChatSession", back_populates="messages")
    persona = relationship("Persona")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

"""
Persona chat models for controlled 1:1 persona conversations.

Each session binds one user to one persona. Messages track whether the
persona refused (out-of-scope) and what evidence grounded the reply.
"""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class PersonaChatSession(Base):
    """A 1:1 chat session between a user and a single persona."""
    __tablename__ = "persona_chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    persona_name = Column(String(255), nullable=False)

    messages = relationship(
        "PersonaChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PersonaChatMessage.id",
    )
    persona = relationship("Persona")
    project = relationship("Project")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PersonaChatMessage(Base):
    """Single message in a persona chat session."""
    __tablename__ = "persona_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("persona_chat_sessions.id"), nullable=False, index=True)
    role = Column(String(32), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)

    refused = Column(Boolean, default=False)
    retrieval_score = Column(Float, nullable=True)
    sources_used = Column(JSON, nullable=True)  # [{chunk_id, score, preview}]
    refusal_reason = Column(String(64), nullable=True)  # low_relevance | model_refusal | strict_gate

    session = relationship("PersonaChatSession", back_populates="messages")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

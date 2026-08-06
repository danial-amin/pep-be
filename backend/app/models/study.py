"""
User-study mode: studies, participants, and action events.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Study(Base):
    """A feature-flagged user study linked to a project / persona set."""

    __tablename__ = "studies"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    persona_set_id = Column(Integer, ForeignKey("persona_sets.id"), nullable=False, index=True)

    # Ordered list of persona IDs for the all-profiles screen
    persona_order = Column(JSON, nullable=True)

    # When true, any unused code like P01 is accepted and auto-created
    allow_open_codes = Column(Boolean, default=True, nullable=False)
    # Max participants when using open codes (P01..Pn)
    max_participants = Column(Integer, default=40, nullable=False)

    # Optional welcome copy for the study entry screen
    welcome_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project")
    persona_set = relationship("PersonaSet")
    participants = relationship(
        "StudyParticipant",
        back_populates="study",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "StudyEvent",
        back_populates="study",
        cascade="all, delete-orphan",
    )


class StudyParticipant(Base):
    """Study participant identified by a code (P01, P02, …) — no password."""

    __tablename__ = "study_participants"
    __table_args__ = (
        UniqueConstraint("study_id", "code", name="uq_study_participant_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("studies.id"), nullable=False, index=True)
    code = Column(String(32), nullable=False, index=True)  # e.g. P01
    display_name = Column(String(255), nullable=True)

    # Linked app user (auto-created on first enter) for JWT / existing auth
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    study = relationship("Study", back_populates="participants")
    user = relationship("User")
    events = relationship("StudyEvent", back_populates="participant")


class StudyEvent(Base):
    """Instrumented action taken by a study participant (or researcher in study UI)."""

    __tablename__ = "study_events"

    id = Column(Integer, primary_key=True, index=True)
    study_id = Column(Integer, ForeignKey("studies.id"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("study_participants.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    event_type = Column(String(64), nullable=False, index=True)
    path = Column(String(512), nullable=True)
    payload = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    study = relationship("Study", back_populates="events")
    participant = relationship("StudyParticipant", back_populates="events")
    user = relationship("User")

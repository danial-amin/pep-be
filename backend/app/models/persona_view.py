"""
Persona profile view-time tracking.

Records how long users spend on individual persona profiles
and on the all-profiles (set) page.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class PersonaProfileView(Base):
    """A single timed visit to a persona profile or set profiles page."""

    __tablename__ = "persona_profile_views"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    persona_set_id = Column(Integer, ForeignKey("persona_sets.id"), nullable=False, index=True)
    # Null when view_type is set_profiles (all personas on one page)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=True, index=True)
    # "persona" | "set_profiles"
    view_type = Column(String(32), nullable=False, index=True)
    duration_seconds = Column(Float, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    persona_set = relationship("PersonaSet")
    persona = relationship("Persona")

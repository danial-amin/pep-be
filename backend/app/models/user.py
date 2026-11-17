"""
User and invite models for invite-only authentication.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    """Authenticated application user."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    invites_sent = relationship(
        "Invite",
        back_populates="invited_by",
        foreign_keys="Invite.invited_by_id",
    )
    projects = relationship("Project", back_populates="owner")


class Invite(Base):
    """Email invitation to join the app (no public signup)."""
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    accepted_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Optional note for the invitee
    note = Column(Text, nullable=True)

    invited_by = relationship("User", back_populates="invites_sent", foreign_keys=[invited_by_id])

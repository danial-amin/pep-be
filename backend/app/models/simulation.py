"""
Simulation models for multi-persona conversation playground.

Implements a simulation environment where persona-infused LLMs can
converse with each other towards a common goal.
"""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Simulation(Base):
    """
    Simulation session model - a conversation between multiple personas.

    Tracks the goal, duration, token limits, and participating personas.
    """
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    # Goal and configuration
    goal = Column(Text, nullable=False)  # The common goal for the conversation
    goal_context = Column(Text, nullable=True)  # Additional context for the goal

    # Constraints
    max_duration_seconds = Column(Integer, default=300)  # Max duration in seconds (default 5 min)
    max_tokens = Column(Integer, default=4000)  # Max tokens for entire conversation
    max_turns = Column(Integer, default=20)  # Max number of turns

    # Current state
    status = Column(String(50), default="pending")  # pending, running, completed, stopped
    current_turn = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Summary generated at end
    summary = Column(Text, nullable=True)
    key_insights = Column(JSON, nullable=True)  # Array of key insights from conversation
    action_items = Column(JSON, nullable=True)  # Array of action items/recommendations

    # Project scoping
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    # Relationships
    messages = relationship("SimulationMessage", back_populates="simulation", cascade="all, delete-orphan", order_by="SimulationMessage.turn_number")
    participants = relationship("SimulationParticipant", back_populates="simulation", cascade="all, delete-orphan")
    project = relationship("Project", back_populates="simulations")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SimulationParticipant(Base):
    """
    Participant in a simulation - links a persona to a simulation with a role.
    """
    __tablename__ = "simulation_participants"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=False)

    # Role in the simulation
    role = Column(String(255), nullable=True)  # Optional role assignment (e.g., "moderator", "devil's advocate")

    # Participation stats
    messages_count = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)

    # Relationships
    simulation = relationship("Simulation", back_populates="participants")
    persona = relationship("Persona")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SimulationMessage(Base):
    """
    Single message in a simulation conversation.
    Persona messages have persona_id set; human interventions have is_human_message=True and persona_id=None.
    """
    __tablename__ = "simulation_messages"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False)
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=True)  # None for human interventions

    # Message content
    content = Column(Text, nullable=False)
    turn_number = Column(Integer, nullable=False)

    # Token tracking
    tokens = Column(Integer, default=0)

    # Message metadata
    is_moderator_message = Column(Boolean, default=False)  # System/moderator messages
    is_human_message = Column(Boolean, default=False)  # Human facilitator intervention
    responding_to_id = Column(Integer, ForeignKey("simulation_messages.id"), nullable=True)

    # Relationships
    simulation = relationship("Simulation", back_populates="messages")
    persona = relationship("Persona")
    responding_to = relationship("SimulationMessage", remote_side=[id])

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

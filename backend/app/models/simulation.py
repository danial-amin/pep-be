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

    # Agreement-based termination
    run_until_agreement = Column(Boolean, default=False)  # Keep running until personas agree
    agreement_threshold = Column(Float, default=0.75)  # Score 0.0-1.0 needed to stop
    # Cached initial stance inference per persona (JSON: {str(persona_id): {stance_summary, key_positions}})
    initial_persona_stances = Column(JSON, nullable=True)

    # Current state
    status = Column(String(50), default="pending")  # pending, running, completed, stopped
    # Number of fully completed rounds (each participant spoke once per round).
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
    messages = relationship(
        "SimulationMessage",
        back_populates="simulation",
        cascade="all, delete-orphan",
        order_by="SimulationMessage.id",
    )
    participants = relationship("SimulationParticipant", back_populates="simulation", cascade="all, delete-orphan")
    project = relationship("Project", back_populates="simulations")
    agreement_evaluations = relationship("SimulationAgreementEvaluation", back_populates="simulation", cascade="all, delete-orphan", order_by="SimulationAgreementEvaluation.turn_number")

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

    # Personality drift score for this message (0.0 = on-persona, 1.0 = fully drifted)
    # Populated asynchronously by the agreement evaluator when available
    persona_drift_score = Column(Float, nullable=True)

    # Relationships
    simulation = relationship("Simulation", back_populates="messages")
    persona = relationship("Persona")
    responding_to = relationship("SimulationMessage", remote_side=[id])

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SimulationAgreementEvaluation(Base):
    """
    Snapshot of agreement state captured after each complete round of a simulation.

    Tracks stance drift per persona and pairwise alignment across personas,
    enabling time-series visualisation of convergence/divergence.
    """
    __tablename__ = "simulation_agreement_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False, index=True)

    # Which turn (round) this evaluation was taken after
    turn_number = Column(Integer, nullable=False)

    # Aggregate score: 0.0 = complete disagreement, 1.0 = full agreement
    overall_agreement_score = Column(Float, nullable=False)

    # Whether the threshold was met (agreement_reached)
    agreement_reached = Column(Boolean, default=False)

    # Per-persona stance data
    # {
    #   "<persona_id>": {
    #     "persona_name": "...",
    #     "initial_stance": "...",
    #     "current_stance": "...",
    #     "drift_score": 0.3,           # 0=unchanged, 1=complete shift from original
    #     "alignment_scores": {         # pairwise with every other persona (0-1)
    #       "<other_persona_id>": 0.7
    #     }
    #   }
    # }
    persona_stances = Column(JSON, nullable=True)

    # LLM's reasoning for the scores
    evaluation_reasoning = Column(Text, nullable=True)

    # Relationship
    simulation = relationship("Simulation", back_populates="agreement_evaluations")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

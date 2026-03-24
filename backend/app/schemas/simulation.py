"""
Simulation schemas for multi-persona conversation playground.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class SimulationStatus(str, Enum):
    """Status of a simulation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"


class ParticipantConfig(BaseModel):
    """Configuration for a participant in the simulation."""
    persona_id: int = Field(..., description="ID of the persona to include")
    role: Optional[str] = Field(
        default=None,
        description="Optional role for this persona (e.g., 'moderator', 'critic', 'advocate')"
    )


class SimulationCreateRequest(BaseModel):
    """Request to create a new simulation session."""
    name: str = Field(..., description="Name for this simulation session")
    goal: str = Field(
        ...,
        description="The common goal or topic for the personas to discuss and work towards"
    )
    goal_context: Optional[str] = Field(
        default=None,
        description="Additional context about the goal, constraints, or desired outcomes"
    )

    # Participants — personas may come from different persona sets
    participants: List[ParticipantConfig] = Field(
        ...,
        min_length=2,
        max_length=8,
        description=(
            "List of personas to participate (2-8 personas). "
            "Personas may belong to different persona sets — mix freely."
        )
    )

    # Constraints - simulation stops when EITHER limit is reached
    max_turns: int = Field(
        default=10,
        ge=2,
        le=100,
        description=(
            "Maximum number of turns; 1 turn = all selected personas have spoken once (one full round). "
            "When run_until_agreement=True this acts as an absolute safety cap."
        )
    )
    max_duration_seconds: int = Field(
        default=120,
        ge=30,
        le=600,
        description="Maximum duration in seconds (30s - 10 minutes). Simulation stops after this time."
    )
    # Token tracking (for reference, not a hard limit)
    max_tokens: Optional[int] = Field(
        default=None,
        description="Optional soft limit for total tokens (for cost tracking)"
    )

    # Agreement-based termination
    run_until_agreement: bool = Field(
        default=False,
        description=(
            "When True the simulation keeps running beyond max_turns until the agreement "
            "evaluator reports that all personas have reached the agreement_threshold, "
            "or until max_turns (safety cap) is hit."
        )
    )
    agreement_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description=(
            "Agreement score (0.0–1.0) that must be reached across all personas for the simulation "
            "to terminate when run_until_agreement=True. 0.75 means 75% pairwise stance alignment."
        )
    )

    # Project scoping
    project_id: Optional[int] = Field(
        default=None,
        description="Optional project ID for context"
    )


class SimulationStartRequest(BaseModel):
    """Request to start or continue a simulation."""
    auto_continue: bool = Field(
        default=True,
        description="Whether to automatically continue the conversation until limits are reached"
    )


class HumanInterventionRequest(BaseModel):
    """Request to add a human facilitator intervention to the simulation."""
    content: str = Field(..., min_length=1, description="The facilitator's message or directive")


class SimulationMessageResponse(BaseModel):
    """Response for a single simulation message."""
    id: int
    persona_id: Optional[int] = None  # None for human interventions
    persona_name: str
    persona_image_url: Optional[str] = None
    content: str
    turn_number: int
    tokens: int
    is_moderator_message: bool = False
    is_human_message: bool = False
    persona_drift_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SimulationParticipantResponse(BaseModel):
    """Response for a simulation participant."""
    id: int
    persona_id: int
    persona_name: str
    persona_image_url: Optional[str] = None
    persona_set_id: Optional[int] = None
    persona_set_name: Optional[str] = None
    role: Optional[str] = None
    messages_count: int = 0
    tokens_used: int = 0

    class Config:
        from_attributes = True


class PersonaSummaryEntry(BaseModel):
    """Per-persona summary for simulation summary response."""
    persona_id: int
    persona_name: str
    summary: str


# ─── Agreement Evaluation Schemas ────────────────────────────────────────────

class PersonaStanceDetail(BaseModel):
    """Stance analysis for a single persona at a given evaluation point."""
    persona_name: str
    initial_stance: str
    current_stance: str
    # 0.0 = unchanged from original, 1.0 = completely shifted
    drift_score: float
    # Pairwise alignment scores with every other persona {str(persona_id): score}
    alignment_scores: Dict[str, float] = {}


class AgreementEvaluationResponse(BaseModel):
    """Response for a single agreement evaluation snapshot."""
    id: int
    simulation_id: int
    turn_number: int
    overall_agreement_score: float
    agreement_reached: bool
    # Keys are str(persona_id)
    persona_stances: Optional[Dict[str, PersonaStanceDetail]] = None
    evaluation_reasoning: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgreementHistoryResponse(BaseModel):
    """Time-series agreement history for a simulation."""
    simulation_id: int
    agreement_threshold: float
    agreement_reached: bool
    evaluations: List[AgreementEvaluationResponse] = []


# ─── Core Simulation Responses ───────────────────────────────────────────────

class SimulationResponse(BaseModel):
    """Response for a simulation session."""
    id: int
    name: str
    goal: str
    goal_context: Optional[str] = None

    # Constraints
    max_duration_seconds: int
    max_tokens: int
    max_turns: int

    # Agreement settings
    run_until_agreement: bool = False
    agreement_threshold: float = 0.75

    # Current state
    status: str
    current_turn: int
    tokens_used: int

    # Latest agreement snapshot (None if not yet evaluated)
    latest_agreement_score: Optional[float] = None
    agreement_reached: bool = False

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    summary: Optional[str] = None
    persona_summaries: Optional[List[PersonaSummaryEntry]] = None
    key_insights: Optional[List[str]] = None
    action_items: Optional[List[str]] = None

    # Participants and messages
    participants: List[SimulationParticipantResponse] = []
    messages: List[SimulationMessageResponse] = []

    # Project
    project_id: Optional[int] = None

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SimulationListResponse(BaseModel):
    """Response for listing simulations."""
    id: int
    name: str
    goal: str
    status: str
    current_turn: int
    max_turns: int
    tokens_used: int
    max_tokens: int
    participant_count: int
    run_until_agreement: bool = False
    latest_agreement_score: Optional[float] = None
    agreement_reached: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SimulationTurnResponse(BaseModel):
    """Response for a single turn in the simulation."""
    message: SimulationMessageResponse
    simulation_status: str
    current_turn: int
    tokens_used: int
    tokens_remaining: int
    turns_remaining: int
    is_complete: bool
    # Agreement info after this turn (populated if a full round just completed)
    agreement_evaluation: Optional[AgreementEvaluationResponse] = None


class SimulationSummaryResponse(BaseModel):
    """Response for simulation summary generation."""
    simulation_id: int
    persona_summaries: List[PersonaSummaryEntry] = []
    summary: Optional[str] = None  # legacy
    key_insights: List[str] = []
    action_items: List[str] = []
    total_turns: int
    total_tokens: int
    duration_seconds: Optional[int] = None


class StreamTurnResponse(BaseModel):
    """Response for streaming a turn (for real-time updates)."""
    type: str = Field(description="Type of stream event: 'start', 'chunk', 'complete'")
    persona_id: Optional[int] = None
    persona_name: Optional[str] = None
    content: Optional[str] = None
    turn_number: Optional[int] = None
    is_complete: bool = False

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

    # Participants
    participants: List[ParticipantConfig] = Field(
        ...,
        min_length=2,
        max_length=8,
        description="List of personas to participate (2-8 personas)"
    )

    # Constraints
    max_duration_seconds: int = Field(
        default=300,
        ge=60,
        le=1800,
        description="Maximum duration in seconds (1-30 minutes)"
    )
    max_tokens: int = Field(
        default=4000,
        ge=1000,
        le=16000,
        description="Maximum total tokens for the conversation"
    )
    max_turns: int = Field(
        default=20,
        ge=4,
        le=50,
        description="Maximum number of conversation turns"
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


class SimulationMessageResponse(BaseModel):
    """Response for a single simulation message."""
    id: int
    persona_id: int
    persona_name: str
    persona_image_url: Optional[str] = None
    content: str
    turn_number: int
    tokens: int
    is_moderator_message: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class SimulationParticipantResponse(BaseModel):
    """Response for a simulation participant."""
    id: int
    persona_id: int
    persona_name: str
    persona_image_url: Optional[str] = None
    role: Optional[str] = None
    messages_count: int = 0
    tokens_used: int = 0

    class Config:
        from_attributes = True


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

    # Current state
    status: str
    current_turn: int
    tokens_used: int

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    summary: Optional[str] = None
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


class SimulationSummaryResponse(BaseModel):
    """Response for simulation summary generation."""
    simulation_id: int
    summary: str
    key_insights: List[str]
    action_items: List[str]
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

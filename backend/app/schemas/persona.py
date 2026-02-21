"""
Persona schemas for API requests/responses.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


class PersonaBasic(BaseModel):
    """Basic persona structure."""
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    basic_description: Optional[str] = None
    key_characteristics: Optional[List[str]] = None


class PersonaFormat(str, Enum):
    """Persona output format options."""
    JSON = "json"
    PROFILE = "profile"
    CHAT = "chat"
    PROTO = "proto"
    ADHOC = "adhoc"
    ENGAGING = "engaging"
    GOAL_BASED = "goal_based"
    ROLE_BASED = "role_based"
    INTERACTIVE = "interactive"


class PersonaSetCreateRequest(BaseModel):
    """
    Request to create a persona set with advanced configuration.

    Follows the PEP paper methodology with:
    - Iterative generation until RQE threshold is met
    - Configurable diversity thresholds
    - Project-level scoping
    """
    num_personas: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of personas to generate (paper recommends 4-6 for optimal coverage)"
    )
    context_details: Optional[str] = Field(
        default=None,
        description="Additional context about the research, market, or domain"
    )
    interview_topic: Optional[str] = Field(
        default=None,
        description="What the interviews are about (e.g., 'user experience with mobile app', 'customer pain points')"
    )
    user_study_design: Optional[str] = Field(
        default=None,
        description="Description of the user study design, methodology, and research approach"
    )
    include_ethical_guardrails: bool = Field(
        default=True,
        description="Whether to include ethical and fairness considerations in persona generation"
    )
    output_format: PersonaFormat = Field(
        default=PersonaFormat.JSON,
        description="Format for persona output: json, profile, chat, proto, adhoc, engaging, goal_based, role_based, or interactive"
    )
    document_ids: Optional[List[int]] = Field(
        default=None,
        description="Optional list of document IDs to use for persona generation (for session isolation). If not provided, all documents will be used."
    )
    project_id: Optional[int] = Field(
        default=None,
        description="Optional project ID to filter documents by project (for session isolation). Alternative to document_ids."
    )

    # PEP Paper Parameters - Iterative Generation
    rqe_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Target RQE (diversity) score. Paper recommends >= 0.75 for good diversity. Generation iterates until this threshold is met."
    )
    max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of generation iterations to attempt if RQE threshold is not met"
    )
    auto_iterate: bool = Field(
        default=True,
        description="Whether to automatically regenerate if RQE is below threshold. If False, generates once and returns results regardless of RQE."
    )

    # Validation thresholds
    cs_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for attribute validation. Attributes below this are flagged for review."
    )


class PersonaSetResponse(BaseModel):
    """Persona set response with PEP paper metrics."""
    id: int
    name: str
    description: Optional[str] = None
    project_id: Optional[int] = None
    personas: List["PersonaResponse"] = []

    # Generation configuration
    generation_config: Optional[Dict[str, Any]] = None
    rqe_threshold: Optional[float] = None
    max_iterations: Optional[int] = None

    # Metrics and analytics
    rqe_scores: Optional[List[Dict[str, Any]]] = None
    diversity_score: Optional[Dict[str, Any]] = None
    validation_scores: Optional[List[Dict[str, Any]]] = None
    evaluation_scores: Optional[Dict[str, Any]] = None  # Comprehensive evaluation (groundedness, coverage, etc.)

    # Generation tracking
    generation_cycle: Optional[int] = None
    status: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PersonaResponse(BaseModel):
    """Persona response with validation and traceability."""
    id: int
    persona_set_id: int
    name: str
    persona_data: Dict[str, Any]

    # Image generation
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None

    # Source traceability (PEP paper)
    source_references: Optional[Dict[str, Any]] = None

    # Validation metrics
    similarity_score: Optional[Dict[str, Any]] = None
    attribute_validation: Optional[Dict[str, Any]] = None
    validation_status: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PersonaSetGenerateResponse(BaseModel):
    """
    Response for persona set generation.

    Includes PEP paper metrics from iterative generation.
    """
    persona_set_id: int
    personas: List[PersonaBasic]
    status: str = "created"

    # Iterative generation metrics
    generation_cycle: int = 1
    rqe_score: Optional[float] = None
    rqe_threshold: Optional[float] = None
    threshold_met: bool = False
    iterations_used: int = 1

    # Detailed metrics per iteration
    iteration_history: Optional[List[Dict[str, Any]]] = None


class PersonaExpandResponse(BaseModel):
    """Response for persona expansion."""
    persona_id: int
    persona_data: Dict[str, Any]
    status: str = "expanded"


class PersonaImageResponse(BaseModel):
    """Response for persona image generation."""
    persona_id: int
    image_url: str
    image_prompt: str
    status: str = "image_generated"


class PromptCompleteRequest(BaseModel):
    """Request to complete a prompt."""
    prompt: str = Field(..., description="User prompt to complete")
    max_tokens: int = Field(default=1000, ge=100, le=4000)


class PromptCompleteResponse(BaseModel):
    """Response for prompt completion."""
    completed_text: str
    context_used: int = Field(description="Number of context documents used")


# ============================================================================
# Verification Schemas - Semantic Similarity Verification
# ============================================================================

class VerificationRequest(BaseModel):
    """Request for persona verification against source data."""
    similarity_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Minimum semantic similarity threshold (default 80% as requested)"
    )
    use_indirect_similarity: bool = Field(
        default=True,
        description="Whether to calculate indirect similarity through intermediate concepts"
    )
    filter_low_similarity: bool = Field(
        default=True,
        description="Whether to remove attributes below the similarity threshold"
    )
    project_id: Optional[int] = Field(
        default=None,
        description="Optional project ID for scoping vector DB queries"
    )
    force: bool = Field(
        default=False,
        description="Force re-run verification even if cached results exist"
    )


class AttributeVerificationResult(BaseModel):
    """Verification result for a single attribute."""
    direct_similarity: float = Field(description="Direct cosine similarity with source data")
    indirect_similarity: Optional[float] = Field(
        default=None,
        description="Indirect similarity through intermediate concepts"
    )
    combined_similarity: float = Field(description="Combined similarity score")
    verified: bool = Field(description="Whether the attribute meets the threshold")
    threshold: float = Field(description="Similarity threshold used")
    source_chunks: List[str] = Field(
        default_factory=list,
        description="Source chunks that support this attribute"
    )
    indirect_path: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Path of intermediate concepts for indirect similarity"
    )


class VerificationMetrics(BaseModel):
    """Aggregate metrics for verification."""
    average_direct_similarity: float
    average_indirect_similarity: float
    verification_rate: float = Field(description="Percentage of attributes that passed verification")
    verified_attributes: int
    filtered_attributes: int
    total_attributes: int
    threshold: float


class PersonaVerificationResponse(BaseModel):
    """Response for single persona verification."""
    persona_id: int
    persona_name: str
    verification_results: Dict[str, AttributeVerificationResult]
    original_persona_data: Dict[str, Any]
    filtered_persona_data: Dict[str, Any] = Field(
        description="Persona data with low-similarity items removed"
    )
    metrics: VerificationMetrics
    source_references: Dict[str, List[Dict[str, Any]]]
    validation_status: str


class PersonaSetVerificationResponse(BaseModel):
    """Response for persona set verification."""
    persona_set_id: int
    persona_results: List[Dict[str, Any]]
    aggregate_metrics: Dict[str, Any] = Field(
        description="Aggregate verification metrics across all personas"
    )
    status: str
    verified_at: str


class VerifiedPersonaResponse(BaseModel):
    """Response for getting a verified persona (filtered)."""
    persona_id: int
    persona_name: str
    verified_persona_data: Dict[str, Any] = Field(
        description="Persona data with only high-similarity attributes retained"
    )
    verification_rate: float
    threshold: float
    source_references: Dict[str, List[Dict[str, Any]]]


# ============================================================================
# Evaluation Schemas - Comprehensive evaluation beyond cosine similarity
# ============================================================================

class EvaluationRequest(BaseModel):
    """Request for comprehensive persona set evaluation."""
    include_groundedness: bool = Field(
        default=True,
        description="Evaluate claim-level grounding against source data"
    )
    include_coverage: bool = Field(
        default=True,
        description="Evaluate topic coverage of source data"
    )
    include_diversity_extended: bool = Field(
        default=True,
        description="Evaluate demographic and attitudinal diversity"
    )
    include_coherence: bool = Field(
        default=True,
        description="Evaluate internal consistency of personas"
    )
    include_realism: bool = Field(
        default=True,
        description="Evaluate plausibility/realism"
    )
    include_fairness: bool = Field(
        default=True,
        description="Check for stereotypes and fairness"
    )
    force: bool = Field(
        default=False,
        description="Force re-run even if cached evaluation exists"
    )


class PersonaEvaluationResponse(BaseModel):
    """Response for comprehensive persona set evaluation."""
    persona_set_id: int
    evaluation_timestamp: str
    summary: Dict[str, Any] = Field(
        description="Aggregate scores: groundedness, coverage, diversity, coherence, realism, fairness"
    )
    per_persona: List[Dict[str, Any]] = Field(
        description="Per-persona evaluation details"
    )


# Update forward references
PersonaSetResponse.model_rebuild()


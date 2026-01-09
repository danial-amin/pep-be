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
    """Request to create a persona set with advanced configuration."""
    num_personas: int = Field(
        default=3, 
        ge=1, 
        le=10, 
        description="Number of personas to generate"
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
    project_id: Optional[str] = Field(
        default=None,
        description="Optional project/session ID to filter documents by project (for session isolation). Alternative to document_ids."
    )


class PersonaSetResponse(BaseModel):
    """Persona set response."""
    id: int
    name: str
    description: Optional[str] = None
    personas: List["PersonaResponse"] = []
    rqe_scores: Optional[List[Dict[str, Any]]] = None
    diversity_score: Optional[Dict[str, Any]] = None
    validation_scores: Optional[List[Dict[str, Any]]] = None
    generation_cycle: Optional[int] = None
    status: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PersonaResponse(BaseModel):
    """Persona response."""
    id: int
    persona_set_id: int
    name: str
    persona_data: Dict[str, Any]
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    similarity_score: Optional[Dict[str, Any]] = None
    validation_status: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PersonaSetGenerateResponse(BaseModel):
    """Response for persona set generation."""
    persona_set_id: int
    personas: List[PersonaBasic]
    status: str = "created"


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


# Update forward references
PersonaSetResponse.model_rebuild()


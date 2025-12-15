"""
Persona schemas for API requests/responses.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class PersonaBasic(BaseModel):
    """Basic persona structure."""
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    basic_description: Optional[str] = None
    key_characteristics: Optional[List[str]] = None


class PersonaSetCreateRequest(BaseModel):
    """Request to create a persona set."""
    num_personas: int = Field(default=3, ge=1, le=10, description="Number of personas to generate")


class PersonaSetResponse(BaseModel):
    """Persona set response."""
    id: int
    name: str
    description: Optional[str] = None
    personas: List["PersonaResponse"] = []
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


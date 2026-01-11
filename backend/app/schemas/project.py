"""
Project schemas for API requests/responses.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ProjectCreateRequest(BaseModel):
    """Request to create a new project."""
    name: str = Field(..., description="Project name")
    field_of_study: Optional[str] = Field(None, description="Field of study (e.g., 'Electric Vehicle Transition', 'Healthcare AI')")
    core_objective: Optional[str] = Field(None, description="Core objective for persona generation")
    includes_context: bool = Field(True, description="Whether project uses context documents")
    includes_interviews: bool = Field(True, description="Whether project uses interview documents")


class ProjectUpdateRequest(BaseModel):
    """Request to update a project."""
    name: Optional[str] = None
    field_of_study: Optional[str] = None
    core_objective: Optional[str] = None
    includes_context: Optional[bool] = None
    includes_interviews: Optional[bool] = None


class ProjectResponse(BaseModel):
    """Project response schema."""
    id: int
    name: str
    field_of_study: Optional[str] = None
    core_objective: Optional[str] = None
    includes_context: bool
    includes_interviews: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

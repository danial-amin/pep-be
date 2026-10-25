"""
Schemas for persona profile view-time tracking.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PersonaProfileViewCreate(BaseModel):
    persona_set_id: int
    view_type: str = Field(..., description="'persona' or 'set_profiles'")
    duration_seconds: float = Field(..., ge=0)
    persona_id: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class PersonaProfileViewResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    persona_set_id: int
    persona_id: Optional[int] = None
    view_type: str
    duration_seconds: float
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PersonaViewTimeTotal(BaseModel):
    persona_id: Optional[int] = None
    persona_name: Optional[str] = None
    view_type: str
    total_seconds: float
    view_count: int


class PersonaSetViewTimeSummary(BaseModel):
    persona_set_id: int
    totals: List[PersonaViewTimeTotal]
    grand_total_seconds: float

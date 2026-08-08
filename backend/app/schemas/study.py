"""
Schemas for user-study mode.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StudyEnterRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=32, description="Participant code, e.g. P01")


class StudyPublicInfo(BaseModel):
    slug: str
    name: str
    enabled: bool
    welcome_text: Optional[str] = None
    persona_set_id: int
    project_id: Optional[int] = None


class StudyParticipantInfo(BaseModel):
    id: int
    code: str
    display_name: Optional[str] = None

    class Config:
        from_attributes = True


class StudyEnterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    study: StudyPublicInfo
    participant: StudyParticipantInfo
    user: Dict[str, Any]


class StudyPersonaOrderUpdate(BaseModel):
    persona_order: List[int] = Field(..., min_length=1)


class StudyEventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=64)
    path: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class StudyEventResponse(BaseModel):
    id: int
    study_id: int
    participant_id: Optional[int] = None
    user_id: Optional[int] = None
    event_type: str
    path: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StudyConfigResponse(BaseModel):
    id: int
    slug: str
    name: str
    enabled: bool
    project_id: Optional[int] = None
    persona_set_id: int
    persona_order: Optional[List[int]] = None
    order_rotations: Optional[List[List[str]]] = None
    allow_open_codes: bool
    max_participants: int
    welcome_text: Optional[str] = None

    class Config:
        from_attributes = True


class StudyConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    enabled: Optional[bool] = None
    project_id: Optional[int] = None
    persona_set_id: Optional[int] = None
    persona_order: Optional[List[int]] = None
    order_rotations: Optional[List[List[str]]] = None
    allow_open_codes: Optional[bool] = None
    max_participants: Optional[int] = Field(None, ge=1, le=500)
    welcome_text: Optional[str] = None
    # When true and persona_set_id changes, rebuild AH/HW/BISP rotations if groups exist
    rebuild_rotations: bool = True


class StudyParticipantAdminInfo(BaseModel):
    id: int
    code: str
    display_name: Optional[str] = None
    user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    event_count: int = 0
    is_test: bool = False

    class Config:
        from_attributes = True


class StudyEventAdminResponse(BaseModel):
    id: int
    study_id: int
    participant_id: Optional[int] = None
    participant_code: Optional[str] = None
    user_id: Optional[int] = None
    event_type: str
    path: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class StudyAdminSummary(BaseModel):
    id: int
    slug: str
    name: str
    enabled: bool
    project_id: Optional[int] = None
    persona_set_id: int
    participant_count: int = 0
    event_count: int = 0

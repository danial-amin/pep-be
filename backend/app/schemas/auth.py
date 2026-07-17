"""
Auth and invite request/response schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    is_admin: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class InviteCreateRequest(BaseModel):
    email: EmailStr
    note: Optional[str] = None
    expires_in_days: Optional[int] = Field(None, ge=1, le=90)


class InviteResponse(BaseModel):
    id: int
    email: str
    token: str
    invited_by_id: int
    accepted_at: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime
    note: Optional[str] = None
    # Convenience for admin UI: full accept URL path
    accept_path: str = ""

    class Config:
        from_attributes = True


class InvitePreviewResponse(BaseModel):
    email: str
    expires_at: datetime
    note: Optional[str] = None
    valid: bool


class AcceptInviteRequest(BaseModel):
    token: str = Field(..., min_length=16)
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


TokenResponse.model_rebuild()

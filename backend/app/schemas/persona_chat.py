"""
Schemas for controlled persona chat endpoints.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime


class PersonaChatCreateRequest(BaseModel):
    persona_id: int
    project_id: Optional[int] = None


class PersonaChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    strict_mode: bool = True


class PersonaChatSourceUsed(BaseModel):
    chunk_id: Optional[str] = None
    score: float
    preview: str


class PersonaChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    refused: bool = False
    retrieval_score: Optional[float] = None
    sources_used: Optional[List[PersonaChatSourceUsed]] = None
    refusal_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PersonaChatSessionResponse(BaseModel):
    id: int
    persona_id: int
    persona_name: str
    persona_image_url: Optional[str] = None
    project_id: Optional[int] = None
    messages: List[PersonaChatMessageResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class PersonaChatReplyResponse(BaseModel):
    reply: str
    refused: bool
    retrieval_score: Optional[float] = None
    sources_used: List[PersonaChatSourceUsed] = []
    refusal_reason: Optional[str] = None
    message_id: int
    session_id: int

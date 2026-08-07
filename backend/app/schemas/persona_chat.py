"""
Schemas for controlled persona chat endpoints.
"""
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import datetime


class PersonaChatCreateRequest(BaseModel):
    """Create a single-persona or set-mode chat session."""
    persona_id: Optional[int] = None
    persona_set_id: Optional[int] = None
    project_id: Optional[int] = None
    # When true (default), return the latest matching session for this user
    # instead of starting a blank conversation.
    resume: bool = True

    @model_validator(mode="after")
    def require_target(self):
        if self.persona_id is None and self.persona_set_id is None:
            raise ValueError("Provide persona_id or persona_set_id")
        if self.persona_id is not None and self.persona_set_id is not None:
            raise ValueError("Provide only one of persona_id or persona_set_id")
        return self


class PersonaChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    strict_mode: bool = False


class PersonaChatSourceUsed(BaseModel):
    chunk_id: Optional[str] = None
    score: float
    preview: str


class PersonaChatParticipant(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None


class PersonaChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    persona_id: Optional[int] = None
    persona_name: Optional[str] = None
    persona_image_url: Optional[str] = None
    refused: bool = False
    retrieval_score: Optional[float] = None
    sources_used: Optional[List[PersonaChatSourceUsed]] = None
    refusal_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PersonaChatSessionResponse(BaseModel):
    id: int
    mode: str = "single"
    persona_id: Optional[int] = None
    persona_name: str
    persona_image_url: Optional[str] = None
    persona_set_id: Optional[int] = None
    persona_set_name: Optional[str] = None
    project_id: Optional[int] = None
    participants: List[PersonaChatParticipant] = []
    messages: List[PersonaChatMessageResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class PersonaChatSingleReply(BaseModel):
    reply: str
    refused: bool
    persona_id: Optional[int] = None
    persona_name: Optional[str] = None
    persona_image_url: Optional[str] = None
    retrieval_score: Optional[float] = None
    sources_used: List[PersonaChatSourceUsed] = []
    refusal_reason: Optional[str] = None
    message_id: int


class PersonaChatReplyResponse(BaseModel):
    """
    Backward-compatible reply:
      - single mode: reply + message_id populated
      - set mode: replies[] with one entry per speaking persona
    """
    reply: Optional[str] = None
    refused: bool = False
    retrieval_score: Optional[float] = None
    sources_used: List[PersonaChatSourceUsed] = []
    refusal_reason: Optional[str] = None
    message_id: Optional[int] = None
    session_id: int
    replies: List[PersonaChatSingleReply] = []

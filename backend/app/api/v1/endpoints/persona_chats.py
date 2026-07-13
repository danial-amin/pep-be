"""
Persona chat endpoints — controlled 1:1 conversations with a single persona.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.persona_chat import PersonaChatSession, PersonaChatMessage
from app.schemas.persona_chat import (
    PersonaChatCreateRequest,
    PersonaChatMessageRequest,
    PersonaChatSessionResponse,
    PersonaChatMessageResponse,
    PersonaChatReplyResponse,
    PersonaChatSourceUsed,
)
from app.services.persona_chat_service import persona_chat_service

router = APIRouter()


def _build_message_response(msg: PersonaChatMessage) -> PersonaChatMessageResponse:
    sources = None
    if msg.sources_used:
        sources = [
            PersonaChatSourceUsed(
                chunk_id=s.get("chunk_id"),
                score=s.get("score", 0.0),
                preview=s.get("preview", ""),
            )
            for s in msg.sources_used
        ]
    return PersonaChatMessageResponse(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        refused=bool(msg.refused),
        retrieval_score=msg.retrieval_score,
        sources_used=sources,
        refusal_reason=msg.refusal_reason,
        created_at=msg.created_at,
    )


def _build_session_response(session: PersonaChatSession) -> PersonaChatSessionResponse:
    image_url = None
    if session.persona:
        image_url = session.persona.image_url
    return PersonaChatSessionResponse(
        id=session.id,
        persona_id=session.persona_id,
        persona_name=session.persona_name,
        persona_image_url=image_url,
        project_id=session.project_id,
        messages=[_build_message_response(m) for m in (session.messages or [])],
        created_at=session.created_at,
    )


@router.post("/", response_model=PersonaChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_persona_chat_session(
    request: PersonaChatCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start a new controlled chat session with a persona."""
    try:
        chat_session = await persona_chat_service.create_session(
            db, request.persona_id, request.project_id
        )
        await db.commit()
        loaded = await persona_chat_service.get_session(db, chat_session.id)
        return _build_session_response(loaded)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{session_id}", response_model=PersonaChatSessionResponse)
async def get_persona_chat_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a chat session with full message history."""
    chat_session = await persona_chat_service.get_session(db, session_id)
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return _build_session_response(chat_session)


@router.post("/{session_id}/messages", response_model=PersonaChatReplyResponse)
async def send_persona_chat_message(
    session_id: int,
    request: PersonaChatMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a message and receive a knowledge-bounded persona reply."""
    try:
        result = await persona_chat_service.send_message(
            db,
            session_id,
            request.message,
            strict_mode=request.strict_mode,
        )
        await db.commit()
        return PersonaChatReplyResponse(
            reply=result["reply"],
            refused=result["refused"],
            retrieval_score=result.get("retrieval_score"),
            sources_used=[
                PersonaChatSourceUsed(
                    chunk_id=s.get("chunk_id"),
                    score=s.get("score", 0.0),
                    preview=s.get("preview", ""),
                )
                for s in (result.get("sources_used") or [])
            ],
            refusal_reason=result.get("refusal_reason"),
            message_id=result["message_id"],
            session_id=result["session_id"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona_chat_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session and all its messages."""
    result = await db.execute(
        select(PersonaChatSession).where(PersonaChatSession.id == session_id)
    )
    chat_session = result.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await db.delete(chat_session)
    await db.commit()

"""
Persona chat endpoints — controlled 1:1 and set-mode conversations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.persona_chat import PersonaChatSession, PersonaChatMessage
from app.schemas.persona_chat import (
    PersonaChatCreateRequest,
    PersonaChatMessageRequest,
    PersonaChatSessionResponse,
    PersonaChatMessageResponse,
    PersonaChatReplyResponse,
    PersonaChatSourceUsed,
    PersonaChatParticipant,
    PersonaChatSingleReply,
)
from app.services.persona_chat_service import persona_chat_service

router = APIRouter()


def _sources(msg_or_list) -> list:
    raw = msg_or_list if isinstance(msg_or_list, list) else (msg_or_list or [])
    return [
        PersonaChatSourceUsed(
            chunk_id=s.get("chunk_id"),
            score=s.get("score", 0.0),
            preview=s.get("preview", ""),
        )
        for s in raw
    ]


def _build_message_response(msg: PersonaChatMessage) -> PersonaChatMessageResponse:
    image_url = None
    if msg.persona:
        image_url = msg.persona.image_url
    return PersonaChatMessageResponse(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        persona_id=msg.persona_id,
        persona_name=msg.persona_name,
        persona_image_url=image_url,
        refused=bool(msg.refused),
        retrieval_score=msg.retrieval_score,
        sources_used=_sources(msg.sources_used) if msg.sources_used else None,
        refusal_reason=msg.refusal_reason,
        created_at=msg.created_at,
    )


def _build_session_response(session: PersonaChatSession) -> PersonaChatSessionResponse:
    mode = getattr(session, "mode", None) or ("set" if session.persona_set_id else "single")
    image_url = None
    if session.persona:
        image_url = session.persona.image_url

    participants = []
    set_name = None
    if mode == "set" and session.persona_set:
        set_name = session.persona_set.name
        for p in session.persona_set.personas or []:
            participants.append(PersonaChatParticipant(
                id=p.id,
                name=(p.persona_data or {}).get("name") or p.name,
                image_url=p.image_url,
            ))
    elif session.persona:
        participants.append(PersonaChatParticipant(
            id=session.persona.id,
            name=session.persona.name,
            image_url=session.persona.image_url,
        ))

    return PersonaChatSessionResponse(
        id=session.id,
        mode=mode,
        persona_id=session.persona_id,
        persona_name=session.persona_name,
        persona_image_url=image_url,
        persona_set_id=session.persona_set_id,
        persona_set_name=set_name,
        project_id=session.project_id,
        participants=participants,
        messages=[_build_message_response(m) for m in (session.messages or [])],
        created_at=session.created_at,
    )


@router.post("/", response_model=PersonaChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_persona_chat_session(
    request: PersonaChatCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Start a chat session with one persona or an entire persona set.

    By default resumes the latest session for this user + target so switching
    personas does not wipe conversation history. Pass resume=false for a blank chat.
    """
    try:
        chat_session = await persona_chat_service.create_session(
            db,
            persona_id=request.persona_id,
            persona_set_id=request.persona_set_id,
            project_id=request.project_id,
            user_id=user.id,
            resume=request.resume,
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
    """
    Send a message and receive persona reply/replies.

    Set mode:
      - no @mention → all personas in the set reply
      - @PersonaName → only that persona replies
    """
    try:
        result = await persona_chat_service.send_message(
            db,
            session_id,
            request.message,
            strict_mode=request.strict_mode,
        )
        await db.commit()

        replies = [
            PersonaChatSingleReply(
                reply=r["reply"],
                refused=r.get("refused", False),
                persona_id=r.get("persona_id"),
                persona_name=r.get("persona_name"),
                persona_image_url=r.get("persona_image_url"),
                retrieval_score=r.get("retrieval_score"),
                sources_used=_sources(r.get("sources_used")),
                refusal_reason=r.get("refusal_reason"),
                message_id=r["message_id"],
            )
            for r in (result.get("replies") or [])
        ]

        return PersonaChatReplyResponse(
            reply=result.get("reply"),
            refused=result.get("refused", False),
            retrieval_score=result.get("retrieval_score"),
            sources_used=_sources(result.get("sources_used")),
            refusal_reason=result.get("refusal_reason"),
            message_id=result.get("message_id"),
            session_id=result["session_id"],
            replies=replies,
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

"""
Simulation endpoints for multi-persona conversation playground.

Enables creating and running simulations where persona-infused LLMs
converse with each other towards a common goal.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional, Any
from datetime import datetime
import json

from app.core.database import get_db
from app.models.simulation import Simulation, SimulationParticipant, SimulationMessage
from app.models.persona import Persona
from app.schemas.simulation import (
    SimulationCreateRequest,
    SimulationStartRequest,
    HumanInterventionRequest,
    SimulationResponse,
    SimulationListResponse,
    SimulationMessageResponse,
    SimulationParticipantResponse,
    PersonaSummaryEntry,
    SimulationTurnResponse,
    SimulationSummaryResponse
)
from app.services.persona_simulation_service import simulation_service
from app.services.persona_evaluation_service import persona_evaluation_service

router = APIRouter()


def _build_message_response(msg: SimulationMessage, persona: Optional[Persona]) -> SimulationMessageResponse:
    """Build a message response with persona details."""
    if getattr(msg, "is_human_message", False) or msg.persona_id is None:
        return SimulationMessageResponse(
            id=msg.id,
            persona_id=None,
            persona_name="Facilitator",
            persona_image_url=None,
            content=msg.content,
            turn_number=msg.turn_number,
            tokens=msg.tokens,
            is_moderator_message=msg.is_moderator_message,
            is_human_message=True,
            created_at=msg.created_at
        )
    return SimulationMessageResponse(
        id=msg.id,
        persona_id=msg.persona_id,
        persona_name=persona.name if persona else "Unknown",
        persona_image_url=persona.image_url if persona else None,
        content=msg.content,
        turn_number=msg.turn_number,
        tokens=msg.tokens,
        is_moderator_message=msg.is_moderator_message,
        is_human_message=getattr(msg, "is_human_message", False),
        created_at=msg.created_at
    )


def _build_participant_response(participant: SimulationParticipant, persona: Optional[Persona]) -> SimulationParticipantResponse:
    """Build a participant response with persona details."""
    return SimulationParticipantResponse(
        id=participant.id,
        persona_id=participant.persona_id,
        persona_name=persona.name if persona else "Unknown",
        persona_image_url=persona.image_url if persona else None,
        role=participant.role,
        messages_count=participant.messages_count,
        tokens_used=participant.tokens_used
    )


async def _build_simulation_response(
    simulation: Simulation,
    session: AsyncSession
) -> SimulationResponse:
    """Build a full simulation response with participants and messages."""
    # Get personas for participants
    participant_responses = []
    personas_map = {}

    for p in simulation.participants:
        result = await session.execute(
            select(Persona).where(Persona.id == p.persona_id)
        )
        persona = result.scalar_one_or_none()
        if persona:
            personas_map[p.persona_id] = persona
        participant_responses.append(_build_participant_response(p, persona))

    # Build message responses
    message_responses = []
    for msg in simulation.messages:
        persona = personas_map.get(msg.persona_id)
        message_responses.append(_build_message_response(msg, persona))

    # Parse summary: may be JSON array of persona summaries or legacy string
    summary_raw = simulation.summary
    summary_out: Optional[str] = None
    persona_summaries_out: Optional[List[PersonaSummaryEntry]] = None
    if summary_raw:
        try:
            parsed = json.loads(summary_raw)
            if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                if "persona_id" in parsed[0] and "summary" in parsed[0]:
                    persona_summaries_out = [
                        PersonaSummaryEntry(
                            persona_id=e["persona_id"],
                            persona_name=e.get("persona_name", ""),
                            summary=e.get("summary", "")
                        )
                        for e in parsed
                    ]
        except (json.JSONDecodeError, TypeError):
            pass
        if persona_summaries_out is None:
            summary_out = summary_raw

    return SimulationResponse(
        id=simulation.id,
        name=simulation.name,
        goal=simulation.goal,
        goal_context=simulation.goal_context,
        max_duration_seconds=simulation.max_duration_seconds,
        max_tokens=simulation.max_tokens,
        max_turns=simulation.max_turns,
        status=simulation.status,
        current_turn=simulation.current_turn,
        tokens_used=simulation.tokens_used,
        started_at=simulation.started_at,
        completed_at=simulation.completed_at,
        summary=summary_out,
        persona_summaries=persona_summaries_out,
        key_insights=simulation.key_insights,
        action_items=simulation.action_items,
        participants=participant_responses,
        messages=message_responses,
        project_id=simulation.project_id,
        created_at=simulation.created_at,
        updated_at=simulation.updated_at
    )


@router.post("/", response_model=SimulationResponse, status_code=status.HTTP_201_CREATED)
async def create_simulation(
    request: SimulationCreateRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Create a new simulation session.

    Sets up the simulation with the specified personas, goal, and constraints.
    The simulation will not start running until the start endpoint is called.
    """
    # Validate that all personas exist
    for participant in request.participants:
        result = await session.execute(
            select(Persona).where(Persona.id == participant.persona_id)
        )
        persona = result.scalar_one_or_none()
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona with ID {participant.persona_id} not found"
            )

    # Create simulation
    simulation = Simulation(
        name=request.name,
        goal=request.goal,
        goal_context=request.goal_context,
        max_duration_seconds=request.max_duration_seconds,
        max_tokens=request.max_tokens,
        max_turns=request.max_turns,
        project_id=request.project_id,
        status="pending"
    )
    session.add(simulation)
    await session.flush()  # Get the simulation ID

    # Add participants
    for participant in request.participants:
        sim_participant = SimulationParticipant(
            simulation_id=simulation.id,
            persona_id=participant.persona_id,
            role=participant.role
        )
        session.add(sim_participant)

    await session.commit()

    # Refresh to load relationships
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages)
        )
        .where(Simulation.id == simulation.id)
    )
    simulation = result.scalar_one()

    return await _build_simulation_response(simulation, session)


@router.get("/", response_model=List[SimulationListResponse])
async def list_simulations(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """
    List all simulations, optionally filtered by project or status.
    """
    query = select(Simulation).options(selectinload(Simulation.participants))

    if project_id:
        query = query.where(Simulation.project_id == project_id)
    if status:
        query = query.where(Simulation.status == status)

    query = query.order_by(Simulation.created_at.desc())

    result = await session.execute(query)
    simulations = result.scalars().all()

    return [
        SimulationListResponse(
            id=sim.id,
            name=sim.name,
            goal=sim.goal,
            status=sim.status,
            current_turn=sim.current_turn,
            max_turns=sim.max_turns,
            tokens_used=sim.tokens_used,
            max_tokens=sim.max_tokens,
            participant_count=len(sim.participants),
            started_at=sim.started_at,
            completed_at=sim.completed_at,
            created_at=sim.created_at
        )
        for sim in simulations
    ]


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    Get a simulation by ID with full details.
    """
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages)
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found"
        )

    return await _build_simulation_response(simulation, session)


def _serialize_export_value(v: Any) -> Any:
    """Serialize a value for JSON export (datetimes to ISO string)."""
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, list):
        return [_serialize_export_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _serialize_export_value(x) for k, x in v.items()}
    return v


async def _build_simulation_export(simulation: Simulation, session: AsyncSession) -> dict:
    """Build the full simulation export payload (setup, conversations, summaries)."""
    personas_map = {}
    for p in simulation.participants:
        result = await session.execute(select(Persona).where(Persona.id == p.persona_id))
        persona = result.scalar_one_or_none()
        if persona:
            personas_map[p.persona_id] = persona

    setup = {
        "name": simulation.name,
        "goal": simulation.goal,
        "goal_context": simulation.goal_context,
        "max_duration_seconds": simulation.max_duration_seconds,
        "max_tokens": simulation.max_tokens,
        "max_turns": simulation.max_turns,
        "status": simulation.status,
        "current_turn": simulation.current_turn,
        "tokens_used": simulation.tokens_used,
        "project_id": simulation.project_id,
        "created_at": simulation.created_at,
        "updated_at": simulation.updated_at,
        "started_at": simulation.started_at,
        "completed_at": simulation.completed_at,
        "participants": [
            {
                "id": p.id,
                "persona_id": p.persona_id,
                "persona_name": (persona.name if (persona := personas_map.get(p.persona_id)) else "Unknown"),
                "role": p.role,
                "messages_count": p.messages_count,
                "tokens_used": p.tokens_used,
            }
            for p in simulation.participants
        ],
    }

    conversations = []
    for msg in simulation.messages:
        persona = personas_map.get(msg.persona_id)
        name = "Facilitator" if (getattr(msg, "is_human_message", False) or msg.persona_id is None) else (persona.name if persona else "Unknown")
        conversations.append({
            "id": msg.id,
            "turn_number": msg.turn_number,
            "persona_id": msg.persona_id,
            "persona_name": name,
            "content": msg.content,
            "tokens": msg.tokens,
            "is_moderator_message": msg.is_moderator_message,
            "is_human_message": getattr(msg, "is_human_message", False),
            "responding_to_id": msg.responding_to_id,
            "created_at": msg.created_at,
        })

    payload = {
        "simulation_id": simulation.id,
        "setup": _serialize_export_value(setup),
        "conversations": _serialize_export_value(conversations),
    }

    if simulation.summary or simulation.key_insights or simulation.action_items:
        summaries_payload = {"key_insights": simulation.key_insights or [], "action_items": simulation.action_items or []}
        if simulation.summary:
            try:
                parsed = json.loads(simulation.summary)
                if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict) and "persona_id" in parsed[0]:
                    summaries_payload["persona_summaries"] = parsed
                    summaries_payload["summary"] = ""
                else:
                    summaries_payload["summary"] = simulation.summary
            except (json.JSONDecodeError, TypeError):
                summaries_payload["summary"] = simulation.summary
        else:
            summaries_payload["summary"] = ""
        payload["summaries"] = _serialize_export_value(summaries_payload)

    return payload


@router.get("/{simulation_id}/download")
async def download_simulation(
    simulation_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    Download the simulation as JSON including setup, all conversations, and summaries (if generated).

    Returns a JSON file with:
    - setup: name, goal, constraints, participants, timestamps
    - conversations: all messages in turn order with persona and content
    - summaries: summary text, key_insights, action_items (only present if generated)
    """
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages)
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found"
        )

    payload = await _build_simulation_export(simulation, session)
    filename = f"simulation-{simulation_id}.json"
    return JSONResponse(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/{simulation_id}/start", response_model=SimulationResponse)
async def start_simulation(
    simulation_id: int,
    request: SimulationStartRequest = SimulationStartRequest(),
    session: AsyncSession = Depends(get_db)
):
    """
    Start running a simulation.

    If auto_continue is True, runs all turns until completion.
    If False, runs only one turn.
    """
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages)
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found"
        )

    if simulation.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation is already {simulation.status}"
        )

    if request.auto_continue:
        # Run full simulation
        await simulation_service.run_full_simulation(simulation, session)
    else:
        # Run single turn
        if simulation.status == "pending":
            from datetime import datetime, timezone
            simulation.status = "running"
            simulation.started_at = datetime.now(timezone.utc)
            await session.commit()

        await simulation_service.generate_turn(simulation, session)

    # Refresh to get updated state
    await session.refresh(simulation, ["messages", "participants"])

    return await _build_simulation_response(simulation, session)


@router.post("/{simulation_id}/next-turn", response_model=SimulationTurnResponse)
async def next_turn(
    simulation_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    Generate the next turn in the simulation.

    Returns the new message and updated simulation state.
    """
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages)
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found"
        )

    if simulation.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation is already completed"
        )

    if simulation.status == "pending":
        from datetime import datetime, timezone
        simulation.status = "running"
        simulation.started_at = datetime.now(timezone.utc)
        await session.commit()

    message = await simulation_service.generate_turn(simulation, session)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not generate next turn"
        )

    # Get persona for message
    result = await session.execute(
        select(Persona).where(Persona.id == message.persona_id)
    )
    persona = result.scalar_one_or_none()

    return SimulationTurnResponse(
        message=_build_message_response(message, persona),
        simulation_status=simulation.status,
        current_turn=simulation.current_turn,
        tokens_used=simulation.tokens_used,
        tokens_remaining=simulation.max_tokens - simulation.tokens_used,
        turns_remaining=simulation.max_turns - simulation.current_turn,
        is_complete=simulation.status == "completed"
    )


@router.post("/{simulation_id}/intervene", response_model=SimulationMessageResponse, status_code=status.HTTP_201_CREATED)
async def human_intervene(
    simulation_id: int,
    request: HumanInterventionRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Add a human facilitator intervention to the simulation.

    The next persona turn will be prompted to address this intervention
    and give it strong weight in the conversation.
    """
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages)
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found"
        )

    if simulation.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot intervene: simulation is already {simulation.status}"
        )

    # Turn = round (all personas spoke once). Human message gets current round number.
    persona_count = simulation_service._count_persona_messages(list(simulation.messages))
    num_participants = max(1, len(simulation.participants))
    current_round = max(1, (persona_count + num_participants - 1) // num_participants)
    message = SimulationMessage(
        simulation_id=simulation.id,
        persona_id=None,
        content=request.content.strip(),
        turn_number=current_round,
        tokens=0,
        is_human_message=True
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)

    return _build_message_response(message, None)


@router.post("/{simulation_id}/stop")
async def stop_simulation(
    simulation_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    Stop a running simulation.
    """
    result = await session.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found"
        )

    if simulation.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation is already {simulation.status}"
        )

    from datetime import datetime, timezone
    simulation.status = "stopped"
    simulation.completed_at = datetime.now(timezone.utc)
    await session.commit()

    return {"status": "stopped", "simulation_id": simulation_id}


@router.post("/{simulation_id}/evaluate-adherence")
async def evaluate_simulation_adherence(
    simulation_id: int,
    sample_size: int = 5,
    session: AsyncSession = Depends(get_db)
):
    """
    Evaluate how well simulation messages adhere to personas (LLM-as-judge).

    Samples messages and rates each for persona consistency.
    """
    try:
        result = await persona_evaluation_service.evaluate_simulation_adherence(
            session=session,
            simulation_id=simulation_id,
            sample_size=sample_size
        )
        return result
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error evaluating simulation adherence: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating simulation adherence: {str(e)}"
        )


@router.post("/{simulation_id}/summary", response_model=SimulationSummaryResponse)
async def generate_summary(
    simulation_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    Generate a summary of the simulation conversation.

    Extracts key insights and action items from the discussion.
    """
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages)
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found"
        )

    if not simulation.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation has no messages to summarize"
        )

    summary_result = await simulation_service.generate_summary(simulation, session)

    # Calculate duration
    duration_seconds = None
    if simulation.started_at and simulation.completed_at:
        duration_seconds = int((simulation.completed_at - simulation.started_at).total_seconds())

    persona_summaries = [
        PersonaSummaryEntry(persona_id=e["persona_id"], persona_name=e["persona_name"], summary=e["summary"])
        for e in summary_result.get("persona_summaries", [])
    ]
    return SimulationSummaryResponse(
        simulation_id=simulation.id,
        persona_summaries=persona_summaries,
        summary=None,
        key_insights=summary_result.get("key_insights", []),
        action_items=summary_result.get("action_items", []),
        total_turns=simulation.current_turn,
        total_tokens=simulation.tokens_used,
        duration_seconds=duration_seconds
    )


@router.get("/{simulation_id}/stream")
async def stream_next_turn(
    simulation_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    Stream the next turn response in real-time.

    Returns a server-sent events stream with chunks of the response.
    """
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages)
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found"
        )

    if simulation.status == "pending":
        from datetime import datetime, timezone
        simulation.status = "running"
        simulation.started_at = datetime.now(timezone.utc)
        await session.commit()

    async def event_generator():
        async for event in simulation_service.stream_turn(simulation, session):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.delete("/{simulation_id}")
async def delete_simulation(
    simulation_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    Delete a simulation and all its messages.
    """
    result = await session.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found"
        )

    await session.delete(simulation)
    await session.commit()

    return {"status": "deleted", "simulation_id": simulation_id}

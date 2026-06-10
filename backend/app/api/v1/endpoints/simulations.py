"""
Simulation endpoints for multi-persona conversation playground.

Enables creating and running simulations where persona-infused LLMs
converse with each other towards a common goal.

Supports:
  - Personas from different persona sets in a single simulation
  - Continuous turns until agreement (agreement-based termination)
  - Personality trait maintenance via Core Identity Anchors
  - Agreement evaluation time-series via the AgreementEvaluatorService
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
from app.models.simulation import (
    Simulation,
    SimulationParticipant,
    SimulationMessage,
    SimulationAgreementEvaluation,
)
from app.models.persona import Persona, PersonaSet
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
    SimulationSummaryResponse,
    AgreementEvaluationResponse,
    AgreementHistoryResponse,
    PersonaStanceDetail,
)
from app.services.persona_simulation_service import simulation_service
from app.services.persona_evaluation_service import persona_evaluation_service
from app.services.agreement_evaluator_service import agreement_evaluator_service
from app.services.simulation_judge_service import simulation_judge_service
from app.schemas.judge import SimulationEvaluateRequest

router = APIRouter()


# ─── Helper builders ──────────────────────────────────────────────────────────

def _build_message_response(
    msg: SimulationMessage, persona: Optional[Persona]
) -> SimulationMessageResponse:
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
            persona_drift_score=None,
            created_at=msg.created_at,
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
        persona_drift_score=getattr(msg, "persona_drift_score", None),
        created_at=msg.created_at,
    )


def _build_participant_response(
    participant: SimulationParticipant,
    persona: Optional[Persona],
    persona_set: Optional[PersonaSet] = None,
) -> SimulationParticipantResponse:
    """Build a participant response with persona and persona-set details."""
    return SimulationParticipantResponse(
        id=participant.id,
        persona_id=participant.persona_id,
        persona_name=persona.name if persona else "Unknown",
        persona_image_url=persona.image_url if persona else None,
        persona_set_id=persona_set.id if persona_set else None,
        persona_set_name=persona_set.name if persona_set else None,
        role=participant.role,
        messages_count=participant.messages_count,
        tokens_used=participant.tokens_used,
    )


def _build_agreement_evaluation_response(
    ev: SimulationAgreementEvaluation,
) -> AgreementEvaluationResponse:
    """Convert a SimulationAgreementEvaluation ORM object to response schema."""
    persona_stances_out = None
    if ev.persona_stances:
        persona_stances_out = {}
        for pid_str, data in ev.persona_stances.items():
            persona_stances_out[pid_str] = PersonaStanceDetail(
                persona_name=data.get("persona_name", ""),
                initial_stance=data.get("initial_stance", ""),
                current_stance=data.get("current_stance", ""),
                drift_score=data.get("drift_score", 0.0),
                alignment_scores=data.get("alignment_scores", {}),
            )
    return AgreementEvaluationResponse(
        id=ev.id,
        simulation_id=ev.simulation_id,
        turn_number=ev.turn_number,
        overall_agreement_score=ev.overall_agreement_score,
        agreement_reached=ev.agreement_reached,
        persona_stances=persona_stances_out,
        evaluation_reasoning=ev.evaluation_reasoning,
        created_at=ev.created_at,
    )


async def _build_simulation_response(
    simulation: Simulation,
    session: AsyncSession,
) -> SimulationResponse:
    """Build a full simulation response with participants and messages."""
    participant_responses = []
    personas_map = {}

    for p in simulation.participants:
        result = await session.execute(
            select(Persona).where(Persona.id == p.persona_id)
        )
        persona = result.scalar_one_or_none()
        persona_set = None
        if persona:
            personas_map[p.persona_id] = persona
            result_ps = await session.execute(
                select(PersonaSet).where(PersonaSet.id == persona.persona_set_id)
            )
            persona_set = result_ps.scalar_one_or_none()
        participant_responses.append(
            _build_participant_response(p, persona, persona_set)
        )

    message_responses = []
    for msg in simulation.messages:
        persona = personas_map.get(msg.persona_id)
        message_responses.append(_build_message_response(msg, persona))

    # Parse summary
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
                            summary=e.get("summary", ""),
                        )
                        for e in parsed
                    ]
        except (json.JSONDecodeError, TypeError):
            pass
        if persona_summaries_out is None:
            summary_out = summary_raw

    # Latest agreement snapshot
    latest_score: Optional[float] = None
    agreement_reached = False
    evals = getattr(simulation, "agreement_evaluations", [])
    if evals:
        latest_eval = max(evals, key=lambda e: e.turn_number)
        latest_score = latest_eval.overall_agreement_score
        agreement_reached = latest_eval.agreement_reached

    return SimulationResponse(
        id=simulation.id,
        name=simulation.name,
        goal=simulation.goal,
        goal_context=simulation.goal_context,
        max_duration_seconds=simulation.max_duration_seconds,
        max_tokens=simulation.max_tokens or 0,
        max_turns=simulation.max_turns,
        run_until_agreement=getattr(simulation, "run_until_agreement", False) or False,
        agreement_threshold=getattr(simulation, "agreement_threshold", 0.75) or 0.75,
        status=simulation.status,
        current_turn=simulation.current_turn,
        tokens_used=simulation.tokens_used,
        latest_agreement_score=latest_score,
        agreement_reached=agreement_reached,
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
        updated_at=simulation.updated_at,
    )


# ─── Core simulation endpoints ────────────────────────────────────────────────

@router.post("/", response_model=SimulationResponse, status_code=status.HTTP_201_CREATED)
async def create_simulation(
    request: SimulationCreateRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Create a new simulation session.

    Participants may come from **different persona sets** — simply supply each
    persona's id regardless of which set it belongs to.

    When ``run_until_agreement=True`` the simulation will continue beyond
    ``max_turns`` (used as a safety cap) until the agreement evaluator reports
    that all personas have reached ``agreement_threshold``.
    """
    # Validate that all personas exist (no cross-set restriction)
    for participant in request.participants:
        result = await session.execute(
            select(Persona).where(Persona.id == participant.persona_id)
        )
        persona = result.scalar_one_or_none()
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Persona with ID {participant.persona_id} not found",
            )

    simulation = Simulation(
        name=request.name,
        goal=request.goal,
        goal_context=request.goal_context,
        max_duration_seconds=request.max_duration_seconds,
        max_tokens=request.max_tokens,
        max_turns=request.max_turns,
        run_until_agreement=request.run_until_agreement,
        agreement_threshold=request.agreement_threshold,
        project_id=request.project_id,
        status="pending",
    )
    session.add(simulation)
    await session.flush()

    for participant in request.participants:
        sim_participant = SimulationParticipant(
            simulation_id=simulation.id,
            persona_id=participant.persona_id,
            role=participant.role,
        )
        session.add(sim_participant)

    await session.commit()

    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages),
            selectinload(Simulation.agreement_evaluations),
        )
        .where(Simulation.id == simulation.id)
    )
    simulation = result.scalar_one()
    return await _build_simulation_response(simulation, session)


@router.get("/", response_model=List[SimulationListResponse])
async def list_simulations(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    """List all simulations, optionally filtered by project or status."""
    query = select(Simulation).options(
        selectinload(Simulation.participants),
        selectinload(Simulation.agreement_evaluations),
    )
    if project_id:
        query = query.where(Simulation.project_id == project_id)
    if status:
        query = query.where(Simulation.status == status)
    query = query.order_by(Simulation.created_at.desc())

    result = await session.execute(query)
    simulations = result.scalars().all()

    rows = []
    for sim in simulations:
        latest_score: Optional[float] = None
        agreement_reached = False
        evals = getattr(sim, "agreement_evaluations", [])
        if evals:
            latest_eval = max(evals, key=lambda e: e.turn_number)
            latest_score = latest_eval.overall_agreement_score
            agreement_reached = latest_eval.agreement_reached

        rows.append(
            SimulationListResponse(
                id=sim.id,
                name=sim.name,
                goal=sim.goal,
                status=sim.status,
                current_turn=sim.current_turn,
                max_turns=sim.max_turns,
                tokens_used=sim.tokens_used,
                max_tokens=sim.max_tokens or 0,
                participant_count=len(sim.participants),
                run_until_agreement=getattr(sim, "run_until_agreement", False) or False,
                latest_agreement_score=latest_score,
                agreement_reached=agreement_reached,
                started_at=sim.started_at,
                completed_at=sim.completed_at,
                created_at=sim.created_at,
            )
        )
    return rows


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Get a simulation by ID with full details."""
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages),
            selectinload(Simulation.agreement_evaluations),
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )
    return await _build_simulation_response(simulation, session)


# ─── Export ───────────────────────────────────────────────────────────────────

def _serialize_export_value(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, list):
        return [_serialize_export_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _serialize_export_value(x) for k, x in v.items()}
    return v


async def _build_simulation_export(simulation: Simulation, session: AsyncSession) -> dict:
    """Build the full simulation export payload."""
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
        "run_until_agreement": getattr(simulation, "run_until_agreement", False),
        "agreement_threshold": getattr(simulation, "agreement_threshold", 0.75),
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
                "persona_name": (personas_map[p.persona_id].name if p.persona_id in personas_map else "Unknown"),
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
        name = (
            "Facilitator"
            if (getattr(msg, "is_human_message", False) or msg.persona_id is None)
            else (persona.name if persona else "Unknown")
        )
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
            "persona_drift_score": getattr(msg, "persona_drift_score", None),
            "created_at": msg.created_at,
        })

    payload: dict = {
        "simulation_id": simulation.id,
        "setup": _serialize_export_value(setup),
        "conversations": _serialize_export_value(conversations),
    }

    if simulation.summary or simulation.key_insights or simulation.action_items:
        summaries_payload = {
            "key_insights": simulation.key_insights or [],
            "action_items": simulation.action_items or [],
        }
        if simulation.summary:
            try:
                parsed = json.loads(simulation.summary)
                if (
                    isinstance(parsed, list)
                    and parsed
                    and isinstance(parsed[0], dict)
                    and "persona_id" in parsed[0]
                ):
                    summaries_payload["persona_summaries"] = parsed
                    summaries_payload["summary"] = ""
                else:
                    summaries_payload["summary"] = simulation.summary
            except (json.JSONDecodeError, TypeError):
                summaries_payload["summary"] = simulation.summary
        else:
            summaries_payload["summary"] = ""
        payload["summaries"] = _serialize_export_value(summaries_payload)

    # Include agreement history in export
    evals = getattr(simulation, "agreement_evaluations", [])
    if evals:
        payload["agreement_history"] = _serialize_export_value([
            {
                "turn_number": e.turn_number,
                "overall_agreement_score": e.overall_agreement_score,
                "agreement_reached": e.agreement_reached,
                "persona_stances": e.persona_stances,
                "evaluation_reasoning": e.evaluation_reasoning,
                "created_at": e.created_at,
            }
            for e in sorted(evals, key=lambda e: e.turn_number)
        ])

    return payload


@router.get("/{simulation_id}/download")
async def download_simulation(
    simulation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Download the simulation as JSON including setup, conversations, summaries, and agreement history."""
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages),
            selectinload(Simulation.agreement_evaluations),
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )

    payload = await _build_simulation_export(simulation, session)
    filename = f"simulation-{simulation_id}.json"
    return JSONResponse(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Simulation lifecycle ─────────────────────────────────────────────────────

@router.post("/{simulation_id}/start", response_model=SimulationResponse)
async def start_simulation(
    simulation_id: int,
    request: SimulationStartRequest = SimulationStartRequest(),
    session: AsyncSession = Depends(get_db),
):
    """
    Start running a simulation.

    If ``auto_continue`` is True, runs all turns until completion
    (including agreement-based termination if configured).
    If False, runs only one turn.
    """
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages),
            selectinload(Simulation.agreement_evaluations),
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )

    if simulation.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation is already {simulation.status}",
        )

    if request.auto_continue:
        await simulation_service.run_full_simulation(simulation, session)
    else:
        if simulation.status == "pending":
            simulation.status = "running"
            simulation.started_at = datetime.now()
            await session.commit()
        await simulation_service.generate_turn(simulation, session)

    await session.refresh(simulation, ["messages", "participants", "agreement_evaluations"])
    return await _build_simulation_response(simulation, session)


@router.post("/{simulation_id}/next-turn", response_model=SimulationTurnResponse)
async def next_turn(
    simulation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """
    Generate the next turn in the simulation.

    Returns the new message and updated simulation state.
    If a complete round just finished (all personas spoke), an agreement
    evaluation is included in the response when run_until_agreement=True.
    """
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages),
            selectinload(Simulation.agreement_evaluations),
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )

    if simulation.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation is already completed",
        )

    if simulation.status == "pending":
        from datetime import timezone
        simulation.status = "running"
        simulation.started_at = datetime.now(timezone.utc)
        await session.commit()

    turn_before = simulation.current_turn
    message = await simulation_service.generate_turn(simulation, session)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not generate next turn",
        )

    # Run agreement evaluation if a full round just completed and mode is enabled
    agreement_eval_response = None
    run_until = getattr(simulation, "run_until_agreement", False)
    if run_until and simulation.current_turn > turn_before:
        await session.refresh(simulation, ["messages", "participants"])
        participants = {}
        for p in simulation.participants:
            result_p = await session.execute(
                select(Persona).where(Persona.id == p.persona_id)
            )
            persona = result_p.scalar_one_or_none()
            if persona:
                participants[p.persona_id] = persona
        try:
            ev = await agreement_evaluator_service.evaluate_agreement(
                simulation=simulation,
                participants=participants,
                session=session,
                turn_number=simulation.current_turn,
            )
            agreement_eval_response = _build_agreement_evaluation_response(ev)
            # Stop if agreement reached
            if ev.agreement_reached and simulation.status == "running":
                from datetime import timezone
                simulation.status = "completed"
                simulation.completed_at = datetime.now(timezone.utc)
                await session.commit()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Agreement evaluation failed in next-turn: %s", exc
            )

    result_p = await session.execute(
        select(Persona).where(Persona.id == message.persona_id)
    )
    persona = result_p.scalar_one_or_none()

    max_tokens = simulation.max_tokens or 0
    return SimulationTurnResponse(
        message=_build_message_response(message, persona),
        simulation_status=simulation.status,
        current_turn=simulation.current_turn,
        tokens_used=simulation.tokens_used,
        tokens_remaining=max_tokens - simulation.tokens_used if max_tokens else 0,
        turns_remaining=simulation.max_turns - simulation.current_turn,
        is_complete=simulation.status == "completed",
        agreement_evaluation=agreement_eval_response,
    )


@router.post(
    "/{simulation_id}/intervene",
    response_model=SimulationMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def human_intervene(
    simulation_id: int,
    request: HumanInterventionRequest,
    session: AsyncSession = Depends(get_db),
):
    """Add a human facilitator intervention to the simulation."""
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages),
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )

    if simulation.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot intervene: simulation is already {simulation.status}",
        )

    persona_count = simulation_service._count_persona_messages(list(simulation.messages))
    num_participants = max(1, len(simulation.participants))
    current_round = max(1, (persona_count + num_participants - 1) // num_participants)
    message = SimulationMessage(
        simulation_id=simulation.id,
        persona_id=None,
        content=request.content.strip(),
        turn_number=current_round,
        tokens=0,
        is_human_message=True,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return _build_message_response(message, None)


@router.post("/{simulation_id}/stop")
async def stop_simulation(
    simulation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Stop a running simulation."""
    result = await session.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )

    if simulation.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation is already {simulation.status}",
        )

    from datetime import timezone
    simulation.status = "stopped"
    simulation.completed_at = datetime.now(timezone.utc)
    await session.commit()
    return {"status": "stopped", "simulation_id": simulation_id}


# ─── Agreement evaluation endpoints ──────────────────────────────────────────

@router.get(
    "/{simulation_id}/agreement-history",
    response_model=AgreementHistoryResponse,
)
async def get_agreement_history(
    simulation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """
    Return the full time-series agreement history for a simulation.

    Each entry represents a snapshot taken after a complete round and shows:
    - Overall agreement score (0.0–1.0)
    - Per-persona stance summaries, drift from initial position, and
      pairwise alignment with every other persona
    - Whether the agreement threshold was reached at that point

    Use this data to render a convergence chart in the front-end.
    """
    result = await session.execute(
        select(Simulation)
        .options(selectinload(Simulation.agreement_evaluations))
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )

    evals = sorted(
        getattr(simulation, "agreement_evaluations", []),
        key=lambda e: e.turn_number,
    )
    agreement_reached = any(e.agreement_reached for e in evals)
    return AgreementHistoryResponse(
        simulation_id=simulation_id,
        agreement_threshold=getattr(simulation, "agreement_threshold", 0.75) or 0.75,
        agreement_reached=agreement_reached,
        evaluations=[_build_agreement_evaluation_response(e) for e in evals],
    )


@router.post(
    "/{simulation_id}/evaluate-agreement",
    response_model=AgreementEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_agreement_now(
    simulation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """
    Manually trigger an agreement evaluation at the current turn.

    Useful when the simulation is in single-step mode (auto_continue=False)
    or when you want an on-demand snapshot regardless of run_until_agreement.

    The evaluator will:
    1. Infer (or retrieve cached) initial stances from each persona's profile
    2. Extract current stances from their recent messages
    3. Score pairwise alignment and per-persona drift from original position
    4. Persist and return the snapshot
    """
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages),
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )

    if not simulation.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot evaluate agreement: simulation has no messages yet",
        )

    participants = {}
    for p in simulation.participants:
        result_p = await session.execute(
            select(Persona).where(Persona.id == p.persona_id)
        )
        persona = result_p.scalar_one_or_none()
        if persona:
            participants[p.persona_id] = persona

    try:
        ev = await agreement_evaluator_service.evaluate_agreement(
            simulation=simulation,
            participants=participants,
            session=session,
            turn_number=simulation.current_turn,
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Agreement evaluation error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agreement evaluation failed: {str(exc)}",
        )

    return _build_agreement_evaluation_response(ev)


# ─── Adherence evaluation & summary ──────────────────────────────────────────

@router.post("/{simulation_id}/evaluate")
async def evaluate_simulation(
    simulation_id: int,
    body: SimulationEvaluateRequest = SimulationEvaluateRequest(),
    session: AsyncSession = Depends(get_db),
):
    """
    Run LLM-as-judge evaluation for this simulation.

    Scores the full discussion and every participating persona. Only available
    when the simulation is completed or stopped.
    """
    try:
        return await simulation_judge_service.evaluate_simulation(
            session,
            simulation_id,
            force=body.force,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "Simulation evaluation error: %s", exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation evaluation failed: {str(exc)}",
        ) from exc


@router.get("/{simulation_id}/evaluation-scores")
async def get_simulation_evaluation_scores(
    simulation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Return stored LLM-as-judge scores for a simulation."""
    result = await session.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )
    return await simulation_judge_service.get_evaluation_scores(session, simulation_id)


@router.post("/{simulation_id}/evaluate-adherence")
async def evaluate_simulation_adherence(
    simulation_id: int,
    sample_size: int = 5,
    session: AsyncSession = Depends(get_db),
):
    """Evaluate how well simulation messages adhere to personas (LLM-as-judge)."""
    try:
        result = await persona_evaluation_service.evaluate_simulation_adherence(
            session=session,
            simulation_id=simulation_id,
            sample_size=sample_size,
        )
        return result
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            "Error evaluating simulation adherence: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating simulation adherence: {str(e)}",
        )


@router.post("/{simulation_id}/summary", response_model=SimulationSummaryResponse)
async def generate_summary(
    simulation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Generate a summary of the simulation conversation."""
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages),
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )

    if not simulation.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation has no messages to summarise",
        )

    summary_result = await simulation_service.generate_summary(simulation, session)

    duration_seconds = None
    if simulation.started_at and simulation.completed_at:
        duration_seconds = int(
            (simulation.completed_at - simulation.started_at).total_seconds()
        )

    persona_summaries = [
        PersonaSummaryEntry(
            persona_id=e["persona_id"],
            persona_name=e["persona_name"],
            summary=e["summary"],
        )
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
        duration_seconds=duration_seconds,
    )


# ─── Streaming ────────────────────────────────────────────────────────────────

@router.get("/{simulation_id}/stream")
async def stream_next_turn(
    simulation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Stream the next turn response in real-time (Server-Sent Events)."""
    result = await session.execute(
        select(Simulation)
        .options(
            selectinload(Simulation.participants),
            selectinload(Simulation.messages),
        )
        .where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )

    if simulation.status == "pending":
        from datetime import timezone
        simulation.status = "running"
        simulation.started_at = datetime.now(timezone.utc)
        await session.commit()

    async def event_generator():
        async for event in simulation_service.stream_turn(simulation, session):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ─── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/{simulation_id}")
async def delete_simulation(
    simulation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Delete a simulation and all its messages."""
    result = await session.execute(
        select(Simulation).where(Simulation.id == simulation_id)
    )
    simulation = result.scalar_one_or_none()
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found",
        )

    await session.delete(simulation)
    await session.commit()
    return {"status": "deleted", "simulation_id": simulation_id}

"""
Build formatted transcripts for simulation LLM-as-judge evaluation.

Read-only access to simulation_messages — does not modify simulation code.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.persona import Persona
from app.models.simulation import Simulation, SimulationMessage, SimulationParticipant


async def load_simulation_with_messages(
    session: AsyncSession,
    simulation_id: int,
) -> Simulation:
    result = await session.execute(
        select(Simulation)
        .where(Simulation.id == simulation_id)
        .options(
            selectinload(Simulation.messages).selectinload(SimulationMessage.persona),
            selectinload(Simulation.participants).selectinload(SimulationParticipant.persona),
        )
    )
    simulation = result.scalar_one_or_none()
    if simulation is None:
        raise ValueError(f"Simulation {simulation_id} not found")
    return simulation


def _participant_names(simulation: Simulation) -> Dict[int, str]:
    names: Dict[int, str] = {}
    for participant in simulation.participants:
        if participant.persona:
            names[participant.persona_id] = participant.persona.name
    for message in simulation.messages:
        if message.persona_id and message.persona:
            names[message.persona_id] = message.persona.name
    return names


def _ordered_messages(simulation: Simulation) -> List[SimulationMessage]:
    return sorted(
        simulation.messages,
        key=lambda m: (m.turn_number, m.id),
    )


def build_discussion_transcript(simulation: Simulation) -> str:
    """Full multi-persona discussion transcript."""
    names = _participant_names(simulation)
    lines = [
        f"Discussion ID: {simulation.id}",
        f"Discussion name: {simulation.name}",
        "",
        "Policy framing:",
        (
            "This is a multi-persona policy discussion in PEP on whether Cipherbot should "
            "provide direct explanatory answers to academic content questions or redirect "
            "students to existing resources. It is a wicked problem with no objectively correct answer."
        ),
        "",
        f"Goal: {simulation.goal}",
    ]
    if simulation.goal_context:
        lines.extend(["", f"Goal context: {simulation.goal_context}"])

    lines.extend([
        "",
        "Turn structure:",
        "- Turn 1: each persona wrote an independent opening statement without seeing others' messages.",
        "- Turns 2 onward: each persona could see the full conversation history.",
        "",
        "=== FULL DISCUSSION TRANSCRIPT ===",
    ])

    current_turn: Optional[int] = None
    for message in _ordered_messages(simulation):
        if message.is_moderator_message:
            continue
        if message.turn_number != current_turn:
            current_turn = message.turn_number
            lines.append(f"\n--- Turn {current_turn} ---")
        if message.is_human_message or message.persona_id is None:
            lines.append(f"[Facilitator]: {message.content}")
            continue
        speaker = names.get(message.persona_id, f"Persona {message.persona_id}")
        lines.append(f"[{speaker} (persona_id={message.persona_id})]: {message.content}")

    return "\n".join(lines)


def build_persona_transcript(
    simulation: Simulation,
    persona_id: int,
    persona_name: Optional[str] = None,
) -> str:
    """Full transcript for one persona across all turns in the discussion."""
    names = _participant_names(simulation)
    target_name = persona_name or names.get(persona_id, f"Persona {persona_id}")
    messages = _ordered_messages(simulation)
    target_messages = [m for m in messages if m.persona_id == persona_id and not m.is_moderator_message]

    if not target_messages:
        raise ValueError(
            f"Persona {persona_id} has no messages in simulation {simulation.id}"
        )

    lines = [
        f"Target persona: {target_name} (persona_id={persona_id})",
        f"Discussion ID: {simulation.id}",
        f"Discussion name: {simulation.name}",
        "",
        "Policy framing:",
        (
            "This is a multi-persona policy discussion in PEP on whether Cipherbot should "
            "provide direct explanatory answers to academic content questions or redirect "
            "students to existing resources. It is a wicked problem with no objectively correct answer."
        ),
        "",
        f"Goal: {simulation.goal}",
        "",
        "Turn structure:",
        "- Turn 1: this persona wrote an independent opening statement without seeing others' messages.",
        "- Turns 2 onward: this persona could see the full conversation history.",
        "",
        "Rate ONLY this persona's contributions, but use the full discussion context below.",
        "",
        "=== PERSONA TRANSCRIPT (full discussion with target persona highlighted) ===",
    ]

    current_turn: Optional[int] = None
    for message in messages:
        if message.is_moderator_message:
            continue
        if message.turn_number != current_turn:
            current_turn = message.turn_number
            turn_note = (
                " [Turn 1 — independent opening; target persona had not seen others yet]"
                if current_turn == 1
                else " [Target persona could see full history]"
            )
            lines.append(f"\n--- Turn {current_turn}{turn_note} ---")

        if message.is_human_message or message.persona_id is None:
            lines.append(f"[Facilitator]: {message.content}")
            continue

        speaker = names.get(message.persona_id, f"Persona {message.persona_id}")
        marker = " <<TARGET PERSONA>>" if message.persona_id == persona_id else ""
        lines.append(f"[{speaker} (persona_id={message.persona_id}){marker}]: {message.content}")

    return "\n".join(lines)


async def get_persona_name(session: AsyncSession, persona_id: int) -> str:
    result = await session.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if persona is None:
        raise ValueError(f"Persona {persona_id} not found")
    return persona.name

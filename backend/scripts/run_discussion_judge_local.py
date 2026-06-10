"""
Run a single discussion-level judge call locally (no database).

Fetches a completed simulation from a PEP API, builds the transcript, calls
one OpenAI judge model, and prints parsed scores. Use this to verify judge
parsing without Railway timeouts or a local DATABASE_URL.

Usage:
  cd backend && PYTHONPATH=. python scripts/run_discussion_judge_local.py \\
    --api-base https://backend-production-5b49c.up.railway.app \\
    --simulation-id 25 \\
    --judge-model gpt-4o-mini

Requires OPENAI_API_KEY in the environment.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from types import SimpleNamespace
from typing import Dict, List, Optional

import httpx
from openai import AsyncOpenAI

from app.schemas.judge import JudgeLLMOutput, parse_judge_response
from app.utils.judge_prompts import build_full_prompt


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discussion-only local judge smoke test.")
    parser.add_argument("--api-base", required=True, help="PEP backend base URL (no trailing /api/v1).")
    parser.add_argument("--simulation-id", type=int, required=True)
    parser.add_argument("--judge-model", default="gpt-4o-mini")
    parser.add_argument("--temperature", type=float, default=0.0)
    return parser.parse_args()


async def _fetch_simulation(api_base: str, simulation_id: int) -> dict:
    base = api_base.rstrip("/")
    url = f"{base}/api/v1/simulations/{simulation_id}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def _simulation_from_payload(payload: dict):
    messages = []
    for row in payload.get("messages", []):
        persona_name = row.get("persona_name") or f"Persona {row.get('persona_id')}"
        messages.append(
            SimpleNamespace(
                id=row.get("id", 0),
                turn_number=row.get("turn_number"),
                persona_id=row.get("persona_id"),
                persona=SimpleNamespace(name=persona_name) if row.get("persona_id") else None,
                is_moderator_message=row.get("is_moderator_message", False),
                is_human_message=row.get("is_human_message", False),
                content=row.get("content", ""),
            )
        )
    participants = []
    for row in payload.get("participants", []):
        nested = row.get("persona") or {}
        persona_name = nested.get("name") or row.get("persona_name") or f"Persona {row.get('persona_id')}"
        participants.append(
            SimpleNamespace(
                persona_id=row.get("persona_id"),
                persona=SimpleNamespace(name=persona_name),
            )
        )
    return SimpleNamespace(
        id=payload["id"],
        name=payload.get("name"),
        goal=payload.get("goal"),
        goal_context=payload.get("goal_context"),
        messages=messages,
        participants=participants,
    )


def _participant_names(simulation) -> Dict[int, str]:
    names: Dict[int, str] = {}
    for participant in simulation.participants:
        if participant.persona:
            names[participant.persona_id] = participant.persona.name
    for message in simulation.messages:
        if message.persona_id and message.persona:
            names[message.persona_id] = message.persona.name
    return names


def _ordered_messages(simulation) -> List:
    return sorted(simulation.messages, key=lambda m: (m.turn_number, m.id))


def _build_discussion_transcript(simulation) -> str:
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


async def _run(args: argparse.Namespace) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    payload = await _fetch_simulation(args.api_base, args.simulation_id)
    simulation = _simulation_from_payload(payload)
    transcript = _build_discussion_transcript(simulation)
    system_prompt, user_prompt, _template_hash = build_full_prompt("discussion", transcript)

    schema = JudgeLLMOutput.json_schema_for_level("discussion")
    client = AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model=args.judge_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=args.temperature,
        max_tokens=16384,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "simulation_judge_discussion",
                "strict": True,
                "schema": schema,
            },
        },
    )
    raw = json.loads(response.choices[0].message.content or "{}")
    parsed = parse_judge_response("discussion", raw)
    return {
        "simulation_id": args.simulation_id,
        "judge_model": args.judge_model,
        "model": getattr(response, "model", args.judge_model),
        "scores": {
            name: {
                "response_code": item.response_code,
                "response_label": item.response_label,
                "justification": item.justification,
            }
            for name, item in parsed.items()
        },
    }


def main() -> None:
    args = _parse_args()
    try:
        result = asyncio.run(_run(args))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

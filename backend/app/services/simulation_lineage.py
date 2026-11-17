"""Walk a simulation as a tree of messages instead of one flat transcript.

The focused path is the chain of parent_message_id links ending at
active_head_message_id. A null head is the goal root, so the path is empty.
Sibling children of the same parent are branches and stay out of each other's context.
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence


def lineage_messages(messages: Sequence, head_id: Optional[int]) -> list:
    """Messages from the root child up to and including head_id, in speak order."""
    by_id = {}
    for message in messages or []:
        message_id = getattr(message, "id", None)
        if message_id is not None:
            by_id[message_id] = message
    if head_id is None or head_id not in by_id:
        return []

    chain = []
    seen = set()
    current_id = head_id
    while current_id is not None and current_id not in seen:
        seen.add(current_id)
        message = by_id.get(current_id)
        if message is None:
            break
        chain.append(message)
        current_id = getattr(message, "parent_message_id", None)
    chain.reverse()
    return chain


def _persona_message(message) -> bool:
    return (
        getattr(message, "persona_id", None) is not None
        and not getattr(message, "is_human_message", False)
    )


def path_is_closed(simulation, lineage: Iterable, num_participants: int) -> bool:
    """True when the focused path should not grow: turn cap, token cap, or agreement."""
    messages = list(lineage or [])
    persona_count = sum(1 for message in messages if _persona_message(message))
    max_turns = getattr(simulation, "max_turns", 0) or 0
    if num_participants > 0 and max_turns > 0 and persona_count // num_participants >= max_turns:
        return True

    max_tokens = getattr(simulation, "max_tokens", None)
    if max_tokens:
        used = sum((getattr(message, "tokens", 0) or 0) for message in messages)
        if messages and used >= max_tokens:
            return True

    if getattr(simulation, "run_until_agreement", False):
        head_id = getattr(simulation, "active_head_message_id", None)
        for evaluation in getattr(simulation, "agreement_evaluations", None) or []:
            if (
                getattr(evaluation, "agreement_reached", False)
                and head_id is not None
                and getattr(evaluation, "head_message_id", None) == head_id
            ):
                return True
    return False


def completed_rounds(lineage: Sequence, num_participants: int) -> int:
    if num_participants <= 0:
        return 0
    persona_count = sum(1 for message in lineage if _persona_message(message))
    return persona_count // num_participants


def path_tokens(lineage: Sequence) -> int:
    return sum((getattr(message, "tokens", 0) or 0) for message in lineage)

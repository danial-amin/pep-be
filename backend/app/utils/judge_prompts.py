"""
Prompt construction for simulation LLM-as-judge evaluation.
"""
from __future__ import annotations

import hashlib
import json
from typing import List

from app.utils.judge_survey_items import (
    CONSTRUCT_DEFINITIONS,
    LIKERT_ANCHOR_LIST,
    Level,
    SurveyItem,
    items_for_level,
)

SIMULATION_FRAMING = """You are rating a multi-persona policy discussion simulation in PEP (Persona Extraction Pipeline).

The policy question and goal are stated in the transcript. Treat it as a contested question with no objectively correct answer.

Discussion structure:
- Turn 1: each persona wrote an independent opening statement without seeing what others said.
- Turns 2 onward: each persona could see the full conversation history.

Base every judgment ONLY on the transcript provided. Do not use outside knowledge.
For each rating, provide a one-sentence justification grounded in the transcript with at least one short direct quote or turn reference (e.g., "Turn 3").
Return ONLY the structured JSON object requested. No prose outside required justification fields."""

PERSONA_INSTRUCTIONS = """You are rating ONE target persona's behavior across the full discussion transcript.

Items are grouped in this order:
1. Stance development (Likert 1-7)
2. Identity consistency (Likert 1-7)
3. Argumentation (Likert 1-7)
4. Convergence and resistance (Likert 1-7; NA permitted on convergence1 and convergence2 only)
5. Stance outcome (single categorical choice)

Likert anchors (use these verbatim labels):
1 = Strongly disagree
2 = Disagree
3 = Somewhat disagree
4 = Neither agree nor disagree
5 = Somewhat agree
6 = Agree
7 = Strongly agree

For reverse-keyed items (argumentation3, convergence3): store the raw agreement rating; do not reverse-code.

For stance_full, select exactly one option verbatim from the list provided."""

DISCUSSION_INSTRUCTIONS = """You are rating the FULL multi-persona discussion.

Items are grouped in this order:
1. Overall pattern (single categorical choice)
2. Coordination (Likert 1-7)
3. Convergence character (Likert 1-7)
4. Argument quality (Likert 1-7)
5. Overall authenticity (single categorical choice)

Likert anchors (use these verbatim labels):
1 = Strongly disagree
2 = Disagree
3 = Somewhat disagree
4 = Neither agree nor disagree
5 = Somewhat agree
6 = Agree
7 = Strongly agree

Construct definitions:
- Overall pattern — """ + CONSTRUCT_DEFINITIONS["discussion_pattern"] + """
- Coordination — """ + CONSTRUCT_DEFINITIONS["coordination"] + """

For categorical items, select exactly one option verbatim. Do not invent categories."""


def _format_item_block(items: List[SurveyItem]) -> str:
    lines: List[str] = []
    current_construct = ""
    for item in items:
        if item.construct != current_construct:
            current_construct = item.construct
            lines.append(f"\n## {current_construct}")
        if item.item_type == "likert":
            na_note = " (NA permitted)" if item.allows_na else ""
            rev_note = f" [{item.reverse_keyed_note}]" if item.reverse_keyed_note else ""
            lines.append(f"- {item.name}: {item.text}{na_note}{rev_note}")
            lines.append(f"  Scale: {', '.join(f'{i+1}={a}' for i, a in enumerate(LIKERT_ANCHOR_LIST))}")
        else:
            lines.append(f"- {item.name}: {item.text}")
            for opt in item.options or ():
                lines.append(f"    • {opt}")
    return "\n".join(lines)


def build_system_prompt(level: Level) -> str:
    level_instructions = PERSONA_INSTRUCTIONS if level == "persona" else DISCUSSION_INSTRUCTIONS
    return f"{SIMULATION_FRAMING}\n\n{level_instructions}"


def build_user_prompt(level: Level, transcript: str) -> str:
    items = items_for_level(level)
    item_block = _format_item_block(items)
    output_shape = {
        item.name: {
            "response_code": "integer 1-7 for likert (null for NA or categorical)",
            "response_label": "verbatim anchor or category string",
            "justification": "one sentence with quote or turn reference",
        }
        for item in items
    }
    return f"""TRANSCRIPT:
{transcript}

SURVEY ITEMS (rate every item):
{item_block}

Return JSON with this shape (one entry per item, all items required):
{json.dumps(output_shape, indent=2)}"""


def prompt_template_hash(level: Level) -> str:
    payload = {
        "level": level,
        "system": build_system_prompt(level),
        "item_names": [i.name for i in items_for_level(level)],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def build_full_prompt(level: Level, transcript: str) -> tuple[str, str, str]:
    system = build_system_prompt(level)
    user = build_user_prompt(level, transcript)
    template_hash = prompt_template_hash(level)
    return system, user, template_hash

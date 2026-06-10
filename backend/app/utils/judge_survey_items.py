"""
Survey rubric for simulation LLM-as-judge evaluation.

Fixed item wording and scale anchors for reproducible, comparable scores.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

ItemType = Literal["likert", "categorical"]
Level = Literal["persona", "discussion"]

LIKERT_ANCHORS: Dict[int, str] = {
    1: "Strongly disagree",
    2: "Disagree",
    3: "Somewhat disagree",
    4: "Neither agree nor disagree",
    5: "Somewhat agree",
    6: "Agree",
    7: "Strongly agree",
}

LIKERT_ANCHOR_LIST: List[str] = [LIKERT_ANCHORS[i] for i in range(1, 8)]


@dataclass(frozen=True)
class SurveyItem:
    name: str
    text: str
    item_type: ItemType
    level: Level
    construct: str
    options: Optional[Tuple[str, ...]] = None
    allows_na: bool = False
    reverse_keyed_note: Optional[str] = None


PERSONA_STANCE_FULL_OPTIONS: Tuple[str, ...] = (
    "The persona maintained its stance and added new reasoning or examples.",
    "The persona maintained its stance but mostly repeated the same reasoning.",
    "The persona appeared to soften or qualify the stance, but did not change the basic position.",
    "The persona shifted away from its original position.",
)

DISCUSSION_PATTERN_OPTIONS: Tuple[str, ...] = (
    "Genuine: The closing positions appear connected to specific reasons or arguments made during the conversation.",
    "Mixed / Unclear: At least one persona shows reasoned movement, while others shift or align without a stated reason, or the evidence is too limited to classify confidently.",
    "Performative: The closing positions align or soften, but no reasons are stated in the conversation that account for the change (personas agree socially rather than argumentatively).",
    "Polarized: The personas remain divided with little sign of movement toward any shared position.",
)

AUTHENTICITY_OVERALL_OPTIONS: Tuple[str, ...] = (
    "Completely authentic",
    "Mostly authentic",
    "Somewhat authentic",
    "Mixed / Unclear",
    "Somewhat inauthentic",
    "Mostly inauthentic",
)

PERSONA_ITEMS: List[SurveyItem] = [
    SurveyItem("stance1", "This persona maintained the same basic position throughout the discussion.", "likert", "persona", "Stance development"),
    SurveyItem("stance2", "The persona added new reasons, examples, or qualifications while keeping the same overall stance.", "likert", "persona", "Stance development"),
    SurveyItem("stance3", "Other personas' arguments influenced how this persona justified their stance, even though the stance itself did not change.", "likert", "persona", "Stance development"),
    SurveyItem("consistency1", "This persona maintained a consistent identity across turns.", "likert", "persona", "Identity consistency"),
    SurveyItem("consistency2", "The language and tone remained stable throughout the discussion.", "likert", "persona", "Identity consistency"),
    SurveyItem("consistency3", "The concerns and priorities that defined this persona in Turn 1 were still recognisable in their later turns.", "likert", "persona", "Identity consistency"),
    SurveyItem("argumentation1", "The persona gave clear reasons for maintaining their original position.", "likert", "persona", "Argumentation"),
    SurveyItem("argumentation2", "The persona responded to other arguments while still preserving their original stance.", "likert", "persona", "Argumentation"),
    SurveyItem(
        "argumentation3",
        "The persona repeated their stance without adding meaningful reasoning.",
        "likert",
        "persona",
        "Argumentation",
        reverse_keyed_note="reverse-keyed relative to argument quality; store raw response",
    ),
    SurveyItem("convergence1", "This persona resisted changing their stance despite hearing opposing or moderating arguments.", "likert", "persona", "Convergence and resistance", allows_na=True),
    SurveyItem("convergence2", "The persona's continued stance seemed justified by their own priorities rather than by simply ignoring others.", "likert", "persona", "Convergence and resistance", allows_na=True),
    SurveyItem(
        "convergence3",
        "The persona failed to engage meaningfully with opposing arguments.",
        "likert",
        "persona",
        "Convergence and resistance",
        reverse_keyed_note="reverse-keyed; store raw response",
    ),
    SurveyItem("stance_full", "Stance outcome (select one):", "categorical", "persona", "Stance outcome", options=PERSONA_STANCE_FULL_OPTIONS),
]

DISCUSSION_ITEMS: List[SurveyItem] = [
    SurveyItem("discussion_pattern", "Overall pattern (select one):", "categorical", "discussion", "Overall pattern", options=DISCUSSION_PATTERN_OPTIONS),
    SurveyItem("coordination1", "The personas moved toward a more shared position by the end of the discussion.", "likert", "discussion", "Coordination"),
    SurveyItem("coordination2", "The closing positions were supported by reasons or arguments shown in the discussion.", "likert", "discussion", "Coordination"),
    SurveyItem("coordination3", "When persona(s) changed, softened, or qualified their positions, they explained why.", "likert", "discussion", "Coordination"),
    SurveyItem("coordination4", "The discussion shows genuine coordination (personas changed or held positions in response to each other's arguments, rather than simply agreeing without stated reasons).", "likert", "discussion", "Coordination"),
    SurveyItem("socialpressure", "Personas that changed their position appeared to do so because of social pressure from others (deference, politeness, or avoidance of conflict) rather than because of a specific argument.", "likert", "discussion", "Convergence character"),
    SurveyItem("authenticity", "The discussion felt like an authentic exchange, similar to how real people with different views would discuss a contested policy question.", "likert", "discussion", "Convergence character"),
    SurveyItem("performative", "The discussion felt performative (personas appeared to go through the motions of debate without genuinely engaging with each other's positions).", "likert", "discussion", "Convergence character"),
    SurveyItem("homogeneity", "The personas were equally skilled at expressing and defending their positions throughout the discussion.", "likert", "discussion", "Convergence character"),
    SurveyItem("argument1", "The arguments directly addressed the policy question stated in the discussion goal.", "likert", "discussion", "Argument quality"),
    SurveyItem("argument2", "The claims were supported with reasons, examples, or consequences rather than bare assertions.", "likert", "discussion", "Argument quality"),
    SurveyItem("argument3", "Personas engaged with concerns raised by other positions, such as efficiency, academic integrity, equity, institutional accountability, or student learning.", "likert", "discussion", "Argument quality"),
    SurveyItem("argument4", "The closing positions added new reasoning, qualifications, or synthesis compared with the opening positions.", "likert", "discussion", "Argument quality"),
    SurveyItem("argument5", "The discussion showed development rather than simple repetition of opening positions.", "likert", "discussion", "Argument quality"),
    SurveyItem("authenticity_overall", "Overall authenticity (select one):", "categorical", "discussion", "Overall authenticity", options=AUTHENTICITY_OVERALL_OPTIONS),
]

ALL_ITEMS: Dict[str, SurveyItem] = {
    item.name: item for item in PERSONA_ITEMS + DISCUSSION_ITEMS
}


def items_for_level(level: Level) -> List[SurveyItem]:
    if level == "persona":
        return PERSONA_ITEMS
    return DISCUSSION_ITEMS


def validate_likert_response(item: SurveyItem, response_code: Optional[int], response_label: str) -> None:
    if item.allows_na and response_label.strip().upper() == "NA":
        if response_code is not None:
            raise ValueError(f"{item.name}: NA response must have null response_code")
        return
    if response_code is None or response_code < 1 or response_code > 7:
        raise ValueError(f"{item.name}: Likert response_code must be 1-7")
    if LIKERT_ANCHORS[response_code] != response_label.strip():
        raise ValueError(
            f"{item.name}: response_label must match anchor for code {response_code}"
        )


def normalize_categorical_label(item: SurveyItem, response_label: str) -> str:
    """Map judge output to a verbatim option (models often return the short prefix only)."""
    label = response_label.strip()
    if not item.options:
        return label
    if label in item.options:
        return label
    lower = label.lower()
    for opt in item.options:
        if lower == opt.lower():
            return opt
        prefix = opt.split(":", 1)[0].strip()
        if lower == prefix.lower() or lower.startswith(prefix.lower()):
            return opt
        if opt.lower().startswith(lower):
            return opt
    return label


def validate_categorical_response(item: SurveyItem, response_code: Optional[int], response_label: str) -> None:
    if response_code is not None:
        raise ValueError(f"{item.name}: categorical response_code must be null")
    canonical = normalize_categorical_label(item, response_label)
    if not item.options or canonical not in item.options:
        raise ValueError(f"{item.name}: response_label must be one of the verbatim options")


CONSTRUCT_DEFINITIONS: Dict[str, str] = {
    "discussion_pattern": (
        "Genuine: closing positions are connected to specific reasons or arguments made during the conversation. "
        "Mixed / Unclear: at least one persona shows reasoned movement while others shift without stated reason, "
        "or evidence is too limited. Performative: closing positions align or soften but no reasons in the conversation "
        "account for the change (social agreement rather than argumentative). Polarized: personas remain divided "
        "with little movement toward any shared position."
    ),
    "coordination": (
        "Genuine coordination means personas changed or held positions in response to each other's arguments, "
        "rather than simply agreeing without stated reasons."
    ),
}

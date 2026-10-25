"""
Pydantic schemas for simulation LLM-as-judge evaluation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field

from app.utils.judge_survey_items import ALL_ITEMS


class ItemResponse(BaseModel):
    response_code: Optional[int] = None
    response_label: str
    justification: str = Field(min_length=10)


class JudgeLLMOutput(BaseModel):
    @classmethod
    def json_schema_for_level(cls, level: Literal["persona", "discussion"]) -> dict:
        from app.utils.judge_survey_items import LIKERT_ANCHOR_LIST, items_for_level

        properties = {}
        required = []
        for item in items_for_level(level):
            if item.item_type == "categorical" and item.options:
                label_schema: dict = {
                    "type": "string",
                    "enum": list(item.options),
                    "description": "Must be exactly one of the listed verbatim options",
                }
                item_properties = {
                    "response_label": label_schema,
                    "justification": {
                        "type": "string",
                        "description": "One sentence with quote or turn reference",
                    },
                }
                item_required = ["response_label", "justification"]
            else:
                likert_labels = list(LIKERT_ANCHOR_LIST)
                if item.allows_na:
                    likert_labels = likert_labels + ["NA"]
                label_schema = {
                    "type": "string",
                    "enum": likert_labels,
                    "description": "Must be exactly one of the Likert anchor labels",
                }
                item_properties = {
                    "response_code": {
                        "type": ["integer", "null"],
                        "description": "1-7 for Likert; null only when response_label is NA",
                    },
                    "response_label": label_schema,
                    "justification": {
                        "type": "string",
                        "description": "One sentence with quote or turn reference",
                    },
                }
                item_required = ["response_code", "response_label", "justification"]
            properties[item.name] = {
                "type": "object",
                "properties": item_properties,
                "required": item_required,
                "additionalProperties": False,
            }
            required.append(item.name)
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }


class SimulationEvaluateRequest(BaseModel):
    force: bool = False
    judge_models: Optional[list[str]] = None


class JudgeScoreRow(BaseModel):
    judge_model: str
    model_version: str
    pass_number: int
    temperature: float
    level: Literal["persona", "discussion"]
    simulation_id: int
    target_id: int
    item: str
    item_type: Literal["likert", "categorical"]
    response_code: Optional[int] = None
    response_label: str
    justification: str
    run_timestamp: datetime


def parse_judge_response(level: str, raw: dict) -> Dict[str, ItemResponse]:
    from app.utils.judge_survey_items import items_for_level

    expected = {item.name for item in items_for_level(level)}  # type: ignore[arg-type]
    missing = expected - set(raw.keys())
    if missing:
        raise ValueError(f"Judge response missing items: {sorted(missing)}")
    parsed: Dict[str, ItemResponse] = {}
    for name in expected:
        entry = dict(raw[name])
        if ALL_ITEMS[name].item_type == "categorical":
            entry.setdefault("response_code", None)
        item_response = ItemResponse(**entry)
        item_def = ALL_ITEMS[name]
        if item_def.item_type == "categorical":
            from app.utils.judge_survey_items import (
                normalize_categorical_label,
                validate_categorical_response,
            )
            canonical_label = normalize_categorical_label(item_def, item_response.response_label)
            item_response = ItemResponse(
                response_code=None,
                response_label=canonical_label,
                justification=item_response.justification,
            )
            validate_categorical_response(item_def, item_response.response_label)
        else:
            from app.utils.judge_survey_items import normalize_likert_response, validate_likert_response
            code, label = normalize_likert_response(
                item_def, item_response.response_code, item_response.response_label
            )
            item_response = ItemResponse(
                response_code=code,
                response_label=label,
                justification=item_response.justification,
            )
            validate_likert_response(item_def, item_response.response_code, item_response.response_label)
        parsed[name] = item_response
    return parsed

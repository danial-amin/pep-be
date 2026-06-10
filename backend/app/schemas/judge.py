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
        from app.utils.judge_survey_items import items_for_level

        properties = {}
        required = []
        for item in items_for_level(level):
            properties[item.name] = {
                "type": "object",
                "properties": {
                    "response_code": {
                        "type": ["integer", "null"],
                        "description": "1-7 for Likert; null for NA or categorical",
                    },
                    "response_label": {"type": "string"},
                    "justification": {
                        "type": "string",
                        "description": "One sentence with quote or turn reference",
                    },
                },
                "required": ["response_code", "response_label", "justification"],
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
        entry = raw[name]
        parsed[name] = ItemResponse(**entry)
        item_def = ALL_ITEMS[name]
        if item_def.item_type == "likert":
            from app.utils.judge_survey_items import validate_likert_response
            validate_likert_response(item_def, parsed[name].response_code, parsed[name].response_label)
        else:
            from app.utils.judge_survey_items import validate_categorical_response
            validate_categorical_response(item_def, parsed[name].response_code, parsed[name].response_label)
    return parsed

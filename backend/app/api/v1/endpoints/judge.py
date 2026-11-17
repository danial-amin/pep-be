"""
API endpoints for simulation LLM-as-judge score queries.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.judge_score import JudgeScore

router = APIRouter()


@router.get("/scores")
async def list_judge_scores(
    simulation_id: Optional[int] = Query(default=None),
    judge_model: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    """Return stored judge scores in long format, optionally filtered by simulation."""
    query = select(JudgeScore).order_by(
        JudgeScore.run_timestamp.desc(),
        JudgeScore.simulation_id,
        JudgeScore.judge_model,
        JudgeScore.target_id,
        JudgeScore.item,
    )
    if simulation_id is not None:
        query = query.where(JudgeScore.simulation_id == simulation_id)
    if judge_model:
        query = query.where(JudgeScore.judge_model == judge_model)
    if level:
        query = query.where(JudgeScore.level == level)

    result = await session.execute(query)
    rows = result.scalars().all()
    return [
        {
            "judge_model": r.judge_model,
            "model_version": r.model_version,
            "pass_number": r.pass_number,
            "temperature": r.temperature,
            "level": r.level,
            "simulation_id": r.simulation_id,
            "target_id": r.target_id,
            "item": r.item,
            "item_type": r.item_type,
            "response_code": r.response_code,
            "response_label": r.response_label,
            "justification": r.justification,
            "run_timestamp": r.run_timestamp.isoformat() if r.run_timestamp else None,
        }
        for r in rows
    ]


@router.get("/config")
async def judge_config():
    """Return current judge configuration defaults."""
    return {
        "judge_models": settings.judge_models_list(),
        "pass_count": settings.JUDGE_PASS_COUNT,
        "temperature": settings.JUDGE_TEMPERATURE,
    }

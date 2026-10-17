"""
ORM models for simulation LLM-as-judge scores (long format).
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class JudgeRun(Base):
    """One LLM judge call for a simulation target. Persists the exact prompt sent."""
    __tablename__ = "judge_runs"

    id = Column(Integer, primary_key=True, index=True)
    judge_model = Column(String(128), nullable=False)
    model_version = Column(String(128), nullable=False)
    pass_number = Column(Integer, nullable=False, default=1)
    temperature = Column(Float, nullable=False, default=0.0)
    level = Column(String(32), nullable=False)  # persona | discussion
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False, index=True)
    target_id = Column(Integer, nullable=False)  # persona_id for persona level; simulation_id for discussion
    prompt_template_hash = Column(String(64), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)
    run_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scores = relationship("JudgeScore", back_populates="judge_run", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "ix_judge_runs_unique",
            "judge_model",
            "level",
            "simulation_id",
            "target_id",
            "pass_number",
            unique=True,
        ),
    )


class JudgeScore(Base):
    """One row per (judge_model, pass_number, simulation, target, item)."""
    __tablename__ = "judge_scores"

    id = Column(Integer, primary_key=True, index=True)
    judge_run_id = Column(Integer, ForeignKey("judge_runs.id"), nullable=False, index=True)

    judge_model = Column(String(128), nullable=False)
    model_version = Column(String(128), nullable=False)
    pass_number = Column(Integer, nullable=False, default=1)
    temperature = Column(Float, nullable=False, default=0.0)
    level = Column(String(32), nullable=False)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False, index=True)
    target_id = Column(Integer, nullable=False)
    item = Column(String(64), nullable=False)
    item_type = Column(String(32), nullable=False)  # likert | categorical
    response_code = Column(Integer, nullable=True)
    response_label = Column(Text, nullable=False)
    justification = Column(Text, nullable=False)
    run_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    judge_run = relationship("JudgeRun", back_populates="scores")

    __table_args__ = (
        Index(
            "ix_judge_scores_unique",
            "judge_model",
            "pass_number",
            "level",
            "simulation_id",
            "target_id",
            "item",
            unique=True,
        ),
    )

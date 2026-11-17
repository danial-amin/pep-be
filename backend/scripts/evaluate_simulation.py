"""
Run LLM-as-judge evaluation for one simulation (local or against configured DB).

Usage:
  cd backend && PYTHONPATH=. python scripts/evaluate_simulation.py --simulation-id 24
  cd backend && PYTHONPATH=. python scripts/evaluate_simulation.py --simulation-id 24 --force
  cd backend && PYTHONPATH=. python scripts/evaluate_simulation.py --simulation-id 24 --judge-models gpt-4o-mini

Requires DATABASE_URL and OPENAI_API_KEY in the environment (or .env loaded by app config).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from app.core.database import AsyncSessionLocal
from app.services.simulation_judge_service import simulation_judge_service

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate one simulation with LLM judges.")
    parser.add_argument("--simulation-id", type=int, required=True)
    parser.add_argument("--force", action="store_true", help="Re-run even if scores exist.")
    parser.add_argument(
        "--judge-models",
        type=str,
        default=None,
        help="Comma-separated judge models (default: JUDGE_MODELS from config).",
    )
    parser.add_argument("--pass-count", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> dict:
    judge_models = None
    if args.judge_models:
        judge_models = [m.strip() for m in args.judge_models.split(",") if m.strip()]

    async with AsyncSessionLocal() as session:
        return await simulation_judge_service.evaluate_simulation(
            session,
            args.simulation_id,
            judge_models=judge_models,
            pass_count=args.pass_count,
            temperature=args.temperature,
            force=args.force,
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()
    try:
        result = asyncio.run(_run(args))
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc)
        sys.exit(1)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()

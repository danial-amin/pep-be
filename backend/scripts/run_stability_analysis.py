#!/usr/bin/env python3
"""
Repeated-run interaction stability analysis for Policy Study (SCI chat / MPS simulation).

Selects the longest and shortest observed persona responses per mode from real
study sessions, then reruns each fixed input N times (default 30).

Usage:
  cd backend && PYTHONPATH=. python scripts/run_stability_analysis.py
  cd backend && PYTHONPATH=. python scripts/run_stability_analysis.py --iterations 30 --output stability_report.json
  cd backend && PYTHONPATH=. python scripts/run_stability_analysis.py --list-only

Requires DATABASE_URL and OPENAI_API_KEY.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import AsyncSessionLocal
from app.services.stability_analysis_service import stability_analysis_service

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SCI/MPS repeated-run stability analysis")
    p.add_argument("--study-slug", default="policy-study")
    p.add_argument("--iterations", type=int, default=30)
    p.add_argument("--strict-mode", action="store_true", default=True)
    p.add_argument("--output", type=str, default="stability_analysis_report.json")
    p.add_argument(
        "--list-only",
        action="store_true",
        help="Only list longest/shortest candidates; do not rerun",
    )
    return p.parse_args()


async def _main(args: argparse.Namespace) -> dict:
    async with AsyncSessionLocal() as session:
        sci_long, sci_short = await stability_analysis_service.find_sci_candidates(
            session, args.study_slug
        )
        mps_long, mps_short = await stability_analysis_service.find_mps_candidates(
            session, args.study_slug
        )

        summary = {
            "study_slug": args.study_slug,
            "candidates": {
                "sci_longest": sci_long,
                "sci_shortest": sci_short,
                "mps_longest": mps_long,
                "mps_shortest": mps_short,
            },
        }

        if args.list_only:
            from dataclasses import asdict
            return {
                "study_slug": args.study_slug,
                "candidates": {
                    k: asdict(v) if v else None
                    for k, v in summary["candidates"].items()
                },
            }

        return await stability_analysis_service.run_full_analysis(
            session,
            study_slug=args.study_slug,
            iterations=args.iterations,
            strict_mode=args.strict_mode,
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()
    try:
        result = asyncio.run(_main(args))
    except Exception as exc:
        logger.error("Stability analysis failed: %s", exc)
        sys.exit(1)

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = BACKEND_ROOT / out_path
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Wrote {out_path}")

    # Console summary
    analyses = result.get("analyses") or {}
    for key, block in analyses.items():
        if "error" in block:
            print(f"{key}: ERROR — {block['error']}")
            continue
        m = block.get("metrics") or {}
        print(
            f"{key}: refusal_rate={m.get('refusal_rate'):.2f} "
            f"unique={m.get('unique_response_count')}/{m.get('n_runs')} "
            f"stance_consistency={m.get('stance_consistency'):.2f} "
            f"embed_mean={m.get('embedding_pairwise_mean')}"
        )


if __name__ == "__main__":
    main()

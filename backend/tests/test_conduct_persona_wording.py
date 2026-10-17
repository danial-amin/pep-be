"""Comparisons must name the month as a whole, which is the baseline population.

The month mean includes the group. Calling it "other accounts" uses the wrong population.
"""
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

from app.utils.nonanthropomorphized_personas import (  # noqa: E402
    _comparison_sentence,
    _stands_out,
)


def test_comparison_names_the_month_as_a_whole():
    sentence = _comparison_sentence(
        "comment_write_share", 0.13, 0.35, 0.13 - 0.35, "January 2026"
    )
    assert "other accounts" not in sentence
    assert "January 2026" in sentence
    assert "13%" in sentence
    assert "35%" in sentence
    assert "as a whole" in sentence


def test_visible_profile_stays_short():
    from app.utils.nonanthropomorphized_personas import _background, _goal_lines

    background = _background(
        "The Mixed Voice",
        "2026-01",
        "Mixed style/conduct account",
        {},
        [],
        "prose_or_other",
        None,
        [],
    )
    assert len(background) < 500
    assert "characterization" not in background
    assert "%" not in background
    goals = _goal_lines("The Mixed Voice", "2026-01", [], None, None, {})
    assert goals
    assert all("%" not in goal for goal in goals)


def test_stands_out_does_not_call_the_baseline_other_accounts():
    clause = _stands_out("comment_write_share", -0.2)
    assert clause is not None
    assert "other accounts" not in clause
    assert "across that month" in clause

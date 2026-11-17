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


def test_conduct_narrative_does_not_invent_a_life():
    from app.utils.nonanthropomorphized_personas import conduct_narrative

    text = conduct_narrative({
        "name": "The Direct Speaker",
        "basic_description": "States a claim directly.",
        "background": "The Direct Speaker is on Moltbook in February 2026.",
        "goals": ["State a claim directly"],
        "frustrations": ["One description does not fit every account in the group"],
        "behaviors": "The usual post is prose.",
        "quote": "Hello there.",
    })
    assert "The Direct Speaker" in text
    assert "no age" in text.lower()
    assert "anonymous" in text.lower()
    assert "not a chart" in text.lower()
    assert "family" not in text.lower()
    assert "café" not in text.lower()
    assert "\n\n" in text
    assert text.count("\n\n") >= 4


def test_repeated_conduct_labels_get_different_titles():
    from app.utils.nonanthropomorphized_personas import _titles_for_records

    def record(group_id, protocol, comments):
        baseline = {
            "median_chars": 800,
            "first_person_rate": 0.7,
            "fn_arrival_share": 0.1,
            "emoji_per_1k": 2,
            "hedge_rate": 0.15,
            "comment_write_share": 0.4,
            "spam_share": 0.05,
            "protocol_share": 0.02,
        }
        values = dict(baseline)
        values["protocol_share"] = protocol
        values["comment_write_share"] = comments
        attributes = [{"name": "month_baseline", "value": baseline}]
        attributes.extend({"name": key, "value": value} for key, value in values.items())
        return {
            "group_id": group_id,
            "conduct_label": "Low-reply prose poster",
            "attributes": attributes,
        }

    titles = _titles_for_records([
        record("2026-02_c4", 0.46, 0.25),
        record("2026-02_c10", 0.87, 0.16),
        {
            "group_id": "2026-02_c6",
            "conduct_label": "Long first-person writer",
            "attributes": [],
        },
    ])
    names = list(titles.values())
    assert len(names) == len(set(names))
    assert all("(c" not in name for name in names)
    assert titles["2026-02_c10"] == "The Protocol Poster"
    assert titles["2026-02_c6"] == "The Long Writer"


def test_creation_prompts_keep_nielsen_and_drop_a_private_life():
    from app.utils.prompts import (
        ENGAGING_NARRATIVE_PROMPT,
        NONANTHROPOMORPHIZED_NARRATIVE_PROMPT,
        narrative_json_contract,
    )

    normal = ENGAGING_NARRATIVE_PROMPT.format(num_personas=3)
    anonymous = NONANTHROPOMORPHIZED_NARRATIVE_PROMPT.format(num_personas=3)
    assert "Lene Nielsen" in normal
    assert "family situation" in normal
    assert "A Day in the Life" in normal
    assert "favorite café" in normal
    assert "non-anthropomorphized" in anonymous
    assert "Do not invent an age" in anonymous
    assert "Not a chart" in anonymous
    assert "favorite café" in anonymous
    assert "anonymous, featureless figure" in anonymous
    contract = narrative_json_contract(3, anonymous=True)
    assert '"narrative"' in contract
    assert "demographics" in contract
    assert "non_anthropomorphized" in contract


def test_stands_out_does_not_call_the_baseline_other_accounts():
    clause = _stands_out("comment_write_share", -0.2)
    assert clause is not None
    assert "other accounts" not in clause
    assert "across that month" in clause

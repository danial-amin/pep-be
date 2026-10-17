"""Build persona sets that describe observed account patterns, not people.

Source records are the monthly conduct groups in moltbook-ddps
(revision/final/personas/<month>/<month>_cN.json). Each month becomes one
persona set. Demographic fields, goals, motives, and a quoted voice are left
empty because the source marks them unknown.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

NO_PERSON_IMAGE_PROMPT = (
    "No person, no figure, no portrait, no face, no body, no hands. "
    "Square editorial diagram of account participation only: marks for post length, "
    "comment share, and a few unreadable text lines. No demographic cues, no flags, no names."
)

_STYLE_FIELDS = (
    ("median_chars", "Median characters"),
    ("first_person_rate", "First-person rate"),
    ("comment_write_share", "Comment-write share"),
    ("fn_arrival_share", "Arrival-function share"),
    ("spam_share", "Spam share"),
    ("hedge_rate", "Hedge rate"),
    ("emoji_per_1k", "Emoji per 1k characters"),
    ("protocol_share", "Protocol share"),
)

_EXCERPT_ORDER = ("central", "random", "boundary")
_MONTH_DIR = re.compile(r"^\d{4}-\d{2}$")
_CLUSTER_SUFFIX = re.compile(r"_c(\d+)$")
_UNKNOWN_LINE = re.compile(r"Unknown:\s*(.+?)\.\s*$")


def _fmt_num(value: float) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    magnitude = abs(value)
    if magnitude >= 100:
        return f"{value:,.0f}"
    if magnitude >= 10:
        return f"{value:.1f}"
    if magnitude >= 1:
        return f"{value:.2f}"
    return f"{value:.3g}"


def _attr_map(record: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    mapped: Dict[str, Dict[str, Any]] = {}
    for attr in record.get("attributes") or []:
        if isinstance(attr, dict) and attr.get("name"):
            mapped[str(attr["name"])] = attr
    return mapped


def _compact_attributes(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    compact: List[Dict[str, Any]] = []
    for attr in record.get("attributes") or []:
        if not isinstance(attr, dict) or not attr.get("name"):
            continue
        item: Dict[str, Any] = {
            "name": attr["name"],
            "value": attr.get("value"),
            "basis": attr.get("basis"),
            "status": attr.get("status"),
        }
        if attr.get("note"):
            item["note"] = attr["note"]
        compact.append(item)
    return compact


def _unknowns(narrative: str) -> List[str]:
    match = _UNKNOWN_LINE.search(narrative.strip())
    if not match:
        return [
            "goals",
            "motivations",
            "demographics",
            "architecture",
            "offline activity",
        ]
    return [part.strip() for part in match.group(1).split(",") if part.strip()]


def _truncate(text: str, limit: int = 240) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _observed_excerpts(record: Dict[str, Any], per_stratum: int = 2) -> List[Dict[str, str]]:
    buckets: Dict[str, List[Dict[str, str]]] = {}
    for item in record.get("excerpts") or []:
        if not isinstance(item, dict):
            continue
        text = _truncate(str(item.get("text") or ""))
        if not text:
            continue
        stratum = str(item.get("stratum") or "unspecified")
        bucket = buckets.setdefault(stratum, [])
        if len(bucket) >= per_stratum:
            continue
        excerpt: Dict[str, str] = {"stratum": stratum, "text": text}
        post_id = item.get("post_id")
        if post_id:
            excerpt["post_id"] = str(post_id)
        bucket.append(excerpt)

    ordered: List[Dict[str, str]] = []
    seen = set()
    for stratum in list(_EXCERPT_ORDER) + sorted(buckets):
        if stratum in seen:
            continue
        seen.add(stratum)
        ordered.extend(buckets.get(stratum, []))
    return ordered


def _behaviors(attrs: Dict[str, Dict[str, Any]]) -> str:
    lines: List[str] = []
    n_accounts = (attrs.get("n_accounts") or {}).get("value")
    account_share = (attrs.get("account_share") or {}).get("value")
    if isinstance(n_accounts, (int, float)):
        share_bit = ""
        if isinstance(account_share, (int, float)):
            share_bit = f" ({account_share:.1%} of eligible accounts that month)"
        lines.append(f"Group size: {int(n_accounts):,} accounts{share_bit}.")

    baseline = (attrs.get("month_baseline") or {}).get("value")
    if not isinstance(baseline, dict):
        baseline = {}
    for key, label in _STYLE_FIELDS:
        raw = (attrs.get(key) or {}).get("value")
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            continue
        base = baseline.get(key)
        if isinstance(base, (int, float)) and not isinstance(base, bool):
            delta = raw - base
            sign = "+" if delta >= 0 else ""
            lines.append(
                f"{label}: {_fmt_num(raw)} (month mean {_fmt_num(base)}, Δ={sign}{_fmt_num(delta)})."
            )
        else:
            lines.append(f"{label}: {_fmt_num(raw)}.")

    modal = (attrs.get("modal_communicative_function") or {}).get("value")
    modal_share = (attrs.get("modal_communicative_function_share_in_sample") or {}).get("value")
    if modal:
        share_bit = ""
        if isinstance(modal_share, (int, float)) and not isinstance(modal_share, bool):
            share_bit = f" ({modal_share:.0%} of the excerpt sample)"
        lines.append(
            f"Modal communicative function in the excerpt sample: {modal}{share_bit}. "
            "This share is the sample, not every account in the group."
        )

    variation = (attrs.get("observed_variation") or {}).get("value")
    if isinstance(variation, dict):
        codes = variation.get("minority_codes")
        if isinstance(codes, dict) and codes:
            parts = [f"{name} {count}" for name, count in codes.items()]
            lines.append(
                "Code mix among characterization-pool posts: " + "; ".join(parts) + "."
            )
    return " ".join(lines)


_MONTH_NAMES = {
    "01": "January",
    "02": "February",
    "03": "March",
    "04": "April",
    "05": "May",
    "06": "June",
    "07": "July",
    "08": "August",
    "09": "September",
    "10": "October",
    "11": "November",
    "12": "December",
}

# (when higher than the month, when lower). Infinitive, the way PEP states a goal.
_GOAL_PHRASES = {
    "median_chars": (
        "Write longer posts than the rest of that month",
        "Write shorter posts than the rest of that month",
    ),
    "first_person_rate": (
        "Write in the first person more often than the month",
        "Write in the first person less often than the month",
    ),
    "comment_write_share": (
        "Put more of their writing into comments than the month",
        "Put less of their writing into comments than the month",
    ),
    "fn_arrival_share": (
        "Open with an arrival or introduction more often than the month",
        "Open with an arrival or introduction less often than the month",
    ),
    "spam_share": (
        "Post material scored as spam more often than the month",
        "Post material scored as spam less often than the month",
    ),
    "hedge_rate": (
        "Hedge claims more often than the month",
        "Hedge claims less often than the month",
    ),
    "emoji_per_1k": (
        "Use more emoji than the month",
        "Use less emoji than the month",
    ),
    "protocol_share": (
        "Post protocol text more often than the month",
        "Post protocol text less often than the month",
    ),
}


def _month_label(month: str) -> str:
    year, _, mm = month.partition("-")
    return f"{_MONTH_NAMES.get(mm, mm)} {year}".strip()


def _value(attrs: Dict[str, Dict[str, Any]], name: str) -> Any:
    raw = (attrs.get(name) or {}).get("value")
    if isinstance(raw, bool):
        return None
    return raw


def _plain_code(code: str) -> str:
    return str(code).replace("_", " ")


def _comparisons(attrs: Dict[str, Dict[str, Any]]) -> List[tuple]:
    baseline = _value(attrs, "month_baseline")
    if not isinstance(baseline, dict):
        baseline = {}
    rows = []
    for key, _label in _STYLE_FIELDS:
        raw = _value(attrs, key)
        base = baseline.get(key)
        if not isinstance(raw, (int, float)) or not isinstance(base, (int, float)):
            continue
        if isinstance(raw, bool) or isinstance(base, bool):
            continue
        scale = abs(base) if abs(base) > 1e-9 else 1.0
        rows.append((key, raw, base, raw - base, abs(raw - base) / scale))
    rows.sort(key=lambda row: row[4], reverse=True)
    return rows


def _notable(rows: List[tuple]) -> List[tuple]:
    kept = []
    for key, raw, base, delta, score in rows:
        if key == "median_chars" and abs(delta) < 80:
            continue
        if key == "emoji_per_1k" and abs(delta) < 0.5:
            continue
        if key not in {"median_chars", "emoji_per_1k"} and abs(delta) < 0.04:
            continue
        kept.append((key, raw, base, delta, score))
    return kept


def _goal_lines(rows: List[tuple], modal: Optional[str]) -> List[str]:
    lines = []
    for key, _raw, _base, delta, _score in _notable(rows)[:4]:
        pair = _GOAL_PHRASES.get(key)
        if not pair:
            continue
        lines.append(pair[0] if delta > 0 else pair[1])
    if not lines and modal:
        lines.append(f"Post mostly {_plain_code(modal)} in the posts that were sampled")
    return lines


def _frustration_lines(
    attrs: Dict[str, Dict[str, Any]],
    modal: Optional[str],
    modal_share: Any,
) -> List[str]:
    lines = [
        "Being read as one voice when the group is a mix of accounts",
        "Working from a sample of posts rather than every account in the group",
    ]
    if isinstance(modal_share, (int, float)) and not isinstance(modal_share, bool) and modal_share < 0.6:
        label = _plain_code(modal) if modal else "one post type"
        lines.append(
            f"Having no single post type that covers the sample — {label} is {modal_share:.0%} of it"
        )
    variation = _value(attrs, "observed_variation")
    codes = variation.get("minority_codes") if isinstance(variation, dict) else None
    if isinstance(codes, dict) and codes:
        ranked = sorted(codes.items(), key=lambda item: item[1], reverse=True)
        others = [_plain_code(name) for name, _count in ranked if name != modal][:3]
        if others:
            lines.append("Sharing the group with posts that are " + ", ".join(others))
    return lines[:4]


def _third_person(phrase: str) -> str:
    verb, _, rest = phrase.partition(" ")
    if verb.endswith("e"):
        verb = verb + "s"
    elif verb.endswith("y"):
        verb = verb[:-1] + "ies"
    else:
        verb = verb + "s"
    return f"{verb} {rest}" if rest else verb


def _tagline(conduct_label: str, rows: List[tuple]) -> str:
    bits = []
    for key, _raw, _base, delta, _score in _notable(rows)[:2]:
        pair = _GOAL_PHRASES.get(key)
        if not pair:
            continue
        bits.append(_third_person(pair[0] if delta > 0 else pair[1]))
    if not bits:
        fallback = conduct_label[:1].lower() + conduct_label[1:] if conduct_label else "an account pattern"
        return fallback
    if len(bits) == 1:
        return bits[0]
    return f"{bits[0]}, and {bits[1][0].lower()}{bits[1][1:]}"


def _as_measure(key: str, raw: float) -> str:
    if key == "median_chars":
        return f"about {_fmt_num(raw)} characters"
    if key == "emoji_per_1k":
        return f"{_fmt_num(raw)} per 1,000 characters"
    if 0 <= raw <= 1:
        return f"{raw:.0%}" if raw >= 0.1 else f"{raw:.1%}"
    return _fmt_num(raw)


def _comparison_sentence(key: str, raw: float, base: float, delta: float) -> str:
    higher = delta > 0
    if key == "median_chars":
        direction = "longer" if higher else "shorter"
        return (
            f"A typical post is about {_fmt_num(raw)} characters, {direction} than "
            f"the month average of about {_fmt_num(base)}."
        )
    if key == "emoji_per_1k":
        direction = "more" if higher else "less"
        return (
            f"Emoji show up {_fmt_num(raw)} times per 1,000 characters, {direction} than "
            f"the month's {_fmt_num(base)}."
        )
    if key == "comment_write_share":
        direction = "more" if higher else "less"
        return f"About {raw:.0%} of the writing is comments, {direction} than the month's {base:.0%}."
    if key == "first_person_rate":
        direction = "more" if higher else "less"
        return (
            f"About {raw:.0%} of the writing is in the first person, {direction} than the month's {base:.0%}."
        )
    if key == "fn_arrival_share":
        direction = "more" if higher else "less"
        return (
            f"About {raw:.0%} of posts open as an arrival or introduction, {direction} than the month's {base:.0%}."
        )
    if key == "spam_share":
        direction = "more" if higher else "less"
        told = f"{raw:.0%}" if raw >= 0.1 else f"{raw:.1%}"
        month = f"{base:.0%}" if base >= 0.1 else f"{base:.1%}"
        return f"About {told} of posts are scored as spam, {direction} than the month's {month}."
    if key == "hedge_rate":
        direction = "more" if higher else "less"
        told = f"{raw:.0%}" if raw >= 0.1 else f"{raw:.1%}"
        month = f"{base:.0%}" if base >= 0.1 else f"{base:.1%}"
        return f"About {told} of the writing hedges a claim, {direction} than the month's {month}."
    if key == "protocol_share":
        direction = "more" if higher else "less"
        return (
            f"About {raw:.1%} of posts are protocol text, {direction} than the month's {base:.1%}."
        )
    direction = "higher" if higher else "lower"
    return f"{_as_measure(key, raw)} is {direction} than the month average of {_as_measure(key, base)}."


def _background(
    name: str,
    month: str,
    conduct_label: str,
    attrs: Dict[str, Dict[str, Any]],
    rows: List[tuple],
    modal: Optional[str],
    modal_share: Any,
) -> str:
    when = _month_label(month)
    n_accounts = _value(attrs, "n_accounts")
    account_share = _value(attrs, "account_share")
    called = conduct_label[0].lower() + conduct_label[1:] if conduct_label else "an account pattern"
    sentences = [
        f"{name} is an account pattern on Moltbook in {when}, not a person. It is the {called} pattern."
    ]
    if isinstance(n_accounts, (int, float)):
        share_bit = ""
        if isinstance(account_share, (int, float)) and not isinstance(account_share, bool):
            share_bit = f", {account_share:.1%} of the accounts eligible that month"
        sentences.append(f"It covers {int(n_accounts):,} accounts{share_bit}.")
    for key, raw, base, delta, _score in _notable(rows)[:3]:
        sentences.append(_comparison_sentence(key, raw, base, delta))
    if modal:
        share_bit = ""
        if isinstance(modal_share, (int, float)) and not isinstance(modal_share, bool):
            share_bit = f", and that is {modal_share:.0%} of the sampled posts"
        sentences.append(
            f"In the sampled posts, the most common form is {_plain_code(modal)}{share_bit}. "
            "That share is the sample, not every account in the group."
        )
    sentences.append(
        "Age, gender, location, occupation, and motive are not known, and they are not assigned."
    )
    return " ".join(sentences)


def _behaviors_prose(
    name: str,
    month: str,
    attrs: Dict[str, Dict[str, Any]],
    modal: Optional[str],
    modal_share: Any,
) -> str:
    when = _month_label(month)
    variation = _value(attrs, "observed_variation")
    codes = variation.get("minority_codes") if isinstance(variation, dict) else None
    mix = ""
    if isinstance(codes, dict) and codes:
        ranked = sorted(codes.items(), key=lambda item: item[1], reverse=True)
        parts = [f"{_plain_code(code)} ({count:,})" for code, count in ranked[:4]]
        mix = " The posts in the characterization pool mix " + ", ".join(parts) + "."
    modal_bit = ""
    if modal:
        share_bit = ""
        if isinstance(modal_share, (int, float)) and not isinstance(modal_share, bool):
            share_bit = f" ({modal_share:.0%} of that sample)"
        modal_bit = f" The sampled posts most often take the form of {_plain_code(modal)}{share_bit}."
    return (
        f"{name} is how a group of accounts participates on Moltbook in {when}. "
        f"The description follows the measured conduct of the group, not a story about one account."
        f"{modal_bit}{mix} "
        "The same cluster id in another month is a different fit."
    )


def _quote_from_excerpts(excerpts: List[Dict[str, str]]) -> Optional[str]:
    ordered = sorted(excerpts, key=lambda item: 0 if item.get("stratum") == "central" else 1)
    for item in ordered:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        sentence = text
        for mark in (". ", "! ", "? "):
            if mark in text:
                sentence = text.split(mark, 1)[0].strip() + mark.strip()
                break
        if len(sentence) > 220:
            sentence = sentence[:217].rstrip() + "..."
        return sentence
    return None


def persona_from_conduct_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Turn one conduct-group record into a PEP-shaped persona with no demographics.

    Background, goals, frustrations, behaviors, and quote use the same slots as
    every other PEP persona. The sentences stay with the measured account pattern.
    They do not add a person, a motive, or a demographic.
    """
    group_id = str(record.get("group_id") or "").strip()
    if not group_id:
        raise ValueError("Conduct record is missing group_id")
    month = group_id.split("_", 1)[0]
    conduct_label = str(record.get("conduct_label") or group_id).strip()
    narrative = str(record.get("narrative") or "").strip()
    attrs = _attr_map(record)
    unknowns = _unknowns(narrative)
    rows = _comparisons(attrs)
    modal = _value(attrs, "modal_communicative_function")
    modal_share = _value(attrs, "modal_communicative_function_share_in_sample")
    if modal is not None:
        modal = str(modal)
    name = f"{conduct_label} ({group_id})"
    tagline = _tagline(conduct_label, rows)
    excerpts = _observed_excerpts(record)
    quote = _quote_from_excerpts(excerpts)
    spoken = tagline[0].upper() + tagline[1:] if tagline else ""
    if spoken and not spoken.endswith("."):
        spoken = spoken + "."
    overview = f"{conduct_label} on Moltbook in {_month_label(month)}. {spoken}".strip()
    persona: Dict[str, Any] = {
        "persona_id": group_id,
        "name": name,
        "tagline": tagline,
        "basic_description": overview,
        "anthropomorphized": False,
        "persona_kind": "conduct",
        "conduct_label": conduct_label,
        "unit": record.get("unit") or "account",
        "group_id": group_id,
        "month": month,
        "demographics": {},
        "objective": "",
        "segment_name": "",
        "k_selected": None,
        "background": _background(name, month, conduct_label, attrs, rows, modal, modal_share),
        "goals": _goal_lines(rows, modal),
        "frustrations": _frustration_lines(attrs, modal, modal_share),
        "behaviors": _behaviors_prose(name, month, attrs, modal, modal_share),
        "unknowns": unknowns,
        "rules": record.get("rules") or {},
        "narrative_template": record.get("narrative_template"),
        "measured_attributes": _compact_attributes(record),
        "observed_excerpts": excerpts,
        "other_information": (
            "Goals and frustrations are the measured conduct and its limits, not a person's motives. "
            "The quote, when present, is one sampled post, not a line every account uses. "
            f"Unknown, and not filled in: {', '.join(unknowns)}. "
            "Cluster ids are fit separately each month and are not aligned across months."
        ),
        "image_prompt": NO_PERSON_IMAGE_PROMPT,
    }
    if quote:
        persona["quote"] = quote
    if narrative:
        persona["source_narrative"] = narrative
    return persona


def _cluster_sort_key(path: Path) -> int:
    match = _CLUSTER_SUFFIX.search(path.stem)
    return int(match.group(1)) if match else 0


def load_month_records(month_dir: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for path in sorted(month_dir.glob("*.json"), key=_cluster_sort_key):
        if path.name == "summary.json":
            continue
        with path.open(encoding="utf-8") as handle:
            record = json.load(handle)
        if isinstance(record, dict) and record.get("group_id"):
            records.append(record)
    return records


def build_month_persona_set(month_dir: Path) -> Dict[str, Any]:
    """Build one persona set from a month directory of conduct-group JSON files."""
    month = month_dir.name
    records = load_month_records(month_dir)
    personas = [persona_from_conduct_record(record) for record in records]
    return {
        "metadata": {
            "context": (
                f"Moltbook {month}. Non-anthropomorphized conduct personas. "
                "Each persona uses the PEP profile — tagline, background, goals, frustrations, "
                "behaviors, and a quote — and describes an account pattern, not a person. "
                "Demographic fields are empty. Goals are measured conduct, not motives. "
                "Cluster ids are fit separately each month and are not aligned across months."
            ),
            "month": month,
            "anthropomorphized": False,
            "persona_kind": "conduct",
            "demographics": "none",
            "n_personas": len(personas),
            "generator": "conduct_record_no_llm",
            "source": "moltbook-ddps/revision/final/personas",
        },
        "personas": personas,
    }


def iter_month_dirs(source_dir: Path) -> Iterable[Path]:
    for path in sorted(source_dir.iterdir()):
        if path.is_dir() and _MONTH_DIR.match(path.name):
            yield path


def write_month_persona_sets(source_dir: Path, out_dir: Path) -> List[Path]:
    """Write one persona-set JSON per month. Returns the written paths."""
    source_dir = source_dir.expanduser().resolve()
    out_dir = out_dir.expanduser().resolve()
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Conduct persona source not found: {source_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []
    for month_dir in iter_month_dirs(source_dir):
        persona_set = build_month_persona_set(month_dir)
        if not persona_set["personas"]:
            continue
        destination = out_dir / f"personas_moltbook_conduct_{month_dir.name}.json"
        with destination.open("w", encoding="utf-8") as handle:
            json.dump(persona_set, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        written.append(destination)
    if not written:
        raise ValueError(f"No month directories with conduct personas in {source_dir}")
    return written


def conduct_persona_instructions(persona_data: Dict[str, Any]) -> str:
    """Prompt text for chat and simulation. Does not assign a person."""
    name = (
        persona_data.get("name")
        or persona_data.get("conduct_label")
        or "this account pattern"
    )
    background = persona_data.get("background") or ""
    behaviors = persona_data.get("behaviors") or ""
    unknowns = persona_data.get("unknowns") or [
        "goals",
        "motivations",
        "demographics",
    ]
    if isinstance(unknowns, list):
        unknown_line = ", ".join(str(item) for item in unknowns)
    else:
        unknown_line = str(unknowns)

    excerpt_lines: List[str] = []
    for item in (persona_data.get("observed_excerpts") or [])[:4]:
        if isinstance(item, dict) and item.get("text"):
            stratum = item.get("stratum") or "excerpt"
            excerpt_lines.append(f"  - [{stratum}] {item['text']}")
    excerpt_block = ""
    if excerpt_lines:
        excerpt_block = "SAMPLED POSTS (evidence of the pattern, not a personal voice):\n" + "\n".join(
            excerpt_lines
        )

    return f"""You describe the observed account pattern "{name}".
This is not a person. Do not speak as a human, and do not invent a name, age, gender, occupation, location, goal, or motive.

OBSERVED PATTERN:
{background}

MEASURED CONDUCT:
{behaviors}

{excerpt_block}

UNKNOWNS — if asked about these, say they are unknown: {unknown_line}.

Rules:
- Describe the group pattern. Do not claim every account shows the modal conduct.
- Goals and frustrations in this profile are measured conduct and its limits, not personal motives.
- Do not add a personality, a backstory, or a demographic.
- If asked who you are, say you are this measured account pattern, not a person.
- Stay with the measurements and the sampled posts.
- Keep the reply short: usually 2–4 sentences, and finish the last sentence."""


def default_source_dir() -> Optional[Path]:
    candidate = Path(
        "/Users/danialamin/Documents/Git-DA-p/moltbook-ddps/revision/final/personas"
    )
    if candidate.is_dir():
        return candidate
    return None

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


def persona_from_conduct_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Turn one conduct-group record into a persona with no demographic fields."""
    group_id = str(record.get("group_id") or "").strip()
    if not group_id:
        raise ValueError("Conduct record is missing group_id")
    month = group_id.split("_", 1)[0]
    conduct_label = str(record.get("conduct_label") or group_id).strip()
    narrative = str(record.get("narrative") or "").strip()
    attrs = _attr_map(record)
    unknowns = _unknowns(narrative)
    name = f"{conduct_label} ({group_id})"
    overview = (
        f"Observed account participation pattern in {month}: {conduct_label}. "
        "Not a person, and not a psychological personality."
    )
    return {
        "persona_id": group_id,
        "name": name,
        "tagline": conduct_label,
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
        "background": narrative,
        "goals": [],
        "frustrations": [],
        "behaviors": _behaviors(attrs),
        "unknowns": unknowns,
        "rules": record.get("rules") or {},
        "narrative_template": record.get("narrative_template"),
        "measured_attributes": _compact_attributes(record),
        "observed_excerpts": _observed_excerpts(record),
        "other_information": (
            "This persona is an observed account participation pattern, not a person. "
            f"Unknown, and left blank: {', '.join(unknowns)}. "
            "Not every account in the group matches the modal pattern. "
            "Cluster ids are fit separately each month and are not aligned across months."
        ),
        "image_prompt": NO_PERSON_IMAGE_PROMPT,
    }


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
                "Each persona is an observed account participation pattern, not a person. "
                "Demographic fields are empty. Goals and motivations are empty. "
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

"""Build persona sets that describe observed account patterns, not people.

Source records are the monthly conduct groups in moltbook-ddps
(revision/final/personas/<month>/<month>_cN.json). Each month becomes one
persona set. Demographic fields stay empty. Goals and frustrations restate
measured conduct. They do not invent a motive, an age, or a gender.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ANONYMOUS_FIGURE_IMAGE_PROMPT = (
    "Square editorial scene of one anonymous figure at a desk, features unspecified. "
    "No readable age, no gender, no ethnicity, no nationality, no gendered clothing. "
    "No flags, no skin tone used as identity, no readable personal name. "
    "The figure is the one making the posts. Not a chart, not a graph, not a diagram. "
)

# Role titles, not personal names. No age or gender is implied.
# One plain sentence of what this conduct looks like on the feed.
_PORTRAITS = {
    "Mixed style/conduct account": (
        "writes in several different ways on the same feed and does not settle on one kind of post"
    ),
    "Long hedged commenter": (
        "writes long comments and softens the claim instead of stating it flat"
    ),
    "First-person commenter": (
        "writes as \"I\" and puts a lot of that writing into replies"
    ),
    "Arrival / introduction account": "shows up by introducing themselves",
    "Spam-elevated poster": "posts short, repeated material more often than other accounts",
    "Low-reply prose poster": "writes prose on the main feed and rarely stays for a reply",
    "Long first-person writer": "writes long posts in the first person",
    "Short emoji-heavy broadcaster": "puts up short posts and marks them with emoji",
    "CJK-leaning poster": (
        "writes in more than one writing system, often with Chinese, Japanese, or Korean characters"
    ),
    "High comment-writing account": "puts most of their writing into comments rather than main posts",
}

_TITLES = {
    "Mixed style/conduct account": "The Mixed Voice",
    "Long hedged commenter": "The Hedged Commenter",
    "First-person commenter": "The First-Person Commenter",
    "Arrival / introduction account": "The Arrival",
    "Spam-elevated poster": "The Elevated Poster",
    "Low-reply prose poster": "The Low-Reply Writer",
    "Long first-person writer": "The Long Writer",
    "Short emoji-heavy broadcaster": "The Emoji Broadcaster",
    "CJK-leaning poster": "The Script Poster",
    "High comment-writing account": "The Heavy Commenter",
}

_SCENES = {
    "Mixed style/conduct account": "several different pages on the desk, none of them the same length",
    "Long hedged commenter": "a long page with many small reply marks under it and a few penciled asides",
    "First-person commenter": "a page that begins with I, and a stack of reply marks under it",
    "Arrival / introduction account": "one short card just set down on an otherwise empty desk",
    "Spam-elevated poster": "the same short slip copied several times in a row",
    "Low-reply prose poster": "a prose page with almost no marks underneath",
    "Long first-person writer": "one long page written out by hand",
    "Short emoji-heavy broadcaster": "a very short note with a few simple marks beside it",
    "CJK-leaning poster": "a page set in more than one writing system, as type samples only, with no flag",
    "High comment-writing account": "a short note with a tall stack of replies underneath",
}

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

def _image_prompt(conduct_label: str) -> str:
    scene = _SCENES.get(conduct_label, "the pages they are posting")
    return ANONYMOUS_FIGURE_IMAGE_PROMPT + f"Nearby: {scene}."


# When one conduct label covers several groups, each group gets the title of
# the habit that sets it apart. (full title, adjective for a two-habit name)
_TRAIT_TITLES = {
    ("comment_write_share", True): ("The Reply Writer", "Replying"),
    ("comment_write_share", False): ("The Main-Feed Writer", "Main-Feed"),
    ("hedge_rate", True): ("The Soft Speaker", "Soft-Spoken"),
    ("hedge_rate", False): ("The Direct Speaker", "Direct"),
    ("fn_arrival_share", True): ("The Introducer", "Introducing"),
    ("fn_arrival_share", False): ("The Straight Poster", "Straight"),
    ("median_chars", True): ("The Long Poster", "Long"),
    ("median_chars", False): ("The Short Poster", "Short"),
    ("first_person_rate", True): ("The First-Person Writer", "First-Person"),
    ("first_person_rate", False): ("The Impersonal Writer", "Impersonal"),
    ("emoji_per_1k", True): ("The Emoji Poster", "Emoji"),
    ("emoji_per_1k", False): ("The Plain Poster", "Plain"),
    ("spam_share", True): ("The Repeated Poster", "Repeated"),
    ("spam_share", False): ("The Clean Poster", "Clean"),
    ("protocol_share", True): ("The Protocol Poster", "Protocol"),
    ("protocol_share", False): ("The Open Poster", "Open"),
}

_MODAL_TITLES = {
    "explicit_self_description": "The Self-Describer",
    "question_opening": "The Questioner",
    "arrival_or_introduction": "The Introducer",
    "greeting": "The Greeter",
    "insufficient_text": "The Fragment Poster",
    "protocol_op": "The Protocol Poster",
}


def _trait_pair(key: str, delta: float) -> Optional[tuple]:
    return _TRAIT_TITLES.get((key, delta > 0))


def _title_offers(record: Dict[str, Any]) -> List[tuple]:
    """(score, title) pairs. A higher score is a stronger claim on that name."""
    attrs = _attr_map(record)
    rows = _notable(_comparisons(attrs))
    modal = _value(attrs, "modal_communicative_function")
    modal_share = _value(attrs, "modal_communicative_function_share_in_sample")
    offers: List[tuple] = []
    if modal and str(modal) in _MODAL_TITLES:
        share = float(modal_share) if isinstance(modal_share, (int, float)) and not isinstance(modal_share, bool) else 0.5
        offers.append((share + 1.0, _MODAL_TITLES[str(modal)]))
    for key, _raw, _base, delta, score in rows:
        pair = _trait_pair(key, delta)
        if not pair:
            continue
        title, _adjective = pair
        offers.append((float(score), title))
    return offers


def _titles_for_records(records: List[Dict[str, Any]]) -> Dict[str, str]:
    """One title per group. A repeated conduct label does not reuse the same name."""
    counts: Dict[str, int] = {}
    for record in records:
        label = str(record.get("conduct_label") or "")
        counts[label] = counts.get(label, 0) + 1

    titles: Dict[str, str] = {}
    taken = set()
    collisions: List[Dict[str, Any]] = []
    for record in records:
        label = str(record.get("conduct_label") or "")
        group_id = str(record.get("group_id") or "")
        base = _TITLES.get(label) or (label or group_id)
        if counts.get(label, 0) > 1:
            collisions.append(record)
            continue
        titles[group_id] = base
        taken.add(base)

    bids = []
    for record in collisions:
        group_id = str(record.get("group_id") or "")
        for score, candidate in _title_offers(record):
            bids.append((score, group_id, candidate))
    bids.sort(key=lambda item: item[0], reverse=True)
    for _score, group_id, candidate in bids:
        if group_id in titles or candidate in taken:
            continue
        titles[group_id] = candidate
        taken.add(candidate)
    for record in collisions:
        group_id = str(record.get("group_id") or "")
        if group_id in titles:
            continue
        label = str(record.get("conduct_label") or "Account")
        chosen = _TITLES.get(label) or label
        suffix = 2
        while chosen in taken:
            chosen = f"{_TITLES.get(label) or label} {suffix}"
            suffix += 1
        titles[group_id] = chosen
        taken.add(chosen)
    return titles


def _month_label(month: str) -> str:
    year, _, mm = month.partition("-")
    return f"{_MONTH_NAMES.get(mm, mm)} {year}".strip()


def _value(attrs: Dict[str, Dict[str, Any]], name: str) -> Any:
    raw = (attrs.get(name) or {}).get("value")
    if isinstance(raw, bool):
        return None
    return raw


_CODE_WORDS = {
    "prose_or_other": "prose",
    "question_opening": "questions",
    "explicit_self_description": "self-description",
    "arrival_or_introduction": "introductions",
    "insufficient_text": "fragments",
    "greeting": "greetings",
    "protocol_op": "protocol text",
}


def _plain_code(code: str) -> str:
    key = str(code)
    return _CODE_WORDS.get(key, key.replace("_", " "))


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


def _stands_out(key: str, delta: float) -> Optional[str]:
    """A clause after 'they'. The comparison is the month as a whole, which includes this group."""
    higher = delta > 0
    if key == "median_chars":
        return (
            "write longer posts than accounts do across that month"
            if higher
            else "write shorter posts than accounts do across that month"
        )
    if key == "first_person_rate":
        return (
            'write as "I" more often than accounts do across that month'
            if higher
            else 'write as "I" less often than accounts do across that month'
        )
    if key == "comment_write_share":
        return (
            "put a larger share of their writing into replies than accounts do across that month"
            if higher
            else "put a smaller share of their writing into replies than accounts do across that month"
        )
    if key == "fn_arrival_share":
        return (
            "open with an introduction more often than accounts do across that month"
            if higher
            else "open with an introduction less often than accounts do across that month"
        )
    if key == "spam_share":
        return (
            "post material scored as spam more often than accounts do across that month"
            if higher
            else "post material scored as spam less often than accounts do across that month"
        )
    if key == "hedge_rate":
        return (
            "soften a claim more often than accounts do across that month"
            if higher
            else "state a claim more directly than accounts do across that month"
        )
    if key == "emoji_per_1k":
        return (
            "use emoji more than accounts do across that month"
            if higher
            else "use emoji less than accounts do across that month"
        )
    if key == "protocol_share":
        return (
            "post protocol text more often than accounts do across that month"
            if higher
            else "post protocol text less often than accounts do across that month"
        )
    return None


def _portrait(conduct_label: str) -> str:
    return _PORTRAITS.get(conduct_label) or "follows one measured way of posting"


def _habit(key: str, delta: float) -> Optional[str]:
    """A short conduct line. No counts, and no comparison against the month mean."""
    higher = delta > 0
    habits = {
        "median_chars": ("Write long posts", "Keep posts short"),
        "first_person_rate": ('Write as "I"', 'Write less often as "I"'),
        "comment_write_share": (
            "Put most of the writing into replies",
            "Keep most of the writing on the main feed, not in replies",
        ),
        "fn_arrival_share": ("Open with an introduction", "Skip the introduction"),
        "spam_share": ("Post repeated material", "Leave repeated material off the feed"),
        "hedge_rate": ("Soften a claim instead of stating it flat", "State a claim directly"),
        "emoji_per_1k": ("Mark posts with emoji", "Leave emoji off"),
        "protocol_share": ("Post protocol text", "Leave protocol text off the feed"),
    }
    pair = habits.get(key)
    if not pair:
        return None
    return pair[0] if higher else pair[1]


def _overview(name: str, month: str, conduct_label: str, rows: List[tuple]) -> str:
    """One sentence under the title, the way the other personas state a role."""
    del name, month, rows
    portrait = _portrait(conduct_label)
    return portrait[0].upper() + portrait[1:] + "."


def _code_counts(attrs: Dict[str, Dict[str, Any]]) -> List[tuple]:
    variation = _value(attrs, "observed_variation")
    codes = variation.get("minority_codes") if isinstance(variation, dict) else None
    if not isinstance(codes, dict) or not codes:
        return []
    return sorted(codes.items(), key=lambda item: item[1], reverse=True)


def _goal_lines(name: str, month: str, rows: List[tuple], modal: Optional[str], modal_share: Any, attrs: Dict[str, Dict[str, Any]]) -> List[str]:
    del name, month, modal, modal_share, attrs
    lines = []
    for key, _raw, _base, delta, _score in _notable(rows)[:3]:
        habit = _habit(key, delta)
        if habit:
            lines.append(habit)
    if not lines:
        lines.append("Stay with the measured way of posting")
    return lines


def _feed_kinds(attrs: Dict[str, Dict[str, Any]], modal: Optional[str], limit: int = 4) -> List[str]:
    names = [_plain_code(code) for code, _count in _code_counts(attrs)[:limit]]
    if names:
        return names
    if modal:
        return [_plain_code(modal)]
    return []


def _joined(items: List[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _frustration_lines(
    attrs: Dict[str, Dict[str, Any]],
    modal: Optional[str],
    modal_share: Any,
    month: str,
) -> List[str]:
    del modal_share, month
    lines = ["One description does not fit every account in the group"]
    others = [_plain_code(code) for code, _count in _code_counts(attrs) if code != modal][:3]
    if others:
        lines.append(f"{_joined(others).capitalize()} share the feed with the usual post")
    elif modal:
        lines.append(f"Not every account writes {_plain_code(modal)}")
    lines.append("The same title in another month is a different group")
    return lines


def _as_measure(key: str, raw: float) -> str:
    if key == "median_chars":
        return f"about {_fmt_num(raw)} characters"
    if key == "emoji_per_1k":
        return f"{_fmt_num(raw)} per 1,000 characters"
    if 0 <= raw <= 1:
        return f"{raw:.0%}" if raw >= 0.1 else f"{raw:.1%}"
    return _fmt_num(raw)


def _others(when: str) -> str:
    return f"accounts across {when} as a whole"


def _comparison_sentence(key: str, raw: float, base: float, delta: float, when: str) -> str:
    higher = delta > 0
    others = _others(when)
    if key == "median_chars":
        direction = "longer" if higher else "shorter"
        return (
            f"A typical post is about {_fmt_num(raw)} characters, {direction} than "
            f"the posts of {others}, which run about {_fmt_num(base)} characters."
        )
    if key == "emoji_per_1k":
        direction = "more often" if higher else "less often"
        return (
            f"Emoji show up {_fmt_num(raw)} times per 1,000 characters, {direction} than "
            f"for {others}, where the figure is {_fmt_num(base)}."
        )
    if key == "comment_write_share":
        direction = "more" if higher else "less"
        return (
            f"About {raw:.0%} of what they write is a comment, {direction} than for {others}, "
            f"where comments are about {base:.0%} of the writing."
        )
    if key == "first_person_rate":
        direction = "more" if higher else "less"
        return (
            f"About {raw:.0%} of the writing is in the first person, {direction} than for {others}, "
            f"where that share is about {base:.0%}."
        )
    if key == "fn_arrival_share":
        direction = "more" if higher else "less"
        return (
            f"About {raw:.0%} of posts open as an arrival or introduction, {direction} than for {others}, "
            f"where that share is about {base:.0%}."
        )
    if key == "spam_share":
        direction = "more" if higher else "less"
        told = f"{raw:.0%}" if raw >= 0.1 else f"{raw:.1%}"
        month = f"{base:.0%}" if base >= 0.1 else f"{base:.1%}"
        return (
            f"About {told} of posts are scored as spam, {direction} than for {others}, "
            f"where that share is about {month}."
        )
    if key == "hedge_rate":
        direction = "more" if higher else "less"
        told = f"{raw:.0%}" if raw >= 0.1 else f"{raw:.1%}"
        month = f"{base:.0%}" if base >= 0.1 else f"{base:.1%}"
        return (
            f"About {told} of the writing hedges a claim, {direction} than for {others}, "
            f"where that share is about {month}."
        )
    if key == "protocol_share":
        direction = "more" if higher else "less"
        return (
            f"About {raw:.1%} of posts are protocol text, {direction} than for {others}, "
            f"where that share is about {base:.1%}."
        )
    direction = "higher" if higher else "lower"
    return f"{_as_measure(key, raw)} is {direction} than for {others}, at {_as_measure(key, base)}."


def _posting_volume_sentence(attrs: Dict[str, Dict[str, Any]], when: str) -> Optional[str]:
    raw = _value(attrs, "log1p_n_main_posts")
    baseline = _value(attrs, "month_baseline")
    base = baseline.get("log1p_n_main_posts") if isinstance(baseline, dict) else None
    if not isinstance(raw, (int, float)) or not isinstance(base, (int, float)):
        return None
    if isinstance(raw, bool) or isinstance(base, bool):
        return None
    scale = abs(base) if abs(base) > 1e-9 else 1.0
    if abs(raw - base) / scale < 0.12:
        return None
    if raw > base:
        return f"Put up main posts more often than {_others(when)}."
    return f"Put up main posts less often than {_others(when)}."


def _sample_lines(excerpts: List[Dict[str, str]], limit: int = 2) -> List[str]:
    order = {"central": 0, "random": 1, "boundary": 2}
    ordered = sorted(excerpts, key=lambda item: order.get(str(item.get("stratum") or ""), 3))
    lines: List[str] = []
    seen = set()
    for item in ordered:
        text = " ".join(str(item.get("text") or "").split())
        if not text or text in seen:
            continue
        seen.add(text)
        if len(text) > 180:
            text = text[:177].rstrip() + "..."
        lines.append(text)
        if len(lines) >= limit:
            break
    return lines


def _background(
    name: str,
    month: str,
    conduct_label: str,
    attrs: Dict[str, Dict[str, Any]],
    rows: List[tuple],
    modal: Optional[str],
    modal_share: Any,
    excerpts: List[Dict[str, str]],
) -> str:
    """Two or three sentences, the length of the other persona backgrounds."""
    del rows, modal_share, excerpts
    when = _month_label(month)
    del conduct_label
    kinds = _feed_kinds(attrs, modal)
    mix = f" The posts mix {_joined(kinds)}." if kinds else ""
    return (
        f"{name} is on Moltbook in {when}.{mix} "
        f"They have no age, no gender, and no nationality."
    )


def _behaviors_prose(
    name: str,
    month: str,
    conduct_label: str,
    attrs: Dict[str, Dict[str, Any]],
    rows: List[tuple],
    modal: Optional[str],
    modal_share: Any,
) -> str:
    """How a post looks. The goals already name the main habits, so this stays short."""
    del name, month, conduct_label, attrs, modal_share
    extras = []
    for key, _raw, _base, delta, _score in _notable(rows)[3:5]:
        habit = _habit(key, delta)
        if habit:
            extras.append(habit[0].lower() + habit[1:])
    form = f"The usual post is {_plain_code(modal)}." if modal else ""
    also = f"They also {_joined(extras)}." if extras else ""
    return " ".join(
        part for part in (form, also, "Not every account in the group writes this way.") if part
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


def _evidence_note(rows: List[tuple], month: str, unknowns: List[str]) -> str:
    """Numbers stay off the card. Chat can still read them from here."""
    labels = {
        "median_chars": "post length",
        "first_person_rate": "first person",
        "comment_write_share": "comments",
        "fn_arrival_share": "introductions",
        "spam_share": "spam",
        "hedge_rate": "hedging",
        "emoji_per_1k": "emoji",
        "protocol_share": "protocol text",
    }
    bits = []
    for key, raw, base, _delta, _score in _notable(rows)[:4]:
        bits.append(f"{labels.get(key, key)} {_as_measure(key, raw)} against {_as_measure(key, base)}")
    measured = ""
    if bits:
        measured = f" Measured against {_month_label(month)} as a whole: " + "; ".join(bits) + "."
    unknown_line = ", ".join(unknowns) if unknowns else "demographics"
    return (
        "The quote is one sampled post, not a line every account uses."
        + measured
        + f" Unknown, and not filled in: {unknown_line}."
    )


def persona_from_conduct_record(record: Dict[str, Any], title: Optional[str] = None) -> Dict[str, Any]:
    """Turn one conduct-group record into a titled persona with no demographics.

    The profile uses the same slots as the other personas: a title, a tagline,
    a background, goals, frustrations, behaviors, and a quote. Age, gender, and
    nationality are not assigned.
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
    name = title or _TITLES.get(conduct_label) or conduct_label
    excerpts = _observed_excerpts(record)
    quote = _quote_from_excerpts(excerpts)
    overview = _overview(name, month, conduct_label, rows)
    tagline = overview
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
        "background": _background(
            name, month, conduct_label, attrs, rows, modal, modal_share, excerpts
        ),
        "goals": _goal_lines(name, month, rows, modal, modal_share, attrs),
        "frustrations": _frustration_lines(attrs, modal, modal_share, month),
        "behaviors": _behaviors_prose(
            name, month, conduct_label, attrs, rows, modal, modal_share
        ),
        "unknowns": unknowns,
        "rules": record.get("rules") or {},
        "narrative_template": record.get("narrative_template"),
        "measured_attributes": _compact_attributes(record),
        "observed_excerpts": excerpts,
        "other_information": _evidence_note(rows, month, unknowns),
        "image_prompt": _image_prompt(conduct_label),
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
    titles = _titles_for_records(records)
    personas = [
        persona_from_conduct_record(record, title=titles.get(str(record.get("group_id") or "")))
        for record in records
    ]
    return {
        "metadata": {
            "context": (
                f"Moltbook {month}. Conduct personas with titles and no demographic fields. "
                "Each profile uses the same slots as the other personas. "
                "The figure has no age, gender, or nationality. "
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

    return f"""You are {name}. Speak in the first person as this title.
You have no age, no gender, no location, no occupation, and no nationality. Do not invent them.
You stand for how a group of accounts writes. Do not claim every account does what you describe.

BACKGROUND:
{background}

HOW YOU TAKE PART:
{behaviors}

{excerpt_block}

UNKNOWNS — if asked about these, say they are unknown: {unknown_line}.

Rules:
- Keep the reply in the first person, as {name}.
- Goals and frustrations are the conduct and its limits, not a private motive you were not given.
- Do not add an age, a gender, a nationality, or a backstory.
- If asked who you are, give your title and the month you belong to.
- Keep the reply short: usually 2–4 sentences, and finish the last sentence."""


def default_source_dir() -> Optional[Path]:
    candidate = Path(
        "/Users/danialamin/Documents/Git-DA-p/moltbook-ddps/revision/final/personas"
    )
    if candidate.is_dir():
        return candidate
    return None

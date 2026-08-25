"""
OpenAI chat completion helpers.

GPT-5.6 family (e.g. gpt-5.6-luna) rejects temperature and max_tokens on
chat.completions — omit them when calling those models.
"""
from __future__ import annotations

from typing import Any, Dict

from app.core.config import settings


def openai_chat_model() -> str:
    return settings.OPENAI_MODEL


def model_omits_sampling_params(model: str | None = None) -> bool:
    """True when the model should not receive temperature / max_tokens."""
    m = (model or settings.OPENAI_MODEL).lower().strip()
    # GPT-5.6 / reasoning-style chat models
    if m.startswith("gpt-5.6") or m.startswith("gpt-5.4") or m.startswith("gpt-5"):
        return True
    if m.startswith(("o1", "o3", "o4")):
        return True
    return False


def chat_completion_kwargs(**kwargs: Any) -> Dict[str, Any]:
    """
    Build kwargs for client.chat.completions.create.

    Ensures model is set and strips temperature / max_tokens when unsupported.
    """
    out: Dict[str, Any] = dict(kwargs)
    model = out.get("model") or settings.OPENAI_MODEL
    out["model"] = model
    if model_omits_sampling_params(model):
        out.pop("temperature", None)
        out.pop("max_tokens", None)
        # Often unsupported alongside sampling on GPT-5.x chat models
        out.pop("presence_penalty", None)
        out.pop("frequency_penalty", None)
        out.pop("top_p", None)
    return out

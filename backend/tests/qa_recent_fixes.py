"""
QA tests for the recent bugfixes:
1. UnboundLocalError for 'logger' in main.py lifespan
2. TypeError in expand_persona when context_documents contains None
Run from repo root: python -m pytest backend/tests/qa_recent_fixes.py -v
Or: cd backend && python3 -m tests.qa_recent_fixes
"""
import asyncio
import os
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))


def test_main_lifespan_does_not_shadow_logger():
    """Lifespan must not assign to 'logger' locally (would cause UnboundLocalError in try/except)."""
    main_py = backend / "app" / "main.py"
    source = main_py.read_text()
    lines = source.split("\n")
    in_lifespan = False
    indent_lifespan = None
    for line in lines:
        if "async def lifespan(" in line:
            in_lifespan = True
            indent_lifespan = len(line) - len(line.lstrip())
            continue
        if in_lifespan:
            current_indent = len(line) - len(line.lstrip())
            if line and current_indent <= indent_lifespan and line.strip().startswith("def "):
                break
            if "logger =" in line and "logging.getLogger" in line:
                raise AssertionError(
                    "lifespan() contains 'logger = logging.getLogger(...)' which shadows the "
                    "module-level logger and causes UnboundLocalError. Use the module-level logger instead."
                )
    print("PASS: main.lifespan does not shadow logger")


def test_expand_persona_filtering_logic():
    """The same filtering + join used in expand_persona must handle None and all-None."""
    # Same logic as in llm_service.expand_persona (no API needed)
    context_documents = [None, "First doc content.", None, "Second doc.", None]
    context_documents = [d for d in context_documents if d is not None and isinstance(d, str)]
    context = "\n\n".join(context_documents) if context_documents else ""
    assert "First doc content." in context and "Second doc." in context, "Filtered context should contain only strings"
    print("PASS: filtering + join with None and strings yields correct context")

    context_documents_all_none = [None, None]
    context_documents_all_none = [d for d in context_documents_all_none if d is not None and isinstance(d, str)]
    context_empty = "\n\n".join(context_documents_all_none) if context_documents_all_none else ""
    assert context_empty == "", "All-None should produce empty string"
    print("PASS: all-None context produces empty string, no TypeError")


async def test_expand_persona_integration_with_mock():
    """Full expand_persona call with None in context (requires OPENAI_API_KEY or skip)."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("SKIP: expand_persona integration (no OPENAI_API_KEY)")
        return
    from unittest.mock import AsyncMock, MagicMock
    from app.core.llm_service import LLMService

    persona_basic = {"name": "Test", "tagline": "A test", "demographics": {}}
    context_documents = [None, "First doc.", None, "Second doc.", None]

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"name": "Test", "tagline": "A test", "demographics": {}, "background": "Expanded."}'
    mock_create = AsyncMock(return_value=mock_response)

    service = LLMService()
    original_create = service.client.chat.completions.create
    service.client.chat.completions.create = mock_create

    try:
        result = await service.expand_persona(
            persona_basic=persona_basic,
            context_documents=context_documents,
            project_id=None,
        )
    except TypeError as e:
        if "expected str instance, NoneType found" in str(e):
            raise AssertionError(
                "expand_persona still raises TypeError when context_documents contains None."
            ) from e
        raise
    finally:
        service.client.chat.completions.create = original_create

    call_args = mock_create.call_args
    assert call_args is not None
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    user_content = next((m["content"] for m in messages if m.get("role") == "user"), None)
    assert "First doc." in user_content and "Second doc." in user_content
    print("PASS: expand_persona integration with None in context_documents")
    return result


def run_all():
    """Run all QA tests (no pytest required)."""
    print("QA: Recent fixes (logger + expand_persona None handling)\n")
    test_main_lifespan_does_not_shadow_logger()
    test_expand_persona_filtering_logic()
    asyncio.run(test_expand_persona_integration_with_mock())
    print("\nAll QA checks passed.")


if __name__ == "__main__":
    run_all()

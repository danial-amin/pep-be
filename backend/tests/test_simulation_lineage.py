"""Forks stay on their own path.

A child of an earlier message must not see messages that only exist on a sibling branch.
"""
from types import SimpleNamespace

from app.services.simulation_lineage import lineage_messages, path_is_closed


def _msg(message_id, content, parent_id=None, persona_id=1, human=False, tokens=10):
    return SimpleNamespace(
        id=message_id,
        content=content,
        parent_message_id=parent_id,
        persona_id=None if human else persona_id,
        is_human_message=human,
        tokens=tokens,
    )


def _tree():
    shared = _msg(1, "shared opening", parent_id=None, persona_id=1)
    left = _msg(2, "left branch only", parent_id=1, persona_id=2)
    right = _msg(3, "right branch only", parent_id=1, persona_id=2)
    right_child = _msg(4, "right continues", parent_id=3, persona_id=1)
    return [shared, left, right, right_child]


def test_two_children_of_the_same_parent_are_separate_lineages():
    messages = _tree()
    left = [m.content for m in lineage_messages(messages, 2)]
    right = [m.content for m in lineage_messages(messages, 4)]

    assert left == ["shared opening", "left branch only"]
    assert right == ["shared opening", "right branch only", "right continues"]
    assert "right branch only" not in left
    assert "left branch only" not in right


def test_focused_ancestors_are_the_only_context_messages():
    """generate_turn feeds _build_conversation_context this lineage and nothing else."""
    messages = _tree()
    visible = lineage_messages(messages, 2)
    contents = [m.content for m in visible]
    assert contents == ["shared opening", "left branch only"]
    assert all("right" not in content for content in contents)


def test_null_head_is_the_root_and_sees_nothing():
    assert lineage_messages(_tree(), None) == []


def test_turn_cap_leaves_a_shorter_prefix_open():
    messages = _tree()
    simulation = SimpleNamespace(
        max_turns=1,
        max_tokens=None,
        run_until_agreement=False,
        active_head_message_id=4,
        agreement_evaluations=[],
    )
    # Two participants, so one full round is two persona messages.
    # The right path has three persona messages -> one completed round -> closed at max_turns=1.
    # The left path has two persona messages -> one completed round as well.
    assert path_is_closed(simulation, lineage_messages(messages, 4), 2) is True
    simulation.active_head_message_id = 2
    assert path_is_closed(simulation, lineage_messages(messages, 2), 2) is True

    simulation.active_head_message_id = 1
    assert path_is_closed(simulation, lineage_messages(messages, 1), 2) is False


def test_agreement_closes_the_head_it_was_scored_on():
    messages = _tree()
    evaluation = SimpleNamespace(agreement_reached=True, head_message_id=2)
    simulation = SimpleNamespace(
        max_turns=10,
        max_tokens=None,
        run_until_agreement=True,
        active_head_message_id=2,
        agreement_evaluations=[evaluation],
    )
    assert path_is_closed(simulation, lineage_messages(messages, 2), 2) is True
    simulation.active_head_message_id = 4
    assert path_is_closed(simulation, lineage_messages(messages, 4), 2) is False

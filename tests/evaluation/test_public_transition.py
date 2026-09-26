from __future__ import annotations

from dataclasses import fields

import pytest

from pchsi.evaluation.action_trace import (
    sha256_string_sequence,
    sha256_text,
)
from pchsi.evaluation.alfworld_contracts import (
    MenuSnapshot,
    StepPublicState,
)
from pchsi.evaluation.public_transition import (
    build_public_transition,
)


def _menu(commands: tuple[str, ...]) -> MenuSnapshot:
    return MenuSnapshot(
        commands=commands,
        sequence_sha256=sha256_string_sequence(
            commands
        ),
    )


def _result() -> StepPublicState:
    return StepPublicState(
        observation="after",
        menu=_menu(("inventory", "go north")),
        score=1,
        done=True,
        won=True,
    )


def test_public_transition_contains_only_pre_and_post_public_fields() -> None:
    transition = build_public_transition(
        scheduled_cell_id="e1-t0000-s0000000017",
        execution_attempt_id=(
            "e1-t0000-s0000000017-a000"
        ),
        model_call_index=0,
        environment_step_index=0,
        submitted_action="look",
        pre_observation="before",
        pre_menu=_menu(
            ("look", "inventory", "look")
        ),
        result=_result(),
    )

    observed = set(transition.to_dict())
    expected = {
        field.name
        for field in fields(type(transition))
        if not field.name.startswith("_")
    }
    assert observed == expected

    forbidden = {
        "infos",
        "raw_infos",
        "expert_plan",
        "policy_commands",
        "facts",
        "gamefile",
        "exception",
    }
    assert forbidden.isdisjoint(observed)


def test_public_transition_hashes_match_exact_sequences_and_text() -> None:
    pre_menu = _menu(
        ("look", "inventory", "look")
    )
    result = _result()

    transition = build_public_transition(
        scheduled_cell_id="e1-t0000-s0000000017",
        execution_attempt_id=(
            "e1-t0000-s0000000017-a000"
        ),
        model_call_index=0,
        environment_step_index=0,
        submitted_action="look",
        pre_observation="before",
        pre_menu=pre_menu,
        result=result,
    )

    assert transition.pre_action_observation_sha256 == (
        sha256_text("before")
    )
    assert (
        transition.pre_action_admissible_commands
        == pre_menu.commands
    )
    assert (
        transition.pre_action_admissible_commands_sha256
        == sha256_string_sequence(pre_menu.commands)
    )
    assert transition.resulting_observation_sha256 == (
        sha256_text(result.observation)
    )
    assert (
        transition.resulting_admissible_commands
        == result.menu.commands
    )
    assert (
        transition.resulting_admissible_commands_sha256
        == sha256_string_sequence(
            result.menu.commands
        )
    )


def test_transition_visibility_labels_are_frozen() -> None:
    transition = build_public_transition(
        scheduled_cell_id="e1-t0000-s0000000017",
        execution_attempt_id=(
            "e1-t0000-s0000000017-a000"
        ),
        model_call_index=0,
        environment_step_index=0,
        submitted_action="look",
        pre_observation="before",
        pre_menu=_menu(("look",)),
        result=_result(),
    )

    assert transition.pre_action_visibility == (
        "POLICY_VISIBLE_BEFORE_ACTION"
    )
    assert transition.resulting_visibility == (
        "POST_ACTION_PUBLIC_AUDIT_ONLY"
    )


def test_environment_exception_produces_no_public_transition() -> None:
    with pytest.raises(TypeError):
        build_public_transition(
            scheduled_cell_id="e1-t0000-s0000000017",
            execution_attempt_id=(
                "e1-t0000-s0000000017-a000"
            ),
            model_call_index=0,
            environment_step_index=0,
            submitted_action="look",
            pre_observation="before",
            pre_menu=_menu(("look",)),
            result=None,
        )

from __future__ import annotations

from dataclasses import FrozenInstanceError
import inspect
import json

import pytest

from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    FORMAT_ERROR_V1,
    INVALID_ACTION_V1,
    InterfaceFeedbackCode,
    build_raw_policy_prompt,
    canonical_executed_transitions_json,
    sha256_executed_transitions,
)


def _transition(index: int) -> ExecutedTransition:
    return ExecutedTransition(
        action=f"action-{index}",
        resulting_observation=f"observation-{index}",
    )


def _decoded_prompt_field(
    prompt: str,
    prefix: str,
) -> object:
    matching_lines = [
        line
        for line in prompt.splitlines()
        if line.startswith(prefix)
    ]

    assert len(matching_lines) == 1

    return json.loads(
        matching_lines[0][len(prefix):]
    )


def test_feedback_enum_and_constants_are_exact() -> None:
    assert {
        item.name: item.value
        for item in InterfaceFeedbackCode
    } == {
        "FORMAT_ERROR_V1": "FORMAT_ERROR_V1",
        "INVALID_ACTION_V1": "INVALID_ACTION_V1",
    }

    assert FORMAT_ERROR_V1 == (
        "FORMAT_ERROR_V1:\n"
        "Expected exactly one JSON object with exactly "
        "one string field:\n"
        '{"action":"<command>"}\n'
        "No environment action was executed."
    )

    assert INVALID_ACTION_V1 == (
        "INVALID_ACTION_V1:\n"
        "The parsed action is not an exact member of "
        "the visible admissible-command menu.\n"
        "No environment action was executed."
    )


def test_executed_transition_is_immutable() -> None:
    transition = ExecutedTransition(
        action="look",
        resulting_observation="You see a desk.",
    )

    with pytest.raises(FrozenInstanceError):
        transition.action = "done"  # type: ignore[misc]


def test_prompt_signature_has_no_failed_response_input() -> None:
    signature = inspect.signature(
        build_raw_policy_prompt
    )

    assert list(signature.parameters) == [
        "public_task_goal",
        "observation",
        "executed_transitions",
        "admissible_commands",
        "interface_feedback",
    ]

    assert all(
        parameter.kind
        is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )

    prohibited = {
        "raw_response",
        "raw_model_response",
        "failed_response",
        "model_reason",
        "phase",
    }

    assert (
        prohibited
        & set(signature.parameters)
    ) == set()


def test_exact_prompt_without_feedback() -> None:
    prompt = build_raw_policy_prompt(
        public_task_goal=(
            "put the café cup on the shelf"
        ),
        observation="You see a café.",
        executed_transitions=(
            ExecutedTransition(
                action="look",
                resulting_observation=(
                    "You see a desk."
                ),
            ),
        ),
        admissible_commands=(
            "look",
            "go to café 1",
        ),
        interface_feedback=None,
    )

    assert prompt == "\n".join(
        [
            "RAW_POLICY_PROMPT_V1",
            (
                'TASK_GOAL_JSON='
                '"put the café cup on the shelf"'
            ),
            (
                'CURRENT_OBSERVATION_JSON='
                '"You see a café."'
            ),
            (
                "EXECUTED_TRANSITIONS_JSON="
                '[{"action":"look",'
                '"resulting_observation":'
                '"You see a desk."}]'
            ),
            (
                "VISIBLE_ADMISSIBLE_COMMANDS_JSON="
                '["look","go to café 1"]'
            ),
            "INTERFACE_FEEDBACK_JSON=null",
            (
                'OUTPUT_REQUIREMENT='
                '{"action":"<command>"}'
            ),
        ]
    )

    assert not prompt.endswith("\n")


def test_task_goal_is_present_in_every_prompt() -> None:
    prompts = [
        build_raw_policy_prompt(
            public_task_goal="put pencil on shelf",
            observation=observation,
            executed_transitions=(),
            admissible_commands=("look",),
            interface_feedback=None,
        )
        for observation in (
            "Observation one.",
            "Observation two.",
        )
    ]

    for prompt in prompts:
        assert _decoded_prompt_field(
            prompt,
            "TASK_GOAL_JSON=",
        ) == "put pencil on shelf"


def test_full_multiline_observation_is_retained() -> None:
    observation = (
        "Line one.\n"
        "Line two with café.\n"
        "Line three."
    )

    prompt = build_raw_policy_prompt(
        public_task_goal="goal",
        observation=observation,
        executed_transitions=(),
        admissible_commands=("look",),
        interface_feedback=None,
    )

    assert _decoded_prompt_field(
        prompt,
        "CURRENT_OBSERVATION_JSON=",
    ) == observation


def test_command_order_duplicates_and_unicode_are_preserved() -> None:
    commands = (
        "go to desk 2",
        "look",
        "go to café 1",
        "look",
    )

    prompt = build_raw_policy_prompt(
        public_task_goal="goal",
        observation="observation",
        executed_transitions=(),
        admissible_commands=commands,
        interface_feedback=None,
    )

    assert _decoded_prompt_field(
        prompt,
        "VISIBLE_ADMISSIBLE_COMMANDS_JSON=",
    ) == list(commands)


def test_only_final_eight_executed_transitions_remain() -> None:
    transitions = tuple(
        _transition(index)
        for index in range(10)
    )

    prompt = build_raw_policy_prompt(
        public_task_goal="goal",
        observation="observation",
        executed_transitions=transitions,
        admissible_commands=("look",),
        interface_feedback=None,
    )

    decoded_history = _decoded_prompt_field(
        prompt,
        "EXECUTED_TRANSITIONS_JSON=",
    )

    assert decoded_history == [
        {
            "action": f"action-{index}",
            "resulting_observation": (
                f"observation-{index}"
            ),
        }
        for index in range(2, 10)
    ]


def test_non_transition_history_items_are_rejected() -> None:
    invalid_history = (
        {
            "action": "look",
            "resulting_observation": "observation",
        },
    )

    with pytest.raises(
        TypeError,
        match="ExecutedTransition",
    ):
        build_raw_policy_prompt(
            public_task_goal="goal",
            observation="observation",
            executed_transitions=(
                invalid_history  # type: ignore[arg-type]
            ),
            admissible_commands=("look",),
            interface_feedback=None,
        )

    with pytest.raises(
        TypeError,
        match="ExecutedTransition",
    ):
        canonical_executed_transitions_json(
            invalid_history  # type: ignore[arg-type]
        )


def test_none_feedback_serializes_to_null() -> None:
    prompt = build_raw_policy_prompt(
        public_task_goal="goal",
        observation="observation",
        executed_transitions=(),
        admissible_commands=("look",),
        interface_feedback=None,
    )

    assert _decoded_prompt_field(
        prompt,
        "INTERFACE_FEEDBACK_JSON=",
    ) is None


@pytest.mark.parametrize(
    (
        "feedback_code",
        "expected_text",
    ),
    [
        (
            InterfaceFeedbackCode.FORMAT_ERROR_V1,
            FORMAT_ERROR_V1,
        ),
        (
            InterfaceFeedbackCode.INVALID_ACTION_V1,
            INVALID_ACTION_V1,
        ),
    ],
)
def test_feedback_enum_maps_to_fixed_text(
    feedback_code: InterfaceFeedbackCode,
    expected_text: str,
) -> None:
    prompt = build_raw_policy_prompt(
        public_task_goal="goal",
        observation="observation",
        executed_transitions=(),
        admissible_commands=("look",),
        interface_feedback=feedback_code,
    )

    assert _decoded_prompt_field(
        prompt,
        "INTERFACE_FEEDBACK_JSON=",
    ) == expected_text


def test_arbitrary_feedback_string_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="interface_feedback",
    ):
        build_raw_policy_prompt(
            public_task_goal="goal",
            observation="observation",
            executed_transitions=(),
            admissible_commands=("look",),
            interface_feedback=(
                "Try going to the desk."
                # type: ignore[arg-type]
            ),
        )


def test_identical_inputs_produce_identical_bytes() -> None:
    kwargs = {
        "public_task_goal": "goal",
        "observation": "observation",
        "executed_transitions": (
            ExecutedTransition(
                action="look",
                resulting_observation="seen",
            ),
        ),
        "admissible_commands": (
            "look",
            "go to desk 1",
        ),
        "interface_feedback": (
            InterfaceFeedbackCode
            .INVALID_ACTION_V1
        ),
    }

    first = build_raw_policy_prompt(**kwargs)
    second = build_raw_policy_prompt(**kwargs)

    assert first == second
    assert first.encode("utf-8") == second.encode(
        "utf-8"
    )


def test_canonical_transition_json_golden_value() -> None:
    transitions = (
        ExecutedTransition(
            action="look",
            resulting_observation="You see a desk.",
        ),
    )

    assert canonical_executed_transitions_json(
        transitions
    ) == (
        '[{"action":"look",'
        '"resulting_observation":"You see a desk."}]'
    )


def test_canonical_transition_json_preserves_unicode() -> None:
    transitions = (
        ExecutedTransition(
            action="go to café 1",
            resulting_observation="杯子在桌上。",
        ),
    )

    result = canonical_executed_transitions_json(
        transitions
    )

    assert "café" in result
    assert "杯子在桌上。" in result
    assert "\\u00e9" not in result


def test_canonical_transition_json_uses_final_eight() -> None:
    transitions = tuple(
        _transition(index)
        for index in range(12)
    )

    result = json.loads(
        canonical_executed_transitions_json(
            transitions
        )
    )

    assert [
        item["action"]
        for item in result
    ] == [
        f"action-{index}"
        for index in range(4, 12)
    ]


def test_memory_m0_sha256_golden_value() -> None:
    transitions = (
        ExecutedTransition(
            action="look",
            resulting_observation="You see a desk.",
        ),
    )

    assert sha256_executed_transitions(
        transitions
    ) == (
        "af30775b5c2278a829632643ee4a6752c"
        "68b2d729d84d5dcb9871e2a097637aa"
    )


def test_memory_hash_depends_only_on_final_eight() -> None:
    final_eight = tuple(
        _transition(index)
        for index in range(1, 9)
    )

    with_ignored_prefix = (
        ExecutedTransition(
            action="ignored-prefix",
            resulting_observation="ignored",
        ),
        *final_eight,
    )

    assert sha256_executed_transitions(
        with_ignored_prefix
    ) == sha256_executed_transitions(
        final_eight
    )

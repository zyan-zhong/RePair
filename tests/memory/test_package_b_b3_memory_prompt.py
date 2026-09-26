from __future__ import annotations

import json

from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    InterfaceFeedbackCode,
    build_raw_policy_prompt,
)
from pchsi.memory.memory_augmented_prompt import (
    build_memory_augmented_raw_policy_prompt_v1,
    prompt_without_memory_line_v1,
)


def _history():
    return tuple(
        ExecutedTransition(
            action=f"action-{index}",
            resulting_observation=f"obs-{index}",
        )
        for index in range(10)
    )


def test_b3_m0_and_memory_on_share_all_non_memory_bytes():
    common = {
        "public_task_goal": "goal",
        "observation": "current",
        "executed_transitions": _history(),
        "admissible_commands": (
            "z command",
            "a command",
            "m command",
        ),
        "interface_feedback": (
            InterfaceFeedbackCode.INVALID_ACTION_V1
        ),
    }

    m0 = build_memory_augmented_raw_policy_prompt_v1(
        retrieved_failure_experiences=(),
        **common,
    )
    on = build_memory_augmented_raw_policy_prompt_v1(
        retrieved_failure_experiences=(
            {
                "failure_cue": "visible cue",
            },
        ),
        **common,
    )

    assert prompt_without_memory_line_v1(m0) == (
        prompt_without_memory_line_v1(on)
    )


def test_b3_complete_menu_preserves_original_sequence():
    prompt = build_memory_augmented_raw_policy_prompt_v1(
        public_task_goal="goal",
        observation="obs",
        executed_transitions=(),
        retrieved_failure_experiences=(),
        admissible_commands=(
            "z command",
            "a command",
            "m command",
        ),
        interface_feedback=None,
    )
    line = next(
        item
        for item in prompt.splitlines()
        if item.startswith(
            "VISIBLE_ADMISSIBLE_COMMANDS_JSON="
        )
    )
    values = json.loads(line.split("=", 1)[1])
    assert values == [
        "z command",
        "a command",
        "m command",
    ]


def test_b3_executed_history_remains_exact_memory_m0_last_eight():
    prompt = build_memory_augmented_raw_policy_prompt_v1(
        public_task_goal="goal",
        observation="obs",
        executed_transitions=_history(),
        retrieved_failure_experiences=(),
        admissible_commands=("look",),
        interface_feedback=None,
    )
    line = next(
        item
        for item in prompt.splitlines()
        if item.startswith(
            "EXECUTED_TRANSITIONS_JSON="
        )
    )
    values = json.loads(line.split("=", 1)[1])
    assert [
        item["action"]
        for item in values
    ] == [
        f"action-{index}"
        for index in range(2, 10)
    ]


def test_b3_historical_raw_prompt_has_no_memory_field_and_is_unchanged():
    historical = build_raw_policy_prompt(
        public_task_goal="goal",
        observation="obs",
        executed_transitions=(),
        admissible_commands=("look",),
        interface_feedback=None,
    )
    assert historical.startswith("RAW_POLICY_PROMPT_V1\n")
    assert "RETRIEVED_FAILURE_EXPERIENCES_JSON" not in historical

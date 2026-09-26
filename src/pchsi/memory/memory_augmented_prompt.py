"""Deterministic Memory-augmented RAW policy prompt for Package B."""

from __future__ import annotations

from collections.abc import Sequence
import json

from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    FORMAT_ERROR_V1,
    INVALID_ACTION_V1,
    InterfaceFeedbackCode,
    canonical_executed_transitions_json,
)


PROMPT_ID = "MEMORY_AUGMENTED_RAW_POLICY_PROMPT_V1"
OUTPUT_REQUIREMENT = '{"action":"<command>"}'


def _json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _feedback(
    value: InterfaceFeedbackCode | None,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, InterfaceFeedbackCode):
        raise TypeError(
            "interface_feedback must be InterfaceFeedbackCode or None"
        )
    if value is InterfaceFeedbackCode.FORMAT_ERROR_V1:
        return FORMAT_ERROR_V1
    if value is InterfaceFeedbackCode.INVALID_ACTION_V1:
        return INVALID_ACTION_V1
    raise AssertionError("unreachable interface feedback")


def _commands(
    admissible_commands: Sequence[str],
) -> tuple[str, ...]:
    if isinstance(admissible_commands, str):
        raise TypeError("admissible_commands must not be str")
    values = tuple(admissible_commands)
    if any(not isinstance(item, str) for item in values):
        raise TypeError("admissible commands must be strings")
    return values


def _memory_payloads(
    retrieved_failure_experiences: Sequence[
        dict[str, object]
    ],
) -> tuple[dict[str, object], ...]:
    if isinstance(
        retrieved_failure_experiences,
        (str, bytes, bytearray),
    ):
        raise TypeError("Memory payloads must be a sequence of objects")
    values = tuple(retrieved_failure_experiences)
    if any(not isinstance(item, dict) for item in values):
        raise TypeError("Memory payload entries must be objects")
    return values


def build_memory_augmented_raw_policy_prompt_v1(
    *,
    public_task_goal: str,
    observation: str,
    executed_transitions: Sequence[ExecutedTransition],
    retrieved_failure_experiences: Sequence[
        dict[str, object]
    ],
    admissible_commands: Sequence[str],
    interface_feedback: InterfaceFeedbackCode | None,
) -> str:
    if not isinstance(public_task_goal, str):
        raise TypeError("public_task_goal must be str")
    if not isinstance(observation, str):
        raise TypeError("observation must be str")

    memory = _memory_payloads(
        retrieved_failure_experiences
    )
    commands = _commands(admissible_commands)
    feedback = _feedback(interface_feedback)

    return "\n".join(
        [
            PROMPT_ID,
            "TASK_GOAL_JSON="
            + _json(public_task_goal),
            "CURRENT_OBSERVATION_JSON="
            + _json(observation),
            "EXECUTED_TRANSITIONS_JSON="
            + canonical_executed_transitions_json(
                executed_transitions
            ),
            "RETRIEVED_FAILURE_EXPERIENCES_JSON="
            + _json(memory),
            "VISIBLE_ADMISSIBLE_COMMANDS_JSON="
            + _json(commands),
            "INTERFACE_FEEDBACK_JSON="
            + _json(feedback),
            "OUTPUT_REQUIREMENT="
            + OUTPUT_REQUIREMENT,
        ]
    )


def prompt_without_memory_line_v1(prompt: str) -> str:
    if not isinstance(prompt, str):
        raise TypeError("prompt must be str")
    lines = prompt.splitlines()
    prefix = "RETRIEVED_FAILURE_EXPERIENCES_JSON="
    matches = [
        index
        for index, line in enumerate(lines)
        if line.startswith(prefix)
    ]
    if len(matches) != 1:
        raise ValueError("prompt has invalid Memory field count")
    del lines[matches[0]]
    return "\n".join(lines)

"""Deterministic prompt construction for E1 RAW_WITH_MENU_V1.

This module contains only:

- the fixed raw-policy prompt format;
- the MEMORY_M0_V1 history window;
- fixed interface feedback messages;
- deterministic transition serialization and hashing.

It does not implement retrieval, summarization, planning, action repair,
budget accounting, admissibility checking or environment execution.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Final


__all__ = [
    "ExecutedTransition",
    "FORMAT_ERROR_V1",
    "INVALID_ACTION_V1",
    "InterfaceFeedbackCode",
    "build_raw_policy_prompt",
    "canonical_executed_transitions_json",
    "sha256_executed_transitions",
]


class InterfaceFeedbackCode(str, Enum):
    """Frozen interface feedback codes."""

    FORMAT_ERROR_V1 = "FORMAT_ERROR_V1"
    INVALID_ACTION_V1 = "INVALID_ACTION_V1"


FORMAT_ERROR_V1: Final[str] = (
    "FORMAT_ERROR_V1:\n"
    "Expected exactly one JSON object with exactly one string field:\n"
    '{"action":"<command>"}\n'
    "No environment action was executed."
)

INVALID_ACTION_V1: Final[str] = (
    "INVALID_ACTION_V1:\n"
    "The parsed action is not an exact member of "
    "the visible admissible-command menu.\n"
    "No environment action was executed."
)


@dataclass(frozen=True, slots=True)
class ExecutedTransition:
    """One environment transition that was actually executed."""

    action: str
    resulting_observation: str


_MEMORY_M0_WINDOW: Final[int] = 8

_OUTPUT_REQUIREMENT: Final[str] = (
    '{"action":"<command>"}'
)


def _canonical_json(
    value: object,
    *,
    sort_keys: bool = False,
) -> str:
    """Serialize one value using the frozen compact JSON contract."""

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=sort_keys,
        separators=(",", ":"),
    )


def _validated_transition_tuple(
    executed_transitions: Sequence[ExecutedTransition],
) -> tuple[ExecutedTransition, ...]:
    """Validate the complete supplied history before taking M0."""

    transitions = tuple(executed_transitions)

    for index, transition in enumerate(transitions):
        if not isinstance(
            transition,
            ExecutedTransition,
        ):
            raise TypeError(
                "executed_transitions"
                f"[{index}] must be ExecutedTransition"
            )

        if not isinstance(transition.action, str):
            raise TypeError(
                "ExecutedTransition.action must be str"
            )

        if not isinstance(
            transition.resulting_observation,
            str,
        ):
            raise TypeError(
                "ExecutedTransition.resulting_observation "
                "must be str"
            )

    return transitions


def _memory_m0(
    executed_transitions: Sequence[ExecutedTransition],
) -> tuple[ExecutedTransition, ...]:
    """Return exactly the final eight executed transitions."""

    transitions = _validated_transition_tuple(
        executed_transitions
    )

    return transitions[-_MEMORY_M0_WINDOW:]


def _transition_payload(
    executed_transitions: Sequence[ExecutedTransition],
) -> list[dict[str, str]]:
    """Build the canonical JSON payload for MEMORY_M0_V1."""

    history = _memory_m0(
        executed_transitions
    )

    return [
        {
            "action": transition.action,
            "resulting_observation": (
                transition.resulting_observation
            ),
        }
        for transition in history
    ]


def canonical_executed_transitions_json(
    executed_transitions: Sequence[ExecutedTransition],
) -> str:
    """Serialize the final eight executed transitions canonically."""

    return _canonical_json(
        _transition_payload(
            executed_transitions
        ),
        sort_keys=True,
    )


def sha256_executed_transitions(
    executed_transitions: Sequence[ExecutedTransition],
) -> str:
    """Return the MEMORY_M0_V1 canonical-state SHA-256."""

    canonical_json = (
        canonical_executed_transitions_json(
            executed_transitions
        )
    )

    return hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()


def _feedback_text(
    interface_feedback: InterfaceFeedbackCode | None,
) -> str | None:
    """Map only frozen feedback enums to frozen text."""

    if interface_feedback is None:
        return None

    if not isinstance(
        interface_feedback,
        InterfaceFeedbackCode,
    ):
        raise TypeError(
            "interface_feedback must be "
            "InterfaceFeedbackCode or None"
        )

    if (
        interface_feedback
        is InterfaceFeedbackCode.FORMAT_ERROR_V1
    ):
        return FORMAT_ERROR_V1

    if (
        interface_feedback
        is InterfaceFeedbackCode.INVALID_ACTION_V1
    ):
        return INVALID_ACTION_V1

    raise AssertionError(
        "unreachable InterfaceFeedbackCode"
    )


def _validated_commands(
    admissible_commands: Sequence[str],
) -> tuple[str, ...]:
    """Freeze command order and reject non-string command entries."""

    if isinstance(admissible_commands, str):
        raise TypeError(
            "admissible_commands must be a sequence "
            "of strings, not str"
        )

    commands = tuple(admissible_commands)

    for index, command in enumerate(commands):
        if not isinstance(command, str):
            raise TypeError(
                "admissible_commands"
                f"[{index}] must be str"
            )

    return commands


def build_raw_policy_prompt(
    *,
    public_task_goal: str,
    observation: str,
    executed_transitions: Sequence[ExecutedTransition],
    admissible_commands: Sequence[str],
    interface_feedback: InterfaceFeedbackCode | None,
) -> str:
    """Construct exactly one deterministic RAW_POLICY_PROMPT_V1."""

    if not isinstance(public_task_goal, str):
        raise TypeError(
            "public_task_goal must be str"
        )

    if not isinstance(observation, str):
        raise TypeError(
            "observation must be str"
        )

    commands = _validated_commands(
        admissible_commands
    )

    feedback = _feedback_text(
        interface_feedback
    )

    return "\n".join(
        [
            "RAW_POLICY_PROMPT_V1",
            (
                "TASK_GOAL_JSON="
                + _canonical_json(
                    public_task_goal
                )
            ),
            (
                "CURRENT_OBSERVATION_JSON="
                + _canonical_json(
                    observation
                )
            ),
            (
                "EXECUTED_TRANSITIONS_JSON="
                + canonical_executed_transitions_json(
                    executed_transitions
                )
            ),
            (
                "VISIBLE_ADMISSIBLE_COMMANDS_JSON="
                + _canonical_json(
                    commands
                )
            ),
            (
                "INTERFACE_FEEDBACK_JSON="
                + _canonical_json(
                    feedback
                )
            ),
            (
                "OUTPUT_REQUIREMENT="
                + _OUTPUT_REQUIREMENT
            ),
        ]
    )

"""Mechanical direct applicability gate for Failure Memory B-DIRECT.

No Analyzer, semantic paraphrase, phase inference or hidden-state inference.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    FORMAT_ERROR_V1,
    INVALID_ACTION_V1,
    InterfaceFeedbackCode,
)


class DirectApplicabilityDispositionV1(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONFLICTING = "CONFLICTING"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True, slots=True)
class DirectApplicabilityResultV1:
    disposition: DirectApplicabilityDispositionV1
    activation_hits: tuple[str, ...]
    release_hits: tuple[str, ...]
    non_applicability_hits: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "activation_hits",
            "release_hits",
            "non_applicability_hits",
        ):
            value = getattr(self, name)
            if type(value) is not tuple:
                raise TypeError(f"{name} must be tuple")


def _feedback_text(
    value: InterfaceFeedbackCode | None,
) -> str:
    if value is None:
        return ""
    if value is InterfaceFeedbackCode.FORMAT_ERROR_V1:
        return FORMAT_ERROR_V1
    if value is InterfaceFeedbackCode.INVALID_ACTION_V1:
        return INVALID_ACTION_V1
    raise TypeError("unsupported interface feedback")


def _visible_strings(
    *,
    observation: str,
    executed_transitions: Sequence[ExecutedTransition],
    admissible_commands: Sequence[str],
    interface_feedback: InterfaceFeedbackCode | None,
) -> tuple[str, ...]:
    if not isinstance(observation, str):
        raise TypeError("observation must be str")

    values = [observation]

    transitions = tuple(executed_transitions)
    for item in transitions:
        if not isinstance(item, ExecutedTransition):
            raise TypeError("executed transition type mismatch")
        values.extend(
            (
                item.action,
                item.resulting_observation,
            )
        )

    if isinstance(admissible_commands, str):
        raise TypeError("admissible_commands must not be str")
    commands = tuple(admissible_commands)
    if any(not isinstance(item, str) for item in commands):
        raise TypeError("admissible commands must be strings")
    values.extend(commands)

    feedback = _feedback_text(interface_feedback)
    if feedback:
        values.append(feedback)

    return tuple(values)


def _hits(
    cues: tuple[str, ...],
    visible_strings: tuple[str, ...],
) -> tuple[str, ...]:
    if type(cues) is not tuple:
        raise TypeError("cues must be tuple")
    if any(not isinstance(cue, str) or not cue for cue in cues):
        raise ValueError("cues must be nonempty strings")

    # Exact case-sensitive substring only. No case normalization, stemming,
    # approximate string matching or semantic paraphrase.
    return tuple(
        cue
        for cue in cues
        if any(
            cue in visible
            for visible in visible_strings
        )
    )


def evaluate_direct_applicability_v1(
    *,
    activation_cues: tuple[str, ...],
    release_cues: tuple[str, ...],
    non_applicability_cues: tuple[str, ...],
    observation: str,
    executed_transitions: Sequence[ExecutedTransition],
    admissible_commands: Sequence[str],
    interface_feedback: InterfaceFeedbackCode | None,
) -> DirectApplicabilityResultV1:
    visible = _visible_strings(
        observation=observation,
        executed_transitions=executed_transitions,
        admissible_commands=admissible_commands,
        interface_feedback=interface_feedback,
    )

    activation = _hits(
        activation_cues,
        visible,
    )
    release = _hits(
        release_cues,
        visible,
    )
    nonapp = _hits(
        non_applicability_cues,
        visible,
    )

    activation_satisfied = (
        bool(activation_cues)
        and len(activation) == len(activation_cues)
    )
    blocking = bool(release or nonapp)

    if activation_satisfied and blocking:
        disposition = (
            DirectApplicabilityDispositionV1.CONFLICTING
        )
    elif blocking:
        disposition = (
            DirectApplicabilityDispositionV1.NOT_APPLICABLE
        )
    elif activation_satisfied:
        disposition = (
            DirectApplicabilityDispositionV1.APPLICABLE
        )
    else:
        disposition = (
            DirectApplicabilityDispositionV1.UNCERTAIN
        )

    return DirectApplicabilityResultV1(
        disposition=disposition,
        activation_hits=activation,
        release_hits=release,
        non_applicability_hits=nonapp,
    )

from __future__ import annotations

from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
)
from pchsi.memory.applicability_gate import (
    DirectApplicabilityDispositionV1,
    evaluate_direct_applicability_v1,
)


def test_b6_exact_visible_activation_is_applicable():
    result = evaluate_direct_applicability_v1(
        activation_cues=("cabinet 1 is open",),
        release_cues=("task complete",),
        non_applicability_cues=(),
        observation="You see cabinet 1 is open.",
        executed_transitions=(),
        admissible_commands=("look",),
        interface_feedback=None,
    )
    assert (
        result.disposition
        is DirectApplicabilityDispositionV1.APPLICABLE
    )


def test_b6_casefold_or_paraphrase_is_not_allowed():
    result = evaluate_direct_applicability_v1(
        activation_cues=("cabinet 1 is open",),
        release_cues=(),
        non_applicability_cues=(),
        observation="Cabinet 1 is OPEN.",
        executed_transitions=(),
        admissible_commands=("look",),
        interface_feedback=None,
    )
    assert (
        result.disposition
        is DirectApplicabilityDispositionV1.UNCERTAIN
    )


def test_b6_release_or_nonapp_blocks_normal_exposure():
    result = evaluate_direct_applicability_v1(
        activation_cues=("at desk 1",),
        release_cues=("task complete",),
        non_applicability_cues=("different task state",),
        observation="at desk 1; task complete",
        executed_transitions=(),
        admissible_commands=("look",),
        interface_feedback=None,
    )
    assert (
        result.disposition
        is DirectApplicabilityDispositionV1.CONFLICTING
    )


def test_b6_visible_state_includes_exact_recent_transition_and_menu():
    result = evaluate_direct_applicability_v1(
        activation_cues=("opened cabinet", "examine cabinet 1"),
        release_cues=(),
        non_applicability_cues=(),
        observation="current observation",
        executed_transitions=(
            ExecutedTransition(
                action="open cabinet 1",
                resulting_observation="opened cabinet",
            ),
        ),
        admissible_commands=(
            "examine cabinet 1",
            "go to desk 1",
        ),
        interface_feedback=None,
    )
    assert (
        result.disposition
        is DirectApplicabilityDispositionV1.APPLICABLE
    )

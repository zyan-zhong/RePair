from __future__ import annotations

import pytest

from pchsi.round_control.analyzer_substage import (
    AnalyzerPipelineStateV1,
    AnalyzerSubstageV1,
    future_nonhuman_phases_are_automatic,
    next_analyzer_substage_action,
)
from pchsi.round_control.role_authority import AuthorityPhaseV1
from pchsi.research_intelligence.takeover import build_takeover_evaluation


def _takeover() -> dict[str, object]:
    return build_takeover_evaluation(
        metrics={
            "completed_reference_round_count": 1,
            "full_round_go_count": 1,
            "strong_pre_shadow_round_count": 2,
            "strong_post_shadow_round_count": 2,
            "future_outcome_leakage_count": 0,
            "single_change_compliance_rate": 1.0,
            "budget_compliance_rate": 1.0,
            "evidence_validity_rate": 0.95,
            "human_field_revision_rate": 0.0,
            "repeated_nogo_avoidance_rate": 0.90,
            "downstream_benefits_per_budget_ratio_vs_human": 0.90,
        }
    )


def _state(
    phase: AuthorityPhaseV1,
    substage: AnalyzerSubstageV1,
) -> AnalyzerPipelineStateV1:
    return AnalyzerPipelineStateV1.from_frozen_receipt(
        round_id="r",
        authority_phase=phase,
        current_substage=substage,
        receipt_sha256="1" * 64,
        transition_index=2,
    )


def test_human_bootstrap_group_stage_pauses_for_human_primary() -> None:
    action = next_analyzer_substage_action(
        state=_state(
            AuthorityPhaseV1.HUMAN_PRIMARY_STRONG_SHADOW,
            AnalyzerSubstageV1.GROUP_A2_A3,
        ),
        takeover_evaluation=None,
    )
    assert action.primary_actor == "HUMAN"
    assert action.shadow_actors == ("STRONG",)
    assert action.routine_human_scientific_action_required is True
    assert action.automatic_handoff_after_terminal_receipt is False


def test_strong_primary_group_stage_auto_handoffs_to_local_shadow() -> None:
    action = next_analyzer_substage_action(
        state=_state(
            AuthorityPhaseV1.STRONG_PRIMARY_LOCAL_SHADOW,
            AnalyzerSubstageV1.GROUP_A2_A3,
        ),
        takeover_evaluation=_takeover(),
    )
    assert action.primary_actor == "STRONG"
    assert action.shadow_actors == ("LOCAL",)
    assert action.routine_human_scientific_action_required is False
    assert action.automatic_handoff_after_terminal_receipt is True


def test_local_primary_crosscheck_has_no_routine_human_action() -> None:
    action = next_analyzer_substage_action(
        state=_state(
            AuthorityPhaseV1.LOCAL_PRIMARY_STRONG_AUDIT,
            AnalyzerSubstageV1.CROSSCHECK_X,
        ),
        takeover_evaluation=_takeover(),
    )
    assert action.primary_actor == "LOCAL"
    assert "STRONG" in action.auditor_actors
    assert action.routine_human_scientific_action_required is False
    assert action.automatic_handoff_after_terminal_receipt is True


def test_deterministic_grouping_always_auto_handoffs() -> None:
    action = next_analyzer_substage_action(
        state=_state(
            AuthorityPhaseV1.HUMAN_PRIMARY_STRONG_SHADOW,
            AnalyzerSubstageV1.DETERMINISTIC_GROUPING,
        ),
        takeover_evaluation=None,
    )
    assert action.deterministic is True
    assert action.primary_actor is None
    assert action.routine_human_scientific_action_required is False
    assert action.automatic_handoff_after_terminal_receipt is True


def test_pipeline_transition_order_is_fixed() -> None:
    state = _state(
        AuthorityPhaseV1.HUMAN_PRIMARY_STRONG_SHADOW,
        AnalyzerSubstageV1.GROUP_A2_A3,
    )
    next_state = state.advance(
        next_substage=AnalyzerSubstageV1.COMPONENT_C,
        receipt_sha256="2" * 64,
    )
    assert next_state.current_substage is AnalyzerSubstageV1.COMPONENT_C

    with pytest.raises(ValueError):
        state.advance(
            next_substage=AnalyzerSubstageV1.CROSSCHECK_X,
            receipt_sha256="3" * 64,
        )


def test_future_nonhuman_phases_have_no_routine_human_scientific_steps() -> None:
    future_nonhuman_phases_are_automatic(_takeover())

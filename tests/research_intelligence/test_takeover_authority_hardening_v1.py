from __future__ import annotations

from copy import deepcopy

import pytest

from pchsi.research_intelligence.takeover import (
    build_takeover_evaluation,
    validate_takeover_evaluation,
)
from pchsi.round_control.role_authority import (
    AuthorityPhaseV1,
    ResearchRoleV1,
    resolve_authority_plan,
)


def good_metrics():
    return {
        "completed_reference_round_count": 1,
        "full_round_go_count": 0,
        "strong_pre_shadow_round_count": 1,
        "strong_post_shadow_round_count": 1,
        "future_outcome_leakage_count": 0,
        "single_change_compliance_rate": 1.0,
        "budget_compliance_rate": 1.0,
        "evidence_validity_rate": 0.95,
        "human_field_revision_rate": 0.0,
        "repeated_nogo_avoidance_rate": 0.9,
        "downstream_benefits_per_budget_ratio_vs_human": 0.9,
    }


def test_valid_report_allows_strong_primary_authority_plan():
    report = build_takeover_evaluation(metrics=good_metrics())
    assert validate_takeover_evaluation(report) == report
    plan = resolve_authority_plan(
        phase=AuthorityPhaseV1.STRONG_PRIMARY_LOCAL_SHADOW,
        takeover_evaluation=report,
    )
    assert plan.primary_actor(ResearchRoleV1.ANALYZER) == "STRONG"
    assert "LOCAL" in plan.shadow_actors(ResearchRoleV1.ANALYZER)


def test_handwritten_flags_are_rejected_even_if_true():
    forged = {
        "schema_id": "RESEARCH_PLANNER_TAKEOVER_EVALUATION_V1",
        "schema_version": 1,
        "strong_research_planner_primary_eligible": True,
        "local_training_and_shadow_eligible": True,
    }
    with pytest.raises(ValueError):
        resolve_authority_plan(
            phase=AuthorityPhaseV1.STRONG_PRIMARY_LOCAL_SHADOW,
            takeover_evaluation=forged,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("completed_reference_round_count", True),
        ("completed_reference_round_count", 0.5),
        ("future_outcome_leakage_count", -1),
        ("evidence_validity_rate", 1.01),
        ("human_field_revision_rate", -0.01),
        ("repeated_nogo_avoidance_rate", float("inf")),
        ("downstream_benefits_per_budget_ratio_vs_human", -0.1),
    ],
)
def test_invalid_metric_domains_rejected(field, value):
    metrics = good_metrics()
    metrics[field] = value
    with pytest.raises(ValueError):
        build_takeover_evaluation(metrics=metrics)


def test_report_tampering_is_rejected():
    report = build_takeover_evaluation(metrics=good_metrics())
    forged = deepcopy(report)
    forged["strong_research_planner_primary_eligible"] = False
    with pytest.raises(ValueError, match="canonical report"):
        validate_takeover_evaluation(forged)

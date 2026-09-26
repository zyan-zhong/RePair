from __future__ import annotations

from collections.abc import Mapping
import math
from pathlib import Path

from .common import finalize_hash, write_json_new


_COUNT_FIELDS = {
    "completed_reference_round_count",
    "full_round_go_count",
    "strong_pre_shadow_round_count",
    "strong_post_shadow_round_count",
    "future_outcome_leakage_count",
}
_RATE_FIELDS = {
    "single_change_compliance_rate",
    "budget_compliance_rate",
    "evidence_validity_rate",
    "human_field_revision_rate",
    "repeated_nogo_avoidance_rate",
}
_RATIO_FIELD = "downstream_benefits_per_budget_ratio_vs_human"
_REQUIRED_FIELDS = _COUNT_FIELDS | _RATE_FIELDS | {_RATIO_FIELD}


def _validate_metric_domain(metrics: Mapping[str, object]) -> None:
    missing = sorted(_REQUIRED_FIELDS - set(metrics))
    if missing:
        raise ValueError(f"takeover metrics missing fields: {missing}")

    for field in sorted(_COUNT_FIELDS):
        value = metrics[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(
                f"{field} must be a nonnegative integer and not bool"
            )

    for field in sorted(_RATE_FIELDS):
        value = metrics[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field} must be one finite numeric rate")
        number = float(value)
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            raise ValueError(f"{field} must be finite and within [0,1]")

    ratio = metrics[_RATIO_FIELD]
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)):
        raise ValueError(
            f"{_RATIO_FIELD} must be one finite nonnegative numeric ratio"
        )
    ratio_number = float(ratio)
    if not math.isfinite(ratio_number) or ratio_number < 0.0:
        raise ValueError(
            f"{_RATIO_FIELD} must be finite and nonnegative"
        )


def build_takeover_evaluation(
    *,
    metrics: Mapping[str, object],
) -> dict[str, object]:
    # Pure builder preserving V1 gate semantics for previously valid inputs.
    _validate_metric_domain(metrics)

    checks = {
        "reference_round_completed": metrics[
            "completed_reference_round_count"
        ] >= 1,
        "pre_shadow_observed": metrics["strong_pre_shadow_round_count"] >= 1,
        "post_shadow_observed": metrics["strong_post_shadow_round_count"] >= 1,
        "no_future_outcome_leakage": metrics[
            "future_outcome_leakage_count"
        ] == 0,
        "single_change_compliance": metrics[
            "single_change_compliance_rate"
        ] == 1.0,
        "budget_compliance": metrics["budget_compliance_rate"] == 1.0,
        "evidence_validity": metrics["evidence_validity_rate"] >= 0.95,
        "human_revision_bounded": metrics["human_field_revision_rate"] <= 0.35,
        "repeated_nogo_avoidance": metrics[
            "repeated_nogo_avoidance_rate"
        ] >= 0.90,
        "downstream_value_not_worse_than_human": metrics[
            "downstream_benefits_per_budget_ratio_vs_human"
        ] >= 0.90,
    }
    strong_primary_eligible = all(checks.values())

    local_primary_checks = {
        "at_least_one_full_round_go": metrics["full_round_go_count"] >= 1,
        "repeated_strong_shadow_rounds": (
            metrics["strong_pre_shadow_round_count"] >= 2
            and metrics["strong_post_shadow_round_count"] >= 2
        ),
        "strong_primary_quality_gate": strong_primary_eligible,
    }
    local_training_shadow_eligible = (
        metrics["completed_reference_round_count"] >= 1
        and metrics["future_outcome_leakage_count"] == 0
    )
    local_primary_eligible = all(local_primary_checks.values())

    out = {
        "schema_id": "RESEARCH_PLANNER_TAKEOVER_EVALUATION_V1",
        "schema_version": 1,
        "metrics": dict(metrics),
        "strong_primary_checks": checks,
        "strong_research_planner_primary_eligible": strong_primary_eligible,
        "local_training_and_shadow_eligible": local_training_shadow_eligible,
        "local_primary_checks": local_primary_checks,
        "local_research_planner_primary_eligible": local_primary_eligible,
        "unified_checkpoint_claim_supported": False,
        "fresh_autonomous_round_claim_supported": False,
        "takeover_evaluation_sha256": "0" * 64,
    }
    return finalize_hash(
        domain="RESEARCH_PLANNER_TAKEOVER_EVALUATION_V1",
        field="takeover_evaluation_sha256",
        value=out,
    )


def validate_takeover_evaluation(
    value: Mapping[str, object],
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("takeover evaluation must be one mapping")
    if value.get("schema_id") != "RESEARCH_PLANNER_TAKEOVER_EVALUATION_V1":
        raise ValueError("unexpected takeover evaluation schema")
    if value.get("schema_version") != 1:
        raise ValueError("unexpected takeover evaluation schema version")

    metrics = value.get("metrics")
    if not isinstance(metrics, Mapping):
        raise ValueError("takeover evaluation metrics must be one mapping")

    expected = build_takeover_evaluation(metrics=metrics)
    observed = dict(value)
    if observed != expected:
        raise ValueError(
            "takeover evaluation does not match metrics-derived canonical report"
        )
    return expected


def evaluate_takeover_gate(
    *,
    metrics: Mapping[str, object],
    output: Path,
) -> dict[str, object]:
    out = build_takeover_evaluation(metrics=metrics)
    write_json_new(output, out)
    return out

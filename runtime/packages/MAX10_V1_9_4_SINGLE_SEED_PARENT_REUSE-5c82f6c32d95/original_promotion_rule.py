"""Pure acceptance rule for registered, audited TRAIN_SELECT results.

The native finalizer must verify all task/cell identities, referenced bytes and
the complete registered grid before calling this producer. This module checks
the resulting summary's contract and arithmetic without filesystem access.
Invalid evidence raises; it never becomes a scientific ROLLBACK.
"""
from __future__ import annotations

import math


class PromotionRuleError(ValueError):
    """A frozen rule or its evidence is invalid, so no decision can be made."""


def _require(condition, reason):
    if not condition:
        raise PromotionRuleError(reason)


def _object(value, name):
    _require(isinstance(value, dict), name + ": object required")


def _text(value, name):
    _require(isinstance(value, str) and bool(value.strip()), name + ": nonempty string required")


def _integer(value, name, *, positive=False):
    _require(type(value) is int and value >= (1 if positive else 0),
             name + ": " + ("positive" if positive else "nonnegative") + " integer required")


def _seeds(value, name):
    _require(isinstance(value, (list, tuple)) and bool(value), name + ": nonempty seed sequence required")
    _require(all(type(seed) is int for seed in value), name + ": integer seeds required")
    _require(len(set(value)) == len(value), name + ": duplicate seeds")
    return tuple(value)


def _sha256(value, name):
    _require(isinstance(value, str) and len(value) == 64 and
             all(char in "0123456789abcdef" for char in value), name + ": SHA256 required")


def _reference(value, name):
    _object(value, name)
    _text(value.get("path"), name + ".path")
    _sha256(value.get("sha256"), name + ".sha256")


def validate_rule(frozen_rule):
    """Validate the authorized comparison and registered grid, before outcomes.

Registration metadata may accompany the rule. Its source/registry binding is
verified by the caller and does not add scientific acceptance thresholds.
"""
    _object(frozen_rule, "frozen_rule")
    required = {
        "schema_id": "FROZEN_TRAIN_SELECT_PROMOTION_RULE_V1",
        "evidence_access_class": "TRAIN_SELECT",
        "primary_metric": "total_success_cells",
        "comparison": "strictly_greater",
        "secondary_metrics_role": "explanation_only",
    }
    for field, expected in required.items():
        _require(frozen_rule.get(field) == expected, "frozen_rule." + field + ": unsupported value")
    _require(frozen_rule.get("frozen_before_outcomes") is True, "frozen_rule: must be frozen before outcomes")
    _text(frozen_rule.get("decision_rule_id"), "frozen_rule.decision_rule_id")
    _integer(frozen_rule.get("expected_task_count"), "frozen_rule.expected_task_count", positive=True)
    _seeds(frozen_rule.get("replicate_seeds"), "frozen_rule.replicate_seeds")


def decide(*, frozen_rule, aggregate):
    """PROMOTE iff candidate total successes strictly exceed parent successes.

All secondary metrics are explanatory. The mean-delta tolerance below checks
floating-point consistency only; it never determines promotion.
"""
    validate_rule(frozen_rule)
    _object(aggregate, "aggregate")
    required = {
        "schema_id": "CURRENT_TRAIN_SELECT_AGGREGATE_V1",
        "memory_state": "OFF",
        "harness_state": "OFF",
        "evidence_access_class": "TRAIN_SELECT",
        "primary_statistical_unit": "unique_task",
    }
    for field, expected in required.items():
        _require(aggregate.get(field) == expected, "aggregate." + field + ": unsupported value")
    _require(aggregate.get("replicates_are_not_independent_tasks") is True,
             "aggregate: replicates must not be independent tasks")
    _require(aggregate.get("benchmark_feedback_used") is False,
             "aggregate: benchmark feedback is not authorized")

    for field in ("round_id", "parent_policy_id", "candidate_policy_id"):
        _text(aggregate.get(field), "aggregate." + field)
    _require(aggregate["parent_policy_id"] != aggregate["candidate_policy_id"],
             "aggregate: parent and candidate identities must differ")
    _sha256(aggregate.get("request_sha256"), "aggregate.request_sha256")
    for field in ("frozen_protocol_ref", "identity_audit_ref", "native_paired_results_ref"):
        _reference(aggregate.get(field), "aggregate." + field)

    count_fields = (
        "unique_task_count", "paired_cell_count", "total_condition_cell_count",
        "parent_success_cells", "candidate_success_cells", "both_success_cells",
        "both_failure_cells", "parent_only_success_cells", "candidate_only_success_cells",
    )
    for field in count_fields:
        _integer(aggregate.get(field), "aggregate." + field)
    seeds = _seeds(aggregate.get("replicate_seeds"), "aggregate.replicate_seeds")
    _require(seeds == tuple(frozen_rule["replicate_seeds"]), "aggregate: registered seed grid mismatch")
    _require(aggregate["unique_task_count"] == frozen_rule["expected_task_count"],
             "aggregate: registered task count mismatch")
    pairs = frozen_rule["expected_task_count"] * len(seeds)
    _require(aggregate["paired_cell_count"] == pairs and
             aggregate["total_condition_cell_count"] == 2 * pairs,
             "aggregate: complete registered paired grid required")

    both = aggregate["both_success_cells"]
    neither = aggregate["both_failure_cells"]
    parent_only = aggregate["parent_only_success_cells"]
    candidate_only = aggregate["candidate_only_success_cells"]
    parent = aggregate["parent_success_cells"]
    candidate = aggregate["candidate_success_cells"]
    _require(both + neither + parent_only + candidate_only == pairs,
             "aggregate: joint outcomes must partition the complete grid")
    _require(parent == both + parent_only and candidate == both + candidate_only,
             "aggregate: success counts disagree with joint outcomes")

    mean_delta = aggregate.get("mean_task_success_rate_delta")
    _require(type(mean_delta) in (int, float), "aggregate: numeric mean delta required")
    # Equal seed coverage per task makes these rates equivalent. Allow ordinary
    # summation roundoff from the native per-task aggregation, never an effect gate.
    _require(math.isfinite(mean_delta) and
             math.isclose(mean_delta, (candidate - parent) / pairs, rel_tol=1e-12, abs_tol=1e-12),
             "aggregate: mean delta disagrees with success counts")
    return {
        "decision": "PROMOTE" if candidate > parent else "ROLLBACK",
        "decision_rule_id": frozen_rule["decision_rule_id"],
    }

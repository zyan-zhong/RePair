"""Behavioral contract for the authorized complete-grid success-count rule."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def rule_module():
    path = Path(__file__).resolve().parents[1] / "promotion_rule.py"
    assert path.is_file(), "The authorized promotion rule has not been implemented"
    spec = importlib.util.spec_from_file_location("success_count_promotion_rule", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def frozen_rule():
    return {
        "schema_id": "FROZEN_TRAIN_SELECT_PROMOTION_RULE_V1",
        "frozen_before_outcomes": True,
        "evidence_access_class": "TRAIN_SELECT",
        "decision_rule_id": "synthetic-strict-success-count-v1",
        "primary_metric": "total_success_cells",
        "comparison": "strictly_greater",
        "secondary_metrics_role": "explanation_only",
        "expected_task_count": 3,
        "replicate_seeds": [7, 19],
    }


@pytest.fixture
def aggregate():
    # Three tasks x two seeds. Four joint outcomes sum to six pairs.
    return {
        "schema_id": "CURRENT_TRAIN_SELECT_AGGREGATE_V1",
        "unique_task_count": 3,
        "replicate_seeds": [7, 19],
        "paired_cell_count": 6,
        "total_condition_cell_count": 12,
        "parent_success_cells": 2,
        "candidate_success_cells": 3,
        "both_success_cells": 1,
        "both_failure_cells": 2,
        "parent_only_success_cells": 1,
        "candidate_only_success_cells": 2,
        "mean_task_success_rate_delta": 1 / 6,
        "round_id": "fixture-round",
        "request_sha256": "a" * 64,
        "parent_policy_id": "fixture-parent",
        "candidate_policy_id": "fixture-candidate",
        "memory_state": "OFF",
        "harness_state": "OFF",
        "primary_statistical_unit": "unique_task",
        "replicates_are_not_independent_tasks": True,
        "evidence_access_class": "TRAIN_SELECT",
        "benchmark_feedback_used": False,
        "frozen_protocol_ref": {"path": "fixture/protocol.json", "sha256": "b" * 64},
        "identity_audit_ref": {"path": "fixture/audit.json", "sha256": "c" * 64},
        "native_paired_results_ref": {"path": "fixture/paired.json", "sha256": "d" * 64},
    }


@pytest.mark.parametrize(
    "counts,delta,expected",
    [
        ((1, 2, 1, 2, 2, 3), 1 / 6, "PROMOTE"),
        ((1, 3, 1, 1, 2, 2), 0.0, "ROLLBACK"),
        ((1, 2, 2, 1, 3, 2), -1 / 6, "ROLLBACK"),
        ((0, 6, 0, 0, 0, 0), 0.0, "ROLLBACK"),
        ((6, 0, 0, 0, 6, 6), 0.0, "ROLLBACK"),
    ],
)
def test_only_strict_success_increase_promotes(rule_module, frozen_rule, aggregate, counts, delta, expected):
    aggregate.update(zip(("both_success_cells", "both_failure_cells", "parent_only_success_cells",
                          "candidate_only_success_cells", "parent_success_cells", "candidate_success_cells"), counts))
    aggregate["mean_task_success_rate_delta"] = delta
    assert rule_module.decide(frozen_rule=frozen_rule, aggregate=aggregate) == {
        "decision": expected, "decision_rule_id": "synthetic-strict-success-count-v1",
    }


def test_one_extra_success_never_needs_minimum_effect_or_confidence(rule_module, frozen_rule, aggregate):
    # Deliberately tiny rate increase: numerical tolerance must not become a gate.
    frozen_rule.update(expected_task_count=10**15, replicate_seeds=[97])
    aggregate.update(unique_task_count=10**15, replicate_seeds=[97], paired_cell_count=10**15,
                     total_condition_cell_count=2 * 10**15, parent_success_cells=0,
                     candidate_success_cells=1, both_success_cells=0, both_failure_cells=10**15 - 1,
                     parent_only_success_cells=0, candidate_only_success_cells=1,
                     mean_task_success_rate_delta=1e-15)
    aggregate.update(confidence_interval=[-1, 1], memory_improvement=False,
                     secondary_metrics={"latency_change": 1000, "memory_quality": -1000})
    assert rule_module.decide(frozen_rule=frozen_rule, aggregate=aggregate)["decision"] == "PROMOTE"


def test_auxiliary_improvements_cannot_rescue_a_tie(rule_module, frozen_rule, aggregate):
    aggregate.update(candidate_success_cells=2, candidate_only_success_cells=1,
                     both_failure_cells=3, mean_task_success_rate_delta=0,
                     secondary_metrics={"memory_quality": 1000, "latency_change": -1000})
    assert rule_module.decide(frozen_rule=frozen_rule, aggregate=aggregate)["decision"] == "ROLLBACK"


def test_floating_roundoff_is_not_a_scientific_threshold(rule_module, frozen_rule, aggregate):
    aggregate["mean_task_success_rate_delta"] = 0.16666666666666669
    assert rule_module.decide(frozen_rule=frozen_rule, aggregate=aggregate)["decision"] == "PROMOTE"


@pytest.mark.parametrize("field,value", [
    ("paired_cell_count", 5), ("paired_cell_count", 7),
    ("total_condition_cell_count", 11), ("unique_task_count", 2),
    ("replicate_seeds", [7, 23]), ("replicate_seeds", [19, 7]),
    ("replicate_seeds", [7, 7]), ("replicate_seeds", [True, 19]),
    ("replicate_seeds", [7.0, 19]), ("replicate_seeds", []),
    ("both_failure_cells", 3), ("both_success_cells", -1),
    ("parent_success_cells", 3), ("candidate_success_cells", 4),
    ("parent_only_success_cells", True), ("candidate_only_success_cells", 2.0),
    ("unique_task_count", True), ("total_condition_cell_count", 12.0),
    ("mean_task_success_rate_delta", -1 / 6), ("mean_task_success_rate_delta", 0.16),
    ("mean_task_success_rate_delta", float("nan")),
    ("mean_task_success_rate_delta", float("inf")),
    ("mean_task_success_rate_delta", True),
    ("schema_id", "HELDOUT_AGGREGATE_V1"), ("evidence_access_class", "HELDOUT"),
    ("memory_state", "ON"), ("harness_state", "ON"),
    ("benchmark_feedback_used", True), ("benchmark_feedback_used", 0),
    ("primary_statistical_unit", "replicate"),
    ("replicates_are_not_independent_tasks", False),
    ("replicates_are_not_independent_tasks", 1),
    ("parent_policy_id", "fixture-candidate"), ("candidate_policy_id", ""),
    ("round_id", " "), ("request_sha256", "bad-digest"),
    ("identity_audit_ref", None),
    ("frozen_protocol_ref", {"path": "protocol.json", "sha256": "bad-digest"}),
    ("native_paired_results_ref", {"path": "", "sha256": "d" * 64}),
])
def test_invalid_or_incomplete_evidence_raises_instead_of_rollback(rule_module, frozen_rule, aggregate, field, value):
    aggregate[field] = value
    with pytest.raises(ValueError):
        rule_module.decide(frozen_rule=frozen_rule, aggregate=aggregate)


@pytest.mark.parametrize("field,value", [
    ("schema_id", "OTHER_RULE"), ("frozen_before_outcomes", False),
    ("frozen_before_outcomes", 1), ("evidence_access_class", "HELDOUT"),
    ("decision_rule_id", " "), ("primary_metric", "mean_delta"),
    ("comparison", "greater_or_equal"), ("secondary_metrics_role", "acceptance_gate"),
    ("expected_task_count", 0), ("expected_task_count", -3),
    ("expected_task_count", True), ("expected_task_count", 3.0),
    ("replicate_seeds", []), ("replicate_seeds", [7, 7]),
    ("replicate_seeds", [True, 19]), ("replicate_seeds", [7, 19.0]),
    ("replicate_seeds", "7,19"),
])
def test_invalid_frozen_rule_raises_before_any_decision(rule_module, frozen_rule, aggregate, field, value):
    frozen_rule[field] = value
    with pytest.raises(ValueError):
        rule_module.validate_rule(frozen_rule)
    with pytest.raises(ValueError):
        rule_module.decide(frozen_rule=frozen_rule, aggregate=aggregate)


def test_missing_required_fields_raise(rule_module, frozen_rule, aggregate):
    for field in list(frozen_rule):
        missing = {key: value for key, value in frozen_rule.items() if key != field}
        with pytest.raises(ValueError):
            rule_module.decide(frozen_rule=missing, aggregate=aggregate)
    for field in list(aggregate):
        missing = {key: value for key, value in aggregate.items() if key != field}
        with pytest.raises(ValueError):
            rule_module.decide(frozen_rule=frozen_rule, aggregate=missing)


def test_registered_metadata_is_allowed_and_inputs_are_unchanged(rule_module, frozen_rule, aggregate):
    frozen_rule.update(registered_select_task_access_sha256="e" * 64,
                       decision_producer={"entrypoint": "decide", "source_ref": {"sha256": "f" * 64}})
    before = deepcopy((frozen_rule, aggregate))
    rule_module.validate_rule(frozen_rule)
    rule_module.decide(frozen_rule=frozen_rule, aggregate=aggregate)
    assert (frozen_rule, aggregate) == before


@pytest.mark.parametrize("value", [None, [], "invalid"])
def test_non_object_inputs_raise(rule_module, frozen_rule, aggregate, value):
    with pytest.raises(ValueError):
        rule_module.decide(frozen_rule=value, aggregate=aggregate)
    with pytest.raises(ValueError):
        rule_module.decide(frozen_rule=frozen_rule, aggregate=value)

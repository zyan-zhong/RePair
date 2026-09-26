"""Deterministic, artifact-recomputable decisions for Failure Memory V1.

The cell executor reports only mechanical outcomes.  It never reports Q1--Q3
scientific dispositions.  This module recomputes stage metrics and question
results from the complete registered cell population under a pre-outcome,
content-addressed decision rule.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
)

STAGE_1B = "STAGE_1B_FROZEN_POLICY_FM0_FM3"
STAGE_2 = "STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY"
STAGE_3 = "STAGE_3_FROZEN_FORMAL_EVALUATION"
REGISTERED_STAGES = frozenset({STAGE_1B, STAGE_2, STAGE_3})

FM0 = "FM0_NO_MEMORY"
FM1 = "FM1_MATCHED_RAW_EPISODIC"
FM2 = "FM2_STRUCTURED_DESCRIPTIVE"
FM3 = "FM3_GATED_PRESCRIPTIVE"
ROUND_ACTIVE = "ROUND_ACTIVE_MEMORY"
REGISTERED_CONDITIONS = frozenset({FM0, FM1, FM2, FM3, ROUND_ACTIVE})

OLD_FAILURE_DISPOSITIONS = frozenset({
    "AVOIDED", "REPEATED", "DIFFERENT_FAILURE", "UNCERTAIN", "NOT_APPLICABLE"
})
QUESTION_DISPOSITIONS = frozenset({"SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE"})

_CELL_KEYS = frozenset({
    "schema_id", "schema_version", "cell_result_sha256", "cell_id",
    "execution_manifest_sha256", "stage", "comparison_group_id", "condition",
    "round_index", "split", "task_id", "task_family", "snapshot_sha256",
    "success", "memory_exposed", "correct_memory_exposure",
    "wrong_memory_exposure", "unsafe_memory_exposure", "harm_observed",
    "abstained", "old_failure_disposition", "model_calls", "environment_steps",
    "memory_tokens", "prompt_tokens", "latency_ms",
    "evaluation_writeback_attempted", "same_round_memory_readback",
    "role_pack_sha256s",
})
_RULE_KEYS = frozenset({
    "schema_id", "schema_version", "rule_sha256", "stage", "primary_endpoint",
    "primary_split", "minimum_complete_pairs", "minimum_absolute_success_gain",
    "minimum_coverage_count", "minimum_correct_exposure_count",
    "maximum_harm_count", "maximum_wrong_memory_count",
    "maximum_unsafe_memory_count", "minimum_round_count",
    "confidence_interval_method", "multiple_comparisons_policy",
})
_ROLE_KEYS = frozenset({"policy", "analyzer", "researcher"})


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or any(ch in value for ch in "\x00\r\n"):
        raise ValueError(f"{name} must be nonempty one-line text")
    return value


def _nonnegative(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be nonnegative int")
    return value


def _boolean(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be bool")
    return value


def _optional_sha(name: str, value: object) -> str | None:
    if value is None:
        return None
    require_lower_sha256(name, value)
    return value


def _self_hash(domain: str, value: Mapping[str, object], field: str) -> str:
    payload = dict(value)
    payload.pop(field, None)
    return sha256_bytes(domain.encode("utf-8") + b"\0" + canonical_json_bytes(payload))


@dataclass(frozen=True, slots=True)
class RegisteredDecisionRuleV1:
    stage: str
    primary_split: str | None
    minimum_complete_pairs: int
    minimum_absolute_success_gain: int
    minimum_coverage_count: int
    minimum_correct_exposure_count: int
    maximum_harm_count: int
    maximum_wrong_memory_count: int
    maximum_unsafe_memory_count: int
    minimum_round_count: int
    confidence_interval_method: str
    multiple_comparisons_policy: str
    rule_sha256: str


def validate_decision_rule_v1(value: object) -> RegisteredDecisionRuleV1:
    if not isinstance(value, dict) or set(value) != _RULE_KEYS:
        raise ValueError("decision rule fields mismatch")
    if value["schema_id"] != "FAILURE_MEMORY_REGISTERED_DECISION_RULE_V1" or value["schema_version"] != 1:
        raise ValueError("decision rule schema mismatch")
    stage = _text("stage", value["stage"])
    if stage not in REGISTERED_STAGES:
        raise ValueError("decision rule stage is not registered")
    primary_split = value["primary_split"]
    if primary_split is not None:
        _text("primary_split", primary_split)
    if stage == STAGE_3 and primary_split not in {"VALID_SEEN", "VALID_UNSEEN"}:
        raise ValueError("Stage 3 requires a registered primary split")
    if stage != STAGE_3 and primary_split is not None:
        raise ValueError("only Stage 3 may define primary_split")
    ints = {
        name: _nonnegative(name, value[name])
        for name in (
            "minimum_complete_pairs", "minimum_absolute_success_gain",
            "minimum_coverage_count", "minimum_correct_exposure_count",
            "maximum_harm_count", "maximum_wrong_memory_count",
            "maximum_unsafe_memory_count", "minimum_round_count",
        )
    }
    if ints["minimum_complete_pairs"] < 1:
        raise ValueError("minimum_complete_pairs must be positive")
    if stage == STAGE_2 and ints["minimum_round_count"] < 2:
        raise ValueError("Stage 2 minimum_round_count must be at least two")
    confidence = _text("confidence_interval_method", value["confidence_interval_method"])
    multiple = _text("multiple_comparisons_policy", value["multiple_comparisons_policy"])
    require_lower_sha256("rule_sha256", value["rule_sha256"])
    expected = _self_hash(
        "FAILURE_MEMORY_REGISTERED_DECISION_RULE_V1",
        value,
        "rule_sha256",
    )
    if value["rule_sha256"] != expected:
        raise ValueError("decision rule self-hash mismatch")
    return RegisteredDecisionRuleV1(
        stage=stage,
        primary_split=primary_split,
        rule_sha256=value["rule_sha256"],
        confidence_interval_method=confidence,
        multiple_comparisons_policy=multiple,
        **ints,
    )


def validate_cell_result_v1(
    value: object,
    *,
    expected_stage: str,
    expected_execution_manifest_sha256: str,
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != _CELL_KEYS:
        raise ValueError("cell scientific result fields mismatch")
    if value["schema_id"] != "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1" or value["schema_version"] != 1:
        raise ValueError("cell scientific result schema mismatch")
    if value["stage"] != expected_stage or expected_stage not in REGISTERED_STAGES:
        raise ValueError("cell stage mismatch")
    require_lower_sha256("execution_manifest_sha256", value["execution_manifest_sha256"])
    if value["execution_manifest_sha256"] != expected_execution_manifest_sha256:
        raise ValueError("cell execution-manifest binding mismatch")
    _text("cell_id", value["cell_id"])
    _text("comparison_group_id", value["comparison_group_id"])
    condition = _text("condition", value["condition"])
    if condition not in REGISTERED_CONDITIONS:
        raise ValueError("cell condition is not registered")
    round_index = value["round_index"]
    if round_index is not None:
        _nonnegative("round_index", round_index)
    if expected_stage == STAGE_2:
        if condition != ROUND_ACTIVE or round_index is None:
            raise ValueError("Stage 2 requires ROUND_ACTIVE_MEMORY and round_index")
    else:
        if condition not in {FM0, FM1, FM2, FM3} or round_index is not None:
            raise ValueError("Stage 1B/3 condition or round identity invalid")
    split = value["split"]
    if split is not None:
        _text("split", split)
    if expected_stage == STAGE_3 and split not in {"VALID_SEEN", "VALID_UNSEEN"}:
        raise ValueError("Stage 3 cell split invalid")
    _text("task_id", value["task_id"])
    _text("task_family", value["task_family"])
    _optional_sha("snapshot_sha256", value["snapshot_sha256"])
    for name in (
        "success", "memory_exposed", "correct_memory_exposure",
        "wrong_memory_exposure", "unsafe_memory_exposure", "harm_observed",
        "abstained", "evaluation_writeback_attempted", "same_round_memory_readback",
    ):
        _boolean(name, value[name])
    if value["correct_memory_exposure"] and not value["memory_exposed"]:
        raise ValueError("correct exposure requires memory exposure")
    if value["wrong_memory_exposure"] and not value["memory_exposed"]:
        raise ValueError("wrong exposure requires memory exposure")
    if value["unsafe_memory_exposure"] and not value["memory_exposed"]:
        raise ValueError("unsafe exposure requires memory exposure")
    if value["abstained"] and value["memory_exposed"]:
        raise ValueError("abstention and exposure cannot both be true")
    if condition == FM0 and value["memory_exposed"]:
        raise ValueError("FM0 cannot expose persistent Memory")
    disposition = _text("old_failure_disposition", value["old_failure_disposition"])
    if disposition not in OLD_FAILURE_DISPOSITIONS:
        raise ValueError("old failure disposition invalid")
    for name in (
        "model_calls", "environment_steps", "memory_tokens", "prompt_tokens", "latency_ms"
    ):
        _nonnegative(name, value[name])
    role_shas = value["role_pack_sha256s"]
    if not isinstance(role_shas, dict) or set(role_shas) != _ROLE_KEYS:
        raise ValueError("role_pack_sha256s fields mismatch")
    for role, digest in role_shas.items():
        _optional_sha(f"role_pack_sha256s.{role}", digest)
    require_lower_sha256("cell_result_sha256", value["cell_result_sha256"])
    expected = _self_hash(
        "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1",
        value,
        "cell_result_sha256",
    )
    if value["cell_result_sha256"] != expected:
        raise ValueError("cell result self-hash mismatch")
    return dict(value)


def _validate_registered_population_v1(
    rows: list[dict[str, object]],
    *,
    stage: str,
) -> None:
    if stage in {STAGE_1B, STAGE_3}:
        required = {FM0, FM1, FM2, FM3}
        groups: dict[tuple[str | None, str], list[str]] = defaultdict(list)
        for row in rows:
            key = (
                str(row["split"]) if stage == STAGE_3 else None,
                str(row["comparison_group_id"]),
            )
            groups[key].append(str(row["condition"]))
        for key, conditions in groups.items():
            if len(conditions) != len(set(conditions)):
                raise ValueError(
                    f"registered comparison arm repeats: {key}"
                )
            if set(conditions) != required:
                raise ValueError(
                    f"registered comparison group is incomplete: {key}"
                )
        return

    if stage != STAGE_2:
        raise ValueError("registered population stage is not supported")

    rounds = sorted({int(row["round_index"]) for row in rows})
    if not rounds or rounds != list(range(rounds[-1] + 1)):
        raise ValueError("Stage 2 round population must be contiguous from round zero")

    by_round: dict[int, list[str]] = defaultdict(list)
    for row in rows:
        by_round[int(row["round_index"])].append(
            str(row["comparison_group_id"])
        )
    reference_groups: set[str] | None = None
    for round_index in rounds:
        group_ids = by_round[round_index]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError(
                f"Stage 2 comparison group repeats within round {round_index}"
            )
        current_groups = set(group_ids)
        if reference_groups is None:
            reference_groups = current_groups
        elif current_groups != reference_groups:
            raise ValueError(
                f"Stage 2 comparison-group population differs in round {round_index}"
            )


def _paired(rows: Iterable[dict[str, object]], reference: str, treatment: str) -> dict[str, object]:
    groups: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in rows:
        group_id = str(row["comparison_group_id"])
        condition = str(row["condition"])
        if condition in groups[group_id]:
            raise ValueError(
                f"paired comparison contains duplicate arm: {group_id}:{condition}"
            )
        groups[group_id][condition] = row
    pairs = []
    for group_id in sorted(groups):
        members = groups[group_id]
        if reference in members and treatment in members:
            pairs.append((group_id, members[reference], members[treatment]))
    benefit = sum((not bool(r["success"])) and bool(t["success"]) for _, r, t in pairs)
    harm = sum(bool(r["success"]) and (not bool(t["success"])) for _, r, t in pairs)
    neutral_success = sum(bool(r["success"]) and bool(t["success"]) for _, r, t in pairs)
    neutral_failure = sum((not bool(r["success"])) and (not bool(t["success"])) for _, r, t in pairs)
    return {
        "reference": reference,
        "treatment": treatment,
        "complete_pair_count": len(pairs),
        "benefit_count": benefit,
        "harm_count": harm,
        "neutral_success_count": neutral_success,
        "neutral_failure_count": neutral_failure,
        "net_success_gain": benefit - harm,
        "pair_ids": [group_id for group_id, _, _ in pairs],
    }


def _decision_from_pair(
    pair: Mapping[str, object],
    *,
    rule: RegisteredDecisionRuleV1,
    scope: str,
) -> dict[str, object]:
    pairs = int(pair["complete_pair_count"])
    gain = int(pair["net_success_gain"])
    harm = int(pair["harm_count"])
    if pairs < rule.minimum_complete_pairs:
        disposition = "INCONCLUSIVE"
    elif harm > rule.maximum_harm_count:
        disposition = "NOT_SUPPORTED"
    elif gain >= rule.minimum_absolute_success_gain:
        disposition = "SUPPORTED"
    elif gain <= 0:
        disposition = "NOT_SUPPORTED"
    else:
        disposition = "INCONCLUSIVE"
    return {
        "disposition": disposition,
        "summary": (
            f"{pair['treatment']} vs {pair['reference']}: "
            f"pairs={pairs}, benefit={pair['benefit_count']}, harm={harm}, "
            f"net_success_gain={gain}; frozen thresholds applied."
        ),
        "scope": scope,
    }


def _q3_decision(
    rows: list[dict[str, object]],
    *,
    rule: RegisteredDecisionRuleV1,
    comparison: Mapping[str, object],
    scope: str,
    exposure_labels_registered: bool,
) -> tuple[dict[str, object], dict[str, object]]:
    coverage = sum(bool(row["memory_exposed"]) for row in rows)
    abstention = sum(bool(row["abstained"]) for row in rows)

    if exposure_labels_registered:
        correct: int | None = sum(
            bool(row["correct_memory_exposure"]) for row in rows
        )
        wrong: int | None = sum(
            bool(row["wrong_memory_exposure"]) for row in rows
        )
        unsafe: int | None = sum(
            bool(row["unsafe_memory_exposure"]) for row in rows
        )
        exposure_label_authority = "REGISTERED_DIRECT_GOLD_V1"
    else:
        # Stage 2/3 have no independently registered per-task exposure gold.
        # Schema-V1 cell booleans are placeholders and are not zero evidence.
        correct = None
        wrong = None
        unsafe = None
        exposure_label_authority = (
            "NOT_EVALUATED_NO_REGISTERED_GOLD_V1"
        )

    # Harm is independently identifiable from registered paired task success.
    harm = int(comparison["harm_count"])
    harm_authority = "PAIRED_TASK_SUCCESS_V1"
    gain = int(comparison["net_success_gain"])

    if harm > rule.maximum_harm_count:
        disposition = "NOT_SUPPORTED"
    elif gain <= 0:
        disposition = "NOT_SUPPORTED"
    elif not exposure_labels_registered:
        # Task-success improvement alone cannot establish correct/safe retrieval.
        disposition = "INCONCLUSIVE"
    elif (
        wrong is not None
        and unsafe is not None
        and (
            wrong > rule.maximum_wrong_memory_count
            or unsafe > rule.maximum_unsafe_memory_count
        )
    ):
        disposition = "NOT_SUPPORTED"
    elif (
        correct is not None
        and (
            coverage < rule.minimum_coverage_count
            or correct < rule.minimum_correct_exposure_count
        )
    ):
        disposition = "INCONCLUSIVE"
    elif gain >= rule.minimum_absolute_success_gain:
        disposition = "SUPPORTED"
    else:
        disposition = "INCONCLUSIVE"

    metrics = {
        "row_count": len(rows),
        "coverage_count": coverage,
        "correct_exposure_count": correct,
        "wrong_exposure_count": wrong,
        "unsafe_exposure_count": unsafe,
        "harm_count": harm,
        "abstention_count": abstention,
        "exposure_label_authority": exposure_label_authority,
        "harm_authority": harm_authority,
    }
    decision = {
        "disposition": disposition,
        "summary": (
            f"coverage={coverage}/{len(rows)}, correct={correct}, "
            f"wrong={wrong}, unsafe={unsafe}, harm={harm}, "
            f"abstention={abstention}, net_success_gain={gain}, "
            f"exposure_label_authority={exposure_label_authority}, "
            f"harm_authority={harm_authority}; frozen thresholds applied."
        ),
        "scope": scope,
    }
    return decision, metrics


def recompute_stage_decisions_v1(
    *,
    stage: str,
    cell_results: Iterable[Mapping[str, object]],
    decision_rule: Mapping[str, object],
    execution_manifest_sha256: str,
) -> dict[str, object]:
    require_lower_sha256("execution_manifest_sha256", execution_manifest_sha256)
    rule = validate_decision_rule_v1(dict(decision_rule))
    if rule.stage != stage:
        raise ValueError("decision rule and stage mismatch")
    rows = [
        validate_cell_result_v1(
            dict(row),
            expected_stage=stage,
            expected_execution_manifest_sha256=execution_manifest_sha256,
        )
        for row in cell_results
    ]
    if not rows:
        raise ValueError("stage decisions require cell results")
    ids = [str(row["cell_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("cell result IDs repeat")
    _validate_registered_population_v1(rows, stage=stage)
    selected = rows
    if stage == STAGE_3:
        selected = [row for row in rows if row["split"] == rule.primary_split]
        if not selected:
            raise ValueError("Stage 3 primary split has no cells")
    if stage in {STAGE_1B, STAGE_3}:
        q1_pair = _paired(selected, FM0, FM1)
        q2_pair = _paired(selected, FM1, FM2)
        q3_pair = _paired(selected, FM0, FM3)
        q1 = _decision_from_pair(q1_pair, rule=rule, scope=f"{stage}:{rule.primary_split or 'ALL'}")
        q2 = _decision_from_pair(q2_pair, rule=rule, scope=f"{stage}:{rule.primary_split or 'ALL'}")
        fm3 = [row for row in selected if row["condition"] == FM3]
        q3, q3_metrics = _q3_decision(
            fm3,
            rule=rule,
            comparison=q3_pair,
            scope=f"{stage}:{rule.primary_split or 'ALL'}",
            exposure_labels_registered=(stage == STAGE_1B),
        )
        decisions = {"Q1": q1, "Q2": q2, "Q3": q3}
        metrics = {
            "q1_pair": q1_pair,
            "q2_pair": q2_pair,
            "q3_pair": q3_pair,
            "q3_safety_utility": q3_metrics,
        }
    else:
        rounds = sorted({int(row["round_index"]) for row in selected})
        if len(rounds) < rule.minimum_round_count or rounds[0] != 0:
            raise ValueError("Stage 2 round population is incomplete")
        first = [dict(row, condition="ROUND_0") for row in selected if row["round_index"] == rounds[0]]
        last = [dict(row, condition="ROUND_LAST") for row in selected if row["round_index"] == rounds[-1]]
        pair_rows = [*first, *last]
        q1_pair = _paired(pair_rows, "ROUND_0", "ROUND_LAST")
        q1 = _decision_from_pair(q1_pair, rule=rule, scope=f"{stage}:R0_TO_R{rounds[-1]}")
        q3, q3_metrics = _q3_decision(
            last,
            rule=rule,
            comparison=q1_pair,
            scope=f"{stage}:R{rounds[-1]}",
            exposure_labels_registered=False,
        )
        decisions = {"Q1": q1, "Q3": q3}
        per_round = {}
        round0_by_group = {
            str(row["comparison_group_id"]): row
            for row in selected
            if row["round_index"] == rounds[0]
        }
        for round_index in rounds:
            subset = [
                row for row in selected
                if row["round_index"] == round_index
            ]
            current_by_group = {
                str(row["comparison_group_id"]): row
                for row in subset
            }
            paired_harm = (
                0
                if round_index == rounds[0]
                else sum(
                    bool(round0_by_group[group_id]["success"])
                    and (not bool(current_by_group[group_id]["success"]))
                    for group_id in sorted(round0_by_group)
                )
            )
            per_round[str(round_index)] = {
                "row_count": len(subset),
                "success_count": sum(
                    bool(row["success"]) for row in subset
                ),
                "old_failure_repeated_count": sum(
                    row["old_failure_disposition"] == "REPEATED"
                    for row in subset
                ),
                "correct_exposure_count": None,
                "wrong_memory_count": None,
                "unsafe_memory_count": None,
                "harm_count": paired_harm,
                "exposure_label_authority": (
                    "NOT_EVALUATED_NO_REGISTERED_GOLD_V1"
                ),
                "harm_authority": "PAIRED_TASK_SUCCESS_V1",
                "snapshot_sha256s": sorted({
                    str(row["snapshot_sha256"]) for row in subset
                }),
            }
        metrics = {
            "rounds": rounds,
            "round0_vs_last": q1_pair,
            "last_round_safety_utility": q3_metrics,
            "per_round": per_round,
        }
    return {
        "algorithm_id": "FAILURE_MEMORY_DETERMINISTIC_DECISION_ENGINE_V1",
        "stage": stage,
        "rule_sha256": rule.rule_sha256,
        "primary_endpoint": "TASK_SUCCESS",
        "question_decisions": decisions,
        "effect_estimates": metrics,
        "confidence_interval_method": rule.confidence_interval_method,
        "multiple_comparisons_policy": rule.multiple_comparisons_policy,
        "cell_result_count": len(rows),
        "decision_sha256": sha256_bytes(
            b"FAILURE_MEMORY_RECOMPUTED_STAGE_DECISION_V1\0"
            + canonical_json_bytes({
                "stage": stage,
                "rule_sha256": rule.rule_sha256,
                "question_decisions": decisions,
                "effect_estimates": metrics,
            })
        ),
    }

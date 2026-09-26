from __future__ import annotations

from fractions import Fraction

import pytest

from pchsi.memory.formal_b_retrieval import (
    FormalBGoldDispositionV1,
    FormalBGoldPanelV1,
    FormalBGoldTargetV1,
    FormalBIndependentGoldAuthorityV1,
    FormalBIndependentGoldRowV1,
    FormalBPanelMetricsV1,
    FormalBPoolV1,
    FormalBQueryV1,
    FormalBRetrieverConfigV1,
    FormalBThresholdReportV1,
    select_validation_config_v1,
    validate_panel_against_independent_gold_authority_v1,
)
from pchsi.evaluation.raw_policy_prompt import ExecutedTransition


def _metrics(*, wrong: int, nonapp: int, correct: int, exposure: int):
    return FormalBPanelMetricsV1(
        row_count=2,
        expected_exposure_count=1,
        expected_abstain_count=1,
        exposure_count=exposure,
        abstention_count=2 - exposure,
        correct_exposure_count=correct,
        wrong_exposure_count=wrong,
        non_applicable_exposure_count=nonapp,
        pre_gate_top1_hit_count=correct,
        disposition_counts=(),
    )


def _report(threshold: int, metrics: FormalBPanelMetricsV1):
    return FormalBThresholdReportV1(
        config=FormalBRetrieverConfigV1(threshold_pct=threshold),
        decisions=(),
        metrics=metrics,
    )


def test_selection_is_unsafe_exposure_first_not_coverage_first():
    unsafe_high_coverage = _report(
        0,
        _metrics(wrong=0, nonapp=1, correct=1, exposure=2),
    )
    safe_abstain = _report(
        50,
        _metrics(wrong=0, nonapp=0, correct=0, exposure=0),
    )
    safe_correct = _report(
        25,
        _metrics(wrong=0, nonapp=0, correct=1, exposure=1),
    )

    assert (
        unsafe_high_coverage.metrics.unsafe_memory_exposure_rate.fraction
        == Fraction(1, 2)
    )

    selected = select_validation_config_v1(
        (unsafe_high_coverage, safe_abstain, safe_correct),
        (0, 50, 25),
    )
    assert selected.threshold_pct == 25


def _query(pool: FormalBPoolV1, group: str):
    return FormalBQueryV1(
        pool=pool,
        task_gamefile_group_id=group,
        observation="visible state",
        executed_transitions=(
            ExecutedTransition("look", "visible state"),
        ),
        admissible_commands=("look",),
        interface_feedback=None,
        gold_target=FormalBGoldTargetV1(
            FormalBGoldDispositionV1.ABSTAIN_NO_APPLICABLE_MEMORY,
            None,
        ),
        independent_gold_artifact_sha256="a" * 64,
    )


def test_panel_must_rebind_to_independent_gold_authority():
    queries = (
        _query(FormalBPoolV1.RETRIEVER_CALIBRATION_DEV, "g1"),
        _query(FormalBPoolV1.RETRIEVER_SELECTION_VALIDATION, "g2"),
        _query(FormalBPoolV1.REGISTERED_SAFETY_STRESS, "g3"),
    )
    authority = FormalBIndependentGoldAuthorityV1(
        rows=tuple(
            FormalBIndependentGoldRowV1(
                query_id=query.query_id,
                gold_target=query.gold_target,
                independent_gold_artifact_sha256=(
                    query.independent_gold_artifact_sha256
                ),
            )
            for query in queries
        )
    )
    panel = FormalBGoldPanelV1(
        active_snapshot_sha256="b" * 64,
        independent_gold_authority_sha256=authority.authority_sha256,
        queries=queries,
    )
    validate_panel_against_independent_gold_authority_v1(
        panel=panel,
        authority=authority,
    )

    wrong_authority = FormalBIndependentGoldAuthorityV1(
        rows=(
            FormalBIndependentGoldRowV1(
                query_id=queries[0].query_id,
                gold_target=queries[0].gold_target,
                independent_gold_artifact_sha256="c" * 64,
            ),
            *authority.rows[1:],
        )
    )
    with pytest.raises(ValueError):
        validate_panel_against_independent_gold_authority_v1(
            panel=panel,
            authority=wrong_authority,
        )

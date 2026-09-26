from __future__ import annotations

from pathlib import Path

import pytest

from pchsi.analyzer.formal_failure_collection import (
    FORMAL_ACCESS_CLASS,
    FORMAL_BATCH_SIZE,
    FORMAL_STOPPING_FAILURE_TARGET,
    HARNESS_MODE,
    MEMORY_MODE,
    NO_PERFORMANCE_ESTIMAND,
    FormalCollectionCaseReceiptV1,
    FormalCollectionPolicyIdentityV1,
    stopping_decision_after_complete_prefix_v1,
)


def _policy():
    return FormalCollectionPolicyIdentityV1(
        logical_condition_id="P4-R1-Q2-BAD",
        checkpoint_instance_id="P4-R1-Q2-BAD-TRAIN17",
        training_seed=17,
        served_model_name="P4-R1-Q2-BAD-TRAIN17",
        adapter_bundle_sha256="a" * 64,
        policy_runtime_manifest_sha256="b" * 64,
        server_runtime_manifest_sha256="c" * 64,
        raw_protocol_sha256="d" * 64,
        policy_request_schema_sha256="e" * 64,
    )


def _receipt(index: int, success: bool, previous: str | None):
    return FormalCollectionCaseReceiptV1(
        schema_id="FORMAL_ANALYZER_FRESH_FAILURE_CASE_RECEIPT_V1",
        schema_version=1,
        panel_manifest_sha256="1" * 64,
        panel_index=index,
        batch_index=index // FORMAL_BATCH_SIZE,
        task_access_record_line_index=index,
        task_access_record_sha256="2" * 64,
        task_gamefile_group_id="3" * 64,
        source_task_id=f"task-{index}",
        execution_attempt_id=f"attempt-{index}",
        attempt_bundle_sha256="4" * 64,
        scientific_outcome_status="FAILURE" if not success else "SUCCESS",
        success=success,
        termination_reason="DONE",
        outcome_use="FAILURE_COHORT_STOPPING_ONLY_NO_POLICY_PERFORMANCE_ESTIMAND",
        performance_estimand=NO_PERFORMANCE_ESTIMAND,
        previous_receipt_sha256=previous,
    )


def _chain(successes):
    out = []
    previous = None
    for index, success in enumerate(successes):
        row = _receipt(index, success, previous)
        out.append(row)
        previous = row.receipt_sha256
    return tuple(out)


def test_formal_collection_frozen_constants():
    assert FORMAL_ACCESS_CLASS == "TRAIN_RETRIEVAL_DEV"
    assert FORMAL_BATCH_SIZE == 12
    assert FORMAL_STOPPING_FAILURE_TARGET == 42
    assert MEMORY_MODE == "MEMORY_OFF_M0"
    assert HARNESS_MODE == "HARNESS_OFF"


def test_policy_identity_is_exact_pi1_train17_memory_harness_off():
    value = _policy()
    assert value.logical_condition_id == "P4-R1-Q2-BAD"
    assert value.checkpoint_instance_id == "P4-R1-Q2-BAD-TRAIN17"
    assert value.training_seed == 17
    assert value.memory_mode == "MEMORY_OFF_M0"
    assert value.harness_mode == "HARNESS_OFF"
    assert value.request_kind == "R0"


def test_stopping_never_reads_incomplete_batch():
    receipts = _chain([False] * 42)
    assert len(receipts) == 42
    assert stopping_decision_after_complete_prefix_v1(
        receipts, panel_size=100
    ) == "CONTINUE"


def test_stopping_at_first_complete_batch_with_at_least_42_failures():
    receipts = _chain([False] * 48)
    assert stopping_decision_after_complete_prefix_v1(
        receipts, panel_size=100
    ) == "STOP_FAILURE_TARGET_REACHED"


def test_successes_are_preserved_and_can_delay_stopping():
    receipts = _chain(([False] * 40) + ([True] * 8))
    assert len(receipts) == 48
    assert stopping_decision_after_complete_prefix_v1(
        receipts, panel_size=100
    ) == "CONTINUE"


def test_no_policy_performance_estimand_constant():
    assert NO_PERFORMANCE_ESTIMAND == "NO_PERFORMANCE_ESTIMAND"

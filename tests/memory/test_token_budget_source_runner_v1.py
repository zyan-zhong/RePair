from __future__ import annotations

from pathlib import Path


def test_token_budget_source_runner_is_memory_off_and_outcome_blind():
    text = Path(
        "scripts/memory/run_token_budget_calibration_source_v1.py"
    ).read_text(encoding="utf-8")

    assert "MEMORY_OFF_M0" in text
    assert "HARNESS_OFF" in text
    assert "NO_PERFORMANCE_ESTIMAND" in text
    assert "CALIBRATION_FAILURE_TARGET_V1" in text
    assert "SOURCE_BATCH_SIZE" in text
    assert "FIRST_30_FAILURES_IN_PRE_FROZEN_TRAIN_MEMORY_SOURCE_PANEL_ORDER_V1" in text

    for forbidden in (
        "valid_seen",
        "valid_unseen",
        "success_rate",
        "accuracy",
    ):
        assert forbidden.casefold() not in text.casefold()

    assert '"memory_on_execution_used": False' in text


def test_token_budget_source_runner_reuses_original_attempts():
    text = Path(
        "scripts/memory/run_token_budget_calibration_source_v1.py"
    ).read_text(encoding="utf-8")

    assert "SEALED_SOURCE_COLLECTION_REUSE" in text
    assert "original_receipts" in text
    assert "extension_receipts" in text
    assert "attempt_bundle_sha256" in text

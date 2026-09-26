from __future__ import annotations

from pathlib import Path

import pytest

from pchsi.reference_loop.rebinding import (
    build_trajectory_rebinding_manifest,
)
from pchsi.reference_loop.types import (
    BudgetCounters,
    NormalizedPolicyCall,
    NormalizedTrace,
    ValidatedAttemptBundle,
)


def _bundle(access_class="TRAIN_MEMORY_SOURCE"):
    budget = BudgetCounters(0, 0, 0, 0, 0)
    return ValidatedAttemptBundle(
        bundle_root=Path("/tmp/bundle"),
        episode={
            "task_id": "task-1",
            "gamefile_sha256": "a" * 64,
            "logical_condition_id": "P4-R1-Q2-BAD",
            "checkpoint_instance_id": "P4-R1-Q2-BAD-TRAIN17",
            "access_class": access_class,
            "seed": 17,
        },
        policy_calls=(
            NormalizedPolicyCall(
                0, 0, "p", "goal", "prompt", "obs", ("look",), "{}",
                (), budget,
            ),
        ),
        traces=(
            NormalizedTrace(
                0, None, "not_executed", "goal", "obs", "prompt",
                ("look",), "{}", "", None, "failed", "error",
                "FORMAT_PROTOCOL_FAILURE", "envelope", "code", None,
                None, None, "POLICY_ATTEMPT_BUDGET_EXHAUSTED",
                budget, BudgetCounters(1, 0, 1, 0, 1), {},
            ),
        ),
        transitions=(),
        source_file_sha256s=(("attempt.json", "b" * 64),),
        episode_semantic_sha256="c" * 64,
        attempt_bundle_sha256="d" * 64,
        alignment_census={"status": "VALIDATED"},
    )


def _identity():
    return {
        "logical_policy_id": "P4-R1-Q2-BAD",
        "checkpoint_instance_id": "P4-R1-Q2-BAD-TRAIN17",
        "identity_sha256": "e" * 64,
    }


def _access(strong=True):
    row = {
        "task_id": "task-1",
        "gamefile_sha256": "a" * 64,
        "revalidation_disposition": "CONFIRMED_UNCHANGED",
        "strong_model_allowed": strong,
        "allowed_artifact_granularity": "FULL_TRAJECTORY_DEV_VISIBLE",
        "row_sha256": "f" * 64,
    }
    return {
        "revalidation_sha256": "1" * 64,
        "rows": [row],
    }


def test_rebinding_uses_sidecar_and_keeps_future_ids_null() -> None:
    result = build_trajectory_rebinding_manifest(
        bundle=_bundle(),
        pi1_identity=_identity(),
        task_access=_access(),
    )

    assert result["revalidation_status"] == (
        "VALIDATED_FOR_ANALYZER_EVIDENCE"
    )
    assert result["analyzer_run_id"] is None
    assert result["candidate_repair_ids"] == []
    assert result["training_sample_ids"] == []
    assert len(result["manifest_sha256"]) == 64


def test_rebinding_rejects_summary_only_bundle() -> None:
    with pytest.raises(ValueError, match="bundle-local access"):
        build_trajectory_rebinding_manifest(
            bundle=_bundle("SELECT_SUMMARY_ONLY"),
            pi1_identity=_identity(),
            task_access=_access(),
        )


def test_rebinding_rejects_checkpoint_mismatch() -> None:
    identity = _identity()
    identity["checkpoint_instance_id"] = "P4-R1-Q2-BAD-TRAIN31"
    with pytest.raises(ValueError, match="checkpoint"):
        build_trajectory_rebinding_manifest(
            bundle=_bundle(),
            pi1_identity=identity,
            task_access=_access(),
        )

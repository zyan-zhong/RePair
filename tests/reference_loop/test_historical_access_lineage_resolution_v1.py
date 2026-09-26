from __future__ import annotations

from pathlib import Path

from pchsi.reference_loop.historical_rebinding import (
    build_historical_trajectory_rebinding_manifest,
)
from pchsi.reference_loop.types import (
    BudgetCounters,
    NormalizedPolicyCall,
    NormalizedTrace,
    ValidatedAttemptBundle,
)


def test_historical_rebinding_uses_registered_access_row_sha_not_legacy_task_id(
) -> None:
    budget = BudgetCounters(0, 0, 0, 0, 0)
    bundle = ValidatedAttemptBundle(
        bundle_root=Path("/tmp/source"),
        episode={
            "task_id": "alfworld_train_0000",
            "gamefile_sha256": "a" * 64,
            "seed": 17,
        },
        policy_calls=(
            NormalizedPolicyCall(
                0, 0, "req", "goal", "prompt", "obs", ("look",), "{}",
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

    identity = {
        "schema_id": "PI1_REFERENCE_IDENTITY_V1",
        "logical_policy_id": "P4-R1-Q2-BAD",
        "checkpoint_instance_id": "P4-R1-Q2-BAD-TRAIN17",
        "identity_sha256": "e" * 64,
    }

    # Historical source authority has no episode task_id; revalidation therefore
    # carries task_gamefile_group_id in the task_id compatibility field.
    access = {
        "revalidation_sha256": "f" * 64,
        "rows": [
            {
                "task_id": "1" * 64,
                "task_gamefile_group_id": "1" * 64,
                "gamefile_sha256": "a" * 64,
                "row_sha256": "2" * 64,
                "revalidation_disposition": "CONFIRMED_UNCHANGED",
                "strong_model_allowed": True,
                "allowed_artifact_granularity": (
                    "FULL_TRAJECTORY_DEV_VISIBLE"
                ),
            }
        ],
    }

    lineage = {
        "bridge_sha256": "3" * 64,
        "rows": [
            {
                "attempt_bundle_sha256": "d" * 64,
                "episode_semantic_sha256": "c" * 64,
                "task_id": "alfworld_train_0000",
                "gamefile_sha256": "a" * 64,
                "logical_policy_id": "P4-R1-Q2-BAD",
                "checkpoint_instance_id": "P4-R1-Q2-BAD-TRAIN17",
                "task_access_row_sha256": "2" * 64,
                "row_sha256": "4" * 64,
            }
        ],
    }

    result = build_historical_trajectory_rebinding_manifest(
        bundle=bundle,
        pi1_identity=identity,
        task_access=access,
        lineage_bridge=lineage,
    )

    assert result["task_access_row_sha256"] == "2" * 64
    assert result["task_id"] == "alfworld_train_0000"
    assert result["revalidation_status"] == "VALIDATED_FOR_ANALYZER_EVIDENCE"

from __future__ import annotations

import pytest

from pchsi.reference_loop.historical_bridge import (
    _approval_index,
    _find_access_by_gamefile,
)


def test_access_bridge_resolves_unique_gamefile_sha() -> None:
    artifact = {
        "rows": [
            {
                "gamefile_sha256": "a" * 64,
                "revalidation_disposition": "CONFIRMED_UNCHANGED",
                "existing_access_class": "TRAIN_MEMORY_SOURCE",
                "strong_model_allowed": True,
                "allowed_artifact_granularity": (
                    "FULL_TRAJECTORY_DEV_VISIBLE"
                ),
                "row_sha256": "b" * 64,
            }
        ]
    }
    row = _find_access_by_gamefile(
        artifact,
        gamefile_sha256="a" * 64,
    )
    assert row["existing_access_class"] == "TRAIN_MEMORY_SOURCE"


def test_access_bridge_rejects_ambiguous_gamefile_sha() -> None:
    row = {
        "gamefile_sha256": "a" * 64,
        "revalidation_disposition": "CONFIRMED_UNCHANGED",
        "existing_access_class": "TRAIN_MEMORY_SOURCE",
        "strong_model_allowed": True,
        "allowed_artifact_granularity": "FULL_TRAJECTORY_DEV_VISIBLE",
        "row_sha256": "b" * 64,
    }
    with pytest.raises(ValueError, match="exactly one"):
        _find_access_by_gamefile(
            {"rows": [row, dict(row)]},
            gamefile_sha256="a" * 64,
        )


def test_human_approval_requires_exact_train17_source_condition() -> None:
    value = {
        "schema_id": "FAILURE_MEMORY_HUMAN_REGISTRATION_APPROVAL_V1",
        "schema_version": 1,
        "approval_token": "HUMAN_FAILURE_MEMORY_REGISTRATION_APPROVED_V1",
        "reviewer_decision": "APPROVED",
        "decisions": [
            {
                "source_attempt_id": f"attempt-{index}",
                "attempt_bundle_sha256": str(index) * 64,
                "source_condition": "P4-R1-Q2-BAD-TRAIN17",
            }
            for index in (1, 2, 3)
        ],
    }
    observed = _approval_index(value)
    assert len(observed) == 3

    value["decisions"][1]["source_condition"] = "P4-R1-Q2-BAD-TRAIN31"
    with pytest.raises(ValueError, match="lineage"):
        _approval_index(value)

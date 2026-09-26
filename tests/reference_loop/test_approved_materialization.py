from __future__ import annotations

import pytest

from pchsi.reference_loop.approved_materialization import (
    _selected_candidate,
    _selected_scalar,
)


def test_approval_selection_must_bind_review_candidates() -> None:
    review = {
        "artifact_slots": {
            "adapter_artifact": {
                "candidates": [
                    {"candidate_id": "candidate-1"}
                ]
            }
        },
        "scalar_slots": {
            "training_seed": {
                "candidates": [17]
            }
        },
    }
    approval = {
        "artifact_selections": {
            "adapter_artifact": "candidate-1"
        },
        "scalar_selections": {
            "training_seed": 17
        },
    }

    assert _selected_candidate(
        review,
        approval,
        slot="adapter_artifact",
    )["candidate_id"] == "candidate-1"
    assert _selected_scalar(
        review,
        approval,
        slot="training_seed",
    ) == 17

    approval["artifact_selections"]["adapter_artifact"] = "wrong"
    with pytest.raises(ValueError, match="not uniquely present"):
        _selected_candidate(
            review,
            approval,
            slot="adapter_artifact",
        )

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_contract_is_review_only() -> None:
    value = json.loads(
        (
            ROOT
            / "config/"
            "ROUND_PRETRAINING_HANDOFF_BUILD_CONTRACT_V1.json"
        ).read_text(encoding="utf-8")
    )
    assert value["build_status"] == "REVIEW_ONLY"
    assert value["formal_training_authorized"] is False
    assert value["training_execution_count"] == 0
    assert value["current_training_budget"] == {
        "data_seed": 17,
        "diagnostic_only": True,
        "epochs": 1,
        "optimizer_steps": 3,
        "promotion_eligible": False,
        "row_count": 12,
        "target_loss_tokens": 151,
        "training_seed": 17,
    }


def test_authorization_candidate_is_not_preapproved() -> None:
    source = (
        ROOT / "handoff/handoff_builder.py"
    ).read_text(encoding="utf-8")
    assert '"authorization_status": "NOT_AUTHORIZED"' in source
    assert '"formal_training_authorized": False' in source

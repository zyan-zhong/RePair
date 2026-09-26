from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_embedded_review_freeze_root_reproduces() -> None:
    review = json.loads(
        (
            ROOT
            / "authorities/"
            "ROUND_GENERIC_TRAINING_STAGE_V2_1_REVIEW_MANIFEST.json"
        ).read_text(encoding="utf-8")
    )
    binding = json.loads(
        (
            ROOT
            / "authorities/"
            "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_BINDING_V1.json"
        ).read_text(encoding="utf-8")
    )

    def find(suffix: str) -> str:
        values = [
            row["sha256"]
            for row in review["files"]
            if row["path"].endswith(suffix)
        ]
        assert len(values) == 1
        return values[0]

    payload = {
        "files": review["files"],
        "stage_binding_sha256": (
            binding["training_stage_binding_domain_sha256"]
        ),
        "training_contract_file_sha256": find(
            "ROUND_LOCAL_TRAINING_CONTRACT_V1.json"
        ),
        "sample_order_file_sha256": find(
            "ROUND_SAMPLE_ORDER_MANIFEST_V1.json"
        ),
        "runtime_adapter_sha256": find(
            "frozen_formal_train_peft.py"
        ),
    }
    observed = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert observed == review["runner_freeze_root_sha256"]
    assert observed == (
        binding["reviewed_training_stage_freeze_root_sha256"]
    )


def test_review_does_not_authorize_training_or_model_load() -> None:
    review = json.loads(
        (
            ROOT
            / "authorities/"
            "ROUND_GENERIC_TRAINING_STAGE_V2_1_REVIEW_MANIFEST.json"
        ).read_text(encoding="utf-8")
    )
    assert review["training_execution_authorized"] is False
    assert review["training_execution_count"] == 0
    assert review["model_load_count"] == 0

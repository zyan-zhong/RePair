from __future__ import annotations

import json
from pathlib import Path

import pytest

from pchsi.round_control.local_analyzer_training_adapter import (
    AdapterContractError,
    load_native_records,
    select_longest_record,
)


def _row(ordinal: int, source_sha: str, stage_id: str = "L-A0"):
    input_ids = [1, 2, 3, 4]
    labels = [-100, -100, 3, 4]
    return {
        "schema_id": "LOCAL_ANALYZER_BOOTSTRAP_TRAINER_NATIVE_ROW_V1",
        "schema_version": 1,
        "ordinal": ordinal,
        "source_identity": {
            "source_example_sha256": source_sha,
            "role": "ANALYZER",
            "stage_id": stage_id,
            "scientific_unit_id": f"unit-{ordinal}",
        },
        "tokenization": {
            "input_ids": input_ids,
            "labels": labels,
            "sequence_token_count": 4,
            "prompt_token_count": 2,
            "response_loss_token_count": 2,
        },
    }


def test_select_longest_record_prefers_length_then_case_id():
    rows = (
        {
            "case_id": "a",
            "tokenization": {"sequence_token_count": 4},
        },
        {
            "case_id": "b",
            "tokenization": {"sequence_token_count": 6},
        },
    )
    assert select_longest_record(rows)["case_id"] == "b"


def test_adapter_uses_source_example_identity_not_unique_source_state(tmp_path: Path):
    rows = [
        _row(0, "a" * 64, "L-A0"),
        _row(1, "b" * 64, "L-A1"),
    ]
    data = tmp_path / "data.jsonl"
    data.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    import hashlib

    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    manifest = {
        "schema_id": "LOCAL_ANALYZER_BOOTSTRAP_TRAINER_NATIVE_MANIFEST_V1",
        "row_count": 144,
        "trained_region": "ASSISTANT_COMPLETION_SUFFIX_ONLY",
        "prompt_label_value": -100,
        "packing": False,
        "truncation": False,
        "dataset_sha256": digest,
        "response_loss_token_count_total": 4,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    # Denominator protection intentionally rejects this tiny synthetic corpus.
    with pytest.raises(AdapterContractError, match="Analyzer native population drift"):
        load_native_records(
            dataset_path=data,
            manifest_path=manifest_path,
        )

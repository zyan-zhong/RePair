from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

from pchsi.evaluation.canonical_evidence import strict_json_loads


SCRIPT = Path(__file__).parents[2] / "scripts/memory/run_memory_live_cell_executor_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("_fm_final_executor_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_finalizer_writes_exact_live_cell_artifact_set(tmp_path: Path) -> None:
    module = _load()
    output = tmp_path / "cell"
    manifest = {
        "manifest_sha256": "a" * 64,
        "stage": "STAGE_1B_FROZEN_POLICY_FM0_FM3",
    }
    row = {
        "cell_id": "b" * 64,
        "comparison_group_id": "g",
        "condition": "FM0_NO_MEMORY",
        "round_index": None,
        "split": "TRAIN_RETRIEVAL_DEV",
        "task_id": "task",
        "task_family": "family",
        "snapshot_sha256": "c" * 64,
    }
    module._finalize_five_files(
        output=output,
        manifest=manifest,
        row=row,
        success=False,
        memory_exposed=False,
        correct_memory_exposure=False,
        wrong_memory_exposure=False,
        unsafe_memory_exposure=False,
        harm_observed=False,
        abstained=True,
        old_failure_disposition="UNCERTAIN",
        model_calls=1,
        environment_steps=0,
        memory_tokens=0,
        prompt_tokens=100,
        latency_ms=1,
        policy_payload=None,
        analyzer_payload={},
        researcher_payload={
            "heldout_aggregate_metrics": {},
            "train_side_records": [],
        },
    )
    observed = sorted(path.name for path in output.iterdir())
    assert observed == sorted([
        "CELL_SCIENTIFIC_RESULT_V1.json",
        "CELL_TERMINAL_RECEIPT_V1.json",
        "POLICY_MEMORY_PACK_V1.json",
        "ANALYZER_MEMORY_PACK_V1.json",
        "RESEARCHER_MEMORY_PACK_V1.json",
    ])
    result = strict_json_loads(
        (output / "CELL_SCIENTIFIC_RESULT_V1.json").read_bytes()
    )
    assert result["cell_id"] == row["cell_id"]
    assert result["memory_exposed"] is False
    for role, name in module.ROLE_FILENAMES.items():
        path = output / name
        pack = strict_json_loads(path.read_bytes())
        assert pack["role"] == role.upper()
        assert (
            result["role_pack_sha256s"][role]
            == hashlib.sha256(path.read_bytes()).hexdigest()
        )


def test_domain_self_hash_changes_when_payload_changes() -> None:
    module = _load()
    value = {"schema_id": "X", "value": 1, "hash": "0" * 64}
    first = module._dsha("X", value, "hash")
    value["value"] = 2
    second = module._dsha("X", value, "hash")
    assert first != second

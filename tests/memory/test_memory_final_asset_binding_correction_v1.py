from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

from pchsi.evaluation.canonical_evidence import canonical_json_bytes


SCRIPT = (
    Path(__file__).parents[2]
    / "scripts/memory/build_memory_final_live_inputs_v1.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "_fm_final_input_builder_asset_test",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _snapshot_value(snapshot_sha: str) -> dict[str, object]:
    return {
        "schema_id": "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V2",
        "schema_version": 2,
        "snapshot_sha256": snapshot_sha,
        "package_a_sealed_head": "a" * 40,
        "historical_package_a_snapshot_sha256": "b" * 64,
        "token_budget_contract_sha256": "c" * 64,
        "source_materialization_manifest_sha256": "d" * 64,
        "access_policy": "SAME_TASK_DEV_ALLOWED",
        "effect_authority": "UNTESTED",
        "previous_package_a_exposure": "NOT_EXPOSED_PACKAGE_A",
        "tokenizer_id": "test",
        "tokenizer_revision": "test",
        "single_record_hard_ceiling": 1,
        "library_total_hard_ceiling": 3,
        "max_record_count": 3,
        "members": [
            {
                "memory_lineage_id": "e" * 64,
                "record_version": 1,
                "governed_record_sha256": "f" * 64,
                "retrieval_key_sha256": "1" * 64,
                "fm1_sha256": "2" * 64,
                "fm1_build_disposition": "ELIGIBLE",
                "fm2_sha256": "3" * 64,
                "fm2_build_disposition": "ELIGIBLE",
                "relative_directory": "members/test",
            }
        ],
    }


def test_active_snapshot_resolution_uses_reserved_snapshot_json(
    tmp_path: Path,
) -> None:
    module = _load()
    snapshot_sha = "8" * 64
    snapshot = _snapshot_value(snapshot_sha)

    (tmp_path / "snapshot.json").write_bytes(
        canonical_json_bytes(snapshot)
    )

    (tmp_path / "snapshot_files.json").write_bytes(
        canonical_json_bytes(
            {
                "schema_id": "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_FILES_V2",
                "schema_version": 2,
                "snapshot_sha256": snapshot_sha,
                "files": [],
            }
        )
    )

    resolved = module._resolve_active_snapshot_manifest_v1(
        active_snapshot_dir=tmp_path,
        expected_snapshot_sha256=snapshot_sha,
    )
    assert resolved == tmp_path / "snapshot.json"


def test_active_snapshot_resolution_rejects_wrong_semantic_sha(
    tmp_path: Path,
) -> None:
    module = _load()
    (tmp_path / "snapshot.json").write_bytes(
        canonical_json_bytes(_snapshot_value("7" * 64))
    )

    with pytest.raises(
        SystemExit,
        match="ACTIVE_SNAPSHOT_MANIFEST_SHA_MISMATCH",
    ):
        module._resolve_active_snapshot_manifest_v1(
            active_snapshot_dir=tmp_path,
            expected_snapshot_sha256="8" * 64,
        )


def test_active_snapshot_resolution_rejects_wrong_schema(
    tmp_path: Path,
) -> None:
    module = _load()
    (tmp_path / "snapshot.json").write_bytes(
        canonical_json_bytes(
            {
                "schema_id": "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_FILES_V2",
                "schema_version": 2,
                "snapshot_sha256": "8" * 64,
                "files": [],
            }
        )
    )

    with pytest.raises(
        SystemExit,
        match="ACTIVE_SNAPSHOT_MANIFEST_SCHEMA",
    ):
        module._resolve_active_snapshot_manifest_v1(
            active_snapshot_dir=tmp_path,
            expected_snapshot_sha256="8" * 64,
        )

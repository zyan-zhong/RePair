from __future__ import annotations

import importlib.util
from pathlib import Path

from pchsi.memory.dev_descriptive_snapshot_v2 import (
    MemoryDevDescriptiveSnapshotV2,
    audit_calibrated_snapshot_v2,
)


def _helpers():
    path = Path(
        "tests/memory/package_b_direct_test_helpers.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_token_budget_snapshot_v2_helpers",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_snapshot_v2_binds_historical_snapshot_and_token_contract(tmp_path):
    final, snapshot, contract, _, _ = (
        _helpers().published_snapshot(tmp_path)
    )

    rebuilt = audit_calibrated_snapshot_v2(
        snapshot_directory=final,
        expected_snapshot_sha256=snapshot.snapshot_sha256,
    )

    assert rebuilt == snapshot
    assert snapshot.schema_id == (
        "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V2"
    )
    assert snapshot.historical_package_a_snapshot_sha256 == (
        "e" * 64
    )
    assert snapshot.token_budget_contract_sha256 == (
        contract.contract_sha256
    )
    assert snapshot.single_record_hard_ceiling == 640
    assert snapshot.library_total_hard_ceiling == 768
    assert len(snapshot.members) == 1


def test_snapshot_v2_contains_no_fm3(tmp_path):
    final, snapshot, _, _, _ = (
        _helpers().published_snapshot(tmp_path)
    )

    assert not any(
        path.name.startswith("fm3")
        for path in final.rglob("*")
        if path.is_file()
    )

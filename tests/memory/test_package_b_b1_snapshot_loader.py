from __future__ import annotations

from pathlib import Path
import importlib.util

import pytest

from pchsi.memory.dev_snapshot_loader import (
    FM1AvailabilityV1,
    FM2AvailabilityV1,
    load_calibrated_dev_snapshot_v2,
)

def _helpers():
    path = Path(
        "tests/memory/package_b_direct_test_helpers.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_package_b_direct_helpers_b1",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_b1_loads_exact_calibrated_snapshot_and_availability(tmp_path):
    final, snapshot, contract, contract_path, _ = (
        _helpers().published_snapshot(tmp_path)
    )

    loaded = load_calibrated_dev_snapshot_v2(
        snapshot_directory=final,
        expected_snapshot_sha256=snapshot.snapshot_sha256,
        token_budget_contract_path=contract_path,
        expected_token_budget_contract_sha256=contract.contract_sha256,
    )

    assert loaded.snapshot == snapshot
    assert len(loaded.members) == 1
    assert (
        loaded.members[0].fm1_availability
        is FM1AvailabilityV1.FM1_ELIGIBLE
    )
    assert (
        loaded.members[0].fm2_availability
        is FM2AvailabilityV1.FM2_ELIGIBLE
    )


def test_b1_rejects_latest_and_symlink_snapshot(tmp_path):
    final, snapshot, contract, contract_path, _ = (
        _helpers().published_snapshot(tmp_path)
    )

    latest = tmp_path / "latest"
    latest.symlink_to(final, target_is_directory=True)

    with pytest.raises(ValueError):
        load_calibrated_dev_snapshot_v2(
            snapshot_directory=latest,
            expected_snapshot_sha256=snapshot.snapshot_sha256,
            token_budget_contract_path=contract_path,
            expected_token_budget_contract_sha256=contract.contract_sha256,
        )


def test_b1_rehashes_member_files(tmp_path):
    final, snapshot, contract, contract_path, _ = (
        _helpers().published_snapshot(tmp_path)
    )

    member_dir = next(
        path
        for path in (final / "members").iterdir()
        if path.is_dir()
    )
    fm2 = member_dir / "fm2.json"
    fm2.write_bytes(fm2.read_bytes() + b" ")

    with pytest.raises(ValueError):
        load_calibrated_dev_snapshot_v2(
            snapshot_directory=final,
            expected_snapshot_sha256=snapshot.snapshot_sha256,
            token_budget_contract_path=contract_path,
            expected_token_budget_contract_sha256=contract.contract_sha256,
        )

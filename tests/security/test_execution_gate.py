from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def run_orchestrator(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()

    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        str(SRC_ROOT)
        if not existing_pythonpath
        else os.pathsep.join(
            (
                str(SRC_ROOT),
                existing_pythonpath,
            )
        )
    )

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pchsi.security.orchestrator",
            *arguments,
        ],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        text=True,
        capture_output=True,
    )


def test_python_describe_is_nonexecuting() -> None:
    result = run_orchestrator("--describe")

    assert result.returncode == 0, result.stderr
    assert "S1_COLLECTOR_BACKEND_PROBE_V1" in result.stdout
    assert "BACKEND_PROBE_EXECUTION=NOT_APPROVED" in result.stdout


def test_python_execute_is_closed() -> None:
    result = run_orchestrator("--execute")

    assert result.returncode != 0
    assert "PCHSI_EXECUTION_NOT_APPROVED" in result.stderr


def test_repository_approval_path_cannot_open_gate(tmp_path: Path) -> None:
    fake_approval = tmp_path / "approval.json"
    fake_approval.write_text(
        '{"decision":"BACKEND_PROBE_EXECUTION_APPROVED"}\n',
        encoding="utf-8",
    )

    result = run_orchestrator(
        "--execute",
        "--approval-path",
        str(fake_approval),
    )

    assert result.returncode != 0
    assert "PCHSI_EXECUTION_NOT_APPROVED" in result.stderr
# ---------------------------------------------------------------------------
# Task 11: dataset-bound execution records remain validation-only
# ---------------------------------------------------------------------------

import pytest

from pchsi.security.dataset_identity import DatasetIdentity
from pchsi.security.execution_gate import (
    BackendProbeExecutionRecord,
    validate_backend_probe_execution_record,
)


def _task11_dataset() -> DatasetIdentity:
    return DatasetIdentity(
        dataset_version="json_2.1.1",
        logical_root_id="ALFWORLD_DATASET_LOGICAL_ROOT_V1",
        train_present=True,
        valid_seen_present=True,
        valid_unseen_present=True,
        legacy_manifest_exact_file_sha256="a" * 64,
        input_contract_sha256="b" * 64,
        resolved_device=1,
        resolved_inode=2,
        resolved_mount_id=3,
        filesystem_type="ceph",
    )


def _task11_record(**overrides: object) -> BackendProbeExecutionRecord:
    values: dict[str, object] = {
        "design_commit": "c" * 40,
        "launcher_sha256": "d" * 64,
        "runtime_manifest_sha256": "e" * 64,
        "bootstrap_filter_sha256": "f" * 64,
        "collector_filter_sha256": "0" * 64,
        "sealed_source_manifest_sha256": "1" * 64,
        "p7_profile_id": "S1_P7_SYSCALL_CASE_V1",
        "p7_profile_sha256": "2" * 64,
        "p15_profile_id": "S1_P15_RLIMIT_ATTRIBUTION_V1",
        "p15_profile_sha256": "3" * 64,
        "p18_profile_id": "S1_P18_LANDLOCK_ATTRIBUTION_V1",
        "p18_profile_sha256": "4" * 64,
        "p20_profile_id": "S1_P20_CLEANUP_V1",
        "p20_profile_sha256": "5" * 64,
        "dataset_identity": _task11_dataset(),
        "external_execution_decision_reference": (
            "external://security-board/decision-001"
        ),
    }
    values.update(overrides)
    return BackendProbeExecutionRecord(**values)  # type: ignore[arg-type]


def test_dataset_bound_execution_record_is_exact() -> None:
    record = _task11_record()
    validate_backend_probe_execution_record(record, record)

    with pytest.raises(ValueError):
        validate_backend_probe_execution_record(
            _task11_record(launcher_sha256="6" * 64),
            record,
        )


@pytest.mark.parametrize(
    "reference",
    [
        "",
        "BACKEND_PROBE_EXECUTION_APPROVED",
        "file:///tmp/approval.json",
        "external://repository/approval-label",
    ],
)
def test_repository_only_execution_labels_are_rejected(
    reference: str,
) -> None:
    with pytest.raises(ValueError):
        _task11_record(
            external_execution_decision_reference=reference,
        )

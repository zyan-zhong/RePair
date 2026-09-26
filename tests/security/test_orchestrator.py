from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
RUNNER = REPO_ROOT / "scripts" / "security" / "run_backend_probe.py"


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        str(SRC_ROOT)
        if not existing
        else os.pathsep.join((str(SRC_ROOT), existing))
    )
    return environment


def test_backend_runner_describe_is_dry() -> None:
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--describe"],
        cwd=REPO_ROOT,
        env=_environment(),
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert '"dataset_version":"json_2.1.1"' in result.stdout
    assert '"status":"NOT_APPROVED"' in result.stdout


def test_backend_runner_execute_remains_closed(tmp_path: Path) -> None:
    record = tmp_path / "repository-approval.json"
    record.write_text(
        '{"decision":"BACKEND_PROBE_EXECUTION_APPROVED"}\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--execute",
            "--execution-record",
            str(record),
        ],
        cwd=REPO_ROOT,
        env=_environment(),
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 77
    assert "PCHSI_EXECUTION_NOT_APPROVED" in result.stderr


def test_runner_has_no_default_dataset_inference() -> None:
    source = RUNNER.read_text(encoding="utf-8")

    assert "ALFWORLD_DATA" not in source
    assert "expanduser" not in source
    assert "default_dataset" not in source
# ---------------------------------------------------------------------------
# Task 12: compile-only P1-P20 manifest corpus
# ---------------------------------------------------------------------------

import hashlib as _task12_hashlib
import json as _task12_json


def test_probe_manifest_corpus_is_complete_and_nonexecuting() -> None:
    root = REPO_ROOT / "configs" / "security" / "probes"
    manifests = [
        _task12_json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(root.glob("*.json"))
    ]

    expected_ids = {
        *(f"P{index:02d}" for index in range(1, 15)),
        "P15_CONTROL",
        "P15_LIMITED",
        "P16",
        "P17",
        "P18_BASELINE",
        "P18_RESTRICTED",
        "P19",
        "P20",
    }

    assert {manifest["probe_id"] for manifest in manifests} == expected_ids

    for manifest in manifests:
        assert set(manifest) == {
            "schema_version",
            "probe_id",
            "payload_id",
            "payload_sha256",
            "profile_id",
            "expected_normalized_outcome",
            "timeout_seconds",
            "permitted_side_effects",
            "forbidden_side_effects",
            "execution_status",
        }
        assert manifest["execution_status"] == "NOT_APPROVED"
        assert manifest["permitted_side_effects"] == []
        assert manifest["forbidden_side_effects"]

        source = (
            REPO_ROOT
            / "native"
            / "s1_backend_probe"
            / "probes"
            / (manifest["probe_id"].lower() + ".c")
        )
        assert source.is_file()
        assert (
            _task12_hashlib.sha256(source.read_bytes()).hexdigest()
            == manifest["payload_sha256"]
        )


def test_probe_payload_target_is_compile_only() -> None:
    makefile = (
        REPO_ROOT
        / "native"
        / "s1_backend_probe"
        / "Makefile"
    ).read_text(encoding="utf-8")

    assert "probe-payloads:" in makefile
    assert "PROBE_PAYLOAD_OBJECTS" in makefile
    assert "-c \"$<\" -o \"$@\"" in makefile
    assert "run-probe-payloads" not in makefile

from __future__ import annotations

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
NATIVE_DIR = REPO_ROOT / "native" / "s1_backend_probe"
BINARY = NATIVE_DIR / "build" / "pchsi-s1-backend-probe"


def test_native_binary_describes_backend() -> None:
    assert BINARY.is_file(), f"native binary missing: {BINARY}"

    result = subprocess.run(
        [str(BINARY), "--describe"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert "S1_COLLECTOR_BACKEND_PROBE_V1" in result.stdout
    assert "ROOTLESS_RESTRICTED_ROOT_NAMESPACE_SANDBOX_V2" in result.stdout
    assert "BACKEND_PROBE_EXECUTION=NOT_APPROVED" in result.stdout


def test_native_execute_is_closed() -> None:
    assert BINARY.is_file(), f"native binary missing: {BINARY}"

    result = subprocess.run(
        [str(BINARY), "--execute"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "PCHSI_EXECUTION_NOT_APPROVED" in result.stderr


def test_native_version_is_stable() -> None:
    assert BINARY.is_file(), f"native binary missing: {BINARY}"

    result = subprocess.run(
        [str(BINARY), "--version"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert (
        "design_commit="
        "6199510501841ce3ce3d9ca6da87d70f10d4c787"
    ) in result.stdout

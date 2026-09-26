from __future__ import annotations

from pathlib import Path
import re
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
NATIVE_ROOT = REPO_ROOT / "native" / "s1_backend_probe"
INCLUDE_ROOT = NATIVE_ROOT / "include"
SOURCE_ROOT = NATIVE_ROOT / "src"
TEST_ROOT = NATIVE_ROOT / "tests"
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"


def _compile_and_run(
    tmp_path: Path,
    *,
    test_name: str,
    source_name: str,
) -> None:
    binary = tmp_path / Path(test_name).stem
    result = subprocess.run(
        [
            "/usr/bin/cc",
            "-D_GNU_SOURCE",
            "-std=c17",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wpedantic",
            "-Wconversion",
            "-Wshadow",
            f"-I{INCLUDE_ROOT}",
            str(TEST_ROOT / test_name),
            str(SOURCE_ROOT / source_name),
            "-o",
            str(binary),
        ],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr

    run = subprocess.run(
        [str(binary)],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert run.returncode == 0, run.stderr


def test_native_security_state(tmp_path: Path) -> None:
    _compile_and_run(
        tmp_path,
        test_name="test_security_state.c",
        source_name="security_state.c",
    )


def test_native_resource_contract(tmp_path: Path) -> None:
    _compile_and_run(
        tmp_path,
        test_name="test_resource_contract.c",
        source_name="resource_contract.c",
    )


def test_frozen_resource_constants_are_present() -> None:
    header = (
        INCLUDE_ROOT / "pchsi_s1" / "resource_contract.h"
    ).read_text(encoding="utf-8")

    required = {
        "PCHSI_RLIMIT_CPU_SOFT": "2",
        "PCHSI_RLIMIT_CPU_HARD": "3",
        "PCHSI_RLIMIT_AS_BYTES": "268435456",
        "PCHSI_RLIMIT_FSIZE_BYTES": "4194304",
        "PCHSI_RLIMIT_NOFILE_COUNT": "32",
        "PCHSI_RLIMIT_NPROC_COUNT": "1",
        "PCHSI_RLIMIT_CORE_BYTES": "0",
        "PCHSI_PROBE_WALL_TIMEOUT_SECONDS": "10",
        "PCHSI_P7_CASE_TIMEOUT_SECONDS": "2",
        "PCHSI_P7_AGGREGATE_BASE_SECONDS": "30",
        "PCHSI_P7_AGGREGATE_PER_CASE_SECONDS": "3",
    }

    for name, value in required.items():
        assert re.search(
            rf"#define\s+{name}\s+UINT64_C\({value}\)",
            header,
        ), name


def test_proc_status_fixtures_are_distinct() -> None:
    secure = (
        FIXTURE_ROOT / "proc_status_secure.txt"
    ).read_text(encoding="utf-8")
    leaked = (
        FIXTURE_ROOT / "proc_status_capability_leak.txt"
    ).read_text(encoding="utf-8")

    assert "CapEff:\t0000000000000000" in secure
    assert "CapEff:\t0000000000000001" in leaked
    assert "NoNewPrivs:\t1" in secure
    assert "NoNewPrivs:\t1" in leaked

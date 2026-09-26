from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
NATIVE_ROOT = REPO_ROOT / "native" / "s1_backend_probe"
INCLUDE_ROOT = NATIVE_ROOT / "include"
TEST_ROOT = NATIVE_ROOT / "tests"
SOURCE_ROOT = NATIVE_ROOT / "src"


_NATIVE_CASES: dict[str, tuple[str, ...]] = {
    "test_system_ops.c": (
        "linux_compat.c",
        "linux_mount_uapi.c",
        "linux_openat2_uapi.c",
        "real_system_ops.c",
    ),
    "test_source_resolution.c": (
        "source_resolution.c",
    ),
    "test_mount_contract.c": (
        "mount_contract.c",
    ),
    "test_source_copy.c": (
        "source_copy.c",
        "sha256.c",
    ),
    "test_security_state.c": (
        "security_state.c",
    ),
    "test_resource_contract.c": (
        "resource_contract.c",
    ),
    "test_seccomp_filter.c": (
        "seccomp_filter.c",
    ),
}


def _available_cases() -> tuple[tuple[Path, tuple[Path, ...]], ...]:
    return tuple(
        (
            TEST_ROOT / test_name,
            tuple(
                SOURCE_ROOT / source_name
                for source_name in source_names
            ),
        )
        for test_name, source_names in _NATIVE_CASES.items()
    )


def test_declared_native_unit_cases_are_not_silently_filtered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_test_root = tmp_path / "tests"
    missing_source_root = tmp_path / "src"
    missing_test_root.mkdir()
    missing_source_root.mkdir()

    module = sys.modules[__name__]

    monkeypatch.setattr(
        module,
        "TEST_ROOT",
        missing_test_root,
    )
    monkeypatch.setattr(
        module,
        "SOURCE_ROOT",
        missing_source_root,
    )

    cases = _available_cases()

    assert len(cases) == len(_NATIVE_CASES)
    assert {
        test_path.name
        for test_path, _ in cases
    } == set(_NATIVE_CASES)


def test_declared_native_unit_case_files_exist() -> None:
    cases = _available_cases()

    missing_tests = [
        str(test_path)
        for test_path, _ in cases
        if not test_path.is_file()
    ]
    missing_sources = [
        str(source_path)
        for _, source_paths in cases
        for source_path in source_paths
        if not source_path.is_file()
    ]

    assert missing_tests == [], missing_tests
    assert missing_sources == [], missing_sources
    assert len(cases) == len(_NATIVE_CASES)


@pytest.mark.parametrize(
    ("test_path", "source_paths"),
    _available_cases(),
    ids=lambda value: (
        value.name
        if isinstance(value, Path)
        else None
    ),
)
def test_native_fake_only_unit_case(
    test_path: Path,
    source_paths: tuple[Path, ...],
    tmp_path: Path,
) -> None:
    assert test_path.is_file(), f"native test missing: {test_path}"

    missing_sources = [
        str(path)
        for path in source_paths
        if not path.is_file()
    ]
    assert missing_sources == [], missing_sources

    binary = tmp_path / test_path.stem

    compile_result = subprocess.run(
        [
            "/usr/bin/cc",
            "-D_GNU_SOURCE",
            "-std=c17",
            "-O2",
            "-g",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wpedantic",
            "-Wconversion",
            "-Wshadow",
            "-Werror=date-time",
            "-fstack-protector-strong",
            "-fPIE",
            f"-I{INCLUDE_ROOT}",
            str(test_path),
            *(str(path) for path in source_paths),
            "-pie",
            "-Wl,-z,relro",
            "-Wl,-z,now",
            "-Wl,-z,noexecstack",
            "-o",
            str(binary),
        ],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert compile_result.returncode == 0, compile_result.stderr

    run_result = subprocess.run(
        [str(binary)],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert run_result.returncode == 0, run_result.stderr


# ---------------------------------------------------------------------------
# Task 13: pure supervisor/namespace plan unit binaries
# ---------------------------------------------------------------------------


def test_pure_supervisor_and_namespace_plans(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    native = repo_root / "native" / "s1_backend_probe"

    cases = (
        (
            "test-supervisor",
            native / "tests" / "test_supervisor.c",
            native / "src" / "supervisor.c",
        ),
        (
            "test-namespace-init",
            native / "tests" / "test_namespace_init.c",
            native / "src" / "namespace_init.c",
        ),
    )

    for name, test_source, implementation in cases:
        assert test_source.is_file(), f"native test missing: {test_source}"
        assert implementation.is_file(), (
            f"native implementation missing: {implementation}"
        )

        binary = tmp_path / name
        result = subprocess.run(
            [
                "/usr/bin/cc",
                "-D_GNU_SOURCE",
                "-std=c17",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Wpedantic",
                "-Wconversion",
                "-Wshadow",
                "-I",
                str(native / "include"),
                str(test_source),
                str(implementation),
                "-o",
                str(binary),
            ],
            cwd=repo_root,
            check=False,
            text=True,
            capture_output=True,
        )

        assert result.returncode == 0, result.stderr

        run = subprocess.run(
            [str(binary)],
            check=False,
            text=True,
            capture_output=True,
        )

        assert run.returncode == 0, run.stderr

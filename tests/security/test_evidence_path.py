from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from pchsi.security.evidence_path import (
    EvidencePathError,
    EvidencePathFailure,
    validate_evidence_path,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
VECTOR_PATH = REPO_ROOT / "tests" / "security" / "fixtures" / "path_vectors.json"
NATIVE_DIR = REPO_ROOT / "native" / "s1_backend_probe"


def _expanded_path(value: str) -> bytes:
    if value == "SEGMENT_129":
        return b"a" * 129
    if value == "PATH_513":
        return (b"a" * 128) + b"/" + (b"b" * 384)
    return value.encode("utf-8")


@pytest.mark.parametrize(
    "vector",
    json.loads(VECTOR_PATH.read_text(encoding="utf-8")),
    ids=lambda vector: vector["id"],
)
def test_path_vectors(vector: dict[str, object]) -> None:
    path = _expanded_path(str(vector["path"]))

    if vector["valid"]:
        assert validate_evidence_path(path) == tuple(
            str(value).encode("ascii") for value in vector["segments"]
        )
        return

    with pytest.raises(EvidencePathError) as error:
        validate_evidence_path(path)

    assert error.value.code is EvidencePathFailure[str(vector["code"])]


def test_path_parser_is_byte_exact_and_case_sensitive() -> None:
    assert validate_evidence_path(b"A/a") == (b"A", b"a")


def test_path_parser_rejects_non_bytes() -> None:
    with pytest.raises(TypeError, match="raw_path must be bytes"):
        validate_evidence_path("a")  # type: ignore[arg-type]


def test_native_path_and_evidence_unit_binary(tmp_path: Path) -> None:
    binary = tmp_path / "test-evidence"

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
            str(NATIVE_DIR / "include"),
            str(NATIVE_DIR / "src" / "path_contract.c"),
            str(NATIVE_DIR / "src" / "evidence.c"),
            str(NATIVE_DIR / "tests" / "test_path_contract.c"),
            str(NATIVE_DIR / "tests" / "test_evidence.c"),
            "-o",
            str(binary),
        ],
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
    assert "native evidence tests passed" in run.stdout

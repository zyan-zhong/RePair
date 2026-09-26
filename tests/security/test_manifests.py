from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

import pytest

from pchsi.security.manifests import (
    detached_sha256_record_bytes,
    exact_file_sha256,
    semantic_projection_sha256,
    verify_detached_sha256_record,
    write_canonical_manifest,
    write_detached_sha256_record,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
NATIVE_DIR = REPO_ROOT / "native" / "s1_backend_probe"


def test_semantic_projection_ignores_explicit_local_fields() -> None:
    left = {
        "schema_version": "runtime_manifest_v1",
        "payload": {"b": 2, "a": 1},
        "generated_at_utc": "2026-08-05T00:00:00Z",
        "absolute_path": "/host/a",
    }
    right = {
        "absolute_path": "/different/host",
        "payload": {"a": 1, "b": 2},
        "schema_version": "runtime_manifest_v1",
        "generated_at_utc": "2026-08-06T00:00:00Z",
    }

    excluded = {
        "absolute_path",
        "generated_at_utc",
    }

    assert semantic_projection_sha256(
        left,
        excluded_top_level_fields=excluded,
    ) == semantic_projection_sha256(
        right,
        excluded_top_level_fields=excluded,
    )


def test_exact_file_hash_changes_when_bytes_change(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_bytes(b'{"a":1}\n')
    first = exact_file_sha256(path)

    path.write_bytes(b'{ "a": 1 }\n')
    second = exact_file_sha256(path)

    assert first != second
    assert first == hashlib.sha256(b'{"a":1}\n').hexdigest()
    assert second == hashlib.sha256(b'{ "a": 1 }\n').hexdigest()


def test_write_canonical_manifest_returns_distinct_identities(
    tmp_path: Path,
) -> None:
    path = tmp_path / "manifest.json"
    value = {
        "schema_version": "runtime_manifest_v1",
        "payload": {"z": 2, "a": 1},
        "generated_at_utc": "2026-08-05T00:00:00Z",
    }

    hashes = write_canonical_manifest(
        path,
        value,
        excluded_top_level_fields={"generated_at_utc"},
    )

    assert path.read_bytes() == (
        b'{"generated_at_utc":"2026-08-05T00:00:00Z",'
        b'"payload":{"a":1,"z":2},'
        b'"schema_version":"runtime_manifest_v1"}\n'
    )
    assert hashes.exact_file_sha256 == exact_file_sha256(path)
    assert hashes.semantic_projection_sha256 != hashes.exact_file_sha256
    assert hashes.exact_file_sha256.encode("ascii") not in path.read_bytes()


def test_manifest_rejects_self_exact_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pchsi.security import manifests

    embedded = "a" * 64
    monkeypatch.setattr(
        manifests,
        "sha256_hex",
        lambda data: embedded,
    )

    with pytest.raises(
        ValueError,
        match="must not contain its own exact-file",
    ):
        manifests.write_canonical_manifest(
            tmp_path / "manifest.json",
            {
                "exact_file_sha256": embedded,
            },
        )


def test_detached_record_is_deterministic_and_verifiable(
    tmp_path: Path,
) -> None:
    target = tmp_path / "semantic_evidence.json"
    record = tmp_path / "semantic_evidence.json.sha256"
    target.write_bytes(b'{"status":"pass"}\n')

    identity = write_detached_sha256_record(
        target_path=target,
        record_path=record,
    )

    expected_target = hashlib.sha256(
        target.read_bytes()
    ).hexdigest()
    expected_record = (
        expected_target
        + "  semantic_evidence.json\n"
    ).encode("utf-8")

    assert identity.target_sha256 == expected_target
    assert identity.record_bytes == expected_record
    assert identity.record_sha256 == hashlib.sha256(
        expected_record
    ).hexdigest()
    assert record.read_bytes() == expected_record
    assert verify_detached_sha256_record(
        target_path=target,
        record_path=record,
    )


def test_detached_record_detects_target_mutation(
    tmp_path: Path,
) -> None:
    target = tmp_path / "local_evidence.json"
    record = tmp_path / "local_evidence.json.sha256"
    target.write_bytes(b"first\n")

    write_detached_sha256_record(
        target_path=target,
        record_path=record,
    )
    target.write_bytes(b"second\n")

    assert not verify_detached_sha256_record(
        target_path=target,
        record_path=record,
    )


@pytest.mark.parametrize(
    "display_name",
    [
        "",
        ".",
        "..",
        "../escape",
        "nested/path",
        "line\nbreak",
        "line\rbreak",
    ],
)
def test_detached_record_rejects_unsafe_names(
    display_name: str,
) -> None:
    with pytest.raises(ValueError):
        detached_sha256_record_bytes(
            target_sha256="a" * 64,
            display_name=display_name,
        )


def test_native_sha256_known_answers(tmp_path: Path) -> None:
    binary = tmp_path / "test-sha256"

    compile_result = subprocess.run(
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
            "-I",
            str(NATIVE_DIR / "include"),
            str(NATIVE_DIR / "src" / "sha256.c"),
            str(NATIVE_DIR / "tests" / "test_sha256.c"),
            "-o",
            str(binary),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert compile_result.returncode == 0, compile_result.stderr

    run_result = subprocess.run(
        [str(binary)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert run_result.returncode == 0, run_result.stderr
    assert "native sha256 tests passed" in run_result.stdout
# ---------------------------------------------------------------------------
# Task 14: runtime manifest canonicality and closure generation
# ---------------------------------------------------------------------------

import importlib.util as _task14_importlib
import os as _task14_os
import sys as _task14_sys

from pchsi.security.manifests import RuntimeManifest


def _task14_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "security"
        / "build_runtime_closure.py"
    )
    spec = _task14_importlib.spec_from_file_location(
        "task14_runtime_closure",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = _task14_importlib.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_manifest_is_deterministic_and_sorted() -> None:
    manifest = RuntimeManifest(
        schema_version=1,
        status="candidate_pending_static_and_semantic_review",
        python_sha256="a" * 64,
        bootstrap_sha256="b" * 64,
        interpreter_path="/lib64/ld-linux-x86-64.so.2",
        needed_libraries=("libc.so.6", "libm.so.6"),
        source_date_epoch=0,
        toolchain="GNU readelf",
    )

    assert manifest.canonical_bytes() == manifest.canonical_bytes()
    assert b"candidate_pending_static_and_semantic_review" in (
        manifest.canonical_bytes()
    )


def test_runtime_closure_uses_readelf_and_rejects_symlink(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _task14_module()
    bootstrap = tmp_path / "bootstrap.py"
    bootstrap.write_text("print('bootstrap')\n", encoding="utf-8")
    output = tmp_path / "out"

    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")

    manifest = module.build_runtime_manifest(
        python_binary=Path(_task14_sys.executable).resolve(strict=True),
        bootstrap_source=bootstrap,
        output_root=output,
    )

    assert manifest.status == (
        "candidate_pending_static_and_semantic_review"
    )
    assert (output / "runtime_manifest.json").is_file()

    symlink = tmp_path / "python-link"
    symlink.symlink_to(Path(_task14_sys.executable))

    with pytest.raises(ValueError, match="symlink"):
        module.build_runtime_manifest(
            python_binary=symlink,
            bootstrap_source=bootstrap,
            output_root=tmp_path / "bad",
        )

    source = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "security"
        / "build_runtime_closure.py"
    ).read_text(encoding="utf-8")

    assert "/usr/bin/readelf" in source
    assert "time.time" not in source
    assert "datetime.now" not in source

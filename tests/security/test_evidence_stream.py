from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import subprocess

import pytest

from pchsi.security.evidence_stream import (
    MAGIC,
    MAX_CONTENT_BYTES,
    EvidenceEntry,
    EvidenceStreamError,
    EvidenceStreamFailure,
    decode_evidence_stream,
    encode_evidence_stream,
)


U64 = struct.Struct(">Q")


def _raw_stream(
    index_entries: list[tuple[bytes, bytes, int | None]],
    payload_entries: list[tuple[bytes, bytes, int | None]] | None = None,
) -> bytes:
    index = bytearray()
    for path, content, content_size_override in index_entries:
        index.extend(U64.pack(len(path)))
        index.extend(path)
        index.extend(
            U64.pack(
                len(content)
                if content_size_override is None
                else content_size_override
            )
        )
        index.extend(hashlib.sha256(content).digest())

    payload = bytearray()
    for path, content, content_size_override in (
        index_entries if payload_entries is None else payload_entries
    ):
        payload.extend(U64.pack(len(path)))
        payload.extend(path)
        payload.extend(
            U64.pack(
                len(content)
                if content_size_override is None
                else content_size_override
            )
        )
        payload.extend(content)

    return (
        MAGIC
        + U64.pack(len(index_entries))
        + U64.pack(len(index))
        + bytes(index)
        + bytes(payload)
    )


def test_round_trip_is_sorted_and_deterministic() -> None:
    entries = (
        EvidenceEntry(path=b"z.txt", content=b"z"),
        EvidenceEntry(path=b"logs/a.txt", content=b"a"),
    )

    encoded = encode_evidence_stream(entries)

    assert encoded == encode_evidence_stream(reversed(entries))
    assert decode_evidence_stream(encoded) == (
        EvidenceEntry(path=b"logs/a.txt", content=b"a"),
        EvidenceEntry(path=b"z.txt", content=b"z"),
    )


def test_empty_stream_round_trip() -> None:
    assert decode_evidence_stream(encode_evidence_stream(())) == ()


def test_duplicate_paths_are_rejected() -> None:
    with pytest.raises(EvidenceStreamError) as error:
        encode_evidence_stream(
            (
                EvidenceEntry(path=b"a", content=b"1"),
                EvidenceEntry(path=b"a", content=b"2"),
            )
        )
    assert error.value.code is EvidenceStreamFailure.DUPLICATE_PATH


def test_unsorted_index_is_rejected() -> None:
    raw = _raw_stream([(b"z", b"z", None), (b"a", b"a", None)])
    with pytest.raises(EvidenceStreamError) as error:
        decode_evidence_stream(raw)
    assert error.value.code is EvidenceStreamFailure.INDEX_NOT_SORTED


def test_path_payload_mismatch_is_rejected() -> None:
    raw = _raw_stream(
        [(b"a", b"x", None)],
        payload_entries=[(b"b", b"x", None)],
    )
    with pytest.raises(EvidenceStreamError) as error:
        decode_evidence_stream(raw)
    assert error.value.code is EvidenceStreamFailure.PATH_MISMATCH


def test_content_length_mismatch_is_rejected() -> None:
    raw = _raw_stream(
        [(b"a", b"x", None)],
        payload_entries=[(b"a", b"x", 2)],
    )
    with pytest.raises(EvidenceStreamError) as error:
        decode_evidence_stream(raw)
    assert error.value.code is EvidenceStreamFailure.CONTENT_LENGTH_MISMATCH


def test_content_hash_mismatch_is_rejected() -> None:
    raw = bytearray(_raw_stream([(b"a", b"x", None)]))
    raw[-1] = ord("y")
    with pytest.raises(EvidenceStreamError) as error:
        decode_evidence_stream(bytes(raw))
    assert error.value.code is EvidenceStreamFailure.CONTENT_SHA256_MISMATCH


@pytest.mark.parametrize("cut", [0, 1, len(MAGIC), len(MAGIC) + 7])
def test_truncated_header_is_rejected(cut: int) -> None:
    encoded = encode_evidence_stream((EvidenceEntry(path=b"a", content=b"x"),))
    with pytest.raises(EvidenceStreamError) as error:
        decode_evidence_stream(encoded[:cut])
    assert error.value.code in {
        EvidenceStreamFailure.INVALID_MAGIC,
        EvidenceStreamFailure.TRUNCATED,
    }


def test_trailing_bytes_are_rejected() -> None:
    encoded = encode_evidence_stream((EvidenceEntry(path=b"a", content=b"x"),))
    with pytest.raises(EvidenceStreamError) as error:
        decode_evidence_stream(encoded + b"x")
    assert error.value.code is EvidenceStreamFailure.TRAILING_DATA


def test_oversized_content_is_rejected_at_entry_creation() -> None:
    with pytest.raises(EvidenceStreamError) as error:
        EvidenceEntry(path=b"a", content=b"x" * (MAX_CONTENT_BYTES + 1))
    assert error.value.code is EvidenceStreamFailure.CONTENT_TOO_LARGE


def test_non_bytes_inputs_are_rejected() -> None:
    with pytest.raises(TypeError, match="data must be bytes"):
        decode_evidence_stream(bytearray())  # type: ignore[arg-type]

def test_native_evidence_tree_and_publication_contract(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    native = repo_root / "native" / "s1_backend_probe"
    binary = tmp_path / "test-evidence-tree"

    result = subprocess.run(
        [
            "/usr/bin/cc",
            "-D_GNU_SOURCE",
            "-DPCHSI_EVIDENCE_TREE_TESTS",
            "-std=c17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wpedantic",
            "-Wconversion",
            "-Wshadow",
            "-I",
            str(native / "include"),
            str(native / "src" / "path_contract.c"),
            str(native / "src" / "evidence.c"),
            str(native / "src" / "strict_json.c"),
            str(native / "src" / "sha256.c"),
            str(native / "src" / "linux_compat.c"),
            str(native / "src" / "linux_mount_uapi.c"),
            str(native / "src" / "linux_openat2_uapi.c"),
            str(native / "src" / "real_system_ops.c"),
            str(native / "tests" / "test_path_contract.c"),
            str(native / "tests" / "test_evidence.c"),
            "-pie",
            "-Wl,-z,relro",
            "-Wl,-z,now",
            "-Wl,-z,noexecstack",
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
        cwd=repo_root,
        check=False,
        text=True,
        capture_output=True,
    )

    assert run.returncode == 0, run.stderr
    assert "native evidence tests passed" in run.stdout

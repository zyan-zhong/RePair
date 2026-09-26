"""Deterministic framing for S1 trusted evidence publication."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import struct
from typing import Final, Iterable

from .evidence_path import validate_evidence_path


MAGIC: Final[bytes] = b"PCHSI_EVIDENCE_STREAM_V1"
MAX_ENTRY_COUNT: Final[int] = 1024
MAX_INDEX_BYTES: Final[int] = 16 * 1024 * 1024
MAX_CONTENT_BYTES: Final[int] = 16 * 1024 * 1024
MAX_STREAM_BYTES: Final[int] = 64 * 1024 * 1024
_U64: Final[struct.Struct] = struct.Struct(">Q")


class EvidenceStreamFailure(str, Enum):
    INVALID_MAGIC = "INVALID_MAGIC"
    TRUNCATED = "TRUNCATED"
    TRAILING_DATA = "TRAILING_DATA"
    ENTRY_COUNT_EXCEEDED = "ENTRY_COUNT_EXCEEDED"
    INDEX_TOO_LARGE = "INDEX_TOO_LARGE"
    CONTENT_TOO_LARGE = "CONTENT_TOO_LARGE"
    STREAM_TOO_LARGE = "STREAM_TOO_LARGE"
    INVALID_PATH = "INVALID_PATH"
    DUPLICATE_PATH = "DUPLICATE_PATH"
    INDEX_NOT_SORTED = "INDEX_NOT_SORTED"
    INDEX_LENGTH_MISMATCH = "INDEX_LENGTH_MISMATCH"
    PATH_MISMATCH = "PATH_MISMATCH"
    CONTENT_LENGTH_MISMATCH = "CONTENT_LENGTH_MISMATCH"
    CONTENT_SHA256_MISMATCH = "CONTENT_SHA256_MISMATCH"


class EvidenceStreamError(ValueError):
    """Raised when evidence framing violates its frozen contract."""

    def __init__(self, code: EvidenceStreamFailure) -> None:
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True, slots=True)
class EvidenceEntry:
    path: bytes
    content: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.path, bytes):
            raise TypeError("path must be bytes")
        if not isinstance(self.content, bytes):
            raise TypeError("content must be bytes")
        validate_evidence_path(self.path)
        if len(self.content) > MAX_CONTENT_BYTES:
            raise EvidenceStreamError(EvidenceStreamFailure.CONTENT_TOO_LARGE)


@dataclass(frozen=True, slots=True)
class _IndexEntry:
    path: bytes
    content_size: int
    content_sha256: bytes


def _pack_u64(value: int) -> bytes:
    return _U64.pack(value)


def _read_exact(data: memoryview, offset: int, size: int) -> tuple[memoryview, int]:
    end = offset + size
    if end > len(data):
        raise EvidenceStreamError(EvidenceStreamFailure.TRUNCATED)
    return data[offset:end], end


def _read_u64(data: memoryview, offset: int) -> tuple[int, int]:
    raw, next_offset = _read_exact(data, offset, _U64.size)
    return _U64.unpack(raw)[0], next_offset


def _validated_sorted_entries(entries: Iterable[EvidenceEntry]) -> tuple[EvidenceEntry, ...]:
    materialized = tuple(entries)
    if len(materialized) > MAX_ENTRY_COUNT:
        raise EvidenceStreamError(EvidenceStreamFailure.ENTRY_COUNT_EXCEEDED)

    ordered = tuple(sorted(materialized, key=lambda entry: entry.path))
    for previous, current in zip(ordered, ordered[1:]):
        if previous.path == current.path:
            raise EvidenceStreamError(EvidenceStreamFailure.DUPLICATE_PATH)
    return ordered


def _encode_index(entries: tuple[EvidenceEntry, ...]) -> bytes:
    chunks: list[bytes] = []
    for entry in entries:
        digest = hashlib.sha256(entry.content).digest()
        chunks.extend(
            (
                _pack_u64(len(entry.path)),
                entry.path,
                _pack_u64(len(entry.content)),
                digest,
            )
        )
    index = b"".join(chunks)
    if len(index) > MAX_INDEX_BYTES:
        raise EvidenceStreamError(EvidenceStreamFailure.INDEX_TOO_LARGE)
    return index


def encode_evidence_stream(entries: Iterable[EvidenceEntry]) -> bytes:
    """Encode entries in canonical path order using big-endian u64 fields."""

    ordered = _validated_sorted_entries(entries)
    index = _encode_index(ordered)
    chunks: list[bytes] = [MAGIC, _pack_u64(len(ordered)), _pack_u64(len(index)), index]

    for entry in ordered:
        chunks.extend(
            (
                _pack_u64(len(entry.path)),
                entry.path,
                _pack_u64(len(entry.content)),
                entry.content,
            )
        )

    encoded = b"".join(chunks)
    if len(encoded) > MAX_STREAM_BYTES:
        raise EvidenceStreamError(EvidenceStreamFailure.STREAM_TOO_LARGE)
    return encoded


def _decode_index(index: memoryview, entry_count: int) -> tuple[_IndexEntry, ...]:
    entries: list[_IndexEntry] = []
    offset = 0

    for _ in range(entry_count):
        path_length, offset = _read_u64(index, offset)
        path_view, offset = _read_exact(index, offset, path_length)
        path = bytes(path_view)
        try:
            validate_evidence_path(path)
        except ValueError as error:
            raise EvidenceStreamError(EvidenceStreamFailure.INVALID_PATH) from error

        content_size, offset = _read_u64(index, offset)
        if content_size > MAX_CONTENT_BYTES:
            raise EvidenceStreamError(EvidenceStreamFailure.CONTENT_TOO_LARGE)
        digest_view, offset = _read_exact(index, offset, hashlib.sha256().digest_size)

        if entries:
            if path == entries[-1].path:
                raise EvidenceStreamError(EvidenceStreamFailure.DUPLICATE_PATH)
            if path < entries[-1].path:
                raise EvidenceStreamError(EvidenceStreamFailure.INDEX_NOT_SORTED)

        entries.append(
            _IndexEntry(
                path=path,
                content_size=content_size,
                content_sha256=bytes(digest_view),
            )
        )

    if offset != len(index):
        raise EvidenceStreamError(EvidenceStreamFailure.INDEX_LENGTH_MISMATCH)

    return tuple(entries)


def decode_evidence_stream(data: bytes) -> tuple[EvidenceEntry, ...]:
    """Decode and fully validate one evidence stream."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if len(data) > MAX_STREAM_BYTES:
        raise EvidenceStreamError(EvidenceStreamFailure.STREAM_TOO_LARGE)

    view = memoryview(data)
    offset = 0
    magic_view, offset = _read_exact(view, offset, len(MAGIC))
    if bytes(magic_view) != MAGIC:
        raise EvidenceStreamError(EvidenceStreamFailure.INVALID_MAGIC)

    entry_count, offset = _read_u64(view, offset)
    if entry_count > MAX_ENTRY_COUNT:
        raise EvidenceStreamError(EvidenceStreamFailure.ENTRY_COUNT_EXCEEDED)

    index_length, offset = _read_u64(view, offset)
    if index_length > MAX_INDEX_BYTES:
        raise EvidenceStreamError(EvidenceStreamFailure.INDEX_TOO_LARGE)

    index_view, offset = _read_exact(view, offset, index_length)
    index_entries = _decode_index(index_view, entry_count)

    decoded: list[EvidenceEntry] = []
    for indexed in index_entries:
        path_length, offset = _read_u64(view, offset)
        path_view, offset = _read_exact(view, offset, path_length)
        path = bytes(path_view)
        if path != indexed.path:
            raise EvidenceStreamError(EvidenceStreamFailure.PATH_MISMATCH)

        content_length, offset = _read_u64(view, offset)
        if content_length > MAX_CONTENT_BYTES:
            raise EvidenceStreamError(EvidenceStreamFailure.CONTENT_TOO_LARGE)
        if content_length != indexed.content_size:
            raise EvidenceStreamError(
                EvidenceStreamFailure.CONTENT_LENGTH_MISMATCH
            )

        content_view, offset = _read_exact(view, offset, content_length)
        content = bytes(content_view)
        if hashlib.sha256(content).digest() != indexed.content_sha256:
            raise EvidenceStreamError(
                EvidenceStreamFailure.CONTENT_SHA256_MISMATCH
            )

        decoded.append(EvidenceEntry(path=path, content=content))

    if offset != len(view):
        raise EvidenceStreamError(EvidenceStreamFailure.TRAILING_DATA)

    return tuple(decoded)

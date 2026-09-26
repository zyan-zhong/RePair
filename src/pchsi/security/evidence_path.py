"""Byte-exact evidence-path contract for S1 backend probe artifacts."""

from __future__ import annotations

from enum import Enum


MAX_EVIDENCE_PATH_BYTES = 512
MAX_EVIDENCE_SEGMENTS = 2
MAX_EVIDENCE_SEGMENT_BYTES = 128


class EvidencePathFailure(str, Enum):
    EMPTY = "EMPTY"
    TOO_LONG = "TOO_LONG"
    NON_ASCII = "NON_ASCII"
    ABSOLUTE = "ABSOLUTE"
    TOO_MANY_SEGMENTS = "TOO_MANY_SEGMENTS"
    EMPTY_SEGMENT = "EMPTY_SEGMENT"
    SEGMENT_TOO_LONG = "SEGMENT_TOO_LONG"
    INVALID_INITIAL_BYTE = "INVALID_INITIAL_BYTE"
    INVALID_SEGMENT_BYTE = "INVALID_SEGMENT_BYTE"


class EvidencePathError(ValueError):
    """Raised when an evidence path violates the frozen byte grammar."""

    def __init__(self, code: EvidencePathFailure) -> None:
        super().__init__(code.value)
        self.code = code


def _is_ascii_alnum(value: int) -> bool:
    return (
        ord("0") <= value <= ord("9")
        or ord("A") <= value <= ord("Z")
        or ord("a") <= value <= ord("z")
    )


def validate_evidence_path(raw_path: bytes) -> tuple[bytes, ...]:
    """Validate and split one evidence path without normalization.

    Grammar:
    - ASCII bytes only;
    - one or two slash-delimited segments;
    - each segment matches ``[A-Za-z0-9][A-Za-z0-9._-]{0,127}``;
    - byte-exact, case-sensitive and non-normalizing.
    """

    if not isinstance(raw_path, bytes):
        raise TypeError("raw_path must be bytes")

    if not raw_path:
        raise EvidencePathError(EvidencePathFailure.EMPTY)

    if len(raw_path) > MAX_EVIDENCE_PATH_BYTES:
        raise EvidencePathError(EvidencePathFailure.TOO_LONG)

    if any(value >= 0x80 for value in raw_path):
        raise EvidencePathError(EvidencePathFailure.NON_ASCII)

    if raw_path.startswith(b"/"):
        raise EvidencePathError(EvidencePathFailure.ABSOLUTE)

    segments = tuple(raw_path.split(b"/"))

    if any(not segment for segment in segments):
        raise EvidencePathError(EvidencePathFailure.EMPTY_SEGMENT)

    if len(segments) > MAX_EVIDENCE_SEGMENTS:
        raise EvidencePathError(EvidencePathFailure.TOO_MANY_SEGMENTS)

    for segment in segments:

        if len(segment) > MAX_EVIDENCE_SEGMENT_BYTES:
            raise EvidencePathError(EvidencePathFailure.SEGMENT_TOO_LONG)

        if not _is_ascii_alnum(segment[0]):
            raise EvidencePathError(EvidencePathFailure.INVALID_INITIAL_BYTE)

        for value in segment[1:]:
            if not (
                _is_ascii_alnum(value)
                or value in (ord("."), ord("_"), ord("-"))
            ):
                raise EvidencePathError(
                    EvidencePathFailure.INVALID_SEGMENT_BYTE
                )

    return segments

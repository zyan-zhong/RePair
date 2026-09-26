"""Normalization and publication contracts for S1 probe evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import signal
from typing import Final


__all__ = [
    "EXPECTED_PUBLISHED_EVIDENCE_NAMES",
    "ExpectedOutcome",
    "NormalizedOutcome",
    "NormalizedProbeOutcome",
    "RawProbeDiagnostic",
    "build_local_evidence_sidecar",
    "normalize_probe_outcome",
    "validate_local_evidence_sidecar",
    "validate_published_evidence_names",
]


EXPECTED_PUBLISHED_EVIDENCE_NAMES: Final[tuple[str, ...]] = (
    "local_evidence.json",
    "local_evidence.json.sha256",
    "semantic_evidence.json",
)


class ExpectedOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    SECCOMP_KILL = "SECCOMP_KILL"
    TIMEOUT = "TIMEOUT"


class NormalizedOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    SECCOMP_KILL = "SECCOMP_KILL"
    TIMEOUT = "TIMEOUT"
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"


@dataclass(frozen=True, slots=True)
class RawProbeDiagnostic:
    exit_code: int | None
    signal_number: int | None
    timed_out: bool
    infrastructure_error: str | None
    duration_microseconds: int

    def __post_init__(self) -> None:
        if self.exit_code is not None and (
            isinstance(self.exit_code, bool)
            or not isinstance(self.exit_code, int)
            or self.exit_code < 0
        ):
            raise ValueError(
                "exit_code must be a non-negative integer or None"
            )

        if self.signal_number is not None and (
            isinstance(self.signal_number, bool)
            or not isinstance(self.signal_number, int)
            or self.signal_number <= 0
        ):
            raise ValueError(
                "signal_number must be a positive integer or None"
            )

        if not isinstance(self.timed_out, bool):
            raise ValueError("timed_out must be a bool")

        if self.infrastructure_error is not None and (
            not isinstance(self.infrastructure_error, str)
            or not self.infrastructure_error
        ):
            raise ValueError(
                "infrastructure_error must be a non-empty string or None"
            )

        if (
            isinstance(self.duration_microseconds, bool)
            or not isinstance(self.duration_microseconds, int)
            or self.duration_microseconds < 0
        ):
            raise ValueError(
                "duration_microseconds must be non-negative"
            )

        terminal_indicators = sum(
            (
                self.exit_code is not None,
                self.signal_number is not None,
                self.timed_out,
                self.infrastructure_error is not None,
            )
        )

        if terminal_indicators != 1:
            raise ValueError(
                "exactly one terminal diagnostic must be present"
            )


@dataclass(frozen=True, slots=True)
class NormalizedProbeOutcome:
    expected: ExpectedOutcome
    observed: NormalizedOutcome
    status: str

    def __post_init__(self) -> None:
        if self.status not in {"PASS", "FAIL", "INVALID"}:
            raise ValueError("status must be PASS, FAIL or INVALID")


def normalize_probe_outcome(
    *,
    expected: ExpectedOutcome,
    raw: RawProbeDiagnostic,
) -> NormalizedProbeOutcome:
    """Normalize local process details without leaking them into semantics."""

    if raw.infrastructure_error is not None:
        observed = NormalizedOutcome.INFRASTRUCTURE_ERROR
        status = "INVALID"
    elif raw.timed_out:
        observed = NormalizedOutcome.TIMEOUT
        status = (
            "PASS"
            if expected is ExpectedOutcome.TIMEOUT
            else "FAIL"
        )
    elif raw.signal_number is not None:
        if raw.signal_number in {
            signal.SIGSYS,
            signal.SIGKILL,
        }:
            observed = NormalizedOutcome.SECCOMP_KILL
        else:
            observed = NormalizedOutcome.FAILURE

        status = (
            "PASS"
            if observed.value == expected.value
            else "FAIL"
        )
    elif raw.exit_code == 0:
        observed = NormalizedOutcome.SUCCESS
        status = (
            "PASS"
            if expected is ExpectedOutcome.SUCCESS
            else "FAIL"
        )
    else:
        observed = NormalizedOutcome.FAILURE
        status = (
            "PASS"
            if expected is ExpectedOutcome.FAILURE
            else "FAIL"
        )

    return NormalizedProbeOutcome(
        expected=expected,
        observed=observed,
        status=status,
    )


def validate_published_evidence_names(
    names: tuple[str, ...],
) -> tuple[str, ...]:
    """Require the exact three published evidence paths."""

    if not isinstance(names, tuple):
        raise ValueError("names must be a tuple")

    if tuple(sorted(names)) != EXPECTED_PUBLISHED_EVIDENCE_NAMES:
        raise ValueError(
            "published evidence names do not match the exact contract"
        )

    if len(set(names)) != len(names):
        raise ValueError("published evidence names contain duplicates")

    return names


def build_local_evidence_sidecar(
    local_evidence_bytes: bytes,
) -> bytes:
    """Build one detached sha256sum-style sidecar record."""

    if not isinstance(local_evidence_bytes, bytes):
        raise TypeError("local_evidence_bytes must be bytes")

    digest = hashlib.sha256(local_evidence_bytes).hexdigest()

    return (
        f"{digest}  local_evidence.json\n"
    ).encode("ascii")


def validate_local_evidence_sidecar(
    *,
    local_evidence_bytes: bytes,
    sidecar_bytes: bytes,
) -> None:
    """Validate the detached local-evidence hash record exactly."""

    if not isinstance(local_evidence_bytes, bytes):
        raise TypeError("local_evidence_bytes must be bytes")

    if not isinstance(sidecar_bytes, bytes):
        raise TypeError("sidecar_bytes must be bytes")

    expected = build_local_evidence_sidecar(
        local_evidence_bytes
    )

    if sidecar_bytes != expected:
        raise ValueError(
            "local evidence sidecar does not match exact content"
        )

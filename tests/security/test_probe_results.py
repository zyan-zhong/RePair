from __future__ import annotations

import signal

import pytest

from pchsi.security.probe_results import (
    EXPECTED_PUBLISHED_EVIDENCE_NAMES,
    ExpectedOutcome,
    NormalizedOutcome,
    RawProbeDiagnostic,
    build_local_evidence_sidecar,
    normalize_probe_outcome,
    validate_local_evidence_sidecar,
    validate_published_evidence_names,
)


def test_success_normalizes_to_pass() -> None:
    result = normalize_probe_outcome(
        expected=ExpectedOutcome.SUCCESS,
        raw=RawProbeDiagnostic(
            exit_code=0,
            signal_number=None,
            timed_out=False,
            infrastructure_error=None,
            duration_microseconds=10,
        ),
    )

    assert result.observed is NormalizedOutcome.SUCCESS
    assert result.status == "PASS"


def test_seccomp_signal_normalizes_without_exposing_signal() -> None:
    result = normalize_probe_outcome(
        expected=ExpectedOutcome.SECCOMP_KILL,
        raw=RawProbeDiagnostic(
            exit_code=None,
            signal_number=signal.SIGSYS,
            timed_out=False,
            infrastructure_error=None,
            duration_microseconds=10,
        ),
    )

    assert result.observed is NormalizedOutcome.SECCOMP_KILL
    assert result.status == "PASS"


def test_infrastructure_error_is_invalid_not_fail() -> None:
    result = normalize_probe_outcome(
        expected=ExpectedOutcome.SUCCESS,
        raw=RawProbeDiagnostic(
            exit_code=None,
            signal_number=None,
            timed_out=False,
            infrastructure_error="launcher",
            duration_microseconds=10,
        ),
    )

    assert result.observed is NormalizedOutcome.INFRASTRUCTURE_ERROR
    assert result.status == "INVALID"


def test_raw_diagnostic_requires_one_terminal_state() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        RawProbeDiagnostic(
            exit_code=0,
            signal_number=signal.SIGSYS,
            timed_out=False,
            infrastructure_error=None,
            duration_microseconds=10,
        )


def test_exact_published_names_are_required() -> None:
    assert validate_published_evidence_names(
        EXPECTED_PUBLISHED_EVIDENCE_NAMES
    ) == EXPECTED_PUBLISHED_EVIDENCE_NAMES

    with pytest.raises(ValueError, match="exact contract"):
        validate_published_evidence_names(
            (
                "local_evidence.json",
                "semantic_evidence.json",
            )
        )


def test_local_sidecar_round_trip() -> None:
    local = b'{"duration_microseconds":10}\n'
    sidecar = build_local_evidence_sidecar(local)

    validate_local_evidence_sidecar(
        local_evidence_bytes=local,
        sidecar_bytes=sidecar,
    )

    assert sidecar.endswith(
        b"  local_evidence.json\n"
    )


def test_local_sidecar_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="does not match"):
        validate_local_evidence_sidecar(
            local_evidence_bytes=b"{}\n",
            sidecar_bytes=(
                b"0" * 64
                + b"  local_evidence.json\n"
            ),
        )

"""Closed execution gate for the S1 backend-probe implementation phase."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn


EXECUTION_NOT_APPROVED_MARKER = "PCHSI_EXECUTION_NOT_APPROVED"


class ExecutionNotApprovedError(RuntimeError):
    """Raised whenever runtime probe execution is requested before approval."""


def require_execution_approval(
    *,
    approval_path: Path | None,
    expected_design_commit: str,
    expected_artifact_manifest_sha256: str | None,
) -> NoReturn:
    """Fail closed until the later dataset-bound execution gate exists."""

    del approval_path
    del expected_design_commit
    del expected_artifact_manifest_sha256

    raise ExecutionNotApprovedError(
        f"{EXECUTION_NOT_APPROVED_MARKER}: "
        "backend probe execution is not approved"
    )
# ---------------------------------------------------------------------------
# Task 11: dataset-bound execution record (validation only; gate remains shut)
# ---------------------------------------------------------------------------

from dataclasses import dataclass as _task11_dataclass
import re as _task11_re

from .dataset_identity import (
    DatasetIdentity as _Task11DatasetIdentity,
    validate_dataset_identity as _task11_validate_dataset_identity,
)


_TASK11_SHA256_RE = _task11_re.compile(r"^[0-9a-f]{64}$")
_TASK11_GIT_SHA_RE = _task11_re.compile(r"^[0-9a-f]{40}$")
_TASK11_PROFILE_IDS = frozenset({
    "S1_PRODUCTION_V1",
    "S1_P7_SYSCALL_CASE_V1",
    "S1_P15_RLIMIT_ATTRIBUTION_V1",
    "S1_P18_LANDLOCK_ATTRIBUTION_V1",
    "S1_P20_CLEANUP_V1",
})


def _task11_require_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or _TASK11_SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256")


@_task11_dataclass(frozen=True, slots=True)
class BackendProbeExecutionRecord:
    design_commit: str
    launcher_sha256: str
    runtime_manifest_sha256: str
    bootstrap_filter_sha256: str
    collector_filter_sha256: str
    sealed_source_manifest_sha256: str
    p7_profile_id: str
    p7_profile_sha256: str
    p15_profile_id: str
    p15_profile_sha256: str
    p18_profile_id: str
    p18_profile_sha256: str
    p20_profile_id: str
    p20_profile_sha256: str
    dataset_identity: _Task11DatasetIdentity
    external_execution_decision_reference: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.design_commit, str)
            or _TASK11_GIT_SHA_RE.fullmatch(self.design_commit) is None
        ):
            raise ValueError("design_commit must be a lowercase Git SHA")

        for name in (
            "launcher_sha256",
            "runtime_manifest_sha256",
            "bootstrap_filter_sha256",
            "collector_filter_sha256",
            "sealed_source_manifest_sha256",
            "p7_profile_sha256",
            "p15_profile_sha256",
            "p18_profile_sha256",
            "p20_profile_sha256",
        ):
            _task11_require_sha256(name, getattr(self, name))

        expected_profiles = {
            "p7_profile_id": "S1_P7_SYSCALL_CASE_V1",
            "p15_profile_id": "S1_P15_RLIMIT_ATTRIBUTION_V1",
            "p18_profile_id": "S1_P18_LANDLOCK_ATTRIBUTION_V1",
            "p20_profile_id": "S1_P20_CLEANUP_V1",
        }

        for name, required in expected_profiles.items():
            value = getattr(self, name)
            if value not in _TASK11_PROFILE_IDS or value != required:
                raise ValueError(f"{name} does not match the frozen profile")

        if not isinstance(self.dataset_identity, _Task11DatasetIdentity):
            raise ValueError("dataset_identity must be DatasetIdentity")

        reference = self.external_execution_decision_reference
        if (
            not isinstance(reference, str)
            or not reference.startswith("external://")
            or len(reference) <= len("external://")
            or "BACKEND_PROBE_EXECUTION_APPROVED" in reference
            or reference.startswith("external://repository/")
        ):
            raise ValueError(
                "external_execution_decision_reference must name an "
                "external, non-repository decision record"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "design_commit": self.design_commit,
            "launcher_sha256": self.launcher_sha256,
            "runtime_manifest_sha256": self.runtime_manifest_sha256,
            "bootstrap_filter_sha256": self.bootstrap_filter_sha256,
            "collector_filter_sha256": self.collector_filter_sha256,
            "sealed_source_manifest_sha256": (
                self.sealed_source_manifest_sha256
            ),
            "p7_profile_id": self.p7_profile_id,
            "p7_profile_sha256": self.p7_profile_sha256,
            "p15_profile_id": self.p15_profile_id,
            "p15_profile_sha256": self.p15_profile_sha256,
            "p18_profile_id": self.p18_profile_id,
            "p18_profile_sha256": self.p18_profile_sha256,
            "p20_profile_id": self.p20_profile_id,
            "p20_profile_sha256": self.p20_profile_sha256,
            "dataset_identity": self.dataset_identity.to_dict(),
            "external_execution_decision_reference": (
                self.external_execution_decision_reference
            ),
        }


def validate_backend_probe_execution_record(
    observed: BackendProbeExecutionRecord,
    expected: BackendProbeExecutionRecord,
) -> None:
    if not isinstance(observed, BackendProbeExecutionRecord):
        raise TypeError("observed must be BackendProbeExecutionRecord")
    if not isinstance(expected, BackendProbeExecutionRecord):
        raise TypeError("expected must be BackendProbeExecutionRecord")

    _task11_validate_dataset_identity(
        observed.dataset_identity,
        expected.dataset_identity,
    )

    if observed != expected:
        raise ValueError(
            "execution record does not match frozen external contract"
        )

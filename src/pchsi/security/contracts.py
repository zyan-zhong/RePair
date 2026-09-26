"""Immutable schema contracts for S1 backend-probe artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Final


__all__ = [
    "BootstrapContract",
    "BootstrapState",
    "LandlockPathRule",
    "LandlockPolicy",
    "LocalProbeDiagnostic",
    "ProbeEvidence",
    "ProbeProfileManifest",
    "RuntimeManifest",
    "SealedSourceManifest",
    "SeccompFilterManifest",
    "SemanticProbeResult",
]


_SHA256_RE: Final[re.Pattern[str]] = re.compile(
    r"^[0-9a-f]{64}$"
)
_IDENTIFIER_RE: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
)


def _require_nonempty(
    name: str,
    value: str,
) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{name} must be a non-empty string"
        )


def _require_identifier(
    name: str,
    value: str,
) -> None:
    if not isinstance(value, str) or _IDENTIFIER_RE.fullmatch(value) is None:
        raise ValueError(
            f"{name} must match the frozen identifier grammar"
        )


def _require_sha256(
    name: str,
    value: str | None,
    *,
    optional: bool = False,
) -> None:
    if value is None and optional:
        return

    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(
            f"{name} must be a lowercase SHA-256 hex digest"
        )


def _require_nonnegative_optional_int(
    name: str,
    value: int | None,
) -> None:
    if value is None:
        return

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"{name} must be a non-negative integer or None"
        )


@dataclass(frozen=True, slots=True)
class RuntimeManifest:
    schema_version: str
    python_binary_sha256: str
    stdlib_tree_semantics_sha256: str
    dynamic_linker_sha256: str
    shared_library_manifest_sha256: str

    def __post_init__(self) -> None:
        _require_identifier(
            "schema_version",
            self.schema_version,
        )

        for name in (
            "python_binary_sha256",
            "stdlib_tree_semantics_sha256",
            "dynamic_linker_sha256",
            "shared_library_manifest_sha256",
        ):
            _require_sha256(
                name,
                getattr(self, name),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "python_binary_sha256": self.python_binary_sha256,
            "stdlib_tree_semantics_sha256": (
                self.stdlib_tree_semantics_sha256
            ),
            "dynamic_linker_sha256": self.dynamic_linker_sha256,
            "shared_library_manifest_sha256": (
                self.shared_library_manifest_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class SealedSourceManifest:
    schema_version: str
    bootstrap_source_sha256: str
    collector_source_sha256: str
    source_copy_contract_sha256: str

    def __post_init__(self) -> None:
        _require_identifier(
            "schema_version",
            self.schema_version,
        )

        for name in (
            "bootstrap_source_sha256",
            "collector_source_sha256",
            "source_copy_contract_sha256",
        ):
            _require_sha256(
                name,
                getattr(self, name),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "bootstrap_source_sha256": self.bootstrap_source_sha256,
            "collector_source_sha256": self.collector_source_sha256,
            "source_copy_contract_sha256": (
                self.source_copy_contract_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class SeccompFilterManifest:
    schema_version: str
    architecture: str
    policy_sha256: str
    program_sha256: str

    def __post_init__(self) -> None:
        _require_identifier(
            "schema_version",
            self.schema_version,
        )
        _require_identifier(
            "architecture",
            self.architecture,
        )
        _require_sha256(
            "policy_sha256",
            self.policy_sha256,
        )
        _require_sha256(
            "program_sha256",
            self.program_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "architecture": self.architecture,
            "policy_sha256": self.policy_sha256,
            "program_sha256": self.program_sha256,
        }


@dataclass(frozen=True, slots=True)
class ProbeProfileManifest:
    schema_version: str
    profile_id: str
    contract_sha256: str
    seccomp_filter_sha256: str

    def __post_init__(self) -> None:
        _require_identifier(
            "schema_version",
            self.schema_version,
        )
        _require_identifier(
            "profile_id",
            self.profile_id,
        )
        _require_sha256(
            "contract_sha256",
            self.contract_sha256,
        )
        _require_sha256(
            "seccomp_filter_sha256",
            self.seccomp_filter_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "contract_sha256": self.contract_sha256,
            "seccomp_filter_sha256": self.seccomp_filter_sha256,
        }


@dataclass(frozen=True, slots=True)
class SemanticProbeResult:
    probe_id: str
    payload_sha256: str
    expected_outcome: str
    observed_outcome: str
    status: str
    failure_code: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(
            "probe_id",
            self.probe_id,
        )
        _require_sha256(
            "payload_sha256",
            self.payload_sha256,
        )

        for name in (
            "expected_outcome",
            "observed_outcome",
            "status",
        ):
            _require_identifier(
                name,
                getattr(self, name),
            )

        if self.failure_code is not None:
            _require_identifier(
                "failure_code",
                self.failure_code,
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "probe_id": self.probe_id,
            "payload_sha256": self.payload_sha256,
            "expected_outcome": self.expected_outcome,
            "observed_outcome": self.observed_outcome,
            "status": self.status,
            "failure_code": self.failure_code,
        }


@dataclass(frozen=True, slots=True)
class LocalProbeDiagnostic:
    probe_id: str
    raw_errno: int | None = None
    raw_signal: int | None = None
    duration_microseconds: int | None = None
    log_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(
            "probe_id",
            self.probe_id,
        )

        for name in (
            "raw_errno",
            "raw_signal",
            "duration_microseconds",
        ):
            _require_nonnegative_optional_int(
                name,
                getattr(self, name),
            )

        _require_sha256(
            "log_sha256",
            self.log_sha256,
            optional=True,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "probe_id": self.probe_id,
            "raw_errno": self.raw_errno,
            "raw_signal": self.raw_signal,
            "duration_microseconds": self.duration_microseconds,
            "log_sha256": self.log_sha256,
        }


@dataclass(frozen=True, slots=True)
class ProbeEvidence:
    schema_version: str
    semantic_evidence_sha256: str
    semantic_results: tuple[SemanticProbeResult, ...]
    local_diagnostics: tuple[LocalProbeDiagnostic, ...]

    def __post_init__(self) -> None:
        _require_identifier(
            "schema_version",
            self.schema_version,
        )
        _require_sha256(
            "semantic_evidence_sha256",
            self.semantic_evidence_sha256,
        )

        if not isinstance(self.semantic_results, tuple):
            raise ValueError(
                "semantic_results must be a tuple"
            )

        if not isinstance(self.local_diagnostics, tuple):
            raise ValueError(
                "local_diagnostics must be a tuple"
            )

        semantic_ids = tuple(
            result.probe_id
            for result in self.semantic_results
        )
        local_ids = tuple(
            diagnostic.probe_id
            for diagnostic in self.local_diagnostics
        )

        if len(set(semantic_ids)) != len(semantic_ids):
            raise ValueError(
                "semantic_results contain duplicate probe_id"
            )

        if len(set(local_ids)) != len(local_ids):
            raise ValueError(
                "local_diagnostics contain duplicate probe_id"
            )

        if set(semantic_ids) != set(local_ids):
            raise ValueError(
                "semantic and local probe ID sets must match"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "semantic_evidence_sha256": (
                self.semantic_evidence_sha256
            ),
            "semantic_results": [
                result.to_dict()
                for result in self.semantic_results
            ],
            "local_diagnostics": [
                diagnostic.to_dict()
                for diagnostic in self.local_diagnostics
            ],
        }
def _require_bool(
    name: str,
    value: bool,
) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a bool")


def _require_nonnegative_int(
    name: str,
    value: int,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _require_int_tuple(
    name: str,
    value: tuple[int, ...],
) -> None:
    if not isinstance(value, tuple):
        raise ValueError(f"{name} must be a tuple")

    if any(
        isinstance(item, bool) or not isinstance(item, int) or item < 0
        for item in value
    ):
        raise ValueError(
            f"{name} must contain only non-negative integers"
        )

    if tuple(sorted(set(value))) != value:
        raise ValueError(
            f"{name} must be sorted and contain no duplicates"
        )


@dataclass(frozen=True, slots=True)
class LandlockPathRule:
    path: str
    access_fs: int

    def __post_init__(self) -> None:
        _require_nonempty("path", self.path)

        if (
            not self.path.startswith("/")
            or "\x00" in self.path
            or "//" in self.path
            or "/../" in f"{self.path}/"
            or "/./" in f"{self.path}/"
        ):
            raise ValueError(
                "path must be an absolute normalized sandbox path"
            )

        if (
            isinstance(self.access_fs, bool)
            or not isinstance(self.access_fs, int)
            or self.access_fs <= 0
        ):
            raise ValueError("access_fs must be a positive integer")

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "access_fs": self.access_fs,
        }


@dataclass(frozen=True, slots=True)
class LandlockPolicy:
    profile_id: str
    minimum_abi: int
    handled_access_fs: int
    rules: tuple[LandlockPathRule, ...]
    profile_sha256: str

    def __post_init__(self) -> None:
        _require_identifier("profile_id", self.profile_id)
        _require_nonnegative_int("minimum_abi", self.minimum_abi)

        if self.minimum_abi == 0:
            raise ValueError("minimum_abi must be greater than zero")

        if (
            isinstance(self.handled_access_fs, bool)
            or not isinstance(self.handled_access_fs, int)
            or self.handled_access_fs <= 0
        ):
            raise ValueError(
                "handled_access_fs must be a positive integer"
            )

        if not isinstance(self.rules, tuple) or not self.rules:
            raise ValueError("rules must be a non-empty tuple")

        paths = tuple(rule.path for rule in self.rules)

        if len(set(paths)) != len(paths):
            raise ValueError("rules contain duplicate paths")

        _require_sha256("profile_sha256", self.profile_sha256)

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "minimum_abi": self.minimum_abi,
            "handled_access_fs": self.handled_access_fs,
            "rules": [rule.to_dict() for rule in self.rules],
            "profile_sha256": self.profile_sha256,
        }


@dataclass(frozen=True, slots=True)
class BootstrapState:
    runtime_manifest_sha256: str
    bootstrap_filter_sha256: str
    collector_filter_sha256: str
    landlock_abi: int | None
    landlock_enforced: bool
    mount_contract_verified: bool
    procfs_contract_verified: bool
    capability_contract_verified: bool
    fd_contract_verified: bool
    environment_contract_verified: bool
    inherited_fds: tuple[int, ...]

    def __post_init__(self) -> None:
        for name in (
            "runtime_manifest_sha256",
            "bootstrap_filter_sha256",
            "collector_filter_sha256",
        ):
            _require_sha256(name, getattr(self, name))

        if self.landlock_abi is not None:
            _require_nonnegative_int(
                "landlock_abi",
                self.landlock_abi,
            )

            if self.landlock_abi == 0:
                raise ValueError(
                    "landlock_abi must be greater than zero"
                )

        for name in (
            "landlock_enforced",
            "mount_contract_verified",
            "procfs_contract_verified",
            "capability_contract_verified",
            "fd_contract_verified",
            "environment_contract_verified",
        ):
            _require_bool(name, getattr(self, name))

        _require_int_tuple("inherited_fds", self.inherited_fds)


@dataclass(frozen=True, slots=True)
class BootstrapContract:
    runtime_manifest_sha256: str
    bootstrap_filter_sha256: str
    collector_filter_sha256: str
    minimum_landlock_abi: int
    require_landlock_when_supported: bool
    allowed_fds: tuple[int, ...]

    def __post_init__(self) -> None:
        for name in (
            "runtime_manifest_sha256",
            "bootstrap_filter_sha256",
            "collector_filter_sha256",
        ):
            _require_sha256(name, getattr(self, name))

        _require_nonnegative_int(
            "minimum_landlock_abi",
            self.minimum_landlock_abi,
        )

        if self.minimum_landlock_abi == 0:
            raise ValueError(
                "minimum_landlock_abi must be greater than zero"
            )

        _require_bool(
            "require_landlock_when_supported",
            self.require_landlock_when_supported,
        )
        _require_int_tuple("allowed_fds", self.allowed_fds)

    def to_dict(self) -> dict[str, object]:
        return {
            "runtime_manifest_sha256": self.runtime_manifest_sha256,
            "bootstrap_filter_sha256": self.bootstrap_filter_sha256,
            "collector_filter_sha256": self.collector_filter_sha256,
            "minimum_landlock_abi": self.minimum_landlock_abi,
            "require_landlock_when_supported": (
                self.require_landlock_when_supported
            ),
            "allowed_fds": list(self.allowed_fds),
        }

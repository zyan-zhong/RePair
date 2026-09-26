"""Machine-auditable SHA-authority correction evidence for Failure Memory V1.

This module does not enumerate tasks, partition task groups, or materialize
Failure Memory.  It binds already-produced canonical protected bytes to their
implementation/source identities and computes the correction evidence from
those bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Final


EVIDENCE_SCHEMA: Final[str] = (
    "TASK_ACCESS_SHA_AUTHORITY_CORRECTION_EVIDENCE_V1"
)
ACCESS_POLICY_ID: Final[str] = "MEMORY_TASK_ACCESS_V2_1"

HISTORICAL_CANDIDATE_ROLE: Final[str] = (
    "PRESERVED_HISTORICAL_DESIGN_CANDIDATE"
)

_REQUIRED_REPRODUCTION_IDS: Final[frozenset[str]] = frozenset(
    {
        "CURRENT_PRODUCTION_IN_MEMORY",
        "HISTORICAL_PURE_CORE",
        "STANDALONE_CANONICAL_SERIALIZER",
    }
)

_REQUIRED_ROLE_IDS: Final[frozenset[str]] = frozenset(
    {
        "TRAIN_MEMORY_SOURCE",
        "TRAIN_RETRIEVAL_DEV",
        "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED",
        "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED",
    }
)

_REQUIRED_INCIDENT_ARTIFACT_IDS: Final[frozenset[str]] = frozenset(
    {
        "V2_MATERIALIZATION_STOP",
        "V2_SOURCE_INTEGRITY_PRE",
        "V2_TASK_MATERIALIZER_STDERR",
        "V2_TASK_MATERIALIZER_STDOUT",
    }
)


class TaskAccessShaAuthorityCorrectionError(RuntimeError):
    """Fail-closed correction-evidence contract error."""


@dataclass(frozen=True, slots=True)
class ReproductionInputV1:
    reproduction_id: str
    implementation_identity: str
    implementation_path: Path
    canonical_output_path: Path
    declared_observed_protected_sha256: str
    source_fingerprint: str
    record_count: int
    role_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class IncidentEvidenceInputV1:
    artifact_id: str
    path: Path
    expected_sha256: str


@dataclass(frozen=True, slots=True)
class CorrectionEvidenceRequestV1:
    correction_base_commit: str
    correction_design_commit: str
    access_policy_id: str
    historical_design_candidate_sha256: str
    proposed_exact_contract_protected_sha256: str
    dataset_source_fingerprint: str
    record_count: int
    role_counts: tuple[tuple[str, int], ...]
    reproductions: tuple[ReproductionInputV1, ...]
    incident_evidence: tuple[IncidentEvidenceInputV1, ...]


@dataclass(frozen=True, slots=True)
class CorrectionEvidenceResultV1:
    payload: dict[str, object]
    canonical_bytes: bytes
    evidence_sha256: str


def _require_text(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise TaskAccessShaAuthorityCorrectionError(
            f"{name.upper()}_NOT_STRING"
        )
    if not value:
        raise TaskAccessShaAuthorityCorrectionError(
            f"{name.upper()}_EMPTY"
        )
    if any(ch in value for ch in ("\x00", "\r", "\n")):
        raise TaskAccessShaAuthorityCorrectionError(
            f"{name.upper()}_FORBIDDEN_CHARACTER"
        )
    return value


def _require_sha256(name: str, value: object) -> str:
    value = _require_text(name, value)
    if len(value) != 64 or any(
        ch not in "0123456789abcdef"
        for ch in value
    ):
        raise TaskAccessShaAuthorityCorrectionError(
            f"{name.upper()}_INVALID_SHA256"
        )
    return value


def _require_commit(name: str, value: object) -> str:
    value = _require_text(name, value)
    if len(value) != 40 or any(
        ch not in "0123456789abcdef"
        for ch in value
    ):
        raise TaskAccessShaAuthorityCorrectionError(
            f"{name.upper()}_INVALID_COMMIT"
        )
    return value


def _freeze_role_counts(
    value: object,
) -> tuple[tuple[str, int], ...]:
    if type(value) is not tuple:
        raise TaskAccessShaAuthorityCorrectionError(
            "ROLE_COUNTS_NOT_TUPLE"
        )

    frozen: list[tuple[str, int]] = []
    seen: set[str] = set()

    for item in value:
        if (
            type(item) is not tuple
            or len(item) != 2
        ):
            raise TaskAccessShaAuthorityCorrectionError(
                "ROLE_COUNTS_ITEM_INVALID"
            )

        key, count = item
        key = _require_text("role_count_key", key)

        if key in seen:
            raise TaskAccessShaAuthorityCorrectionError(
                "ROLE_COUNTS_DUPLICATE_KEY"
            )
        seen.add(key)

        if type(count) is not int or count < 0:
            raise TaskAccessShaAuthorityCorrectionError(
                "ROLE_COUNTS_VALUE_INVALID"
            )

        frozen.append((key, count))

    if not frozen:
        raise TaskAccessShaAuthorityCorrectionError(
            "ROLE_COUNTS_EMPTY"
        )

    return tuple(sorted(frozen))


def _read_regular_file(
    path: Path,
    *,
    label: str,
) -> bytes:
    if type(path) is not Path:
        path = Path(path)

    try:
        metadata = path.lstat()
    except OSError as exc:
        raise TaskAccessShaAuthorityCorrectionError(
            f"{label}_UNREADABLE"
        ) from exc

    if stat.S_ISLNK(metadata.st_mode):
        raise TaskAccessShaAuthorityCorrectionError(
            f"{label}_SYMLINK_FORBIDDEN"
        )

    if not stat.S_ISREG(metadata.st_mode):
        raise TaskAccessShaAuthorityCorrectionError(
            f"{label}_NOT_REGULAR_FILE"
        )

    try:
        return path.read_bytes()
    except OSError as exc:
        raise TaskAccessShaAuthorityCorrectionError(
            f"{label}_UNREADABLE"
        ) from exc


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(
    payload: object,
) -> bytes:
    try:
        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise TaskAccessShaAuthorityCorrectionError(
            "EVIDENCE_NOT_CANONICAL_JSON_SERIALIZABLE"
        ) from exc


def _validate_request(
    request: CorrectionEvidenceRequestV1,
) -> tuple[tuple[str, int], ...]:
    if not isinstance(
        request,
        CorrectionEvidenceRequestV1,
    ):
        raise TaskAccessShaAuthorityCorrectionError(
            "REQUEST_TYPE_INVALID"
        )

    _require_commit(
        "correction_base_commit",
        request.correction_base_commit,
    )
    _require_commit(
        "correction_design_commit",
        request.correction_design_commit,
    )

    if request.access_policy_id != ACCESS_POLICY_ID:
        raise TaskAccessShaAuthorityCorrectionError(
            "ACCESS_POLICY_ID_MISMATCH"
        )

    historical_sha = _require_sha256(
        "historical_design_candidate_sha256",
        request.historical_design_candidate_sha256,
    )
    exact_sha = _require_sha256(
        "proposed_exact_contract_protected_sha256",
        request.proposed_exact_contract_protected_sha256,
    )

    # This is an instance-level V1 correction assertion, not a generic
    # schema law for all future authority records.
    if historical_sha == exact_sha:
        raise TaskAccessShaAuthorityCorrectionError(
            "CORRECTION_V1_DIGESTS_MUST_DIFFER"
        )

    _require_sha256(
        "dataset_source_fingerprint",
        request.dataset_source_fingerprint,
    )

    if (
        type(request.record_count) is not int
        or request.record_count <= 0
    ):
        raise TaskAccessShaAuthorityCorrectionError(
            "RECORD_COUNT_INVALID"
        )

    role_counts = _freeze_role_counts(
        request.role_counts
    )

    if frozenset(
        role_id
        for role_id, _count in role_counts
    ) != _REQUIRED_ROLE_IDS:
        raise TaskAccessShaAuthorityCorrectionError(
            "ROLE_COUNTS_KEYS_INVALID"
        )

    if sum(
        count
        for _role_id, count in role_counts
    ) != request.record_count:
        raise TaskAccessShaAuthorityCorrectionError(
            "ROLE_COUNTS_RECORD_COUNT_MISMATCH"
        )

    return role_counts


def build_correction_evidence(
    request: CorrectionEvidenceRequestV1,
) -> CorrectionEvidenceResultV1:
    """Build correction evidence from observed implementation/output bytes."""

    expected_role_counts = _validate_request(
        request
    )

    reproduction_ids = tuple(
        item.reproduction_id
        for item in request.reproductions
    )

    if (
        len(set(reproduction_ids))
        != len(reproduction_ids)
        or frozenset(reproduction_ids)
        != _REQUIRED_REPRODUCTION_IDS
        or len(reproduction_ids)
        != len(_REQUIRED_REPRODUCTION_IDS)
    ):
        raise TaskAccessShaAuthorityCorrectionError(
            "REPRODUCTION_SET_INVALID"
        )

    reproduction_payloads: list[
        dict[str, object]
    ] = []
    canonical_bytes_by_id: dict[str, bytes] = {}

    for reproduction in request.reproductions:
        _require_text(
            "reproduction_id",
            reproduction.reproduction_id,
        )
        _require_text(
            "implementation_identity",
            reproduction.implementation_identity,
        )

        implementation_bytes = _read_regular_file(
            Path(reproduction.implementation_path),
            label="REPRODUCTION_IMPLEMENTATION",
        )
        canonical_bytes = _read_regular_file(
            Path(reproduction.canonical_output_path),
            label="REPRODUCTION_CANONICAL_OUTPUT",
        )

        observed_sha = _sha256_bytes(
            canonical_bytes
        )
        declared_sha = _require_sha256(
            "declared_observed_protected_sha256",
            reproduction.declared_observed_protected_sha256,
        )

        if declared_sha != observed_sha:
            raise TaskAccessShaAuthorityCorrectionError(
                "DECLARED_PROTECTED_SHA256_MISMATCH"
            )

        if (
            reproduction.source_fingerprint
            != request.dataset_source_fingerprint
        ):
            raise TaskAccessShaAuthorityCorrectionError(
                "REPRODUCTION_SOURCE_FINGERPRINT_MISMATCH"
            )

        if (
            reproduction.record_count
            != request.record_count
        ):
            raise TaskAccessShaAuthorityCorrectionError(
                "REPRODUCTION_RECORD_COUNT_MISMATCH"
            )

        reproduction_role_counts = (
            _freeze_role_counts(
                reproduction.role_counts
            )
        )
        if (
            reproduction_role_counts
            != expected_role_counts
        ):
            raise TaskAccessShaAuthorityCorrectionError(
                "REPRODUCTION_ROLE_COUNTS_MISMATCH"
            )

        canonical_bytes_by_id[
            reproduction.reproduction_id
        ] = canonical_bytes

        reproduction_payloads.append(
            {
                "reproduction_id":
                    reproduction.reproduction_id,
                "implementation_identity":
                    reproduction.implementation_identity,
                "implementation_sha256":
                    _sha256_bytes(
                        implementation_bytes
                    ),
                "source_fingerprint":
                    reproduction.source_fingerprint,
                "record_count":
                    reproduction.record_count,
                "role_counts":
                    dict(reproduction_role_counts),
                "canonical_output_artifact_sha256":
                    observed_sha,
                "canonical_output_byte_count":
                    len(canonical_bytes),
                "observed_protected_sha256":
                    observed_sha,
            }
        )

    production_bytes = canonical_bytes_by_id[
        "CURRENT_PRODUCTION_IN_MEMORY"
    ]
    historical_bytes = canonical_bytes_by_id[
        "HISTORICAL_PURE_CORE"
    ]
    standalone_bytes = canonical_bytes_by_id[
        "STANDALONE_CANONICAL_SERIALIZER"
    ]

    production_vs_historical = (
        production_bytes
        == historical_bytes
    )
    if not production_vs_historical:
        raise TaskAccessShaAuthorityCorrectionError(
            "PRODUCTION_HISTORICAL_BYTES_MISMATCH"
        )

    production_vs_standalone = (
        production_bytes
        == standalone_bytes
    )
    if not production_vs_standalone:
        raise TaskAccessShaAuthorityCorrectionError(
            "PRODUCTION_STANDALONE_BYTES_MISMATCH"
        )

    observed_three_way_sha = _sha256_bytes(
        production_bytes
    )

    all_three_sha256_equal = (
        len(
            {
                item[
                    "observed_protected_sha256"
                ]
                for item in reproduction_payloads
            }
        )
        == 1
    )

    requested_incident_ids = tuple(
        incident.artifact_id
        for incident in request.incident_evidence
    )

    if (
        len(set(requested_incident_ids))
        != len(requested_incident_ids)
        or frozenset(requested_incident_ids)
        != _REQUIRED_INCIDENT_ARTIFACT_IDS
        or len(requested_incident_ids)
        != len(_REQUIRED_INCIDENT_ARTIFACT_IDS)
    ):
        raise TaskAccessShaAuthorityCorrectionError(
            "INCIDENT_EVIDENCE_SET_INVALID"
        )

    incident_ids: set[str] = set()
    incident_payloads: list[
        dict[str, object]
    ] = []

    for incident in request.incident_evidence:
        artifact_id = _require_text(
            "incident_artifact_id",
            incident.artifact_id,
        )
        if artifact_id in incident_ids:
            raise TaskAccessShaAuthorityCorrectionError(
                "INCIDENT_EVIDENCE_DUPLICATE_ID"
            )
        incident_ids.add(artifact_id)

        payload = _read_regular_file(
            Path(incident.path),
            label="INCIDENT_EVIDENCE",
        )
        observed_sha = _sha256_bytes(
            payload
        )
        expected_sha = _require_sha256(
            "incident_expected_sha256",
            incident.expected_sha256,
        )

        if observed_sha != expected_sha:
            raise TaskAccessShaAuthorityCorrectionError(
                "INCIDENT_EVIDENCE_SHA256_MISMATCH"
            )

        incident_payloads.append(
            {
                "artifact_id":
                    artifact_id,
                "sha256":
                    observed_sha,
                "byte_count":
                    len(payload),
            }
        )

    proposed_sha = (
        request
        .proposed_exact_contract_protected_sha256
    )
    proposed_matches_reproduction = (
        observed_three_way_sha
        == proposed_sha
    )

    if not proposed_matches_reproduction:
        raise TaskAccessShaAuthorityCorrectionError(
            "THREE_WAY_SHA_DOES_NOT_MATCH_PROPOSED_AUTHORITY"
        )

    payload: dict[str, object] = {
        "schema":
            EVIDENCE_SCHEMA,
        "correction_base_commit":
            request.correction_base_commit,
        "correction_design_commit":
            request.correction_design_commit,
        "access_policy_id":
            request.access_policy_id,
        "historical_design_candidate_sha256":
            request.historical_design_candidate_sha256,
        "historical_candidate_role":
            HISTORICAL_CANDIDATE_ROLE,
        "historical_candidate_execution_authority":
            False,
        "proposed_exact_contract_protected_sha256":
            proposed_sha,
        "dataset_source_fingerprint":
            request.dataset_source_fingerprint,
        "record_count":
            request.record_count,
        "role_counts":
            dict(expected_role_counts),
        "reproductions":
            sorted(
                reproduction_payloads,
                key=lambda item: str(
                    item["reproduction_id"]
                ),
            ),
        "production_vs_historical_bytes_equal":
            production_vs_historical,
        "production_vs_standalone_bytes_equal":
            production_vs_standalone,
        "all_three_sha256_equal":
            all_three_sha256_equal,
        "three_way_observed_protected_sha256":
            observed_three_way_sha,
        "three_way_sha_matches_proposed_authority":
            proposed_matches_reproduction,
        "incident_evidence":
            sorted(
                incident_payloads,
                key=lambda item: str(
                    item["artifact_id"]
                ),
            ),
        "conclusion": (
            "THREE_WAY_CANONICAL_BYTES_AGREE_"
            + (
                "AND_MATCH_PROPOSED_AUTHORITY"
                if proposed_matches_reproduction
                else
                "PROPOSED_AUTHORITY_NOT_CONFIRMED_BY_THIS_FIXTURE"
            )
        ),
    }

    canonical_bytes = _canonical_json_bytes(
        payload
    )

    return CorrectionEvidenceResultV1(
        payload=payload,
        canonical_bytes=canonical_bytes,
        evidence_sha256=_sha256_bytes(
            canonical_bytes
        ),
    )


def write_correction_evidence(
    request: CorrectionEvidenceRequestV1,
    output: str | os.PathLike[str],
) -> CorrectionEvidenceResultV1:
    """Build and exclusively publish one canonical evidence JSON file."""

    result = build_correction_evidence(
        request
    )
    path = Path(output)

    parent = path.parent
    if not parent.is_dir():
        raise TaskAccessShaAuthorityCorrectionError(
            "OUTPUT_PARENT_NOT_DIRECTORY"
        )

    try:
        with path.open("xb") as stream:
            stream.write(
                result.canonical_bytes
            )
            stream.flush()
            os.fsync(
                stream.fileno()
            )
    except FileExistsError as exc:
        raise TaskAccessShaAuthorityCorrectionError(
            "OUTPUT_ALREADY_EXISTS"
        ) from exc
    except OSError as exc:
        # If exclusive creation succeeded but a later write/fsync failed,
        # leave the partial artifact in place rather than silently replacing it.
        raise TaskAccessShaAuthorityCorrectionError(
            "OUTPUT_WRITE_FAILED"
        ) from exc

    return result

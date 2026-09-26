#!/usr/bin/env python3
"""Dry-run-only correction-aware retry wrapper candidate.

This module validates a frozen retry-candidate snapshot.  It does not create
staging directories, run task-access materialization, run policy-identity
materialization, or copy artifacts.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Final


FROZEN_CORRECTION_CODE_HEAD: Final[str] = (
    "ba0a344fcda079e112c84fcbe312121dcf5efb60"
)

FROZEN_TASK1_CORRECTION_DESIGN_COMMIT: Final[str] = (
    "08aa577a299012aa59b03d75a4a0654ae0d74d69"
)

FROZEN_ORIGINAL_FAILURE_MEMORY_DESIGN_COMMIT: Final[str] = (
    "b3cb816e2e727600f79f1947a77c73ce87d4a97c"
)

FROZEN_HISTORICAL_DESIGN_CANDIDATE_SHA256: Final[str] = (
    "6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a"
)

FROZEN_EXACT_CONTRACT_PROTECTED_SHA256: Final[str] = (
    "260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea"
)

EXPECTED_BRANCH: Final[str] = (
    "implementation/"
    "failure-memory-task-access-sha-authority-correction-v1"
)

OLD_FAILURE_STAGING_IDENTITIES: Final[frozenset[str]] = frozenset(
    {
        "failure_memory_foundation_v1_71ce8a4",
        "failure_memory_foundation_v1_1a0feee",
    }
)

CORRECTION_EVIDENCE_SCHEMA: Final[str] = (
    "TASK_ACCESS_SHA_AUTHORITY_CORRECTION_EVIDENCE_V1"
)

AUTHORITY_CONFIG_SCHEMA_V1: Final[str] = (
    "TASK_ACCESS_REGENERATION_CONFIG_V1"
)

AUTHORITY_CONFIG_SCHEMA_V2: Final[str] = (
    "TASK_ACCESS_REGENERATION_CONFIG_V2"
)

REQUIRED_REPRODUCTION_IDS: Final[frozenset[str]] = frozenset(
    {
        "CURRENT_PRODUCTION_IN_MEMORY",
        "HISTORICAL_PURE_CORE",
        "STANDALONE_CANONICAL_SERIALIZER",
    }
)

REQUIRED_ROLE_COUNTS: Final[dict[str, int]] = {
    "TRAIN_MEMORY_SOURCE": 2367,
    "TRAIN_RETRIEVAL_DEV": 1186,
    "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 140,
    (
        "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_"
        "HISTORICALLY_EXPOSED"
    ): 134,
}

REAL_MATERIALIZATION_APPROVED: Final[bool] = False


class RetryWrapperCandidateError(RuntimeError):
    """Fail-closed retry-candidate validation error."""


def _require_text(
    name: str,
    value: object,
) -> str:
    if not isinstance(value, str) or not value:
        raise RetryWrapperCandidateError(
            f"{name.upper()}_INVALID"
        )
    if any(
        character in value
        for character in ("\x00", "\r", "\n")
    ):
        raise RetryWrapperCandidateError(
            f"{name.upper()}_INVALID"
        )
    return value


def _require_sha256(
    name: str,
    value: object,
) -> str:
    value = _require_text(
        name,
        value,
    )
    if len(value) != 64 or any(
        character not in "0123456789abcdef"
        for character in value
    ):
        raise RetryWrapperCandidateError(
            f"{name.upper()}_INVALID"
        )
    return value


def _require_commit(
    name: str,
    value: object,
) -> str:
    value = _require_text(
        name,
        value,
    )
    if len(value) != 40 or any(
        character not in "0123456789abcdef"
        for character in value
    ):
        raise RetryWrapperCandidateError(
            f"{name.upper()}_INVALID"
        )
    return value


def derive_head_bound_staging_identity(
    head: str,
) -> str:
    """Derive the frozen candidate staging identity from a Git head."""

    head = _require_commit(
        "head",
        head,
    )
    return (
        "failure_memory_foundation_v1_"
        "sha_authority_correction_v1_"
        + head[:7]
    )


FROZEN_NEW_STAGING_IDENTITY: Final[str] = (
    derive_head_bound_staging_identity(
        FROZEN_CORRECTION_CODE_HEAD
    )
)


@dataclass(frozen=True, slots=True)
class RetryWrapperCandidateSnapshotV1:
    branch: str
    head: str
    worktree_clean: bool
    requested_staging_identity: str
    requested_staging_exists: bool
    requested_staging_is_symlink: bool
    correction_evidence: dict[str, object] | None
    authority_config: dict[str, object] | None


def _validate_correction_evidence(
    payload: object,
) -> None:
    if payload is None:
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_REQUIRED"
        )
    if type(payload) is not dict:
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_INVALID"
        )

    if payload.get("schema") != CORRECTION_EVIDENCE_SCHEMA:
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_SCHEMA_INVALID"
        )

    if (
        payload.get("correction_design_commit")
        != FROZEN_TASK1_CORRECTION_DESIGN_COMMIT
    ):
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_TASK1_BINDING_MISMATCH"
        )

    if (
        payload.get("historical_design_candidate_sha256")
        != FROZEN_HISTORICAL_DESIGN_CANDIDATE_SHA256
    ):
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_HISTORICAL_SHA_MISMATCH"
        )

    if payload.get(
        "proposed_exact_contract_protected_sha256"
    ) != FROZEN_EXACT_CONTRACT_PROTECTED_SHA256:
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_EXACT_SHA_MISMATCH"
        )

    equality_fields = (
        "production_vs_historical_bytes_equal",
        "production_vs_standalone_bytes_equal",
        "all_three_sha256_equal",
        "three_way_sha_matches_proposed_authority",
    )
    if any(
        payload.get(field) is not True
        for field in equality_fields
    ):
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_THREE_WAY_EQUALITY_REQUIRED"
        )

    if payload.get(
        "three_way_observed_protected_sha256"
    ) != FROZEN_EXACT_CONTRACT_PROTECTED_SHA256:
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_OBSERVED_SHA_MISMATCH"
        )

    if payload.get("record_count") != 3827:
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_RECORD_COUNT_MISMATCH"
        )

    if payload.get("role_counts") != REQUIRED_ROLE_COUNTS:
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_ROLE_COUNTS_MISMATCH"
        )

    reproductions = payload.get("reproductions")
    if type(reproductions) is not list:
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_REPRODUCTIONS_INVALID"
        )

    reproduction_ids: list[str] = []
    for reproduction in reproductions:
        if type(reproduction) is not dict:
            raise RetryWrapperCandidateError(
                "CORRECTION_EVIDENCE_REPRODUCTION_INVALID"
            )

        reproduction_id = reproduction.get(
            "reproduction_id"
        )
        if not isinstance(
            reproduction_id,
            str,
        ):
            raise RetryWrapperCandidateError(
                "CORRECTION_EVIDENCE_REPRODUCTION_ID_INVALID"
            )

        reproduction_ids.append(
            reproduction_id
        )

        if reproduction.get(
            "observed_protected_sha256"
        ) != FROZEN_EXACT_CONTRACT_PROTECTED_SHA256:
            raise RetryWrapperCandidateError(
                "CORRECTION_EVIDENCE_REPRODUCTION_SHA_MISMATCH"
            )

        if reproduction.get(
            "canonical_output_artifact_sha256"
        ) != FROZEN_EXACT_CONTRACT_PROTECTED_SHA256:
            raise RetryWrapperCandidateError(
                "CORRECTION_EVIDENCE_REPRODUCTION_ARTIFACT_SHA_MISMATCH"
            )

        if reproduction.get(
            "record_count"
        ) != 3827:
            raise RetryWrapperCandidateError(
                "CORRECTION_EVIDENCE_REPRODUCTION_COUNT_MISMATCH"
            )

        if reproduction.get(
            "role_counts"
        ) != REQUIRED_ROLE_COUNTS:
            raise RetryWrapperCandidateError(
                "CORRECTION_EVIDENCE_REPRODUCTION_ROLE_COUNTS_MISMATCH"
            )

    if (
        len(reproduction_ids)
        != len(REQUIRED_REPRODUCTION_IDS)
        or len(set(reproduction_ids))
        != len(reproduction_ids)
        or frozenset(reproduction_ids)
        != REQUIRED_REPRODUCTION_IDS
    ):
        raise RetryWrapperCandidateError(
            "CORRECTION_EVIDENCE_REPRODUCTION_SET_INVALID"
        )


def _validate_authority_config(
    payload: object,
) -> None:
    if payload is None:
        raise RetryWrapperCandidateError(
            "AUTHORITY_CONFIG_REQUIRED"
        )
    if type(payload) is not dict:
        raise RetryWrapperCandidateError(
            "AUTHORITY_CONFIG_INVALID"
        )

    schema = payload.get("schema")

    if schema == AUTHORITY_CONFIG_SCHEMA_V1:
        raise RetryWrapperCandidateError(
            "AUTHORITY_CONFIG_V1_REJECTED"
        )

    if schema != AUTHORITY_CONFIG_SCHEMA_V2:
        raise RetryWrapperCandidateError(
            "AUTHORITY_CONFIG_SCHEMA_INVALID"
        )

    if (
        payload.get(
            "original_failure_memory_design_commit"
        )
        != FROZEN_ORIGINAL_FAILURE_MEMORY_DESIGN_COMMIT
    ):
        raise RetryWrapperCandidateError(
            "AUTHORITY_CONFIG_ORIGINAL_DESIGN_BINDING_MISMATCH"
        )

    if (
        payload.get(
            "sha_authority_correction_design_commit"
        )
        != FROZEN_TASK1_CORRECTION_DESIGN_COMMIT
    ):
        raise RetryWrapperCandidateError(
            "AUTHORITY_CONFIG_TASK1_BINDING_MISMATCH"
        )

    if (
        payload.get(
            "historical_design_candidate_sha256"
        )
        != FROZEN_HISTORICAL_DESIGN_CANDIDATE_SHA256
    ):
        raise RetryWrapperCandidateError(
            "AUTHORITY_CONFIG_HISTORICAL_SHA_MISMATCH"
        )

    if (
        payload.get(
            "approved_exact_contract_protected_sha256"
        )
        != FROZEN_EXACT_CONTRACT_PROTECTED_SHA256
    ):
        raise RetryWrapperCandidateError(
            "AUTHORITY_CONFIG_EXACT_SHA_MISMATCH"
        )

    if (
        payload.get("expected_populations")
        != REQUIRED_ROLE_COUNTS
    ):
        raise RetryWrapperCandidateError(
            "AUTHORITY_CONFIG_POPULATIONS_MISMATCH"
        )

    if (
        payload.get("access_policy_id")
        != "MEMORY_TASK_ACCESS_V2_1"
    ):
        raise RetryWrapperCandidateError(
            "AUTHORITY_CONFIG_ACCESS_POLICY_MISMATCH"
        )

    if (
        payload.get("disclosure_policy_id")
        != "HELDOUT_IDENTITY_DISCLOSURE_POLICY_V1"
    ):
        raise RetryWrapperCandidateError(
            "AUTHORITY_CONFIG_DISCLOSURE_POLICY_MISMATCH"
        )


def validate_retry_wrapper_candidate_snapshot(
    snapshot: RetryWrapperCandidateSnapshotV1,
) -> dict[str, object]:
    """Validate one synthetic/read-only candidate snapshot."""

    if not isinstance(
        snapshot,
        RetryWrapperCandidateSnapshotV1,
    ):
        raise RetryWrapperCandidateError(
            "SNAPSHOT_TYPE_INVALID"
        )

    if snapshot.branch != EXPECTED_BRANCH:
        raise RetryWrapperCandidateError(
            "BRANCH_MISMATCH"
        )

    if snapshot.head != FROZEN_CORRECTION_CODE_HEAD:
        raise RetryWrapperCandidateError(
            "HEAD_MISMATCH"
        )

    if snapshot.worktree_clean is not True:
        raise RetryWrapperCandidateError(
            "WORKTREE_NOT_CLEAN"
        )

    staging_identity = _require_text(
        "requested_staging_identity",
        snapshot.requested_staging_identity,
    )

    if staging_identity in OLD_FAILURE_STAGING_IDENTITIES:
        raise RetryWrapperCandidateError(
            "OLD_FAILURE_STAGING_IDENTITY_FORBIDDEN"
        )

    if (
        staging_identity
        != FROZEN_NEW_STAGING_IDENTITY
    ):
        raise RetryWrapperCandidateError(
            "NEW_STAGING_IDENTITY_MISMATCH"
        )

    if snapshot.requested_staging_is_symlink is not False:
        raise RetryWrapperCandidateError(
            "NEW_STAGING_ROOT_SYMLINK_FORBIDDEN"
        )

    if snapshot.requested_staging_exists is not False:
        raise RetryWrapperCandidateError(
            "NEW_STAGING_ROOT_ALREADY_EXISTS"
        )

    _validate_correction_evidence(
        snapshot.correction_evidence
    )

    _validate_authority_config(
        snapshot.authority_config
    )

    return {
        "schema": (
            "TASK_ACCESS_SHA_CORRECTION_"
            "RETRY_WRAPPER_CANDIDATE_V1"
        ),
        "candidate_valid": True,
        "staging_identity": (
            FROZEN_NEW_STAGING_IDENTITY
        ),
        "correction_code_head": (
            FROZEN_CORRECTION_CODE_HEAD
        ),
        "task1_correction_design_commit": (
            FROZEN_TASK1_CORRECTION_DESIGN_COMMIT
        ),
        "real_materialization_authorized": False,
        "create_staging_root": False,
    }


def _snapshot_from_json(
    payload: object,
) -> RetryWrapperCandidateSnapshotV1:
    if type(payload) is not dict:
        raise RetryWrapperCandidateError(
            "SNAPSHOT_JSON_NOT_OBJECT"
        )

    expected_keys = {
        "branch",
        "head",
        "worktree_clean",
        "requested_staging_identity",
        "requested_staging_exists",
        "requested_staging_is_symlink",
        "correction_evidence",
        "authority_config",
    }

    if set(payload) != expected_keys:
        raise RetryWrapperCandidateError(
            "SNAPSHOT_JSON_KEYS_INVALID"
        )

    return RetryWrapperCandidateSnapshotV1(
        branch=payload["branch"],
        head=payload["head"],
        worktree_clean=payload["worktree_clean"],
        requested_staging_identity=payload[
            "requested_staging_identity"
        ],
        requested_staging_exists=payload[
            "requested_staging_exists"
        ],
        requested_staging_is_symlink=payload[
            "requested_staging_is_symlink"
        ],
        correction_evidence=payload[
            "correction_evidence"
        ],
        authority_config=payload[
            "authority_config"
        ],
    )


def _load_snapshot_json(
    path: Path,
) -> RetryWrapperCandidateSnapshotV1:
    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise RetryWrapperCandidateError(
            "SNAPSHOT_JSON_UNREADABLE"
        ) from exc

    return _snapshot_from_json(
        payload
    )


def main(
    argv: list[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot-json",
        required=True,
        type=Path,
    )

    args = parser.parse_args(
        argv
    )

    try:
        snapshot = _load_snapshot_json(
            args.snapshot_json
        )
        result = (
            validate_retry_wrapper_candidate_snapshot(
                snapshot
            )
        )
    except RetryWrapperCandidateError as exc:
        print(
            "TASK_ACCESS_SHA_CORRECTION_RETRY_CANDIDATE_STOP="
            + str(exc),
            file=sys.stderr,
        )
        return 2

    print(
        "TASK_ACCESS_SHA_CORRECTION_RETRY_CANDIDATE_PASS"
    )
    print(
        "staging_identity="
        + str(result["staging_identity"])
    )
    print(
        "correction_code_head="
        + str(result["correction_code_head"])
    )
    print(
        "real_materialization_authorized=false"
    )
    print(
        "create_staging_root=false"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

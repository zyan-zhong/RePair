"""Repair only the known V1233I rollout-request integrity-hash bug.

The V1233I next-round builder used plain SHA256(canonical request payload)
for ``request_sha256``.  The native ``RoundRolloutCollectionRequestV1`` uses a
domain-separated hash.  This module may repair only that exact serialization
integrity field.  All scientific/request fields, including round and execution
identity, must remain byte-for-byte equivalent at the JSON value level.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from safe_io import load_json, sha_file, write_new_json
from runtime_surface_preflight import validate_runtime_surface

_SCHEMA = "ROUND_ROLLOUT_COLLECTION_REQUEST_V1"
_FIXED_SELECTION_RULE = "FULL_FROZEN_TRAIN_UPDATE_UNIVERSE"
_EXPECTED_KEYS = {
    "schema_id",
    "schema_version",
    "round_id",
    "execution_attempt_id",
    "parent_policy_id",
    "parent_policy_artifact_sha256",
    "policy_runtime_binding_sha256",
    "execution_profile_sha256",
    "train_update_manifest_sha256",
    "round_memory_runtime_authority_sha256",
    "round_start_memory_snapshot_sha256",
    "token_budget_contract_sha256",
    "execution_namespace",
    "rollout_seed",
    "benchmark_feedback_authorized",
    "invalid_attempt_adaptive_evidence_reuse_authorized",
    "selection_rule",
    "request_sha256",
}


def _canonical_no_newline(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _plain_legacy_hash(value_without_sha: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_no_newline(dict(value_without_sha))).hexdigest()


def _request_kwargs(value: Mapping[str, Any], *, include_hash: bool) -> dict[str, Any]:
    excluded = {"schema_id", "schema_version", "selection_rule"}
    if not include_hash:
        excluded.add("request_sha256")
    return {k: v for k, v in value.items() if k not in excluded}


def _validate_shape(value: Mapping[str, Any]) -> None:
    if set(value) != _EXPECTED_KEYS:
        raise ValueError("CURRENT_REQUEST_FIELD_SET_MISMATCH")
    if value.get("schema_id") != _SCHEMA or value.get("schema_version") != 1:
        raise ValueError("CURRENT_REQUEST_SCHEMA")
    if value.get("selection_rule") != _FIXED_SELECTION_RULE:
        raise ValueError("CURRENT_REQUEST_SELECTION_RULE")
    embedded = value.get("request_sha256")
    if (
        not isinstance(embedded, str)
        or len(embedded) != 64
        or any(c not in "0123456789abcdef" for c in embedded)
    ):
        raise ValueError("CURRENT_REQUEST_EMBEDDED_SHA_INVALID")


def repair_request_value(value: Mapping[str, Any], *, request_type):
    source = dict(value)
    _validate_shape(source)
    payload = {k: v for k, v in source.items() if k != "request_sha256"}
    source_hash = source["request_sha256"]
    legacy_hash = _plain_legacy_hash(payload)

    if source_hash == legacy_hash:
        # Only this known V1233I builder defect is eligible for repair.
        native = request_type(**_request_kwargs(source, include_hash=False))
        repaired = native.to_dict()
        if {k: v for k, v in repaired.items() if k != "request_sha256"} != payload:
            raise ValueError("REQUEST_REPAIR_CHANGED_NON_HASH_FIELDS")
        if repaired["request_sha256"] == source_hash:
            raise ValueError("REQUEST_REPAIR_DID_NOT_CHANGE_LEGACY_HASH")
        pattern = "V1233I_PLAIN_CANONICAL_SHA256"
        mutation_scope = "REQUEST_SHA256_ONLY"
    else:
        # A native-valid request is safe to adopt.  Any other bad hash must not
        # be generalized into an automatic repair class.
        try:
            native = request_type(**_request_kwargs(source, include_hash=True))
        except ValueError as exc:
            if "request SHA mismatch" in str(exc):
                raise ValueError("REQUEST_HASH_FAILURE_NOT_REGISTERED_V1233I_BUG") from exc
            raise
        repaired = native.to_dict()
        if repaired != source:
            raise ValueError("NATIVE_REQUEST_RECONSTRUCTION_CHANGED_BYTES_SEMANTICS")
        pattern = "NATIVE_DOMAIN_HASH_ALREADY_VALID"
        mutation_scope = "NONE"

    receipt = {
        "schema_id": "R2_ROLLOUT_REQUEST_CANONICAL_HASH_REPAIR_V1",
        "schema_version": 1,
        "source_hash_pattern": pattern,
        "source_embedded_request_sha256": source_hash,
        "canonical_embedded_request_sha256": repaired["request_sha256"],
        "mutation_scope": mutation_scope,
        "scientific_semantics_changed": False,
        "round_id_preserved": repaired["round_id"] == source["round_id"],
        "execution_attempt_id_preserved": repaired["execution_attempt_id"] == source["execution_attempt_id"],
        "parent_policy_id_preserved": repaired["parent_policy_id"] == source["parent_policy_id"],
        "memory_identity_preserved": (
            repaired["round_memory_runtime_authority_sha256"] == source["round_memory_runtime_authority_sha256"]
            and repaired["round_start_memory_snapshot_sha256"] == source["round_start_memory_snapshot_sha256"]
        ),
        "train_update_identity_preserved": repaired["train_update_manifest_sha256"] == source["train_update_manifest_sha256"],
        "non_hash_fields_identical": True,
    }
    return repaired, receipt


def materialize_request_repair(
    source_request: Path,
    worktree: Path,
    capsule_root: Path,
    output_request: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    source_request = Path(source_request)
    worktree = Path(worktree)
    capsule_root = Path(capsule_root)
    # Validate the exact registered runtime surface before importing the native
    # request contract from the historical execution worktree.
    surface = validate_runtime_surface(worktree, capsule_root)
    sys.path.insert(0, str(worktree / "src"))
    from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1

    source = load_json(source_request)
    repaired, receipt = repair_request_value(
        source,
        request_type=RoundRolloutCollectionRequestV1,
    )
    write_new_json(output_request, repaired)
    receipt = {
        **receipt,
        "source_request_path": str(source_request),
        "source_request_file_sha256": sha_file(source_request),
        "canonical_request_path": str(output_request),
        "canonical_request_file_sha256": sha_file(output_request),
        "runtime_surface_preflight": surface,
    }
    write_new_json(receipt_path, receipt)
    return receipt

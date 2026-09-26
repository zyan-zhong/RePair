"""Read-only Round-1 policy identity materializer for Failure Memory V1."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

from pchsi.memory import policy_contract


CONFIG_SCHEMA = "ROUND1_POLICY_SOURCE_IDENTITY_V1"
HISTORICAL_AUTHORITY_ID = "A01_CHECKPOINTS"
HISTORICAL_IDENTITY_KIND = "ROOT_SEAL"


class PolicyIdentityMaterializationError(RuntimeError):
    """Fail-closed policy identity materialization error."""


@dataclass(frozen=True, slots=True)
class PolicySourceConfigEntryV1:
    training_seed: int
    formal_run_manifest_relative_path: str
    formal_run_manifest_sha256: str
    adapter_artifact_manifest_relative_path: str
    adapter_artifact_manifest_sha256: str


@dataclass(frozen=True, slots=True)
class PolicyIdentityMaterializationConfigV1:
    checkpoint_set_root_seal: str
    policy_sources: tuple[PolicySourceConfigEntryV1, ...]


def _require_lower_sha256(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise PolicyIdentityMaterializationError(f"{name.upper()}_TYPE_INVALID")
    if (
        len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PolicyIdentityMaterializationError(f"{name.upper()}_INVALID")
    return value


def _require_relative_path(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise PolicyIdentityMaterializationError(f"{name.upper()}_INVALID")
    if (
        value.startswith("/")
        or value.endswith("/")
        or "\\" in value
        or "\x00" in value
        or "\r" in value
        or "\n" in value
    ):
        raise PolicyIdentityMaterializationError(f"{name.upper()}_INVALID")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PolicyIdentityMaterializationError(f"{name.upper()}_INVALID")
    return value


def _canonical_json_bytes(payload: object) -> bytes:
    try:
        text = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise PolicyIdentityMaterializationError("CANONICAL_JSON_INVALID") from exc
    return (text + "\n").encode("utf-8")


def _contains_forbidden_result_key(value: object) -> bool:
    forbidden = (
        "performance",
        "metric",
        "reward",
        "success",
        "memory_effect",
        "result_score",
        "best_seed",
        "best_checkpoint",
    )
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                return True
            lower = key.lower()
            if any(token in lower for token in forbidden):
                return True
            if _contains_forbidden_result_key(item):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_result_key(item) for item in value)
    return False


def load_policy_source_config(
    path: str | os.PathLike[str],
) -> PolicyIdentityMaterializationConfigV1:
    """Load a closed frozen source-identity configuration."""

    try:
        raw = Path(path).read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PolicyIdentityMaterializationError("POLICY_CONFIG_UNREADABLE") from exc

    if type(payload) is not dict:
        raise PolicyIdentityMaterializationError("POLICY_CONFIG_NOT_OBJECT")

    expected_keys = {
        "schema",
        "historical_authority_id",
        "historical_identity_kind",
        "checkpoint_set_root_seal",
        "selection_rule",
        "primary_training_seed",
        "secondary_training_seeds",
        "source_record_effect_policy",
        "secondary_audit_condition",
        "no_best_of_checkpoint",
        "all_secondary_results_reported",
        "policy_sources",
    }
    if set(payload) != expected_keys:
        raise PolicyIdentityMaterializationError("POLICY_CONFIG_KEYS_INVALID")
    if _contains_forbidden_result_key(payload):
        raise PolicyIdentityMaterializationError("POLICY_CONFIG_RESULT_DATA_FORBIDDEN")
    if payload["schema"] != CONFIG_SCHEMA:
        raise PolicyIdentityMaterializationError("POLICY_CONFIG_SCHEMA_INVALID")
    if payload["historical_authority_id"] != HISTORICAL_AUTHORITY_ID:
        raise PolicyIdentityMaterializationError("HISTORICAL_AUTHORITY_ID_MISMATCH")
    if payload["historical_identity_kind"] != HISTORICAL_IDENTITY_KIND:
        raise PolicyIdentityMaterializationError("HISTORICAL_IDENTITY_KIND_MISMATCH")
    if payload["selection_rule"] != policy_contract.PRIMARY_SELECTION_RULE:
        raise PolicyIdentityMaterializationError("SELECTION_RULE_MISMATCH")
    if payload["primary_training_seed"] != 17:
        raise PolicyIdentityMaterializationError("PRIMARY_TRAINING_SEED_MISMATCH")
    if payload["secondary_training_seeds"] != [31, 47]:
        raise PolicyIdentityMaterializationError("SECONDARY_TRAINING_SEEDS_MISMATCH")
    if payload["source_record_effect_policy"] != policy_contract.SOURCE_RECORD_EFFECT_POLICY:
        raise PolicyIdentityMaterializationError("SOURCE_RECORD_EFFECT_POLICY_MISMATCH")
    if payload["secondary_audit_condition"] != policy_contract.SECONDARY_AUDIT_CONDITION:
        raise PolicyIdentityMaterializationError("SECONDARY_AUDIT_CONDITION_MISMATCH")
    if payload["no_best_of_checkpoint"] is not True:
        raise PolicyIdentityMaterializationError("NO_BEST_OF_CHECKPOINT_MISMATCH")
    if payload["all_secondary_results_reported"] is not True:
        raise PolicyIdentityMaterializationError("SECONDARY_REPORTING_MISMATCH")

    root_seal = _require_lower_sha256(
        "checkpoint_set_root_seal",
        payload["checkpoint_set_root_seal"],
    )

    sources_raw = payload["policy_sources"]
    if type(sources_raw) is not list:
        raise PolicyIdentityMaterializationError("POLICY_SOURCES_NOT_LIST")

    entries = []
    for item in sources_raw:
        if type(item) is not dict:
            raise PolicyIdentityMaterializationError("POLICY_SOURCE_NOT_OBJECT")
        expected_source_keys = {
            "training_seed",
            "formal_run_manifest_relative_path",
            "formal_run_manifest_sha256",
            "adapter_artifact_manifest_relative_path",
            "adapter_artifact_manifest_sha256",
        }
        if set(item) != expected_source_keys:
            raise PolicyIdentityMaterializationError("POLICY_SOURCE_KEYS_INVALID")
        seed = item["training_seed"]
        if type(seed) is not int:
            raise PolicyIdentityMaterializationError("TRAINING_SEED_TYPE_INVALID")
        entries.append(
            PolicySourceConfigEntryV1(
                training_seed=seed,
                formal_run_manifest_relative_path=_require_relative_path(
                    "formal_run_manifest_relative_path",
                    item["formal_run_manifest_relative_path"],
                ),
                formal_run_manifest_sha256=_require_lower_sha256(
                    "formal_run_manifest_sha256",
                    item["formal_run_manifest_sha256"],
                ),
                adapter_artifact_manifest_relative_path=_require_relative_path(
                    "adapter_artifact_manifest_relative_path",
                    item["adapter_artifact_manifest_relative_path"],
                ),
                adapter_artifact_manifest_sha256=_require_lower_sha256(
                    "adapter_artifact_manifest_sha256",
                    item["adapter_artifact_manifest_sha256"],
                ),
            )
        )

    identities = tuple(
        policy_contract.PolicyCheckpointIdentityV1(
            training_seed=entry.training_seed,
            formal_run_manifest_sha256=entry.formal_run_manifest_sha256,
            adapter_artifact_manifest_sha256=entry.adapter_artifact_manifest_sha256,
        )
        for entry in entries
    )
    policy_contract.PolicySourceRegistryV1(
        checkpoint_set_root_seal=root_seal,
        source_identities=identities,
    )

    return PolicyIdentityMaterializationConfigV1(
        checkpoint_set_root_seal=root_seal,
        policy_sources=tuple(entries),
    )


def _strict_regular_file_bytes(
    path: Path,
    *,
    boundary_root: Path | None = None,
    error_prefix: str,
) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise PolicyIdentityMaterializationError(f"{error_prefix}_MISSING") from exc
    if stat.S_ISLNK(info.st_mode):
        raise PolicyIdentityMaterializationError(f"{error_prefix}_SYMLINK_FORBIDDEN")
    if not stat.S_ISREG(info.st_mode):
        raise PolicyIdentityMaterializationError(f"{error_prefix}_NOT_REGULAR_FILE")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise PolicyIdentityMaterializationError(f"{error_prefix}_RESOLVE_FAILED") from exc
    if boundary_root is not None:
        try:
            resolved.relative_to(boundary_root)
        except ValueError as exc:
            raise PolicyIdentityMaterializationError(
                f"{error_prefix}_OUTSIDE_SOURCE_ROOT"
            ) from exc
    try:
        return path.read_bytes()
    except OSError as exc:
        raise PolicyIdentityMaterializationError(f"{error_prefix}_READ_FAILED") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_from_bytes(data: bytes, *, error_code: str) -> object:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PolicyIdentityMaterializationError(error_code) from exc


def _walk_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)



A01_EXPECTED_KEYS = frozenset(
    {
        "absolute_path",
        "exists",
        "file_count",
        "role",
        "slot_id",
        "total_bytes",
        "tree_digest_sha256",
    }
)
A01_ROLE = "training checkpoint archive"
A01_FILE_COUNT = 23
A01_TOTAL_BYTES = 359767109
CHECKPOINT_SET_MANIFEST_RELATIVE_PATH = "checkpoint_set_manifest.json"
RUNNER_MANIFEST_RELATIVE_PATH = "provenance/runner_manifest.json"
AUXILIARY_REGISTERED_MEMBERS = (
    "provenance/execution_spec.json",
    "provenance/formal_submission_ledger.jsonl",
)


def _expected_checkpoint_set_member_paths() -> frozenset[str]:
    paths = {
        *AUXILIARY_REGISTERED_MEMBERS,
        RUNNER_MANIFEST_RELATIVE_PATH,
    }
    for seed in (17, 31, 47):
        paths.update(
            {
                f"seed_{seed}/adapter/README.md",
                f"seed_{seed}/adapter/adapter_config.json",
                f"seed_{seed}/adapter/adapter_model.safetensors",
                f"seed_{seed}/adapter_artifact_manifest.json",
                f"seed_{seed}/formal_run_manifest.json",
                f"seed_{seed}/training_step_ledger.jsonl",
            }
        )
    return frozenset(paths)


def _require_nonempty_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise PolicyIdentityMaterializationError(
            f"{name.upper()}_INVALID"
        )
    return value


def _require_json_object(
    value: object,
    *,
    error_code: str,
) -> dict[str, Any]:
    if type(value) is not dict:
        raise PolicyIdentityMaterializationError(error_code)
    return value


def _strict_regular_file_sha256_size(
    path: Path,
    *,
    boundary_root: Path,
    error_prefix: str,
) -> tuple[str, int]:
    try:
        info = path.lstat()
    except OSError as exc:
        raise PolicyIdentityMaterializationError(
            f"{error_prefix}_MISSING"
        ) from exc
    if stat.S_ISLNK(info.st_mode):
        raise PolicyIdentityMaterializationError(
            f"{error_prefix}_SYMLINK_FORBIDDEN"
        )
    if not stat.S_ISREG(info.st_mode):
        raise PolicyIdentityMaterializationError(
            f"{error_prefix}_NOT_REGULAR_FILE"
        )
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(boundary_root)
    except OSError as exc:
        raise PolicyIdentityMaterializationError(
            f"{error_prefix}_RESOLVE_FAILED"
        ) from exc
    except ValueError as exc:
        raise PolicyIdentityMaterializationError(
            f"{error_prefix}_OUTSIDE_SOURCE_ROOT"
        ) from exc

    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise PolicyIdentityMaterializationError(
            f"{error_prefix}_READ_FAILED"
        ) from exc
    return digest.hexdigest(), total


def _prepare_policy_output_path(
    path: str | os.PathLike[str],
    *,
    source_root: Path,
) -> Path:
    output = Path(path)
    if output.exists() or output.is_symlink():
        raise PolicyIdentityMaterializationError(
            "OUTPUT_ALREADY_EXISTS"
        )
    try:
        parent = output.parent.resolve(strict=True)
    except OSError as exc:
        raise PolicyIdentityMaterializationError(
            "OUTPUT_PARENT_UNRESOLVABLE"
        ) from exc
    if not parent.is_dir():
        raise PolicyIdentityMaterializationError(
            "OUTPUT_PARENT_NOT_DIRECTORY"
        )
    candidate = parent / output.name
    try:
        candidate.relative_to(source_root)
    except ValueError:
        return candidate
    raise PolicyIdentityMaterializationError(
        "OUTPUT_INSIDE_SOURCE_ROOT"
    )


def verify_historical_root_seal_authority(
    path: str | os.PathLike[str],
    *,
    expected_root_seal: str,
    expected_source_root: Path,
) -> None:
    expected_root_seal = _require_lower_sha256(
        "expected_root_seal",
        expected_root_seal,
    )
    raw = _strict_regular_file_bytes(
        Path(path),
        boundary_root=None,
        error_prefix="ROOT_SEAL_AUTHORITY",
    )
    payload = _json_from_bytes(
        raw,
        error_code="ROOT_SEAL_AUTHORITY_JSON_INVALID",
    )
    if type(payload) is not list:
        raise PolicyIdentityMaterializationError(
            "ROOT_SEAL_AUTHORITY_SCHEMA_INVALID"
        )

    candidates = [
        item
        for item in payload
        if (
            type(item) is dict
            and item.get("slot_id") == HISTORICAL_AUTHORITY_ID
        )
    ]
    if not candidates:
        raise PolicyIdentityMaterializationError(
            "ROOT_SEAL_AUTHORITY_RECORD_MISSING"
        )
    if len(candidates) != 1:
        raise PolicyIdentityMaterializationError(
            "ROOT_SEAL_AUTHORITY_RECORD_AMBIGUOUS"
        )

    record = candidates[0]
    if set(record) != A01_EXPECTED_KEYS:
        raise PolicyIdentityMaterializationError(
            "ROOT_SEAL_AUTHORITY_SCHEMA_INVALID"
        )
    if record["exists"] is not True:
        raise PolicyIdentityMaterializationError(
            "ROOT_SEAL_AUTHORITY_EXISTS_INVALID"
        )
    if record["role"] != A01_ROLE:
        raise PolicyIdentityMaterializationError(
            "ROOT_SEAL_AUTHORITY_ROLE_INVALID"
        )
    if record["file_count"] != A01_FILE_COUNT:
        raise PolicyIdentityMaterializationError(
            "ROOT_SEAL_AUTHORITY_FILE_COUNT_INVALID"
        )
    if record["total_bytes"] != A01_TOTAL_BYTES:
        raise PolicyIdentityMaterializationError(
            "ROOT_SEAL_AUTHORITY_TOTAL_BYTES_INVALID"
        )
    if record["tree_digest_sha256"] != expected_root_seal:
        raise PolicyIdentityMaterializationError(
            "ROOT_SEAL_AUTHORITY_VALUE_MISMATCH"
        )

    absolute_path = _require_nonempty_text(
        "root_seal_authority_absolute_path",
        record["absolute_path"],
    )
    try:
        authority_root = Path(absolute_path).resolve(strict=True)
    except OSError as exc:
        raise PolicyIdentityMaterializationError(
            "ROOT_SEAL_AUTHORITY_PATH_UNRESOLVABLE"
        ) from exc
    if authority_root != expected_source_root:
        raise PolicyIdentityMaterializationError(
            "ROOT_SEAL_AUTHORITY_SOURCE_ROOT_MISMATCH"
        )


def _exclusive_write_0600(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise PolicyIdentityMaterializationError(
            "OUTPUT_ALREADY_EXISTS"
        )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise PolicyIdentityMaterializationError(
            "OUTPUT_CREATE_FAILED"
        ) from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink(missing_ok=True)
        finally:
            raise


def _load_checkpoint_set_manifest(
    root: Path,
) -> tuple[
    dict[str, Any],
    dict[int, dict[str, Any]],
    dict[str, str],
    str,
]:
    raw = _strict_regular_file_bytes(
        root / CHECKPOINT_SET_MANIFEST_RELATIVE_PATH,
        boundary_root=root,
        error_prefix="CHECKPOINT_SET_MANIFEST",
    )
    payload = _require_json_object(
        _json_from_bytes(
            raw,
            error_code="CHECKPOINT_SET_MANIFEST_JSON_INVALID",
        ),
        error_code="CHECKPOINT_SET_MANIFEST_NOT_OBJECT",
    )

    if payload.get("checkpoint_count") != 3:
        raise PolicyIdentityMaterializationError(
            "CHECKPOINT_SET_COUNT_INVALID"
        )
    if payload.get("training_seed_schedule") != [17, 31, 47]:
        raise PolicyIdentityMaterializationError(
            "CHECKPOINT_SET_SEED_SCHEDULE_INVALID"
        )
    if payload.get("training_seed_selection") != (
        "ALL_THREE_REQUIRED_NO_BEST_SEED_SELECTION"
    ):
        raise PolicyIdentityMaterializationError(
            "CHECKPOINT_SET_SELECTION_RULE_INVALID"
        )
    if payload.get("checkpoint_set_status") != (
        "FROZEN_READY_FOR_HARNESS_OFF_SELECT"
    ):
        raise PolicyIdentityMaterializationError(
            "CHECKPOINT_SET_STATUS_INVALID"
        )
    if payload.get("teacher_or_runtime_harness_in_select") is not False:
        raise PolicyIdentityMaterializationError(
            "CHECKPOINT_SET_HARNESS_FLAG_INVALID"
        )
    if payload.get("scientific_checkpoint_rule") != "FINAL_STEP_ONLY":
        raise PolicyIdentityMaterializationError(
            "CHECKPOINT_SET_SCIENTIFIC_RULE_INVALID"
        )

    checkpoints_raw = payload.get("checkpoints")
    if type(checkpoints_raw) is not list:
        raise PolicyIdentityMaterializationError(
            "CHECKPOINT_SET_CHECKPOINTS_INVALID"
        )
    checkpoints: dict[int, dict[str, Any]] = {}
    for item in checkpoints_raw:
        item = _require_json_object(
            item,
            error_code="CHECKPOINT_SET_ENTRY_NOT_OBJECT",
        )
        seed = item.get("training_seed")
        if type(seed) is not int:
            raise PolicyIdentityMaterializationError(
                "CHECKPOINT_SET_SEED_INVALID"
            )
        if seed in checkpoints:
            raise PolicyIdentityMaterializationError(
                "CHECKPOINT_SET_DUPLICATE_SEED"
            )
        checkpoints[seed] = item
    if set(checkpoints) != {17, 31, 47}:
        raise PolicyIdentityMaterializationError(
            "CHECKPOINT_SET_SEED_SET_INVALID"
        )

    file_sha_raw = payload.get("file_sha256")
    if type(file_sha_raw) is not dict:
        raise PolicyIdentityMaterializationError(
            "CHECKPOINT_SET_FILE_SHA_MAP_INVALID"
        )
    file_sha: dict[str, str] = {}
    for member, digest in file_sha_raw.items():
        if not isinstance(member, str):
            raise PolicyIdentityMaterializationError(
                "CHECKPOINT_SET_FILE_PATH_INVALID"
            )
        file_sha[member] = _require_lower_sha256(
            "checkpoint_set_member_sha256",
            digest,
        )

    if set(file_sha) != set(
        _expected_checkpoint_set_member_paths()
    ):
        raise PolicyIdentityMaterializationError(
            "CHECKPOINT_SET_FILE_SHA_PATH_SET_INVALID"
        )

    for key in (
        "runner_freeze_root_sha256",
        "training_config_freeze_root_sha256",
        "dataset_freeze_root_sha256",
        "materialization_freeze_root_sha256",
    ):
        _require_lower_sha256(key, payload.get(key))

    _require_nonempty_text(
        "base_model_repository",
        payload.get("base_model_repository"),
    )
    _require_nonempty_text(
        "base_model_revision",
        payload.get("base_model_revision"),
    )

    return payload, checkpoints, file_sha, _sha256(raw)


def _load_and_verify_runner_manifest(
    *,
    root: Path,
    checkpoint_set: dict[str, Any],
    file_sha256: dict[str, str],
) -> tuple[dict[str, Any], str]:
    expected_sha = file_sha256.get(
        RUNNER_MANIFEST_RELATIVE_PATH
    )
    if expected_sha is None:
        raise PolicyIdentityMaterializationError(
            "RUNNER_MANIFEST_NOT_BOUND_BY_CHECKPOINT_SET"
        )
    raw = _strict_regular_file_bytes(
        root / RUNNER_MANIFEST_RELATIVE_PATH,
        boundary_root=root,
        error_prefix="RUNNER_MANIFEST",
    )
    observed_sha = _sha256(raw)
    if observed_sha != expected_sha:
        raise PolicyIdentityMaterializationError(
            "RUNNER_MANIFEST_SHA256_MISMATCH"
        )
    payload = _require_json_object(
        _json_from_bytes(
            raw,
            error_code="RUNNER_MANIFEST_JSON_INVALID",
        ),
        error_code="RUNNER_MANIFEST_NOT_OBJECT",
    )
    if payload.get("formal_training_seeds") != [17, 31, 47]:
        raise PolicyIdentityMaterializationError(
            "RUNNER_MANIFEST_SEED_SCHEDULE_INVALID"
        )
    if payload.get("select_used_for_training_or_model_selection") is not False:
        raise PolicyIdentityMaterializationError(
            "RUNNER_MANIFEST_SELECT_FLAG_INVALID"
        )
    if payload.get("runner_status") != "FROZEN_READY_FOR_FORMAL_TRAINING":
        raise PolicyIdentityMaterializationError(
            "RUNNER_MANIFEST_STATUS_INVALID"
        )
    for key in (
        "training_config_freeze_root_sha256",
        "dataset_freeze_root_sha256",
        "materialization_freeze_root_sha256",
    ):
        if payload.get(key) != checkpoint_set.get(key):
            raise PolicyIdentityMaterializationError(
                f"RUNNER_MANIFEST_{key.upper()}_MISMATCH"
            )
    return payload, observed_sha



def _member_error_token(
    relative_path: str,
) -> str:
    return (
        relative_path
        .upper()
        .replace("/", "_")
        .replace(".", "_")
        .replace("-", "_")
    )


def _verify_auxiliary_registered_members(
    *,
    root: Path,
    file_sha256: dict[str, str],
) -> None:
    for relative in AUXILIARY_REGISTERED_MEMBERS:
        expected_sha = file_sha256.get(
            relative
        )
        if expected_sha is None:
            raise PolicyIdentityMaterializationError(
                "REGISTERED_MEMBER_NOT_BOUND_"
                + _member_error_token(relative)
            )

        observed_sha, _ = (
            _strict_regular_file_sha256_size(
                root / relative,
                boundary_root=root,
                error_prefix=(
                    "REGISTERED_MEMBER_"
                    + _member_error_token(
                        relative
                    )
                ),
            )
        )
        if observed_sha != expected_sha:
            raise PolicyIdentityMaterializationError(
                "REGISTERED_MEMBER_SHA256_MISMATCH_"
                + _member_error_token(relative)
            )


def _validate_adapter_manifest_and_members(
    *,
    root: Path,
    seed: int,
    adapter_payload: object,
    checkpoint_entry: dict[str, Any],
    checkpoint_file_sha256: dict[str, str],
) -> str:
    payload = _require_json_object(
        adapter_payload,
        error_code=f"ADAPTER_MANIFEST_NOT_OBJECT_SEED_{seed}",
    )
    if set(payload) != {
        "adapter_bundle_sha256",
        "files",
        "required_files",
        "schema_id",
        "schema_version",
    }:
        raise PolicyIdentityMaterializationError(
            f"ADAPTER_MANIFEST_SCHEMA_INVALID_SEED_{seed}"
        )

    adapter_bundle = _require_lower_sha256(
        "adapter_bundle_sha256",
        payload.get("adapter_bundle_sha256"),
    )
    if checkpoint_entry.get("adapter_bundle_sha256") != adapter_bundle:
        raise PolicyIdentityMaterializationError(
            f"CHECKPOINT_SET_ADAPTER_BUNDLE_MISMATCH_SEED_{seed}"
        )

    if payload.get("required_files") != [
        "adapter_config.json",
        "adapter_model.safetensors",
    ]:
        raise PolicyIdentityMaterializationError(
            f"ADAPTER_REQUIRED_FILES_INVALID_SEED_{seed}"
        )

    files = payload.get("files")
    if type(files) is not dict:
        raise PolicyIdentityMaterializationError(
            f"ADAPTER_FILES_MAP_INVALID_SEED_{seed}"
        )
    if set(files) != {
        "README.md",
        "adapter_config.json",
        "adapter_model.safetensors",
    }:
        raise PolicyIdentityMaterializationError(
            f"ADAPTER_FILES_SET_INVALID_SEED_{seed}"
        )

    adapter_relative = _require_relative_path(
        "adapter_relative_path",
        checkpoint_entry.get("adapter_relative_path"),
    )
    if adapter_relative != f"seed_{seed}/adapter":
        raise PolicyIdentityMaterializationError(
            f"ADAPTER_RELATIVE_PATH_MISMATCH_SEED_{seed}"
        )

    for name, metadata in files.items():
        metadata = _require_json_object(
            metadata,
            error_code=f"ADAPTER_MEMBER_METADATA_INVALID_SEED_{seed}",
        )
        if set(metadata) != {"sha256", "size_bytes"}:
            raise PolicyIdentityMaterializationError(
                f"ADAPTER_MEMBER_METADATA_SCHEMA_INVALID_SEED_{seed}"
            )
        expected_sha = _require_lower_sha256(
            "adapter_member_sha256",
            metadata["sha256"],
        )
        expected_size = metadata["size_bytes"]
        if type(expected_size) is not int or expected_size < 0:
            raise PolicyIdentityMaterializationError(
                f"ADAPTER_MEMBER_SIZE_INVALID_SEED_{seed}"
            )

        relative = f"{adapter_relative}/{name}"
        if checkpoint_file_sha256.get(relative) != expected_sha:
            raise PolicyIdentityMaterializationError(
                f"CHECKPOINT_SET_ADAPTER_MEMBER_SHA256_MISMATCH_SEED_{seed}"
            )

        observed_sha, observed_size = _strict_regular_file_sha256_size(
            root / relative,
            boundary_root=root,
            error_prefix=f"ADAPTER_MEMBER_SEED_{seed}",
        )
        if observed_sha != expected_sha:
            raise PolicyIdentityMaterializationError(
                f"ADAPTER_MEMBER_SHA256_MISMATCH_SEED_{seed}"
            )
        if observed_size != expected_size:
            raise PolicyIdentityMaterializationError(
                f"ADAPTER_MEMBER_SIZE_MISMATCH_SEED_{seed}"
            )

    return adapter_bundle


def materialize_primary_policy_contract(
    *,
    source_root: str | os.PathLike[str],
    root_seal_authority_path: str | os.PathLike[str],
    config_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
) -> dict[str, object]:
    config = load_policy_source_config(config_path)

    root = Path(source_root)
    try:
        root_info = root.lstat()
    except OSError as exc:
        raise PolicyIdentityMaterializationError(
            "SOURCE_ROOT_MISSING"
        ) from exc
    if stat.S_ISLNK(root_info.st_mode):
        raise PolicyIdentityMaterializationError(
            "SOURCE_ROOT_SYMLINK_FORBIDDEN"
        )
    if not stat.S_ISDIR(root_info.st_mode):
        raise PolicyIdentityMaterializationError(
            "SOURCE_ROOT_NOT_DIRECTORY"
        )
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise PolicyIdentityMaterializationError(
            "SOURCE_ROOT_RESOLVE_FAILED"
        ) from exc

    output = _prepare_policy_output_path(
        output_path,
        source_root=resolved_root,
    )

    (
        checkpoint_set,
        checkpoint_entries,
        checkpoint_file_sha256,
        checkpoint_set_manifest_sha256,
    ) = _load_checkpoint_set_manifest(resolved_root)

    runner, runner_manifest_sha256 = _load_and_verify_runner_manifest(
        root=resolved_root,
        checkpoint_set=checkpoint_set,
        file_sha256=checkpoint_file_sha256,
    )

    _verify_auxiliary_registered_members(
        root=resolved_root,
        file_sha256=checkpoint_file_sha256,
    )

    config_by_seed = {
        entry.training_seed: entry
        for entry in config.policy_sources
    }
    if set(config_by_seed) != {17, 31, 47}:
        raise PolicyIdentityMaterializationError(
            "POLICY_CONFIG_SEED_SET_INVALID"
        )

    observed = []
    tokenizer_bundle_sha256: str | None = None
    training_config_sha256: str | None = None

    for seed in (17, 31, 47):
        entry = config_by_seed[seed]
        checkpoint_entry = checkpoint_entries[seed]

        if checkpoint_entry.get(
            "formal_run_manifest_sha256"
        ) != entry.formal_run_manifest_sha256:
            raise PolicyIdentityMaterializationError(
                f"CHECKPOINT_SET_FORMAL_MANIFEST_SHA256_MISMATCH_SEED_{seed}"
            )
        if checkpoint_entry.get(
            "adapter_artifact_manifest_sha256"
        ) != entry.adapter_artifact_manifest_sha256:
            raise PolicyIdentityMaterializationError(
                f"CHECKPOINT_SET_ADAPTER_MANIFEST_SHA256_MISMATCH_SEED_{seed}"
            )

        if checkpoint_file_sha256.get(
            entry.formal_run_manifest_relative_path
        ) != entry.formal_run_manifest_sha256:
            raise PolicyIdentityMaterializationError(
                f"CHECKPOINT_SET_FORMAL_FILE_MAP_MISMATCH_SEED_{seed}"
            )
        if checkpoint_file_sha256.get(
            entry.adapter_artifact_manifest_relative_path
        ) != entry.adapter_artifact_manifest_sha256:
            raise PolicyIdentityMaterializationError(
                f"CHECKPOINT_SET_ADAPTER_FILE_MAP_MISMATCH_SEED_{seed}"
            )

        formal_bytes = _strict_regular_file_bytes(
            resolved_root / entry.formal_run_manifest_relative_path,
            boundary_root=resolved_root,
            error_prefix=f"FORMAL_RUN_SEED_{seed}",
        )
        adapter_bytes = _strict_regular_file_bytes(
            resolved_root / entry.adapter_artifact_manifest_relative_path,
            boundary_root=resolved_root,
            error_prefix=f"ADAPTER_MANIFEST_SEED_{seed}",
        )

        formal_sha = _sha256(formal_bytes)
        adapter_sha = _sha256(adapter_bytes)
        if formal_sha != entry.formal_run_manifest_sha256:
            raise PolicyIdentityMaterializationError(
                f"FORMAL_RUN_SHA256_MISMATCH_SEED_{seed}"
            )
        if adapter_sha != entry.adapter_artifact_manifest_sha256:
            raise PolicyIdentityMaterializationError(
                f"ADAPTER_MANIFEST_SHA256_MISMATCH_SEED_{seed}"
            )

        formal_payload = _require_json_object(
            _json_from_bytes(
                formal_bytes,
                error_code=f"FORMAL_RUN_JSON_INVALID_SEED_{seed}",
            ),
            error_code=f"FORMAL_RUN_NOT_OBJECT_SEED_{seed}",
        )
        adapter_payload = _json_from_bytes(
            adapter_bytes,
            error_code=f"ADAPTER_MANIFEST_JSON_INVALID_SEED_{seed}",
        )

        if formal_payload.get("formal_training_seed") != seed:
            raise PolicyIdentityMaterializationError(
                f"FORMAL_TRAINING_SEED_MISMATCH_SEED_{seed}"
            )

        for key in (
            "base_model_repository",
            "base_model_revision",
            "runner_freeze_root_sha256",
            "training_config_freeze_root_sha256",
            "dataset_freeze_root_sha256",
            "materialization_freeze_root_sha256",
            "scientific_checkpoint_rule",
        ):
            if formal_payload.get(key) != checkpoint_set.get(key):
                raise PolicyIdentityMaterializationError(
                    f"FORMAL_{key.upper()}_MISMATCH_SEED_{seed}"
                )

        if formal_payload.get(
            "final_trainable_parameter_sha256"
        ) != checkpoint_entry.get(
            "final_trainable_parameter_sha256"
        ):
            raise PolicyIdentityMaterializationError(
                f"FORMAL_FINAL_PARAMETER_SHA256_MISMATCH_SEED_{seed}"
            )
        if formal_payload.get(
            "intermediate_scientific_checkpoint_used"
        ) is not False:
            raise PolicyIdentityMaterializationError(
                f"FORMAL_INTERMEDIATE_CHECKPOINT_FLAG_INVALID_SEED_{seed}"
            )
        if formal_payload.get(
            "select_used_for_training_or_model_selection"
        ) is not False:
            raise PolicyIdentityMaterializationError(
                f"FORMAL_SELECT_FLAG_INVALID_SEED_{seed}"
            )

        observed_tokenizer = _require_lower_sha256(
            "tokenizer_bundle_sha256",
            formal_payload.get("tokenizer_bundle_sha256"),
        )
        if tokenizer_bundle_sha256 is None:
            tokenizer_bundle_sha256 = observed_tokenizer
        elif tokenizer_bundle_sha256 != observed_tokenizer:
            raise PolicyIdentityMaterializationError(
                "TOKENIZER_BUNDLE_CROSS_SEED_MISMATCH"
            )

        observed_training_config = _require_lower_sha256(
            "training_config_sha256",
            formal_payload.get("training_config_sha256"),
        )
        if training_config_sha256 is None:
            training_config_sha256 = observed_training_config
        elif training_config_sha256 != observed_training_config:
            raise PolicyIdentityMaterializationError(
                "TRAINING_CONFIG_CROSS_SEED_MISMATCH"
            )

        adapter_bundle = _validate_adapter_manifest_and_members(
            root=resolved_root,
            seed=seed,
            adapter_payload=adapter_payload,
            checkpoint_entry=checkpoint_entry,
            checkpoint_file_sha256=checkpoint_file_sha256,
        )
        if formal_payload.get("adapter_bundle_sha256") != adapter_bundle:
            raise PolicyIdentityMaterializationError(
                f"FORMAL_ADAPTER_BUNDLE_MISMATCH_SEED_{seed}"
            )

        ledger_sha = _require_lower_sha256(
            "training_step_ledger_sha256",
            checkpoint_entry.get("training_step_ledger_sha256"),
        )
        ledger_relative = f"seed_{seed}/training_step_ledger.jsonl"
        if checkpoint_file_sha256.get(ledger_relative) != ledger_sha:
            raise PolicyIdentityMaterializationError(
                f"CHECKPOINT_SET_LEDGER_FILE_MAP_MISMATCH_SEED_{seed}"
            )
        observed_ledger_sha, _ = _strict_regular_file_sha256_size(
            resolved_root / ledger_relative,
            boundary_root=resolved_root,
            error_prefix=f"TRAINING_LEDGER_SEED_{seed}",
        )
        if observed_ledger_sha != ledger_sha:
            raise PolicyIdentityMaterializationError(
                f"TRAINING_LEDGER_SHA256_MISMATCH_SEED_{seed}"
            )

        observed.append(
            policy_contract.PolicyCheckpointIdentityV1(
                training_seed=seed,
                formal_run_manifest_sha256=formal_sha,
                adapter_artifact_manifest_sha256=adapter_sha,
            )
        )

    if runner.get("training_config_sha256") != training_config_sha256:
        raise PolicyIdentityMaterializationError(
            "RUNNER_TRAINING_CONFIG_SHA256_MISMATCH"
        )

    verify_historical_root_seal_authority(
        root_seal_authority_path,
        expected_root_seal=config.checkpoint_set_root_seal,
        expected_source_root=resolved_root,
    )

    registry = policy_contract.PolicySourceRegistryV1(
        checkpoint_set_root_seal=config.checkpoint_set_root_seal,
        source_identities=tuple(
            policy_contract.PolicyCheckpointIdentityV1(
                training_seed=entry.training_seed,
                formal_run_manifest_sha256=entry.formal_run_manifest_sha256,
                adapter_artifact_manifest_sha256=(
                    entry.adapter_artifact_manifest_sha256
                ),
            )
            for entry in config.policy_sources
        ),
    )
    contract = policy_contract.build_primary_policy_contract(
        registry=registry,
        observed_source_identities=tuple(observed),
        observed_checkpoint_set_root_seal=config.checkpoint_set_root_seal,
    )
    output_bytes = policy_contract.canonical_policy_contract_json(contract)
    output_sha = hashlib.sha256(output_bytes).hexdigest()
    _exclusive_write_0600(output, output_bytes)

    return {
        "contract_sha256": output_sha,
        "primary_training_seed": contract.primary_training_seed,
        "secondary_training_seeds": list(contract.secondary_training_seeds),
        "source_count": len(observed),
        "checkpoint_set_manifest_sha256": checkpoint_set_manifest_sha256,
        "runner_manifest_sha256": runner_manifest_sha256,
        "tokenizer_bundle_sha256": tokenizer_bundle_sha256,
        "base_model_repository": checkpoint_set["base_model_repository"],
        "base_model_revision": checkpoint_set["base_model_revision"],
    }

def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--root-seal-authority", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(
        sys.argv[1:] if argv is None else argv
    )
    try:
        report = materialize_primary_policy_contract(
            source_root=args.source_root,
            root_seal_authority_path=args.root_seal_authority,
            config_path=args.config,
            output_path=args.output,
        )
    except PolicyIdentityMaterializationError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        json.dumps(
            report,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

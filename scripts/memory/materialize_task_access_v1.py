"""Read-only task-access materializer for Failure Memory V1."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

from pchsi.memory import task_access


ORIGINAL_FAILURE_MEMORY_DESIGN_COMMIT = "b3cb816e2e727600f79f1947a77c73ce87d4a97c"
SHA_AUTHORITY_CORRECTION_DESIGN_COMMIT = "08aa577a299012aa59b03d75a4a0654ae0d74d69"
HISTORICAL_DESIGN_CANDIDATE_SHA256 = "6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a"
APPROVED_EXACT_CONTRACT_PROTECTED_SHA256 = "260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea"
DISCLOSURE_POLICY_ID = "HELDOUT_IDENTITY_DISCLOSURE_POLICY_V1"
ACCESS_POLICY_ID = "MEMORY_TASK_ACCESS_V2_1"
CONFIG_SCHEMA_V1 = "TASK_ACCESS_REGENERATION_CONFIG_V1"
CONFIG_SCHEMA = "TASK_ACCESS_REGENERATION_CONFIG_V2"
RECEIPT_SCHEMA = "MEMORY_TASK_ACCESS_REGENERATION_RECEIPT_V2"

_REQUIRED_SPLITS = ("train", "valid_seen", "valid_unseen")
_ALLOWED_TASK_TYPES = (
    "pick_and_place_simple",
    "look_at_obj_in_light",
    "pick_clean_then_place_in_recep",
    "pick_heat_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_two_obj_and_place",
)
_REAL_EXPECTED_POPULATIONS = {
    "TRAIN_MEMORY_SOURCE": 2367,
    "TRAIN_RETRIEVAL_DEV": 1186,
    "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 140,
    "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED": 134,
}


class TaskAccessMaterializationError(RuntimeError):
    """Fail-closed materialization error carrying only a non-semantic code."""


@dataclass(frozen=True, slots=True)
class TaskAccessMaterializationAuthorityV2:
    original_failure_memory_design_commit: str
    approved_exact_contract_protected_sha256: str
    expected_populations: tuple[tuple[str, int], ...]
    sha_authority_correction_design_commit: str = (
        SHA_AUTHORITY_CORRECTION_DESIGN_COMMIT
    )
    historical_design_candidate_sha256: str = (
        HISTORICAL_DESIGN_CANDIDATE_SHA256
    )
    disclosure_policy_id: str = DISCLOSURE_POLICY_ID
    access_policy_id: str = ACCESS_POLICY_ID

    def __post_init__(self) -> None:
        _require_git_commit(
            "original_failure_memory_design_commit",
            self.original_failure_memory_design_commit,
        )
        _require_git_commit(
            "sha_authority_correction_design_commit",
            self.sha_authority_correction_design_commit,
        )
        _require_sha256(
            "historical_design_candidate_sha256",
            self.historical_design_candidate_sha256,
        )
        _require_sha256(
            "approved_exact_contract_protected_sha256",
            self.approved_exact_contract_protected_sha256,
        )
        if (
            self.historical_design_candidate_sha256
            == self.approved_exact_contract_protected_sha256
        ):
            raise TaskAccessMaterializationError(
                "CORRECTION_V1_DIGESTS_MUST_DIFFER"
            )
        if self.disclosure_policy_id != DISCLOSURE_POLICY_ID:
            raise TaskAccessMaterializationError(
                "DISCLOSURE_POLICY_ID_MISMATCH"
            )
        if self.access_policy_id != ACCESS_POLICY_ID:
            raise TaskAccessMaterializationError(
                "ACCESS_POLICY_ID_MISMATCH"
            )
        observed = dict(self.expected_populations)
        if len(observed) != len(self.expected_populations):
            raise TaskAccessMaterializationError(
                "DUPLICATE_EXPECTED_POPULATION_KEY"
            )
        if set(observed) != set(_REAL_EXPECTED_POPULATIONS):
            raise TaskAccessMaterializationError(
                "EXPECTED_POPULATION_KEYS_INVALID"
            )
        if any(
            type(value) is not int or value < 0
            for value in observed.values()
        ):
            raise TaskAccessMaterializationError(
                "EXPECTED_POPULATION_VALUE_INVALID"
            )

    @property
    def expected_population_map(self) -> dict[str, int]:
        return dict(self.expected_populations)


@dataclass(frozen=True, slots=True)
class _GamefileIdentityV1:
    split: str
    task_type: str
    trial_id: str
    dataset_relative_gamefile: str
    gamefile_sha256: str
    task_gamefile_group_id: str


@dataclass(frozen=True, slots=True)
class TaskAccessMaterializationResultV1:
    protected_regeneration_sha256: str
    sanitized_manifest_sha256: str
    protected_record_count: int
    sanitized_record_count: int
    role_counts: tuple[tuple[str, int], ...]
    receipt_sha256: str


def _require_git_commit(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if len(value) != 40 or any(
        character not in "0123456789abcdef"
        for character in value
    ):
        raise ValueError(f"{name} must be a 40-character lowercase Git commit")
    return value


def _require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if len(value) != 64 or any(
        character not in "0123456789abcdef"
        for character in value
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _canonical_json_bytes(payload: object) -> bytes:
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


def load_real_authority_config(
    path: str | os.PathLike[str],
) -> TaskAccessMaterializationAuthorityV2:
    "Load only the exact registered correction-aware V2 authority."

    try:
        raw = Path(path).read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaskAccessMaterializationError(
            "AUTHORITY_CONFIG_UNREADABLE"
        ) from exc

    if type(payload) is not dict:
        raise TaskAccessMaterializationError(
            "AUTHORITY_CONFIG_NOT_OBJECT"
        )

    if "schema" not in payload:
        raise TaskAccessMaterializationError(
            "AUTHORITY_CONFIG_SCHEMA_MISSING"
        )
    if payload["schema"] == CONFIG_SCHEMA_V1:
        raise TaskAccessMaterializationError(
            "AUTHORITY_CONFIG_V1_REJECTED"
        )
    if payload["schema"] != CONFIG_SCHEMA:
        raise TaskAccessMaterializationError(
            "AUTHORITY_CONFIG_SCHEMA_INVALID"
        )

    if "sha_authority_correction_design_commit" not in payload:
        raise TaskAccessMaterializationError(
            "SHA_AUTHORITY_CORRECTION_DESIGN_COMMIT_MISSING"
        )
    if "approved_exact_contract_protected_sha256" not in payload:
        raise TaskAccessMaterializationError(
            "APPROVED_EXACT_CONTRACT_SHA256_MISSING"
        )

    expected_keys = {
        "schema",
        "access_policy_id",
        "disclosure_policy_id",
        "original_failure_memory_design_commit",
        "sha_authority_correction_design_commit",
        "historical_design_candidate_sha256",
        "approved_exact_contract_protected_sha256",
        "expected_populations",
    }
    if set(payload) != expected_keys:
        raise TaskAccessMaterializationError(
            "AUTHORITY_CONFIG_KEYS_INVALID"
        )

    if (
        payload["original_failure_memory_design_commit"]
        != ORIGINAL_FAILURE_MEMORY_DESIGN_COMMIT
    ):
        raise TaskAccessMaterializationError(
            "ORIGINAL_FAILURE_MEMORY_DESIGN_COMMIT_MISMATCH"
        )
    if (
        payload["sha_authority_correction_design_commit"]
        != SHA_AUTHORITY_CORRECTION_DESIGN_COMMIT
    ):
        raise TaskAccessMaterializationError(
            "SHA_AUTHORITY_CORRECTION_DESIGN_COMMIT_MISMATCH"
        )
    if (
        payload["historical_design_candidate_sha256"]
        != HISTORICAL_DESIGN_CANDIDATE_SHA256
    ):
        raise TaskAccessMaterializationError(
            "HISTORICAL_DESIGN_CANDIDATE_SHA256_MISMATCH"
        )
    if (
        payload["approved_exact_contract_protected_sha256"]
        != APPROVED_EXACT_CONTRACT_PROTECTED_SHA256
    ):
        raise TaskAccessMaterializationError(
            "APPROVED_EXACT_CONTRACT_SHA256_MISMATCH"
        )
    if payload["disclosure_policy_id"] != DISCLOSURE_POLICY_ID:
        raise TaskAccessMaterializationError(
            "DISCLOSURE_POLICY_ID_MISMATCH"
        )
    if payload["access_policy_id"] != ACCESS_POLICY_ID:
        raise TaskAccessMaterializationError(
            "ACCESS_POLICY_ID_MISMATCH"
        )
    if payload["expected_populations"] != _REAL_EXPECTED_POPULATIONS:
        raise TaskAccessMaterializationError(
            "REAL_EXPECTED_POPULATIONS_MISMATCH"
        )

    return TaskAccessMaterializationAuthorityV2(
        original_failure_memory_design_commit=(
            ORIGINAL_FAILURE_MEMORY_DESIGN_COMMIT
        ),
        sha_authority_correction_design_commit=(
            SHA_AUTHORITY_CORRECTION_DESIGN_COMMIT
        ),
        historical_design_candidate_sha256=(
            HISTORICAL_DESIGN_CANDIDATE_SHA256
        ),
        approved_exact_contract_protected_sha256=(
            APPROVED_EXACT_CONTRACT_PROTECTED_SHA256
        ),
        expected_populations=tuple(
            sorted(_REAL_EXPECTED_POPULATIONS.items())
        ),
    )


def _resolve_dataset_root(dataset_root: str | os.PathLike[str]) -> Path:
    try:
        root = Path(dataset_root).resolve(strict=True)
    except OSError as exc:
        raise TaskAccessMaterializationError("DATASET_ROOT_UNRESOLVABLE") from exc
    if not root.is_dir():
        raise TaskAccessMaterializationError("DATASET_ROOT_NOT_DIRECTORY")
    return root


def _derive_task_type(task_directory_name: str) -> str:
    for task_type in _ALLOWED_TASK_TYPES:
        if task_directory_name.startswith(task_type + "-"):
            return task_type
    raise TaskAccessMaterializationError("UNSUPPORTED_TASK_TYPE")


def _hash_gamefile(gamefile: Path, *, dataset_root: Path) -> str:
    try:
        metadata = gamefile.lstat()
    except FileNotFoundError as exc:
        raise TaskAccessMaterializationError("MISSING_GAMEFILE") from exc
    except OSError as exc:
        raise TaskAccessMaterializationError("GAMEFILE_LSTAT_FAILED") from exc

    if stat.S_ISLNK(metadata.st_mode):
        raise TaskAccessMaterializationError("SYMLINK_GAMEFILE")
    if not stat.S_ISREG(metadata.st_mode):
        raise TaskAccessMaterializationError("NON_REGULAR_GAMEFILE")

    try:
        resolved = gamefile.resolve(strict=True)
    except OSError as exc:
        raise TaskAccessMaterializationError("GAMEFILE_RESOLVE_FAILED") from exc
    try:
        resolved.relative_to(dataset_root)
    except ValueError as exc:
        raise TaskAccessMaterializationError(
            "RESOLVED_PATH_OUTSIDE_DATASET_ROOT"
        ) from exc

    digest = hashlib.sha256()
    try:
        with gamefile.open("rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise TaskAccessMaterializationError("GAMEFILE_READ_FAILED") from exc
    return digest.hexdigest()


def _enumerate_split(
    dataset_root: Path,
    split: str,
) -> tuple[_GamefileIdentityV1, ...]:
    if split not in _REQUIRED_SPLITS:
        raise TaskAccessMaterializationError("UNSUPPORTED_SPLIT")

    split_root = dataset_root / split
    if not split_root.is_dir():
        raise TaskAccessMaterializationError("MISSING_REQUIRED_SPLIT")

    try:
        task_directories = sorted(
            path
            for path in split_root.iterdir()
            if path.is_dir()
        )
    except OSError as exc:
        raise TaskAccessMaterializationError("SPLIT_ENUMERATION_FAILED") from exc

    records: list[_GamefileIdentityV1] = []
    for task_directory in task_directories:
        try:
            trial_directories = sorted(
                path
                for path in task_directory.iterdir()
                if path.is_dir() and path.name.startswith("trial_")
            )
        except OSError as exc:
            raise TaskAccessMaterializationError(
                "TASK_DIRECTORY_ENUMERATION_FAILED"
            ) from exc
        if not trial_directories:
            raise TaskAccessMaterializationError(
                "TASK_DIRECTORY_HAS_NO_REGISTERED_TRIAL"
            )

        task_type: str | None = None
        for trial_directory in trial_directories:
            gamefile = trial_directory / "game.tw-pddl"
            try:
                gamefile_metadata = gamefile.lstat()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise TaskAccessMaterializationError(
                    "GAMEFILE_LSTAT_FAILED"
                ) from exc

            if stat.S_ISLNK(gamefile_metadata.st_mode):
                raise TaskAccessMaterializationError(
                    "SYMLINK_GAMEFILE"
                )
            if not stat.S_ISREG(gamefile_metadata.st_mode):
                raise TaskAccessMaterializationError(
                    "NON_REGULAR_GAMEFILE"
                )

            if task_type is None:
                task_type = _derive_task_type(
                    task_directory.name
                )

            gamefile_sha256 = _hash_gamefile(
                gamefile,
                dataset_root=dataset_root,
            )
            relative = gamefile.relative_to(dataset_root).as_posix()
            try:
                group_id = task_access.canonical_task_gamefile_group_id(
                    relative_gamefile=relative,
                    gamefile_sha256=gamefile_sha256,
                )
            except (TypeError, ValueError) as exc:
                raise TaskAccessMaterializationError(
                    "TASK_IDENTITY_CONTRACT_REJECTED"
                ) from exc
            records.append(
                _GamefileIdentityV1(
                    split=split,
                    task_type=task_type,
                    trial_id=trial_directory.name,
                    dataset_relative_gamefile=relative,
                    gamefile_sha256=gamefile_sha256,
                    task_gamefile_group_id=group_id,
                )
            )
    return tuple(records)


def _role_kwargs(
    *,
    access_class: task_access.MemoryTaskAccessClass,
) -> dict[str, object]:
    """Apply only the frozen approved V2.1 access policy."""

    if access_class is task_access.MemoryTaskAccessClass.TRAIN_MEMORY_SOURCE:
        return {
            "historical_exposure_class": "NO_REGISTERED_ROUND1_EXPOSURE",
            "historically_exposed": False,
            "benchmark_role": "TRAIN_MEMORY_SOURCE",
            "allowed_prefreeze_uses": ("MEMORY_SOURCE_DEVELOPMENT",),
            "writeback_policy": "ACTIVE_MEMORY_SOURCE_ALLOWED",
            "method_selection_allowed": True,
            "formal_active_memory_source_allowed": True,
            "final_evaluation_allowed_after_method_freeze": False,
            "clean_confirmation": False,
            "fresh_ood_claim_allowed": False,
            "shadow_readback_during_formal_evaluation": False,
        }
    if access_class is task_access.MemoryTaskAccessClass.TRAIN_RETRIEVAL_DEV:
        return {
            "historical_exposure_class": "NO_REGISTERED_ROUND1_EXPOSURE",
            "historically_exposed": False,
            "benchmark_role": "TRAIN_RETRIEVAL_DEVELOPMENT",
            "allowed_prefreeze_uses": ("RETRIEVAL_DEVELOPMENT",),
            "writeback_policy": "SHADOW_ONLY_NO_ACTIVE_BANK_WRITEBACK",
            "method_selection_allowed": True,
            "formal_active_memory_source_allowed": False,
            "final_evaluation_allowed_after_method_freeze": False,
            "clean_confirmation": False,
            "fresh_ood_claim_allowed": False,
            "shadow_readback_during_formal_evaluation": False,
        }
    if (
        access_class
        is task_access.MemoryTaskAccessClass.VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED
    ):
        return {
            "historical_exposure_class": "NO_REGISTERED_ROUND1_EXPOSURE",
            "historically_exposed": False,
            "benchmark_role": "PROJECT_HELD_OUT_ID_CONFIRMATION",
            "allowed_prefreeze_uses": (),
            "writeback_policy": "FORMAL_EVALUATION_WRITEBACK_FORBIDDEN",
            "method_selection_allowed": False,
            "formal_active_memory_source_allowed": False,
            "final_evaluation_allowed_after_method_freeze": True,
            "clean_confirmation": True,
            "fresh_ood_claim_allowed": False,
            "shadow_readback_during_formal_evaluation": False,
        }
    if (
        access_class
        is task_access.MemoryTaskAccessClass
        .VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED
    ):
        return {
            "historical_exposure_class": "HISTORICALLY_EXPOSED",
            "historically_exposed": True,
            "benchmark_role": "STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED",
            "allowed_prefreeze_uses": ("LABELED_MECHANISM_DEVELOPMENT_ONLY",),
            "writeback_policy": "FORMAL_EVALUATION_WRITEBACK_FORBIDDEN",
            "method_selection_allowed": False,
            "formal_active_memory_source_allowed": False,
            "final_evaluation_allowed_after_method_freeze": True,
            "clean_confirmation": False,
            "fresh_ood_claim_allowed": False,
            "shadow_readback_during_formal_evaluation": False,
        }
    raise TaskAccessMaterializationError("ACCESS_CLASS_NOT_IN_FROZEN_POLICY")


def _build_protected_records(
    identities: tuple[_GamefileIdentityV1, ...],
) -> tuple[task_access.MemoryTaskAccessRegenerationRecordV1, ...]:
    ids = tuple(identity.task_gamefile_group_id for identity in identities)
    if len(set(ids)) != len(ids):
        raise TaskAccessMaterializationError("DUPLICATE_TASK_GAMEFILE_GROUP_ID")

    train = tuple(identity for identity in identities if identity.split == "train")
    assignments = task_access.partition_train_task_groups(
        tuple(
            task_access.TrainTaskGroupV1(
                task_type=identity.task_type,
                task_gamefile_group_id=identity.task_gamefile_group_id,
            )
            for identity in train
        )
    )
    assignment_by_id = {
        assignment.task_gamefile_group_id: assignment.access_class
        for assignment in assignments
    }

    protected = []
    for identity in identities:
        if identity.split == "train":
            access_class = assignment_by_id[identity.task_gamefile_group_id]
        elif identity.split == "valid_seen":
            access_class = (
                task_access.MemoryTaskAccessClass
                .VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED
            )
        elif identity.split == "valid_unseen":
            access_class = (
                task_access.MemoryTaskAccessClass
                .VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED
            )
        else:
            raise TaskAccessMaterializationError("UNSUPPORTED_SPLIT")

        protected.append(
            task_access.MemoryTaskAccessRegenerationRecordV1(
                trial_id=identity.trial_id,
                task_type=identity.task_type,
                split=identity.split,
                dataset_relative_gamefile=identity.dataset_relative_gamefile,
                gamefile_sha256=identity.gamefile_sha256,
                task_gamefile_group_id=identity.task_gamefile_group_id,
                access_class=access_class,
                **_role_kwargs(access_class=access_class),
            )
        )
    return tuple(protected)


def _role_counts(
    records: tuple[task_access.MemoryTaskAccessRegenerationRecordV1, ...],
) -> dict[str, int]:
    counts = {key: 0 for key in _REAL_EXPECTED_POPULATIONS}
    for record in records:
        counts[record.access_class.value] += 1
    return counts


def _prepare_output_path(path: str | os.PathLike[str]) -> Path:
    output = Path(path)
    if output.exists() or output.is_symlink():
        raise TaskAccessMaterializationError("OUTPUT_ALREADY_EXISTS")
    try:
        parent = output.parent.resolve(strict=True)
    except OSError as exc:
        raise TaskAccessMaterializationError("OUTPUT_PARENT_UNRESOLVABLE") from exc
    if not parent.is_dir():
        raise TaskAccessMaterializationError("OUTPUT_PARENT_NOT_DIRECTORY")
    return parent / output.name


def _ensure_protected_outside_repository(
    protected_output: Path,
    repository_root: str | os.PathLike[str],
) -> None:
    try:
        repository = Path(repository_root).resolve(strict=True)
        candidate = protected_output.parent.resolve(strict=True) / protected_output.name
        candidate.relative_to(repository)
    except ValueError:
        return
    except OSError as exc:
        raise TaskAccessMaterializationError("REPOSITORY_ROOT_UNRESOLVABLE") from exc
    raise TaskAccessMaterializationError("PROTECTED_OUTPUT_INSIDE_REPOSITORY")


def _exclusive_write(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise TaskAccessMaterializationError("OUTPUT_CREATE_FAILED") from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink(missing_ok=True)
        finally:
            raise



def _ensure_output_outside_dataset_root(
    output: Path,
    *,
    dataset_root: Path,
) -> None:
    candidate = output.parent.resolve(strict=True) / output.name
    try:
        candidate.relative_to(dataset_root)
    except ValueError:
        return
    raise TaskAccessMaterializationError(
        "OUTPUT_INSIDE_DATASET_ROOT"
    )


def _write_outputs_transactionally(
    outputs: tuple[tuple[Path, bytes], ...],
) -> None:
    created: list[Path] = []
    try:
        for path, payload in outputs:
            _exclusive_write(path, payload)
            created.append(path)
    except BaseException as exc:
        cleanup_errors = []
        for path in reversed(created):
            try:
                path.unlink(missing_ok=True)
            except OSError as cleanup_exc:
                cleanup_errors.append((path, cleanup_exc))
        if cleanup_errors:
            raise TaskAccessMaterializationError(
                "OUTPUT_TRANSACTION_CLEANUP_FAILED"
            ) from exc
        raise


def materialize_task_access(
    *,
    dataset_root: str | os.PathLike[str],
    protected_output: str | os.PathLike[str],
    sanitized_output: str | os.PathLike[str],
    receipt_output: str | os.PathLike[str],
    authority: TaskAccessMaterializationAuthorityV2,
    repository_root: str | os.PathLike[str],
) -> TaskAccessMaterializationResultV1:
    """Materialize protected/sanitized task identity without environment use."""

    root = _resolve_dataset_root(dataset_root)
    protected_path = _prepare_output_path(protected_output)
    sanitized_path = _prepare_output_path(sanitized_output)
    receipt_path = _prepare_output_path(receipt_output)
    if len({protected_path, sanitized_path, receipt_path}) != 3:
        raise TaskAccessMaterializationError("OUTPUT_PATHS_NOT_DISTINCT")
    _ensure_protected_outside_repository(protected_path, repository_root)

    for output in (
        protected_path,
        sanitized_path,
        receipt_path,
    ):
        _ensure_output_outside_dataset_root(
            output,
            dataset_root=root,
        )

    identities = tuple(
        identity
        for split in _REQUIRED_SPLITS
        for identity in _enumerate_split(root, split)
    )
    protected_records = _build_protected_records(identities)
    sanitized_records = tuple(record.to_sanitized() for record in protected_records)

    protected_bytes = task_access.canonical_protected_task_access_jsonl(
        protected_records
    )
    protected_sha256 = hashlib.sha256(protected_bytes).hexdigest()
    if (
        protected_sha256
        != authority.approved_exact_contract_protected_sha256
    ):
        raise TaskAccessMaterializationError(
            "PROTECTED_REGENERATION_SHA256_MISMATCH"
        )

    counts = _role_counts(protected_records)
    if counts != authority.expected_population_map:
        raise TaskAccessMaterializationError("ROLE_POPULATION_MISMATCH")

    sanitized_bytes = task_access.canonical_task_access_jsonl(sanitized_records)
    sanitized_sha256 = hashlib.sha256(sanitized_bytes).hexdigest()
    if len(protected_records) != len(sanitized_records):
        raise TaskAccessMaterializationError("SANITIZED_RECORD_COUNT_MISMATCH")
    if {
        record.task_gamefile_group_id
        for record in protected_records
    } != {
        record.task_gamefile_group_id
        for record in sanitized_records
    }:
        raise TaskAccessMaterializationError("SANITIZED_IDENTITY_SET_MISMATCH")

    receipt_payload = {
        "schema": RECEIPT_SCHEMA,
        "original_failure_memory_design_commit": (
            authority.original_failure_memory_design_commit
        ),
        "sha_authority_correction_design_commit": (
            authority.sha_authority_correction_design_commit
        ),
        "historical_design_candidate_sha256": (
            authority.historical_design_candidate_sha256
        ),
        "approved_exact_contract_protected_sha256": (
            authority.approved_exact_contract_protected_sha256
        ),
        "protected_regeneration_sha256": protected_sha256,
        "protected_record_count": len(protected_records),
        "sanitized_manifest_sha256": sanitized_sha256,
        "sanitized_record_count": len(sanitized_records),
        "disclosure_policy_id": authority.disclosure_policy_id,
        "access_policy_id": authority.access_policy_id,
        "role_counts": counts,
    }
    receipt_bytes = _canonical_json_bytes(receipt_payload)
    receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest()

    for output in (protected_path, sanitized_path, receipt_path):
        if output.exists() or output.is_symlink():
            raise TaskAccessMaterializationError("OUTPUT_ALREADY_EXISTS")

    _write_outputs_transactionally(
        (
            (protected_path, protected_bytes),
            (sanitized_path, sanitized_bytes),
            (receipt_path, receipt_bytes),
        )
    )

    return TaskAccessMaterializationResultV1(
        protected_regeneration_sha256=protected_sha256,
        sanitized_manifest_sha256=sanitized_sha256,
        protected_record_count=len(protected_records),
        sanitized_record_count=len(sanitized_records),
        role_counts=tuple(sorted(counts.items())),
        receipt_sha256=receipt_sha256,
    )


def report_materialization_result(result: TaskAccessMaterializationResultV1) -> None:
    print(f"protected_record_count={result.protected_record_count}")
    print(f"sanitized_record_count={result.sanitized_record_count}")
    for key, value in result.role_counts:
        print(f"role_count.{key}={value}")
    print(f"protected_regeneration_sha256={result.protected_regeneration_sha256}")
    print(f"sanitized_manifest_sha256={result.sanitized_manifest_sha256}")
    print(f"receipt_sha256={result.receipt_sha256}")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--protected-output", required=True)
    parser.add_argument("--sanitized-output", required=True)
    parser.add_argument("--receipt-output", required=True)
    parser.add_argument("--authority-config", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        authority = load_real_authority_config(args.authority_config)
        repository_root = Path(__file__).resolve(strict=True).parents[2]
        result = materialize_task_access(
            dataset_root=args.dataset_root,
            protected_output=args.protected_output,
            sanitized_output=args.sanitized_output,
            receipt_output=args.receipt_output,
            authority=authority,
            repository_root=repository_root,
        )
    except TaskAccessMaterializationError as exc:
        print(f"TASK_ACCESS_MATERIALIZATION_STOP={exc}", file=sys.stderr)
        return 2
    report_materialization_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

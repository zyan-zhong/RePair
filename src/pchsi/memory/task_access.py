"""Pure task-access identity and partition contracts for Failure Memory V1."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
import hashlib
import json


_TASK_GAMEFILE_GROUP_DOMAIN = "ALFWORLD_TASK_GAMEFILE_GROUP_V1"
_TRAIN_PARTITION_DOMAIN = "MEMORY_TASK_ACCESS_V2_1"
_ALLOWED_SPLITS = frozenset({"train", "valid_seen", "valid_unseen"})


def _require_text(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if not value:
        raise ValueError(f"{name} must be non-empty")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError(f"{name} contains a forbidden character")
    return value


def _require_lower_sha256(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    if (
        len(value) != 64
        or any(
            character not in "0123456789abcdef"
            for character in value
        )
    ):
        raise ValueError(
            f"{name} must be a 64-character lowercase hexadecimal SHA-256"
        )
    return value


def _require_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be bool")
    return value


def _require_string_tuple(
    name: str,
    value: object,
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be tuple")
    result = tuple(
        _require_text(f"{name} item", item)
        for item in value
    )
    if len(set(result)) != len(result):
        raise ValueError(f"{name} contains duplicates")
    return result


def _validate_relative_gamefile(
    relative_gamefile: object,
) -> str:
    if not isinstance(relative_gamefile, str):
        raise TypeError("relative_gamefile must be str")
    if not relative_gamefile:
        raise ValueError(
            "relative_gamefile must be a non-empty dataset-relative path"
        )
    if (
        relative_gamefile.startswith("/")
        or relative_gamefile.endswith("/")
        or "\\" in relative_gamefile
        or "\x00" in relative_gamefile
        or "\r" in relative_gamefile
        or "\n" in relative_gamefile
    ):
        raise ValueError(
            "relative_gamefile must be a canonical dataset-relative POSIX path"
        )
    segments = relative_gamefile.split("/")
    if any(
        segment in {"", ".", ".."}
        for segment in segments
    ):
        raise ValueError(
            "relative_gamefile must not contain empty, '.' or '..' segments"
        )
    return relative_gamefile


def canonical_task_gamefile_group_id(
    *,
    relative_gamefile: str,
    gamefile_sha256: str,
) -> str:
    """Return the approved opaque task/gamefile group identity."""

    relative_gamefile = _validate_relative_gamefile(
        relative_gamefile
    )
    gamefile_sha256 = _require_lower_sha256(
        "gamefile_sha256",
        gamefile_sha256,
    )

    payload = (
        _TASK_GAMEFILE_GROUP_DOMAIN
        + "\0"
        + relative_gamefile
        + "\0"
        + gamefile_sha256
    )
    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def train_partition_score(
    task_gamefile_group_id: str,
) -> str:
    """Return the approved deterministic train-partition score."""

    task_gamefile_group_id = _require_lower_sha256(
        "task_gamefile_group_id",
        task_gamefile_group_id,
    )

    payload = (
        _TRAIN_PARTITION_DOMAIN
        + "\0"
        + task_gamefile_group_id
    )
    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


class MemoryTaskAccessClass(str, Enum):
    """Frozen top-level Failure Memory V1 task-access roles."""

    TRAIN_MEMORY_SOURCE = "TRAIN_MEMORY_SOURCE"
    TRAIN_RETRIEVAL_DEV = "TRAIN_RETRIEVAL_DEV"
    VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED = (
        "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED"
    )
    VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED = (
        "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED"
    )


@dataclass(frozen=True, slots=True)
class TrainTaskGroupV1:
    """Pure partition input containing no result or outcome field."""

    task_type: str
    task_gamefile_group_id: str

    def __post_init__(self) -> None:
        _require_text("task_type", self.task_type)
        _require_lower_sha256(
            "task_gamefile_group_id",
            self.task_gamefile_group_id,
        )


@dataclass(frozen=True, slots=True)
class TrainTaskGroupAssignmentV1:
    """Deterministic train assignment for one canonical group."""

    task_type: str
    task_gamefile_group_id: str
    split_score: str
    access_class: MemoryTaskAccessClass

    def __post_init__(self) -> None:
        _require_text("task_type", self.task_type)
        _require_lower_sha256(
            "task_gamefile_group_id",
            self.task_gamefile_group_id,
        )
        _require_lower_sha256(
            "split_score",
            self.split_score,
        )
        if self.split_score != train_partition_score(
            self.task_gamefile_group_id
        ):
            raise ValueError(
                "split_score does not match task_gamefile_group_id"
            )
        if self.access_class not in {
            MemoryTaskAccessClass.TRAIN_MEMORY_SOURCE,
            MemoryTaskAccessClass.TRAIN_RETRIEVAL_DEV,
        }:
            raise ValueError(
                "train assignment requires a train access class"
            )


def partition_train_task_groups(
    groups: Sequence[TrainTaskGroupV1],
) -> tuple[TrainTaskGroupAssignmentV1, ...]:
    """Partition canonical train groups by family and deterministic SHA score."""

    if isinstance(groups, (str, bytes, bytearray)):
        raise TypeError("groups must be a sequence of TrainTaskGroupV1")

    frozen = tuple(groups)
    if any(
        not isinstance(group, TrainTaskGroupV1)
        for group in frozen
    ):
        raise TypeError(
            "groups must contain TrainTaskGroupV1"
        )

    ids = tuple(
        group.task_gamefile_group_id
        for group in frozen
    )
    if len(set(ids)) != len(ids):
        raise ValueError(
            "duplicate task_gamefile_group_id"
        )

    by_family: dict[
        str,
        list[tuple[str, TrainTaskGroupV1]],
    ] = defaultdict(list)

    for group in frozen:
        by_family[group.task_type].append(
            (
                train_partition_score(
                    group.task_gamefile_group_id
                ),
                group,
            )
        )

    assignments: list[
        TrainTaskGroupAssignmentV1
    ] = []

    for task_type in sorted(by_family):
        ranked = sorted(
            by_family[task_type],
            key=lambda item: (
                item[0],
                item[1].task_gamefile_group_id,
            ),
        )
        retrieval_dev_count = (
            len(ranked) + 2
        ) // 3

        for index, (
            split_score,
            group,
        ) in enumerate(ranked):
            access_class = (
                MemoryTaskAccessClass.TRAIN_RETRIEVAL_DEV
                if index < retrieval_dev_count
                else MemoryTaskAccessClass.TRAIN_MEMORY_SOURCE
            )
            assignments.append(
                TrainTaskGroupAssignmentV1(
                    task_type=task_type,
                    task_gamefile_group_id=(
                        group.task_gamefile_group_id
                    ),
                    split_score=split_score,
                    access_class=access_class,
                )
            )

    return tuple(assignments)


@dataclass(frozen=True, slots=True)
class MemoryTaskAccessRecordV1:
    """Sanitized development-facing Failure Memory task-access record."""

    task_gamefile_group_id: str
    gamefile_sha256: str
    split: str
    historical_exposure_class: str
    historically_exposed: bool
    access_class: MemoryTaskAccessClass
    benchmark_role: str
    allowed_prefreeze_uses: tuple[str, ...]
    writeback_policy: str
    method_selection_allowed: bool
    formal_active_memory_source_allowed: bool
    final_evaluation_allowed_after_method_freeze: bool
    clean_confirmation: bool
    fresh_ood_claim_allowed: bool
    shadow_readback_during_formal_evaluation: bool

    def __post_init__(self) -> None:
        _require_lower_sha256(
            "task_gamefile_group_id",
            self.task_gamefile_group_id,
        )
        _require_lower_sha256(
            "gamefile_sha256",
            self.gamefile_sha256,
        )
        if self.split not in _ALLOWED_SPLITS:
            raise ValueError(
                "split must be train, valid_seen or valid_unseen"
            )
        _require_text(
            "historical_exposure_class",
            self.historical_exposure_class,
        )
        _require_bool(
            "historically_exposed",
            self.historically_exposed,
        )
        if type(self.access_class) is not MemoryTaskAccessClass:
            raise TypeError(
                "access_class must be MemoryTaskAccessClass"
            )
        _require_text(
            "benchmark_role",
            self.benchmark_role,
        )
        _require_string_tuple(
            "allowed_prefreeze_uses",
            self.allowed_prefreeze_uses,
        )
        _require_text(
            "writeback_policy",
            self.writeback_policy,
        )
        for name in (
            "method_selection_allowed",
            "formal_active_memory_source_allowed",
            "final_evaluation_allowed_after_method_freeze",
            "clean_confirmation",
            "fresh_ood_claim_allowed",
            "shadow_readback_during_formal_evaluation",
        ):
            _require_bool(
                name,
                getattr(self, name),
            )

        self._validate_access_semantics()


    def _validate_access_semantics(self) -> None:
        expected_by_class = {
            MemoryTaskAccessClass.TRAIN_MEMORY_SOURCE: {
                "split": "train",
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
            },
            MemoryTaskAccessClass.TRAIN_RETRIEVAL_DEV: {
                "split": "train",
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
            },
            MemoryTaskAccessClass.VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED: {
                "split": "valid_seen",
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
            },
            (
                MemoryTaskAccessClass
                .VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED
            ): {
                "split": "valid_unseen",
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
            },
        }

        try:
            expected = expected_by_class[self.access_class]
        except KeyError as exc:
            raise AssertionError(
                "unreachable MemoryTaskAccessClass"
            ) from exc

        for field_name, expected_value in expected.items():
            if getattr(self, field_name) != expected_value:
                raise ValueError(
                    f"{field_name} does not match {self.access_class.value}"
                )

    @property
    def active_bank_writeback_allowed(self) -> bool:
        """Return whether this role may contribute to the active Memory bank."""

        return (
            self.access_class
            is MemoryTaskAccessClass.TRAIN_MEMORY_SOURCE
            and self.formal_active_memory_source_allowed
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "task_gamefile_group_id":
                self.task_gamefile_group_id,
            "gamefile_sha256":
                self.gamefile_sha256,
            "split":
                self.split,
            "historical_exposure_class":
                self.historical_exposure_class,
            "historically_exposed":
                self.historically_exposed,
            "access_class":
                self.access_class.value,
            "benchmark_role":
                self.benchmark_role,
            "allowed_prefreeze_uses":
                list(self.allowed_prefreeze_uses),
            "writeback_policy":
                self.writeback_policy,
            "method_selection_allowed":
                self.method_selection_allowed,
            "formal_active_memory_source_allowed":
                self.formal_active_memory_source_allowed,
            "final_evaluation_allowed_after_method_freeze":
                self.final_evaluation_allowed_after_method_freeze,
            "clean_confirmation":
                self.clean_confirmation,
            "fresh_ood_claim_allowed":
                self.fresh_ood_claim_allowed,
            "shadow_readback_during_formal_evaluation":
                self.shadow_readback_during_formal_evaluation,
        }


@dataclass(frozen=True, slots=True)
class MemoryTaskAccessRegenerationRecordV1:
    """Protected path-bearing record used only for V2.1 regeneration."""

    trial_id: str
    task_type: str
    split: str
    dataset_relative_gamefile: str
    gamefile_sha256: str
    task_gamefile_group_id: str
    historical_exposure_class: str
    historically_exposed: bool
    access_class: MemoryTaskAccessClass
    benchmark_role: str
    allowed_prefreeze_uses: tuple[str, ...]
    writeback_policy: str
    method_selection_allowed: bool
    formal_active_memory_source_allowed: bool
    final_evaluation_allowed_after_method_freeze: bool
    clean_confirmation: bool
    fresh_ood_claim_allowed: bool
    shadow_readback_during_formal_evaluation: bool

    def __post_init__(self) -> None:
        _require_text(
            "trial_id",
            self.trial_id,
        )
        _require_text(
            "task_type",
            self.task_type,
        )
        _validate_relative_gamefile(
            self.dataset_relative_gamefile
        )
        expected_group_id = (
            canonical_task_gamefile_group_id(
                relative_gamefile=(
                    self.dataset_relative_gamefile
                ),
                gamefile_sha256=(
                    self.gamefile_sha256
                ),
            )
        )
        if (
            self.task_gamefile_group_id
            != expected_group_id
        ):
            raise ValueError(
                "task_gamefile_group_id does not match "
                "dataset_relative_gamefile/gamefile_sha256"
            )

        # Reuse sanitized role validation without exposing protected fields.
        self.to_sanitized()

    def to_sanitized(self) -> MemoryTaskAccessRecordV1:
        return MemoryTaskAccessRecordV1(
            task_gamefile_group_id=(
                self.task_gamefile_group_id
            ),
            gamefile_sha256=(
                self.gamefile_sha256
            ),
            split=self.split,
            historical_exposure_class=(
                self.historical_exposure_class
            ),
            historically_exposed=(
                self.historically_exposed
            ),
            access_class=self.access_class,
            benchmark_role=self.benchmark_role,
            allowed_prefreeze_uses=(
                self.allowed_prefreeze_uses
            ),
            writeback_policy=(
                self.writeback_policy
            ),
            method_selection_allowed=(
                self.method_selection_allowed
            ),
            formal_active_memory_source_allowed=(
                self.formal_active_memory_source_allowed
            ),
            final_evaluation_allowed_after_method_freeze=(
                self.final_evaluation_allowed_after_method_freeze
            ),
            clean_confirmation=(
                self.clean_confirmation
            ),
            fresh_ood_claim_allowed=(
                self.fresh_ood_claim_allowed
            ),
            shadow_readback_during_formal_evaluation=(
                self.shadow_readback_during_formal_evaluation
            ),
        )

    def to_dict(self) -> dict[str, object]:
        payload = (
            self.to_sanitized().to_dict()
        )
        payload.update(
            {
                "trial_id":
                    self.trial_id,
                "task_type":
                    self.task_type,
                "dataset_relative_gamefile":
                    self.dataset_relative_gamefile,
            }
        )
        return payload


def _canonical_json_line(
    payload: object,
) -> bytes:
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


def _freeze_unique_records(
    records: Sequence[
        MemoryTaskAccessRecordV1
    ],
) -> tuple[MemoryTaskAccessRecordV1, ...]:
    if isinstance(
        records,
        (str, bytes, bytearray),
    ):
        raise TypeError(
            "records must be a sequence of MemoryTaskAccessRecordV1"
        )
    frozen = tuple(records)
    if not frozen:
        raise ValueError(
            "records must not be empty"
        )
    if any(
        not isinstance(
            record,
            MemoryTaskAccessRecordV1,
        )
        for record in frozen
    ):
        raise TypeError(
            "records must contain MemoryTaskAccessRecordV1"
        )
    ids = tuple(
        record.task_gamefile_group_id
        for record in frozen
    )
    if len(set(ids)) != len(ids):
        raise ValueError(
            "duplicate task_gamefile_group_id"
        )
    return frozen


def canonical_task_access_jsonl(
    records: Sequence[
        MemoryTaskAccessRecordV1
    ],
) -> bytes:
    """Serialize the sanitized authoritative task-access manifest."""

    frozen = _freeze_unique_records(
        records
    )
    ordered = sorted(
        frozen,
        key=lambda record: (
            record.split,
            record.task_gamefile_group_id,
        ),
    )
    return b"".join(
        _canonical_json_line(
            record.to_dict()
        )
        for record in ordered
    )


def sha256_task_access_manifest(
    records: Sequence[
        MemoryTaskAccessRecordV1
    ],
) -> str:
    """Hash the canonical sanitized task-access JSONL bytes."""

    return hashlib.sha256(
        canonical_task_access_jsonl(
            records
        )
    ).hexdigest()


def canonical_protected_task_access_jsonl(
    records: Sequence[
        MemoryTaskAccessRegenerationRecordV1
    ],
) -> bytes:
    """Serialize protected V2.1 regeneration records canonically."""

    if isinstance(
        records,
        (str, bytes, bytearray),
    ):
        raise TypeError(
            "records must be a sequence of "
            "MemoryTaskAccessRegenerationRecordV1"
        )
    frozen = tuple(records)
    if not frozen:
        raise ValueError(
            "records must not be empty"
        )
    if any(
        not isinstance(
            record,
            MemoryTaskAccessRegenerationRecordV1,
        )
        for record in frozen
    ):
        raise TypeError(
            "records must contain MemoryTaskAccessRegenerationRecordV1"
        )
    ids = tuple(
        record.task_gamefile_group_id
        for record in frozen
    )
    if len(set(ids)) != len(ids):
        raise ValueError(
            "duplicate task_gamefile_group_id"
        )
    ordered = sorted(
        frozen,
        key=lambda record: (
            record.split,
            record.task_type,
            record.task_gamefile_group_id,
        ),
    )
    return b"".join(
        _canonical_json_line(
            record.to_dict()
        )
        for record in ordered
    )

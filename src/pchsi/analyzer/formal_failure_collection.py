"""Fresh pi1 train-side failure collection contracts for Formal Analyzer.

This is scientific source-evidence collection, not a policy benchmark.

The contract freezes:
- an outcome-blind TRAIN_RETRIEVAL_DEV panel before execution;
- exact pi1/Train17 policy identity;
- Memory OFF / Harness OFF / RAW R0 policy execution;
- batch-complete stopping with a target of 42 failures;
- append-only per-case receipts;
- all executed successes and failures;
- the first 42 failures in frozen panel order as the only eligible Formal
  failure cohort source.

No success rate or policy-performance estimand is produced.
"""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    require_nonnegative_int,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.task_access import canonical_task_gamefile_group_id


FORMAL_COLLECTION_CONTEXT_V1 = "FORMAL_ANALYZER_FRESH_PI1_FAILURE_COLLECTION_V1"
FORMAL_PANEL_SCHEMA_V1 = "FORMAL_ANALYZER_FRESH_FAILURE_PANEL_MANIFEST_V1"
FORMAL_CASE_RECEIPT_V1 = "FORMAL_ANALYZER_FRESH_FAILURE_CASE_RECEIPT_V1"
FORMAL_SELECTED_FAILURE_PANEL_V1 = "FORMAL_ANALYZER_SELECTED_42_FAILURES_V1"

NO_PERFORMANCE_ESTIMAND = "NO_PERFORMANCE_ESTIMAND"

PANEL_ORDER_DOMAIN_V1 = "FORMAL_ANALYZER_FRESH_FAILURE_PANEL_ORDER_V1"
PANEL_MANIFEST_DOMAIN_V1 = "FORMAL_ANALYZER_FRESH_FAILURE_PANEL_ID_V1"
CASE_RECEIPT_DOMAIN_V1 = "FORMAL_ANALYZER_FRESH_FAILURE_RECEIPT_ID_V1"
SELECTED_PANEL_DOMAIN_V1 = "FORMAL_ANALYZER_SELECTED_42_FAILURES_ID_V1"

FORMAL_ACCESS_CLASS = "TRAIN_RETRIEVAL_DEV"
FORMAL_SPLIT = "train"
FORMAL_BATCH_SIZE = 12
FORMAL_STOPPING_FAILURE_TARGET = 42
FORMAL_EVALUATION_SEED = 17

PROTECTED_TASK_ACCESS_SHA256 = (
    "260766366d72a9af7b0b4809d30a45bb"
    "56f42134dad66b29a4b61ff7ed4793ea"
)

PRIMARY_LOGICAL_CONDITION_ID = "P4-R1-Q2-BAD"
PRIMARY_CHECKPOINT_INSTANCE_ID = "P4-R1-Q2-BAD-TRAIN17"
PRIMARY_TRAINING_SEED = 17

MEMORY_MODE = "MEMORY_OFF_M0"
HARNESS_MODE = "HARNESS_OFF"
REQUEST_KIND = "R0"

STOPPING_RULE_ID = (
    "COMPLETE_BATCH_THEN_STOP_IF_CUMULATIVE_FORMAL_FAILURES_GTE_42_V1"
)
OUTCOME_USE = "FAILURE_COHORT_STOPPING_ONLY_NO_POLICY_PERFORMANCE_ESTIMAND"
COMPLETE_PANEL_ORDER_RULE = (
    "TASK_TYPE_ROUND_ROBIN_OVER_WITHIN_TYPE_FORMAL_SHA256_RANK_V1"
)
SELECTED_FAILURE_RULE = "FIRST_42_FAILURES_IN_FROZEN_PANEL_ORDER_V1"


def _text(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or any(ch in value for ch in ("\x00", "\r", "\n"))
    ):
        raise ValueError(f"{name} must be nonempty single-line str")
    return value


def _sha_domain(domain: str, payload: object) -> str:
    return sha256_bytes(
        domain.encode("utf-8") + b"\0" + canonical_json_bytes(payload)
    )


def formal_panel_order_score_v1(task_gamefile_group_id: str) -> str:
    require_lower_sha256("task_gamefile_group_id", task_gamefile_group_id)
    return hashlib.sha256(
        (PANEL_ORDER_DOMAIN_V1 + "\0" + task_gamefile_group_id).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class FormalCollectionPolicyIdentityV1:
    logical_condition_id: str
    checkpoint_instance_id: str
    training_seed: int
    served_model_name: str
    adapter_bundle_sha256: str
    policy_runtime_manifest_sha256: str
    server_runtime_manifest_sha256: str
    raw_protocol_sha256: str
    policy_request_schema_sha256: str
    memory_mode: str = MEMORY_MODE
    harness_mode: str = HARNESS_MODE
    request_kind: str = REQUEST_KIND

    def __post_init__(self) -> None:
        if self.logical_condition_id != PRIMARY_LOGICAL_CONDITION_ID:
            raise ValueError("Formal collection logical condition mismatch")
        if self.checkpoint_instance_id != PRIMARY_CHECKPOINT_INSTANCE_ID:
            raise ValueError("Formal collection checkpoint identity mismatch")
        if self.training_seed != PRIMARY_TRAINING_SEED:
            raise ValueError("Formal collection training seed mismatch")
        _text("served_model_name", self.served_model_name)
        for name in (
            "adapter_bundle_sha256",
            "policy_runtime_manifest_sha256",
            "server_runtime_manifest_sha256",
            "raw_protocol_sha256",
            "policy_request_schema_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        if self.memory_mode != MEMORY_MODE:
            raise ValueError("Formal collection must keep Memory OFF")
        if self.harness_mode != HARNESS_MODE:
            raise ValueError("Formal collection must keep Harness OFF")
        if self.request_kind != REQUEST_KIND:
            raise ValueError("Formal collection must use R0")

    def to_dict(self) -> dict[str, object]:
        return {
            "logical_condition_id": self.logical_condition_id,
            "checkpoint_instance_id": self.checkpoint_instance_id,
            "training_seed": self.training_seed,
            "served_model_name": self.served_model_name,
            "adapter_bundle_sha256": self.adapter_bundle_sha256,
            "policy_runtime_manifest_sha256": self.policy_runtime_manifest_sha256,
            "server_runtime_manifest_sha256": self.server_runtime_manifest_sha256,
            "raw_protocol_sha256": self.raw_protocol_sha256,
            "policy_request_schema_sha256": self.policy_request_schema_sha256,
            "memory_mode": self.memory_mode,
            "harness_mode": self.harness_mode,
            "request_kind": self.request_kind,
        }

    @classmethod
    def from_dict(cls, value: object) -> "FormalCollectionPolicyIdentityV1":
        if not isinstance(value, dict):
            raise TypeError("Formal policy identity must be object")
        expected = set(cls.__dataclass_fields__)
        if set(value) != expected:
            raise ValueError("Formal policy identity fields mismatch")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class FormalPanelEntryV1:
    panel_index: int
    batch_index: int
    task_access_record_line_index: int
    task_access_record_sha256: str
    trial_id: str
    task_type: str
    dataset_relative_gamefile: str
    absolute_gamefile: str
    gamefile_sha256: str
    task_gamefile_group_id: str
    order_score: str

    def __post_init__(self) -> None:
        require_nonnegative_int("panel_index", self.panel_index)
        require_nonnegative_int("batch_index", self.batch_index)
        require_nonnegative_int(
            "task_access_record_line_index", self.task_access_record_line_index
        )
        if self.batch_index != self.panel_index // FORMAL_BATCH_SIZE:
            raise ValueError("Formal batch_index mismatch")
        require_lower_sha256(
            "task_access_record_sha256", self.task_access_record_sha256
        )
        _text("trial_id", self.trial_id)
        _text("task_type", self.task_type)
        _text("dataset_relative_gamefile", self.dataset_relative_gamefile)
        _text("absolute_gamefile", self.absolute_gamefile)
        if not Path(self.absolute_gamefile).is_absolute():
            raise ValueError("absolute_gamefile must be absolute")
        require_lower_sha256("gamefile_sha256", self.gamefile_sha256)
        require_lower_sha256("task_gamefile_group_id", self.task_gamefile_group_id)
        require_lower_sha256("order_score", self.order_score)

        expected_group = canonical_task_gamefile_group_id(
            relative_gamefile=self.dataset_relative_gamefile,
            gamefile_sha256=self.gamefile_sha256,
        )
        if self.task_gamefile_group_id != expected_group:
            raise ValueError("task/gamefile group identity mismatch")
        if self.order_score != formal_panel_order_score_v1(
            self.task_gamefile_group_id
        ):
            raise ValueError("Formal panel order score mismatch")

    def to_dict(self) -> dict[str, object]:
        return {
            "panel_index": self.panel_index,
            "batch_index": self.batch_index,
            "task_access_record_line_index": self.task_access_record_line_index,
            "task_access_record_sha256": self.task_access_record_sha256,
            "trial_id": self.trial_id,
            "task_type": self.task_type,
            "dataset_relative_gamefile": self.dataset_relative_gamefile,
            "absolute_gamefile": self.absolute_gamefile,
            "gamefile_sha256": self.gamefile_sha256,
            "task_gamefile_group_id": self.task_gamefile_group_id,
            "order_score": self.order_score,
        }

    @classmethod
    def from_dict(cls, value: object) -> "FormalPanelEntryV1":
        if not isinstance(value, dict):
            raise TypeError("Formal panel entry must be object")
        if set(value) != set(cls.__dataclass_fields__):
            raise ValueError("Formal panel entry fields mismatch")
        return cls(**value)


def build_complete_formal_panel_order_v1(
    entries: tuple[FormalPanelEntryV1, ...],
) -> tuple[FormalPanelEntryV1, ...]:
    if type(entries) is not tuple or not entries:
        raise ValueError("entries must be nonempty tuple")
    if any(not isinstance(item, FormalPanelEntryV1) for item in entries):
        raise TypeError("entries contain invalid item")

    by_type: dict[str, list[FormalPanelEntryV1]] = {}
    for item in entries:
        by_type.setdefault(item.task_type, []).append(item)
    for task_type in by_type:
        by_type[task_type].sort(
            key=lambda item: (item.order_score, item.task_gamefile_group_id)
        )

    ordered: list[FormalPanelEntryV1] = []
    rank = 0
    task_types = tuple(sorted(by_type))
    while True:
        added = False
        for task_type in task_types:
            ranked = by_type[task_type]
            if rank >= len(ranked):
                continue
            item = ranked[rank]
            index = len(ordered)
            ordered.append(
                FormalPanelEntryV1(
                    panel_index=index,
                    batch_index=index // FORMAL_BATCH_SIZE,
                    task_access_record_line_index=item.task_access_record_line_index,
                    task_access_record_sha256=item.task_access_record_sha256,
                    trial_id=item.trial_id,
                    task_type=item.task_type,
                    dataset_relative_gamefile=item.dataset_relative_gamefile,
                    absolute_gamefile=item.absolute_gamefile,
                    gamefile_sha256=item.gamefile_sha256,
                    task_gamefile_group_id=item.task_gamefile_group_id,
                    order_score=item.order_score,
                )
            )
            added = True
        if not added:
            break
        rank += 1
    return tuple(ordered)


@dataclass(frozen=True, slots=True)
class FormalPanelManifestV1:
    schema_id: str
    schema_version: int
    collection_context: str
    collection_code_commit: str
    runtime_binding_sha256: str
    task_access_protected_manifest_sha256: str
    exclusion_manifest_sha256: str
    complete_panel_order_rule: str
    batch_size: int
    stopping_failure_target: int
    stopping_rule_id: str
    outcome_use: str
    performance_estimand: str
    policy_identity: FormalCollectionPolicyIdentityV1
    eligible_entry_count: int
    entries: tuple[FormalPanelEntryV1, ...]
    panel_manifest_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.schema_id != FORMAL_PANEL_SCHEMA_V1 or self.schema_version != 1:
            raise ValueError("Formal panel manifest schema mismatch")
        if self.collection_context != FORMAL_COLLECTION_CONTEXT_V1:
            raise ValueError("Formal collection context mismatch")
        if (
            not isinstance(self.collection_code_commit, str)
            or len(self.collection_code_commit) != 40
            or any(ch not in "0123456789abcdef" for ch in self.collection_code_commit)
        ):
            raise ValueError("collection_code_commit must be 40 lowercase hex")
        for name in (
            "runtime_binding_sha256",
            "task_access_protected_manifest_sha256",
            "exclusion_manifest_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        if self.task_access_protected_manifest_sha256 != PROTECTED_TASK_ACCESS_SHA256:
            raise ValueError("task-access authority SHA mismatch")
        if self.complete_panel_order_rule != COMPLETE_PANEL_ORDER_RULE:
            raise ValueError("Formal panel order rule mismatch")
        if self.batch_size != FORMAL_BATCH_SIZE:
            raise ValueError("Formal batch size mismatch")
        if self.stopping_failure_target != FORMAL_STOPPING_FAILURE_TARGET:
            raise ValueError("Formal stopping target mismatch")
        if self.stopping_rule_id != STOPPING_RULE_ID:
            raise ValueError("Formal stopping rule mismatch")
        if self.outcome_use != OUTCOME_USE:
            raise ValueError("Formal outcome-use mismatch")
        if self.performance_estimand != NO_PERFORMANCE_ESTIMAND:
            raise ValueError("Formal collection must declare NO_PERFORMANCE_ESTIMAND")
        if not isinstance(self.policy_identity, FormalCollectionPolicyIdentityV1):
            raise TypeError("Formal policy identity type mismatch")
        require_nonnegative_int("eligible_entry_count", self.eligible_entry_count)
        if self.eligible_entry_count < FORMAL_STOPPING_FAILURE_TARGET:
            raise ValueError("Formal eligible panel has fewer than 42 tasks")
        if type(self.entries) is not tuple or len(self.entries) != self.eligible_entry_count:
            raise ValueError("Formal eligible entry count mismatch")
        if any(not isinstance(item, FormalPanelEntryV1) for item in self.entries):
            raise TypeError("Formal entries contain invalid item")
        indices = tuple(item.panel_index for item in self.entries)
        if indices != tuple(range(len(self.entries))):
            raise ValueError("Formal panel indices must be contiguous")
        groups = tuple(item.task_gamefile_group_id for item in self.entries)
        if len(groups) != len(set(groups)):
            raise ValueError("Formal panel duplicate task/gamefile group")

        expected = _sha_domain(PANEL_MANIFEST_DOMAIN_V1, self._payload_without_sha())
        if self.panel_manifest_sha256 is None:
            object.__setattr__(self, "panel_manifest_sha256", expected)
        elif self.panel_manifest_sha256 != expected:
            raise ValueError("Formal panel SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "collection_context": self.collection_context,
            "collection_code_commit": self.collection_code_commit,
            "runtime_binding_sha256": self.runtime_binding_sha256,
            "task_access_protected_manifest_sha256":
                self.task_access_protected_manifest_sha256,
            "exclusion_manifest_sha256": self.exclusion_manifest_sha256,
            "complete_panel_order_rule": self.complete_panel_order_rule,
            "batch_size": self.batch_size,
            "stopping_failure_target": self.stopping_failure_target,
            "stopping_rule_id": self.stopping_rule_id,
            "outcome_use": self.outcome_use,
            "performance_estimand": self.performance_estimand,
            "policy_identity": self.policy_identity.to_dict(),
            "eligible_entry_count": self.eligible_entry_count,
            "entries": [item.to_dict() for item in self.entries],
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._payload_without_sha(),
                "panel_manifest_sha256": self.panel_manifest_sha256}

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> "FormalPanelManifestV1":
        if not isinstance(value, dict):
            raise TypeError("Formal panel manifest must be object")
        raw_entries = value.get("entries")
        if not isinstance(raw_entries, list):
            raise TypeError("Formal entries must be JSON array")
        expected = set(cls.__dataclass_fields__)
        if set(value) != expected:
            raise ValueError("Formal panel manifest fields mismatch")
        return cls(
            **{
                **value,
                "policy_identity": FormalCollectionPolicyIdentityV1.from_dict(
                    value["policy_identity"]
                ),
                "entries": tuple(
                    FormalPanelEntryV1.from_dict(item) for item in raw_entries
                ),
            }
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> "FormalPanelManifestV1":
        return cls.from_dict(strict_json_loads(value))


@dataclass(frozen=True, slots=True)
class FormalCollectionCaseReceiptV1:
    schema_id: str
    schema_version: int
    panel_manifest_sha256: str
    panel_index: int
    batch_index: int
    task_access_record_line_index: int
    task_access_record_sha256: str
    task_gamefile_group_id: str
    source_task_id: str
    execution_attempt_id: str
    attempt_bundle_sha256: str
    scientific_outcome_status: str
    success: bool
    termination_reason: str
    outcome_use: str
    performance_estimand: str
    previous_receipt_sha256: str | None
    receipt_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.schema_id != FORMAL_CASE_RECEIPT_V1 or self.schema_version != 1:
            raise ValueError("Formal receipt schema mismatch")
        for name in (
            "panel_manifest_sha256",
            "task_access_record_sha256",
            "task_gamefile_group_id",
            "attempt_bundle_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        require_nonnegative_int("panel_index", self.panel_index)
        require_nonnegative_int("batch_index", self.batch_index)
        require_nonnegative_int(
            "task_access_record_line_index", self.task_access_record_line_index
        )
        if self.batch_index != self.panel_index // FORMAL_BATCH_SIZE:
            raise ValueError("Formal receipt batch mismatch")
        _text("source_task_id", self.source_task_id)
        _text("execution_attempt_id", self.execution_attempt_id)
        _text("scientific_outcome_status", self.scientific_outcome_status)
        if type(self.success) is not bool:
            raise TypeError("success must be bool")
        _text("termination_reason", self.termination_reason)
        if self.outcome_use != OUTCOME_USE:
            raise ValueError("Formal receipt outcome-use mismatch")
        if self.performance_estimand != NO_PERFORMANCE_ESTIMAND:
            raise ValueError("Formal receipt performance boundary mismatch")
        if self.previous_receipt_sha256 is not None:
            require_lower_sha256(
                "previous_receipt_sha256", self.previous_receipt_sha256
            )
        expected = _sha_domain(CASE_RECEIPT_DOMAIN_V1, self._payload_without_sha())
        if self.receipt_sha256 is None:
            object.__setattr__(self, "receipt_sha256", expected)
        elif self.receipt_sha256 != expected:
            raise ValueError("Formal receipt SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "receipt_sha256"
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._payload_without_sha(), "receipt_sha256": self.receipt_sha256}

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> "FormalCollectionCaseReceiptV1":
        if not isinstance(value, dict):
            raise TypeError("Formal receipt must be object")
        if set(value) != set(cls.__dataclass_fields__):
            raise ValueError("Formal receipt fields mismatch")
        return cls(**value)

    @classmethod
    def from_json(cls, value: str | bytes) -> "FormalCollectionCaseReceiptV1":
        return cls.from_dict(strict_json_loads(value))


def read_formal_collection_ledger_v1(
    path: Path,
) -> tuple[FormalCollectionCaseReceiptV1, ...]:
    path = Path(path)
    if not path.exists():
        return ()
    if path.is_symlink() or not path.is_file():
        raise ValueError("Formal ledger path invalid")
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise ValueError("Formal ledger lacks terminal LF")
    receipts = tuple(
        FormalCollectionCaseReceiptV1.from_json(line)
        for line in data.splitlines()
        if line
    )
    previous = None
    for expected_index, receipt in enumerate(receipts):
        if receipt.panel_index != expected_index:
            raise ValueError("Formal ledger must preserve panel prefix")
        if receipt.previous_receipt_sha256 != previous:
            raise ValueError("Formal receipt hash chain mismatch")
        previous = receipt.receipt_sha256
    return receipts


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("os.write made no progress")
        view = view[written:]


def append_formal_collection_receipt_v1(
    *,
    path: Path,
    receipt: FormalCollectionCaseReceiptV1,
) -> None:
    path = Path(path)
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("Formal ledger parent invalid")
    if path.is_symlink():
        raise ValueError("Formal ledger symlink forbidden")
    lock = parent / f".{path.name}.lock"
    lock_fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        existing = read_formal_collection_ledger_v1(path)
        expected_index = len(existing)
        expected_previous = None if not existing else existing[-1].receipt_sha256
        if receipt.panel_index != expected_index:
            raise ValueError("Formal receipt is not next panel prefix")
        if receipt.previous_receipt_sha256 != expected_previous:
            raise ValueError("Formal receipt previous SHA mismatch")
        old = b"" if not path.exists() else path.read_bytes()
        temp = parent / f".{path.name}.{receipt.receipt_sha256}.tmp"
        if temp.exists() or temp.is_symlink():
            raise FileExistsError(str(temp))
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            _write_all(fd, old + receipt.canonical_bytes())
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(temp, path)
        dfd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
        observed = read_formal_collection_ledger_v1(path)
        if observed[-1] != receipt:
            raise RuntimeError("Formal ledger verification failed")
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def stopping_decision_after_complete_prefix_v1(
    receipts: tuple[FormalCollectionCaseReceiptV1, ...],
    *,
    panel_size: int,
) -> str:
    if type(receipts) is not tuple:
        raise TypeError("receipts must be tuple")
    if type(panel_size) is not int or panel_size <= 0:
        raise ValueError("panel_size must be positive int")
    if len(receipts) > panel_size:
        raise ValueError("receipt prefix exceeds panel size")
    if len(receipts) == panel_size:
        return "STOP_PANEL_EXHAUSTED"
    if len(receipts) == 0 or len(receipts) % FORMAL_BATCH_SIZE != 0:
        return "CONTINUE"
    failures = sum(1 for receipt in receipts if receipt.success is False)
    if failures >= FORMAL_STOPPING_FAILURE_TARGET:
        return "STOP_FAILURE_TARGET_REACHED"
    return "CONTINUE"


@dataclass(frozen=True, slots=True)
class FormalFailureReferenceV1:
    panel_index: int
    case_receipt_sha256: str
    execution_attempt_id: str
    attempt_bundle_sha256: str

    def __post_init__(self) -> None:
        require_nonnegative_int("panel_index", self.panel_index)
        require_lower_sha256("case_receipt_sha256", self.case_receipt_sha256)
        _text("execution_attempt_id", self.execution_attempt_id)
        require_lower_sha256("attempt_bundle_sha256", self.attempt_bundle_sha256)

    def to_dict(self) -> dict[str, object]:
        return {
            "panel_index": self.panel_index,
            "case_receipt_sha256": self.case_receipt_sha256,
            "execution_attempt_id": self.execution_attempt_id,
            "attempt_bundle_sha256": self.attempt_bundle_sha256,
        }


@dataclass(frozen=True, slots=True)
class FormalSelectedFailurePanelV1:
    schema_id: str
    schema_version: int
    panel_manifest_sha256: str
    collection_ledger_sha256: str
    selection_rule: str
    performance_estimand: str
    selected_failures: tuple[FormalFailureReferenceV1, ...]
    selected_panel_sha256: str | None = None

    def __post_init__(self) -> None:
        if (
            self.schema_id != FORMAL_SELECTED_FAILURE_PANEL_V1
            or self.schema_version != 1
        ):
            raise ValueError("Formal selected panel schema mismatch")
        require_lower_sha256("panel_manifest_sha256", self.panel_manifest_sha256)
        require_lower_sha256(
            "collection_ledger_sha256", self.collection_ledger_sha256
        )
        if self.selection_rule != SELECTED_FAILURE_RULE:
            raise ValueError("Formal failure selection rule mismatch")
        if self.performance_estimand != NO_PERFORMANCE_ESTIMAND:
            raise ValueError("Formal selected panel must have no performance estimand")
        if type(self.selected_failures) is not tuple:
            raise TypeError("selected_failures must be tuple")
        if len(self.selected_failures) != FORMAL_STOPPING_FAILURE_TARGET:
            raise ValueError("Formal selected panel requires exactly 42 failures")
        indices = tuple(item.panel_index for item in self.selected_failures)
        if indices != tuple(sorted(indices)) or len(set(indices)) != len(indices):
            raise ValueError("Formal failures must preserve frozen panel order")
        expected = _sha_domain(
            SELECTED_PANEL_DOMAIN_V1, self._payload_without_sha()
        )
        if self.selected_panel_sha256 is None:
            object.__setattr__(self, "selected_panel_sha256", expected)
        elif self.selected_panel_sha256 != expected:
            raise ValueError("Formal selected panel SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "panel_manifest_sha256": self.panel_manifest_sha256,
            "collection_ledger_sha256": self.collection_ledger_sha256,
            "selection_rule": self.selection_rule,
            "performance_estimand": self.performance_estimand,
            "selected_failures": [
                item.to_dict() for item in self.selected_failures
            ],
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "selected_panel_sha256": self.selected_panel_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


def build_selected_formal_failures_v1(
    *,
    panel_manifest_sha256: str,
    collection_ledger_path: Path,
) -> FormalSelectedFailurePanelV1:
    receipts = read_formal_collection_ledger_v1(collection_ledger_path)
    failures = tuple(receipt for receipt in receipts if receipt.success is False)
    if len(failures) < FORMAL_STOPPING_FAILURE_TARGET:
        raise ValueError("at least 42 Formal failures are required")
    selected = failures[:FORMAL_STOPPING_FAILURE_TARGET]
    return FormalSelectedFailurePanelV1(
        schema_id=FORMAL_SELECTED_FAILURE_PANEL_V1,
        schema_version=1,
        panel_manifest_sha256=panel_manifest_sha256,
        collection_ledger_sha256=hashlib.sha256(
            Path(collection_ledger_path).read_bytes()
        ).hexdigest(),
        selection_rule=SELECTED_FAILURE_RULE,
        performance_estimand=NO_PERFORMANCE_ESTIMAND,
        selected_failures=tuple(
            FormalFailureReferenceV1(
                panel_index=item.panel_index,
                case_receipt_sha256=item.receipt_sha256,
                execution_attempt_id=item.execution_attempt_id,
                attempt_bundle_sha256=item.attempt_bundle_sha256,
            )
            for item in selected
        ),
        selected_panel_sha256=None,
    )

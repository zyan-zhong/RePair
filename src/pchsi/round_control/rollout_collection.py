"""Generic round-entry rollout collection contracts and deterministic control.

This module is deliberately environment- and model-client neutral.  It binds
existing rollout execution, receipt, and evidence components without creating a
second evaluator or a second scientific framework.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Callable, Iterable, Mapping, Sequence


_HEX = frozenset("0123456789abcdef")


def _require_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty str")
    if any(ch in value for ch in ("\x00", "\r", "\n")):
        raise ValueError(f"{name} contains forbidden control character")
    return value


def _require_sha(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in _HEX for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _domain_sha(domain: str, payload: Mapping[str, object]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\0" + _canonical(dict(payload))
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class RoundRolloutCollectionRequestV1:
    round_id: str
    execution_attempt_id: str
    parent_policy_id: str
    parent_policy_artifact_sha256: str
    policy_runtime_binding_sha256: str
    execution_profile_sha256: str
    train_update_manifest_sha256: str
    round_memory_runtime_authority_sha256: str
    round_start_memory_snapshot_sha256: str
    token_budget_contract_sha256: str
    execution_namespace: str
    rollout_seed: int
    benchmark_feedback_authorized: bool = False
    invalid_attempt_adaptive_evidence_reuse_authorized: bool = False
    request_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "round_id",
            "execution_attempt_id",
            "parent_policy_id",
            "execution_namespace",
        ):
            _require_text(name, getattr(self, name))
        for name in (
            "parent_policy_artifact_sha256",
            "policy_runtime_binding_sha256",
            "execution_profile_sha256",
            "train_update_manifest_sha256",
            "round_memory_runtime_authority_sha256",
            "round_start_memory_snapshot_sha256",
            "token_budget_contract_sha256",
        ):
            _require_sha(name, getattr(self, name))
        if type(self.rollout_seed) is not int or self.rollout_seed < 0:
            raise ValueError("rollout_seed must be non-negative int")
        if self.benchmark_feedback_authorized is not False:
            raise ValueError("benchmark feedback is forbidden in adaptive rollout")
        if self.invalid_attempt_adaptive_evidence_reuse_authorized is not False:
            raise ValueError("invalid-attempt adaptive evidence reuse is forbidden")
        expected = _domain_sha(
            "ROUND_ROLLOUT_COLLECTION_REQUEST_V1",
            self._without_sha(),
        )
        if self.request_sha256 is None:
            object.__setattr__(self, "request_sha256", expected)
        elif self.request_sha256 != expected:
            raise ValueError("request SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "schema_id": "ROUND_ROLLOUT_COLLECTION_REQUEST_V1",
            "schema_version": 1,
            "round_id": self.round_id,
            "execution_attempt_id": self.execution_attempt_id,
            "parent_policy_id": self.parent_policy_id,
            "parent_policy_artifact_sha256": self.parent_policy_artifact_sha256,
            "policy_runtime_binding_sha256": self.policy_runtime_binding_sha256,
            "execution_profile_sha256": self.execution_profile_sha256,
            "train_update_manifest_sha256": self.train_update_manifest_sha256,
            "round_memory_runtime_authority_sha256": (
                self.round_memory_runtime_authority_sha256
            ),
            "round_start_memory_snapshot_sha256": (
                self.round_start_memory_snapshot_sha256
            ),
            "token_budget_contract_sha256": self.token_budget_contract_sha256,
            "execution_namespace": self.execution_namespace,
            "rollout_seed": self.rollout_seed,
            "benchmark_feedback_authorized": False,
            "invalid_attempt_adaptive_evidence_reuse_authorized": False,
            "selection_rule": "FULL_FROZEN_TRAIN_UPDATE_UNIVERSE",
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._without_sha(), "request_sha256": self.request_sha256}


@dataclass(frozen=True, slots=True)
class RoundRolloutExecutionBindingV1:
    request_sha256: str
    rollout_control_source_sha256: str
    clean_execution_binding_source_sha256: str
    episode_evaluator_source_sha256: str
    attempt_receipts_source_sha256: str
    policy_runtime_adapter_sha256: str
    scientific_execution_authorized: bool
    binding_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "request_sha256",
            "rollout_control_source_sha256",
            "clean_execution_binding_source_sha256",
            "episode_evaluator_source_sha256",
            "attempt_receipts_source_sha256",
            "policy_runtime_adapter_sha256",
        ):
            _require_sha(name, getattr(self, name))
        if type(self.scientific_execution_authorized) is not bool:
            raise TypeError("scientific_execution_authorized must be bool")
        expected = _domain_sha(
            "ROUND_ROLLOUT_EXECUTION_BINDING_V1",
            self._without_sha(),
        )
        if self.binding_sha256 is None:
            object.__setattr__(self, "binding_sha256", expected)
        elif self.binding_sha256 != expected:
            raise ValueError("binding SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "schema_id": "ROUND_ROLLOUT_EXECUTION_BINDING_V1",
            "schema_version": 1,
            "request_sha256": self.request_sha256,
            "rollout_control_source_sha256": self.rollout_control_source_sha256,
            "clean_execution_binding_source_sha256": (
                self.clean_execution_binding_source_sha256
            ),
            "episode_evaluator_source_sha256": self.episode_evaluator_source_sha256,
            "attempt_receipts_source_sha256": self.attempt_receipts_source_sha256,
            "policy_runtime_adapter_sha256": self.policy_runtime_adapter_sha256,
            "scientific_execution_authorized": self.scientific_execution_authorized,
            "shell": False,
            "human_runtime_selection_required": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._without_sha(), "binding_sha256": self.binding_sha256}


@dataclass(frozen=True, slots=True)
class RoundEpisodeTerminalV1:
    scientific_cell_id: str
    execution_attempt_id: str
    task_id: str
    task_index: int
    status: str
    success: bool | None
    terminal_receipt_sha256: str

    def __post_init__(self) -> None:
        for name in ("scientific_cell_id", "execution_attempt_id", "task_id"):
            _require_text(name, getattr(self, name))
        if type(self.task_index) is not int or self.task_index < 0:
            raise ValueError("task_index must be non-negative int")
        if self.status not in {
            "SCIENTIFIC_SUCCESS",
            "SCIENTIFIC_FAILURE",
            "INFRASTRUCTURE_INVALID",
            "PROTOCOL_INVALID",
        }:
            raise ValueError("unsupported terminal status")
        if self.status == "SCIENTIFIC_SUCCESS" and self.success is not True:
            raise ValueError("success terminal requires success=True")
        if self.status == "SCIENTIFIC_FAILURE" and self.success is not False:
            raise ValueError("failure terminal requires success=False")
        if self.status in {"INFRASTRUCTURE_INVALID", "PROTOCOL_INVALID"}:
            if self.success is not None:
                raise ValueError("invalid terminal cannot claim task success/failure")
        _require_sha("terminal_receipt_sha256", self.terminal_receipt_sha256)

    def to_dict(self) -> dict[str, object]:
        return {
            "scientific_cell_id": self.scientific_cell_id,
            "execution_attempt_id": self.execution_attempt_id,
            "task_id": self.task_id,
            "task_index": self.task_index,
            "status": self.status,
            "success": self.success,
            "terminal_receipt_sha256": self.terminal_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class RoundRolloutUniverseSealV1:
    request_sha256: str
    terminal_rows: tuple[RoundEpisodeTerminalV1, ...]
    scheduled_count: int
    success_count: int
    failure_count: int
    infrastructure_invalid_count: int
    protocol_invalid_count: int
    scientific_rollout_valid: bool
    seal_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_sha("request_sha256", self.request_sha256)
        if type(self.terminal_rows) is not tuple:
            raise TypeError("terminal_rows must be tuple")
        observed = len(self.terminal_rows)
        for name, value in (
            ("scheduled_count", self.scheduled_count),
            ("success_count", self.success_count),
            ("failure_count", self.failure_count),
            ("infrastructure_invalid_count", self.infrastructure_invalid_count),
            ("protocol_invalid_count", self.protocol_invalid_count),
        ):
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be non-negative int")
        if self.scheduled_count != observed:
            raise ValueError("scheduled count mismatch")
        if (
            self.success_count
            + self.failure_count
            + self.infrastructure_invalid_count
            + self.protocol_invalid_count
            != observed
        ):
            raise ValueError("terminal census mismatch")
        expected_valid = (
            self.infrastructure_invalid_count == 0
            and self.protocol_invalid_count == 0
        )
        if self.scientific_rollout_valid is not expected_valid:
            raise ValueError("scientific rollout validity mismatch")
        ids = tuple(row.scientific_cell_id for row in self.terminal_rows)
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate scientific cell id")
        expected = _domain_sha(
            "ROUND_ROLLOUT_UNIVERSE_SEAL_V1",
            self._without_sha(),
        )
        if self.seal_sha256 is None:
            object.__setattr__(self, "seal_sha256", expected)
        elif self.seal_sha256 != expected:
            raise ValueError("universe seal SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "schema_id": "ROUND_ROLLOUT_UNIVERSE_SEAL_V1",
            "schema_version": 1,
            "request_sha256": self.request_sha256,
            "terminal_rows": [row.to_dict() for row in self.terminal_rows],
            "scheduled_count": self.scheduled_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "infrastructure_invalid_count": self.infrastructure_invalid_count,
            "protocol_invalid_count": self.protocol_invalid_count,
            "scientific_rollout_valid": self.scientific_rollout_valid,
            "benchmark_feedback_used": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._without_sha(), "seal_sha256": self.seal_sha256}


@dataclass(frozen=True, slots=True)
class RoundFailureCohortSelectionManifestV1:
    universe_seal_sha256: str
    failure_scientific_cell_ids: tuple[str, ...]
    selection_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_sha("universe_seal_sha256", self.universe_seal_sha256)
        if type(self.failure_scientific_cell_ids) is not tuple:
            raise TypeError("failure_scientific_cell_ids must be tuple")
        if any(not isinstance(x, str) or not x for x in self.failure_scientific_cell_ids):
            raise ValueError("failure cohort id invalid")
        if len(self.failure_scientific_cell_ids) != len(set(self.failure_scientific_cell_ids)):
            raise ValueError("failure cohort contains duplicates")
        expected = _domain_sha(
            "ROUND_FAILURE_COHORT_SELECTION_MANIFEST_V1",
            self._without_sha(),
        )
        if self.selection_sha256 is None:
            object.__setattr__(self, "selection_sha256", expected)
        elif self.selection_sha256 != expected:
            raise ValueError("failure cohort SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "schema_id": "ROUND_FAILURE_COHORT_SELECTION_MANIFEST_V1",
            "schema_version": 1,
            "universe_seal_sha256": self.universe_seal_sha256,
            "selection_rule": "ALL_SCIENTIFIC_FAILURES_IN_FROZEN_ROLLOUT_ORDER",
            "failure_scientific_cell_ids": list(self.failure_scientific_cell_ids),
            "human_selection_performed": False,
            "outcome_adaptive_reselection_allowed": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._without_sha(), "selection_sha256": self.selection_sha256}


def seal_rollout_universe(
    *,
    request_sha256: str,
    terminals: Iterable[RoundEpisodeTerminalV1],
) -> RoundRolloutUniverseSealV1:
    rows = tuple(terminals)
    return RoundRolloutUniverseSealV1(
        request_sha256=request_sha256,
        terminal_rows=rows,
        scheduled_count=len(rows),
        success_count=sum(r.status == "SCIENTIFIC_SUCCESS" for r in rows),
        failure_count=sum(r.status == "SCIENTIFIC_FAILURE" for r in rows),
        infrastructure_invalid_count=sum(
            r.status == "INFRASTRUCTURE_INVALID" for r in rows
        ),
        protocol_invalid_count=sum(r.status == "PROTOCOL_INVALID" for r in rows),
        scientific_rollout_valid=not any(
            r.status in {"INFRASTRUCTURE_INVALID", "PROTOCOL_INVALID"} for r in rows
        ),
    )


def build_failure_cohort(
    universe: RoundRolloutUniverseSealV1,
) -> RoundFailureCohortSelectionManifestV1:
    if not isinstance(universe, RoundRolloutUniverseSealV1):
        raise TypeError("universe must be RoundRolloutUniverseSealV1")
    if universe.scientific_rollout_valid is not True:
        raise ValueError("cannot materialize scientific failure cohort from invalid rollout")
    return RoundFailureCohortSelectionManifestV1(
        universe_seal_sha256=universe.seal_sha256,
        failure_scientific_cell_ids=tuple(
            row.scientific_cell_id
            for row in universe.terminal_rows
            if row.status == "SCIENTIFIC_FAILURE"
        ),
    )


def execute_generic_rollout_control(
    *,
    request: RoundRolloutCollectionRequestV1,
    scheduled_items: Sequence[object],
    run_one: Callable[[object], RoundEpisodeTerminalV1],
) -> tuple[RoundRolloutUniverseSealV1, RoundFailureCohortSelectionManifestV1]:
    """Execute a deterministic frozen schedule through an injected existing runner.

    The caller owns environment/model construction.  This control layer only
    governs schedule completeness, terminal census, and cohort materialization.
    """
    if not isinstance(request, RoundRolloutCollectionRequestV1):
        raise TypeError("request type mismatch")
    rows = tuple(run_one(item) for item in tuple(scheduled_items))
    universe = seal_rollout_universe(
        request_sha256=request.request_sha256,
        terminals=rows,
    )
    cohort = build_failure_cohort(universe)
    return universe, cohort

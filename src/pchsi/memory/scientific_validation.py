"""Pure scientific contracts for Memory Scientific Validation V1.

This module contains no model, environment, retriever, network, or process
execution. It freezes identities, local effect semantics, infrastructure retry
semantics, and downstream isolation rules before any Memory-ON outcome exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Iterable, Mapping


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
A0_ARM_ORDER = ("M0", "M1", "M2", "M3")
DIRECT_RETRIEVAL_MODE = "DIRECT_FIXED_RECORD_NO_RETRIEVAL"


def _require_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"{name} must be nonempty NUL-free str")
    return value


def _require_sha(name: str, value: object) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _require_git_commit(name: str, value: object) -> str:
    if not isinstance(value, str) or GIT_COMMIT_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be 40-lowercase-hex Git commit")
    return value


def _require_nonnegative_int(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be nonnegative int")
    return value


def _require_positive_int(name: str, value: object) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be positive int")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _domain_sha(domain: str, payload: object) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\0"
        + _canonical_json_bytes(payload)
    ).hexdigest()


class EffectLabelV1(str, Enum):
    BENEFIT = "Benefit"
    HARM = "Harm"
    NEUTRAL = "Neutral"
    UNCERTAIN = "Uncertain"


class EffectScopeV1(str, Enum):
    SOURCE_STATE_LOCAL_PAIRED = "SOURCE_STATE_LOCAL_PAIRED"


class TerminalRelationV1(str, Enum):
    FAIL_TO_SUCCESS = "FAIL_TO_SUCCESS"
    SUCCESS_TO_FAIL = "SUCCESS_TO_FAIL"
    SAME_TERMINAL = "SAME_TERMINAL"
    UNRESOLVED = "UNRESOLVED"
    NO_SCIENTIFIC_OUTCOME = "NO_SCIENTIFIC_OUTCOME"


class MechanismEffectV1(str, Enum):
    OLD_FAILURE_AVOIDED = "OLD_FAILURE_AVOIDED"
    OLD_FAILURE_REPEATED = "OLD_FAILURE_REPEATED"
    DIFFERENT_FAILURE = "DIFFERENT_FAILURE"
    NOT_EVALUATED = "NOT_EVALUATED"


class InfrastructureDispositionV1(str, Enum):
    NONE = "NONE"
    RETRY_EXACT_SAME_FROZEN_CELL = "RETRY_EXACT_SAME_FROZEN_CELL"
    SCIENTIFIC_UNCERTAIN_OR_HARD_STOP = "SCIENTIFIC_UNCERTAIN_OR_HARD_STOP"


class AmendmentTriggerV1(str, Enum):
    PROTOCOL_DEFECT = "PROTOCOL_DEFECT"
    CONTAMINATION = "CONTAMINATION"
    CRITICAL_SAFETY_FAILURE = "CRITICAL_SAFETY_FAILURE"
    INVALID_SCIENTIFIC_IDENTITY = "INVALID_SCIENTIFIC_IDENTITY"


@dataclass(frozen=True, slots=True)
class A0ArmBindingV1:
    arm_id: str
    representation_class: str
    availability: str
    artifact_sha256: str | None
    policy_payload_sha256: str | None
    token_count: int
    retrieval_mode: str

    def __post_init__(self) -> None:
        if self.arm_id not in A0_ARM_ORDER:
            raise ValueError("arm_id must be M0/M1/M2/M3")
        _require_text("representation_class", self.representation_class)
        if self.availability != "AVAILABLE":
            raise ValueError("A0 core arms must be AVAILABLE")
        _require_nonnegative_int("token_count", self.token_count)
        if self.retrieval_mode != DIRECT_RETRIEVAL_MODE:
            raise ValueError("A0 must use direct fixed-record no-retrieval mode")
        if self.arm_id == "M0":
            if self.representation_class != "M0":
                raise ValueError("M0 representation class mismatch")
            if self.artifact_sha256 is not None:
                raise ValueError("M0 must not bind a Memory artifact")
            if self.policy_payload_sha256 is not None:
                raise ValueError("M0 must not bind a payload SHA")
            if self.token_count != 0:
                raise ValueError("M0 token count must be zero")
        else:
            _require_sha("artifact_sha256", self.artifact_sha256)
            _require_sha("policy_payload_sha256", self.policy_payload_sha256)
        if self.arm_id == "M3" and self.representation_class != "FM2":
            raise ValueError("A0 M3 is structured descriptive FM2 only")

    def to_dict(self) -> dict[str, object]:
        return {
            "arm_id": self.arm_id,
            "representation_class": self.representation_class,
            "availability": self.availability,
            "artifact_sha256": self.artifact_sha256,
            "policy_payload_sha256": self.policy_payload_sha256,
            "token_count": self.token_count,
            "retrieval_mode": self.retrieval_mode,
        }

    @classmethod
    def from_dict(cls, value: object) -> "A0ArmBindingV1":
        if not isinstance(value, dict):
            raise TypeError("A0 arm must be object")
        expected = {
            "arm_id",
            "representation_class",
            "availability",
            "artifact_sha256",
            "policy_payload_sha256",
            "token_count",
            "retrieval_mode",
        }
        if set(value) != expected:
            raise ValueError("A0 arm fields mismatch")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class A0SourceBindingV1:
    source_state_id: str
    source_task_id: str
    task_gamefile_group_id: str
    source_fingerprint_sha256: str
    source_bundle_sha256: str
    memory_lineage_id: str
    record_version: int
    snapshot_sha256: str
    representation_template_sha256: str
    continuation_seed: int
    arms: tuple[A0ArmBindingV1, ...]

    def __post_init__(self) -> None:
        _require_sha("source_state_id", self.source_state_id)
        _require_text("source_task_id", self.source_task_id)
        _require_text("task_gamefile_group_id", self.task_gamefile_group_id)
        _require_sha("source_fingerprint_sha256", self.source_fingerprint_sha256)
        _require_sha("source_bundle_sha256", self.source_bundle_sha256)
        _require_sha("memory_lineage_id", self.memory_lineage_id)
        _require_positive_int("record_version", self.record_version)
        _require_sha("snapshot_sha256", self.snapshot_sha256)
        _require_sha(
            "representation_template_sha256",
            self.representation_template_sha256,
        )
        _require_nonnegative_int("continuation_seed", self.continuation_seed)
        if type(self.arms) is not tuple or len(self.arms) != 4:
            raise ValueError("A0 source requires exactly four arms")
        if tuple(arm.arm_id for arm in self.arms) != A0_ARM_ORDER:
            raise ValueError("A0 source arm order mismatch")
        if len({arm.arm_id for arm in self.arms}) != 4:
            raise ValueError("duplicate A0 arm")

    def identity_payload(self) -> dict[str, object]:
        return {
            "source_state_id": self.source_state_id,
            "source_task_id": self.source_task_id,
            "task_gamefile_group_id": self.task_gamefile_group_id,
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "source_bundle_sha256": self.source_bundle_sha256,
            "memory_lineage_id": self.memory_lineage_id,
            "record_version": self.record_version,
            "snapshot_sha256": self.snapshot_sha256,
            "representation_template_sha256": self.representation_template_sha256,
            "continuation_seed": self.continuation_seed,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self.identity_payload(),
            "arms": [arm.to_dict() for arm in self.arms],
        }

    @classmethod
    def from_dict(cls, value: object) -> "A0SourceBindingV1":
        if not isinstance(value, dict):
            raise TypeError("A0 source binding must be object")
        expected = {
            "source_state_id",
            "source_task_id",
            "task_gamefile_group_id",
            "source_fingerprint_sha256",
            "source_bundle_sha256",
            "memory_lineage_id",
            "record_version",
            "snapshot_sha256",
            "representation_template_sha256",
            "continuation_seed",
            "arms",
        }
        if set(value) != expected:
            raise ValueError("A0 source-binding fields mismatch")
        raw_arms = value["arms"]
        if not isinstance(raw_arms, list):
            raise TypeError("arms must be array")
        return cls(
            source_state_id=value["source_state_id"],
            source_task_id=value["source_task_id"],
            task_gamefile_group_id=value["task_gamefile_group_id"],
            source_fingerprint_sha256=value["source_fingerprint_sha256"],
            source_bundle_sha256=value["source_bundle_sha256"],
            memory_lineage_id=value["memory_lineage_id"],
            record_version=value["record_version"],
            snapshot_sha256=value["snapshot_sha256"],
            representation_template_sha256=value[
                "representation_template_sha256"
            ],
            continuation_seed=value["continuation_seed"],
            arms=tuple(A0ArmBindingV1.from_dict(x) for x in raw_arms),
        )


@dataclass(frozen=True, slots=True)
class A0ScientificCellV1:
    source_state_id: str
    source_task_id: str
    task_gamefile_group_id: str
    source_fingerprint_sha256: str
    source_bundle_sha256: str
    memory_lineage_id: str
    record_version: int
    snapshot_sha256: str
    representation_template_sha256: str
    continuation_seed: int
    arm: A0ArmBindingV1
    effect_scope: EffectScopeV1 = EffectScopeV1.SOURCE_STATE_LOCAL_PAIRED
    scientific_execution_authorized: bool = False
    cell_id: str | None = None

    def __post_init__(self) -> None:
        if self.scientific_execution_authorized is not False:
            raise ValueError("frozen A0 manifest cannot self-authorize execution")
        _require_sha("source_state_id", self.source_state_id)
        _require_text("source_task_id", self.source_task_id)
        _require_text("task_gamefile_group_id", self.task_gamefile_group_id)
        _require_sha("source_fingerprint_sha256", self.source_fingerprint_sha256)
        _require_sha("source_bundle_sha256", self.source_bundle_sha256)
        _require_sha("memory_lineage_id", self.memory_lineage_id)
        _require_positive_int("record_version", self.record_version)
        _require_sha("snapshot_sha256", self.snapshot_sha256)
        _require_sha(
            "representation_template_sha256",
            self.representation_template_sha256,
        )
        _require_nonnegative_int("continuation_seed", self.continuation_seed)
        if not isinstance(self.arm, A0ArmBindingV1):
            raise TypeError("arm must be A0ArmBindingV1")
        expected = _domain_sha(
            "MEMORY_A0_SCIENTIFIC_CELL_V1",
            self._payload_without_id(),
        )
        if self.cell_id is None:
            object.__setattr__(self, "cell_id", expected)
        elif self.cell_id != expected:
            raise ValueError("cell_id mismatch")

    def _payload_without_id(self) -> dict[str, object]:
        return {
            "source_state_id": self.source_state_id,
            "source_task_id": self.source_task_id,
            "task_gamefile_group_id": self.task_gamefile_group_id,
            "source_fingerprint_sha256": self.source_fingerprint_sha256,
            "source_bundle_sha256": self.source_bundle_sha256,
            "memory_lineage_id": self.memory_lineage_id,
            "record_version": self.record_version,
            "snapshot_sha256": self.snapshot_sha256,
            "representation_template_sha256": self.representation_template_sha256,
            "continuation_seed": self.continuation_seed,
            "arm": self.arm.to_dict(),
            "effect_scope": self.effect_scope.value,
            "scientific_execution_authorized": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._payload_without_id(), "cell_id": self.cell_id}


@dataclass(frozen=True, slots=True)
class A0ScientificManifestV1:
    engineering_base_head: str
    sources: tuple[A0SourceBindingV1, ...]
    cells: tuple[A0ScientificCellV1, ...]
    scientific_execution_authorized: bool = False
    schema_id: str = "MEMORY_A0_SCIENTIFIC_MANIFEST_V1"
    schema_version: int = 1
    manifest_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_git_commit("engineering_base_head", self.engineering_base_head)
        if self.schema_id != "MEMORY_A0_SCIENTIFIC_MANIFEST_V1":
            raise ValueError("manifest schema mismatch")
        if self.schema_version != 1:
            raise ValueError("manifest schema version mismatch")
        if self.scientific_execution_authorized is not False:
            raise ValueError("manifest cannot self-authorize scientific execution")
        if type(self.sources) is not tuple or len(self.sources) != 3:
            raise ValueError("A0 requires exactly three source states")
        if len({x.source_state_id for x in self.sources}) != 3:
            raise ValueError("A0 source states must be unique")
        if len({x.task_gamefile_group_id for x in self.sources}) != 3:
            raise ValueError("A0 source task/gamefile groups must be unique")
        if type(self.cells) is not tuple or len(self.cells) != 12:
            raise ValueError("A0 requires exactly twelve scientific cells")
        if len({x.cell_id for x in self.cells}) != 12:
            raise ValueError("A0 cell IDs must be unique")
        by_source: dict[str, list[A0ScientificCellV1]] = {}
        for cell in self.cells:
            by_source.setdefault(cell.source_state_id, []).append(cell)
        if set(by_source) != {x.source_state_id for x in self.sources}:
            raise ValueError("cell/source population mismatch")
        for source in self.sources:
            group = by_source[source.source_state_id]
            if tuple(cell.arm.arm_id for cell in group) != A0_ARM_ORDER:
                raise ValueError("A0 per-source cell arm order mismatch")
            for cell in group:
                if cell.continuation_seed != source.continuation_seed:
                    raise ValueError("A0 paired cells must share continuation seed")
                for key, expected in source.identity_payload().items():
                    if getattr(cell, key) != expected:
                        raise ValueError(f"A0 cell differs from source at {key}")
        expected_sha = _domain_sha(
            "MEMORY_A0_SCIENTIFIC_MANIFEST_V1",
            self._payload_without_sha(),
        )
        if self.manifest_sha256 is None:
            object.__setattr__(self, "manifest_sha256", expected_sha)
        elif self.manifest_sha256 != expected_sha:
            raise ValueError("manifest_sha256 mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "engineering_base_head": self.engineering_base_head,
            "effect_scope": EffectScopeV1.SOURCE_STATE_LOCAL_PAIRED.value,
            "authority": "LOCAL_MECHANISM_REPRESENTATION_PROBE_ONLY",
            "paper_main_representation_claim_authorized": False,
            "a1_status": "OPTIONAL_CONDITIONAL",
            "scientific_execution_authorized": False,
            "sources": [x.to_dict() for x in self.sources],
            "cells": [x.to_dict() for x in self.cells],
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._payload_without_sha(), "manifest_sha256": self.manifest_sha256}

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_dict())


def build_a0_scientific_manifest_v1(
    *,
    engineering_base_head: str,
    sources: Iterable[A0SourceBindingV1],
) -> A0ScientificManifestV1:
    source_tuple = tuple(sources)
    if len(source_tuple) != 3:
        raise ValueError("A0 requires exactly three source bindings")
    cells: list[A0ScientificCellV1] = []
    for source in source_tuple:
        for arm in source.arms:
            cells.append(
                A0ScientificCellV1(
                    **source.identity_payload(),
                    arm=arm,
                )
            )
    return A0ScientificManifestV1(
        engineering_base_head=engineering_base_head,
        sources=source_tuple,
        cells=tuple(cells),
    )


@dataclass(frozen=True, slots=True)
class LocalEffectClassificationV1:
    effect_label: EffectLabelV1 | None
    effect_scope: EffectScopeV1
    terminal_relation: TerminalRelationV1
    mechanism_effect: MechanismEffectV1
    infrastructure_disposition: InfrastructureDispositionV1
    scientific_denominator_eligible: bool
    retry_exact_same_frozen_cell: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "effect_label": None if self.effect_label is None else self.effect_label.value,
            "effect_scope": self.effect_scope.value,
            "terminal_relation": self.terminal_relation.value,
            "mechanism_effect": self.mechanism_effect.value,
            "infrastructure_disposition": self.infrastructure_disposition.value,
            "scientific_denominator_eligible": self.scientific_denominator_eligible,
            "retry_exact_same_frozen_cell": self.retry_exact_same_frozen_cell,
            "reason": self.reason,
        }


def classify_local_paired_effect_v1(
    *,
    f0_success: bool | None,
    f1_success: bool | None,
    scientific_execution_started: bool,
    pre_result_infrastructure_failure: bool,
    identity_resolved: bool,
    evidence_complete: bool,
) -> LocalEffectClassificationV1:
    for name, value in (
        ("scientific_execution_started", scientific_execution_started),
        ("pre_result_infrastructure_failure", pre_result_infrastructure_failure),
        ("identity_resolved", identity_resolved),
        ("evidence_complete", evidence_complete),
    ):
        if type(value) is not bool:
            raise TypeError(f"{name} must be bool")
    for name, value in (("f0_success", f0_success), ("f1_success", f1_success)):
        if value is not None and type(value) is not bool:
            raise TypeError(f"{name} must be bool or None")

    scope = EffectScopeV1.SOURCE_STATE_LOCAL_PAIRED
    if pre_result_infrastructure_failure:
        if scientific_execution_started:
            raise ValueError(
                "pre-result infrastructure failure cannot also claim scientific execution started"
            )
        return LocalEffectClassificationV1(
            effect_label=None,
            effect_scope=scope,
            terminal_relation=TerminalRelationV1.NO_SCIENTIFIC_OUTCOME,
            mechanism_effect=MechanismEffectV1.NOT_EVALUATED,
            infrastructure_disposition=(
                InfrastructureDispositionV1.RETRY_EXACT_SAME_FROZEN_CELL
            ),
            scientific_denominator_eligible=False,
            retry_exact_same_frozen_cell=True,
            reason="PRE_RESULT_INFRASTRUCTURE_FAILURE_NOT_SCIENTIFIC_OUTCOME",
        )

    if not scientific_execution_started:
        return LocalEffectClassificationV1(
            effect_label=None,
            effect_scope=scope,
            terminal_relation=TerminalRelationV1.NO_SCIENTIFIC_OUTCOME,
            mechanism_effect=MechanismEffectV1.NOT_EVALUATED,
            infrastructure_disposition=InfrastructureDispositionV1.NONE,
            scientific_denominator_eligible=False,
            retry_exact_same_frozen_cell=False,
            reason="NO_SCIENTIFIC_EXECUTION",
        )

    if not identity_resolved or not evidence_complete:
        return LocalEffectClassificationV1(
            effect_label=EffectLabelV1.UNCERTAIN,
            effect_scope=scope,
            terminal_relation=TerminalRelationV1.UNRESOLVED,
            mechanism_effect=MechanismEffectV1.NOT_EVALUATED,
            infrastructure_disposition=(
                InfrastructureDispositionV1.SCIENTIFIC_UNCERTAIN_OR_HARD_STOP
            ),
            scientific_denominator_eligible=False,
            retry_exact_same_frozen_cell=False,
            reason="POST_EXECUTION_IDENTITY_OR_EVIDENCE_UNRESOLVED",
        )

    if f0_success is None or f1_success is None:
        return LocalEffectClassificationV1(
            effect_label=EffectLabelV1.UNCERTAIN,
            effect_scope=scope,
            terminal_relation=TerminalRelationV1.UNRESOLVED,
            mechanism_effect=MechanismEffectV1.NOT_EVALUATED,
            infrastructure_disposition=(
                InfrastructureDispositionV1.SCIENTIFIC_UNCERTAIN_OR_HARD_STOP
            ),
            scientific_denominator_eligible=False,
            retry_exact_same_frozen_cell=False,
            reason="TERMINAL_OUTCOME_UNRESOLVED",
        )

    if not f0_success and f1_success:
        label = EffectLabelV1.BENEFIT
        relation = TerminalRelationV1.FAIL_TO_SUCCESS
    elif f0_success and not f1_success:
        label = EffectLabelV1.HARM
        relation = TerminalRelationV1.SUCCESS_TO_FAIL
    else:
        label = EffectLabelV1.NEUTRAL
        relation = TerminalRelationV1.SAME_TERMINAL

    return LocalEffectClassificationV1(
        effect_label=label,
        effect_scope=scope,
        terminal_relation=relation,
        mechanism_effect=MechanismEffectV1.NOT_EVALUATED,
        infrastructure_disposition=InfrastructureDispositionV1.NONE,
        scientific_denominator_eligible=True,
        retry_exact_same_frozen_cell=False,
        reason="LOCAL_PAIRED_TERMINAL_EFFECT_CLASSIFIED",
    )


def validate_task_group_disjointness_v1(
    named_groups: Mapping[str, Iterable[str]],
) -> None:
    seen: dict[str, str] = {}
    for pool_name, raw_values in named_groups.items():
        _require_text("pool_name", pool_name)
        values = tuple(raw_values)
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate task/gamefile group inside {pool_name}")
        for value in values:
            _require_text("task_gamefile_group_id", value)
            if value in seen:
                raise ValueError(
                    f"task/gamefile group overlap: {value} in {seen[value]} and {pool_name}"
                )
            seen[value] = pool_name


def validate_c_query_isolation_v1(
    *,
    c_query_groups: Iterable[str],
    a0_source_groups: Iterable[str],
    token_calibration_groups: Iterable[str],
    active_memory_source_groups: Iterable[str],
    b_development_groups: Iterable[str],
) -> None:
    query = tuple(c_query_groups)
    if len(query) != len(set(query)):
        raise ValueError("duplicate task/gamefile group inside C_QUERY")
    for value in query:
        _require_text("task_gamefile_group_id", value)
    query_set = set(query)
    protected = {
        "A0_SOURCE": tuple(a0_source_groups),
        "TOKEN_CALIBRATION": tuple(token_calibration_groups),
        "ACTIVE_MEMORY_SOURCE": tuple(active_memory_source_groups),
        "B_DEVELOPMENT": tuple(b_development_groups),
    }
    for pool_name, values in protected.items():
        for value in values:
            _require_text("task_gamefile_group_id", value)
        overlap = query_set.intersection(values)
        if overlap:
            raise ValueError(
                f"C query/source overlap with {pool_name}: {sorted(overlap)}"
            )


@dataclass(frozen=True, slots=True)
class C2FrozenHistoricalSupportBindingV1:
    retriever_config_sha256: str
    threshold_config_sha256: str
    active_snapshot_sha256: str
    applicability_gate_sha256: str
    selection_validation_report_sha256: str
    retrieval_mode: str = "PACKAGE_B_FROZEN_RETRIEVER"
    human_memory_selection_allowed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "retriever_config_sha256",
            "threshold_config_sha256",
            "active_snapshot_sha256",
            "applicability_gate_sha256",
            "selection_validation_report_sha256",
        ):
            _require_sha(name, getattr(self, name))
        if self.retrieval_mode != "PACKAGE_B_FROZEN_RETRIEVER":
            raise ValueError("C2 must bind the frozen Package-B retriever")
        if self.human_memory_selection_allowed is not False:
            raise ValueError("C2 human-picked Memory is forbidden")


@dataclass(frozen=True, slots=True)
class PolicyInternalizationPrefreezeV1:
    training_eligibility_rule_sha256: str
    training_arms_sha256: str
    model_initialization_sha256: str
    data_deduplication_rule_sha256: str
    hyperparameter_selection_authority_sha256: str
    off_off_evaluation_panel_sha256: str
    primary_metric_sha256: str
    promotion_rollback_rule_sha256: str
    actual_training_execution_authorized: bool = False

    def __post_init__(self) -> None:
        for name in (
            "training_eligibility_rule_sha256",
            "training_arms_sha256",
            "model_initialization_sha256",
            "data_deduplication_rule_sha256",
            "hyperparameter_selection_authority_sha256",
            "off_off_evaluation_panel_sha256",
            "primary_metric_sha256",
            "promotion_rollback_rule_sha256",
        ):
            _require_sha(name, getattr(self, name))
        if self.actual_training_execution_authorized is not False:
            raise ValueError("prefreeze contract does not authorize training execution")


def require_registered_amendment_trigger_v1(value: str) -> AmendmentTriggerV1:
    try:
        return AmendmentTriggerV1(value)
    except ValueError as exc:
        raise ValueError("outcome-guided redesign is forbidden") from exc

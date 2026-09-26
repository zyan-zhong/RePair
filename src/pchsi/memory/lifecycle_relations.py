from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import ClassVar

from pchsi.memory.procedural_record import (
    MemoryAuthorityTypeV1,
    MemoryEvidenceRefV1,
)


_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _expect_exact_keys(
    value: object,
    expected: frozenset[str],
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be object")
    observed = frozenset(value)
    if observed != expected:
        raise ValueError(
            f"{label} fields do not match contract: "
            f"missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


def _require_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be nonempty str")
    if any(ch in value for ch in ("\x00", "\r", "\n")):
        raise ValueError(f"{name} contains forbidden control character")
    return value


def _require_sha(name: str, value: object) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be 64 lowercase hex")
    return value


class FactualBindingStatusV1(str, Enum):
    BOUND_TO_CODE_APPROVED_UNIT2_OBJECT = (
        "BOUND_TO_CODE_APPROVED_UNIT2_OBJECT"
    )


class SourceIntegrityStatusV1(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class DescriptiveEligibilityStatusV1(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    RETRIEVAL_ELIGIBLE_DESCRIPTIVE = "RETRIEVAL_ELIGIBLE_DESCRIPTIVE"
    INELIGIBLE = "INELIGIBLE"


class RepairValidityStatusV1(str, Enum):
    NOT_TESTED = "NOT_TESTED"
    EXECUTABLE = "EXECUTABLE"
    INVALID = "INVALID"
    UNRESOLVED = "UNRESOLVED"


class EffectStatusV1(str, Enum):
    UNTESTED = "UNTESTED"
    POSITIVE = "POSITIVE"
    HARM = "HARM"
    NEUTRAL = "NEUTRAL"
    CONFLICTING = "CONFLICTING"
    UNCERTAIN = "UNCERTAIN"


class EffectEvidenceScopeV1(str, Enum):
    UNTESTED = "UNTESTED"
    SOURCE_STATE_PAIRED = "SOURCE_STATE_PAIRED"
    REPLICATED_CONTEXT = "REPLICATED_CONTEXT"
    CROSS_TASK_REPLICATED = "CROSS_TASK_REPLICATED"
    FRESH_TASK = "FRESH_TASK"
    LIBRARY_LEVEL = "LIBRARY_LEVEL"


class AccessScopeV1(str, Enum):
    STAGING_ONLY = "STAGING_ONLY"
    SAME_TASK_DEV_ALLOWED = "SAME_TASK_DEV_ALLOWED"
    CROSS_TASK_ALLOWED = "CROSS_TASK_ALLOWED"


class LifecycleStatusV1(str, Enum):
    CANDIDATE = "CANDIDATE"
    STAGING = "STAGING"
    ACTIVE = "ACTIVE"
    QUARANTINE = "QUARANTINE"
    DISABLED = "DISABLED"
    SUPERSEDED = "SUPERSEDED"


class EvaluationContaminationStatusV1(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    CLEAN = "CLEAN"
    HISTORICALLY_EXPOSED = "HISTORICALLY_EXPOSED"
    CONTAMINATED = "CONTAMINATED"


@dataclass(frozen=True, slots=True)
class MemoryGovernanceStateV1:
    factual_binding_status: FactualBindingStatusV1
    source_integrity: SourceIntegrityStatusV1
    descriptive_eligibility: DescriptiveEligibilityStatusV1
    repair_validity: RepairValidityStatusV1
    effect_status: EffectStatusV1
    effect_evidence_scope: EffectEvidenceScopeV1
    access_scope: AccessScopeV1
    lifecycle_status: LifecycleStatusV1
    evaluation_contamination_status: EvaluationContaminationStatusV1
    paired_effect_observation_ids: tuple[str, ...]
    known_harm_ids: tuple[str, ...]

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "factual_binding_status",
            "source_integrity",
            "descriptive_eligibility",
            "repair_validity",
            "effect_status",
            "effect_evidence_scope",
            "access_scope",
            "lifecycle_status",
            "evaluation_contamination_status",
            "paired_effect_observation_ids",
            "known_harm_ids",
        }
    )

    def __post_init__(self) -> None:
        for name, items in (
            ("paired_effect_observation_ids", self.paired_effect_observation_ids),
            ("known_harm_ids", self.known_harm_ids),
        ):
            if type(items) is not tuple:
                raise TypeError(f"{name} must be tuple")
            for item in items:
                _require_text(f"{name} item", item)
            if len(items) != len(set(items)):
                raise ValueError(f"{name} must be unique")

    def to_dict(self) -> dict[str, object]:
        return {
            "factual_binding_status": self.factual_binding_status.value,
            "source_integrity": self.source_integrity.value,
            "descriptive_eligibility": self.descriptive_eligibility.value,
            "repair_validity": self.repair_validity.value,
            "effect_status": self.effect_status.value,
            "effect_evidence_scope": self.effect_evidence_scope.value,
            "access_scope": self.access_scope.value,
            "lifecycle_status": self.lifecycle_status.value,
            "evaluation_contamination_status": (
                self.evaluation_contamination_status.value
            ),
            "paired_effect_observation_ids": list(
                self.paired_effect_observation_ids
            ),
            "known_harm_ids": list(self.known_harm_ids),
        }

    @classmethod
    def from_dict(cls, value: object) -> "MemoryGovernanceStateV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "memory governance state",
        )
        paired = payload["paired_effect_observation_ids"]
        harm = payload["known_harm_ids"]
        if not isinstance(paired, list) or not isinstance(harm, list):
            raise TypeError("governance evidence IDs must be JSON arrays")
        return cls(
            factual_binding_status=FactualBindingStatusV1(
                payload["factual_binding_status"]
            ),
            source_integrity=SourceIntegrityStatusV1(
                payload["source_integrity"]
            ),
            descriptive_eligibility=DescriptiveEligibilityStatusV1(
                payload["descriptive_eligibility"]
            ),
            repair_validity=RepairValidityStatusV1(
                payload["repair_validity"]
            ),
            effect_status=EffectStatusV1(payload["effect_status"]),
            effect_evidence_scope=EffectEvidenceScopeV1(
                payload["effect_evidence_scope"]
            ),
            access_scope=AccessScopeV1(payload["access_scope"]),
            lifecycle_status=LifecycleStatusV1(payload["lifecycle_status"]),
            evaluation_contamination_status=EvaluationContaminationStatusV1(
                payload["evaluation_contamination_status"]
            ),
            paired_effect_observation_ids=tuple(paired),
            known_harm_ids=tuple(harm),
        )


def initial_memory_governance_state_v1() -> MemoryGovernanceStateV1:
    return MemoryGovernanceStateV1(
        factual_binding_status=(
            FactualBindingStatusV1.BOUND_TO_CODE_APPROVED_UNIT2_OBJECT
        ),
        source_integrity=SourceIntegrityStatusV1.NOT_EVALUATED,
        descriptive_eligibility=DescriptiveEligibilityStatusV1.NOT_EVALUATED,
        repair_validity=RepairValidityStatusV1.NOT_TESTED,
        effect_status=EffectStatusV1.UNTESTED,
        effect_evidence_scope=EffectEvidenceScopeV1.UNTESTED,
        access_scope=AccessScopeV1.STAGING_ONLY,
        lifecycle_status=LifecycleStatusV1.CANDIDATE,
        evaluation_contamination_status=(
            EvaluationContaminationStatusV1.NOT_EVALUATED
        ),
        paired_effect_observation_ids=(),
        known_harm_ids=(),
    )


def validate_unit3_initial_governance_state_v1(
    state: MemoryGovernanceStateV1,
) -> None:
    if not isinstance(state, MemoryGovernanceStateV1):
        raise TypeError("state must be MemoryGovernanceStateV1")
    if state != initial_memory_governance_state_v1():
        raise ValueError("Unit-3 governance state must equal frozen initial state")


class MemoryRelationTypeV1(str, Enum):
    DERIVED_FROM = "DERIVED_FROM"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    SIMILAR_TO = "SIMILAR_TO"
    REFINES = "REFINES"
    SUPERSEDES = "SUPERSEDES"
    APPLIES_TO = "APPLIES_TO"
    COUNTEREXAMPLE_OF = "COUNTEREXAMPLE_OF"
    VERIFIED_BY = "VERIFIED_BY"
    HARMFUL_UNDER = "HARMFUL_UNDER"


class MemoryRelationTargetKindV1(str, Enum):
    SEQUENCE_EXPERIENCE = "SEQUENCE_EXPERIENCE"
    MEMORY_LINEAGE = "MEMORY_LINEAGE"
    MEMORY_RECORD = "MEMORY_RECORD"
    REGISTERED_ARTIFACT = "REGISTERED_ARTIFACT"


@dataclass(frozen=True, slots=True)
class MemoryRelationTargetV1:
    target_kind: MemoryRelationTargetKindV1
    target_id: str
    target_canonical_record_sha256: str | None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "target_kind",
            "target_id",
            "target_canonical_record_sha256",
        }
    )

    def __post_init__(self) -> None:
        if self.target_kind in {
            MemoryRelationTargetKindV1.SEQUENCE_EXPERIENCE,
            MemoryRelationTargetKindV1.MEMORY_LINEAGE,
            MemoryRelationTargetKindV1.MEMORY_RECORD,
        }:
            _require_sha("target_id", self.target_id)
        else:
            _require_text("target_id", self.target_id)

        if self.target_kind is MemoryRelationTargetKindV1.MEMORY_RECORD:
            if self.target_canonical_record_sha256 is None:
                raise ValueError("MEMORY_RECORD target requires canonical SHA")
            _require_sha(
                "target_canonical_record_sha256",
                self.target_canonical_record_sha256,
            )
        elif self.target_canonical_record_sha256 is not None:
            raise ValueError(
                "non-MEMORY_RECORD target must not carry canonical record SHA"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "target_kind": self.target_kind.value,
            "target_id": self.target_id,
            "target_canonical_record_sha256": (
                self.target_canonical_record_sha256
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> "MemoryRelationTargetV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "memory relation target",
        )
        return cls(
            target_kind=MemoryRelationTargetKindV1(payload["target_kind"]),
            target_id=payload["target_id"],
            target_canonical_record_sha256=payload[
                "target_canonical_record_sha256"
            ],
        )


class MemoryRelationVerificationStateV1(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    REGISTERED_UNVERIFIED = "REGISTERED_UNVERIFIED"
    SEMANTIC_UNVERIFIED = "SEMANTIC_UNVERIFIED"
    EFFECT_VERIFIED = "EFFECT_VERIFIED"
    HARM_VERIFIED = "HARM_VERIFIED"


@dataclass(frozen=True, slots=True)
class MemoryRelationV1:
    relation_id: str
    relation_type: MemoryRelationTypeV1
    source_memory_lineage_id: str
    target: MemoryRelationTargetV1
    authority_type: MemoryAuthorityTypeV1
    origin_role: str
    source_refs: tuple[MemoryEvidenceRefV1, ...]
    verification_state: MemoryRelationVerificationStateV1
    created_version: int

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "relation_id",
            "relation_type",
            "source_memory_lineage_id",
            "target",
            "authority_type",
            "origin_role",
            "source_refs",
            "verification_state",
            "created_version",
        }
    )

    def __post_init__(self) -> None:
        _require_text("relation_id", self.relation_id)
        _require_sha("source_memory_lineage_id", self.source_memory_lineage_id)
        if not isinstance(self.target, MemoryRelationTargetV1):
            raise TypeError("target must be MemoryRelationTargetV1")
        _require_text("origin_role", self.origin_role)
        if type(self.source_refs) is not tuple or not self.source_refs:
            raise ValueError("relation source_refs must be nonempty tuple")
        if any(not isinstance(item, MemoryEvidenceRefV1) for item in self.source_refs):
            raise TypeError("relation source_refs contain invalid ref")
        if type(self.created_version) is not int or self.created_version < 1:
            raise ValueError("created_version must be positive int")

        if self.relation_type is MemoryRelationTypeV1.DERIVED_FROM:
            if self.authority_type is not MemoryAuthorityTypeV1.FACT_AUTHORITY:
                raise ValueError("DERIVED_FROM authority mismatch")
            if (
                self.verification_state
                is not MemoryRelationVerificationStateV1.DETERMINISTIC
            ):
                raise ValueError("DERIVED_FROM must be deterministic")

        if self.relation_type is MemoryRelationTypeV1.SUPERSEDES:
            if self.authority_type is not MemoryAuthorityTypeV1.GOVERNANCE_AUTHORITY:
                raise ValueError("SUPERSEDES authority mismatch")
            if not any(
                ref.source_kind == "GOVERNANCE_ARTIFACT"
                for ref in self.source_refs
            ):
                raise ValueError("SUPERSEDES requires governance artifact")

        if self.relation_type is MemoryRelationTypeV1.VERIFIED_BY:
            if self.authority_type is not MemoryAuthorityTypeV1.EFFECT_EVIDENCE:
                raise ValueError("VERIFIED_BY authority mismatch")
            if (
                self.verification_state
                is not MemoryRelationVerificationStateV1.EFFECT_VERIFIED
            ):
                raise ValueError("VERIFIED_BY verification mismatch")

        if self.relation_type is MemoryRelationTypeV1.HARMFUL_UNDER:
            if self.authority_type is not MemoryAuthorityTypeV1.EFFECT_EVIDENCE:
                raise ValueError("HARMFUL_UNDER authority mismatch")
            if (
                self.verification_state
                is not MemoryRelationVerificationStateV1.HARM_VERIFIED
            ):
                raise ValueError("HARMFUL_UNDER verification mismatch")

        semantic_types = {
            MemoryRelationTypeV1.SUPPORTS,
            MemoryRelationTypeV1.CONTRADICTS,
            MemoryRelationTypeV1.SIMILAR_TO,
            MemoryRelationTypeV1.REFINES,
            MemoryRelationTypeV1.APPLIES_TO,
            MemoryRelationTypeV1.COUNTEREXAMPLE_OF,
        }
        if self.relation_type in semantic_types:
            if self.authority_type not in {
                MemoryAuthorityTypeV1.REGISTERED_BOUNDARY,
                MemoryAuthorityTypeV1.SEMANTIC_HYPOTHESIS,
            }:
                raise ValueError("semantic/registered relation authority mismatch")
            expected = (
                MemoryRelationVerificationStateV1.REGISTERED_UNVERIFIED
                if self.authority_type
                is MemoryAuthorityTypeV1.REGISTERED_BOUNDARY
                else MemoryRelationVerificationStateV1.SEMANTIC_UNVERIFIED
            )
            if self.verification_state is not expected:
                raise ValueError("semantic/registered relation verification mismatch")

    def to_dict(self) -> dict[str, object]:
        return {
            "relation_id": self.relation_id,
            "relation_type": self.relation_type.value,
            "source_memory_lineage_id": self.source_memory_lineage_id,
            "target": self.target.to_dict(),
            "authority_type": self.authority_type.value,
            "origin_role": self.origin_role,
            "source_refs": [item.to_dict() for item in self.source_refs],
            "verification_state": self.verification_state.value,
            "created_version": self.created_version,
        }

    @classmethod
    def from_dict(cls, value: object) -> "MemoryRelationV1":
        payload = _expect_exact_keys(value, cls._KEYS, "memory relation")
        refs = payload["source_refs"]
        if not isinstance(refs, list):
            raise TypeError("relation source_refs must be JSON array")
        return cls(
            relation_id=payload["relation_id"],
            relation_type=MemoryRelationTypeV1(payload["relation_type"]),
            source_memory_lineage_id=payload["source_memory_lineage_id"],
            target=MemoryRelationTargetV1.from_dict(payload["target"]),
            authority_type=MemoryAuthorityTypeV1(payload["authority_type"]),
            origin_role=payload["origin_role"],
            source_refs=tuple(
                MemoryEvidenceRefV1.from_dict(item) for item in refs
            ),
            verification_state=MemoryRelationVerificationStateV1(
                payload["verification_state"]
            ),
            created_version=payload["created_version"],
        )


def validate_initial_relation_set_v1(
    relations: tuple[MemoryRelationV1, ...],
) -> None:
    if type(relations) is not tuple:
        raise TypeError("relations must be tuple")
    if any(not isinstance(item, MemoryRelationV1) for item in relations):
        raise TypeError("relations contain invalid item")

    ids = tuple(item.relation_id for item in relations)
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate relation_id")

    forbidden_types = {
        MemoryRelationTypeV1.VERIFIED_BY,
        MemoryRelationTypeV1.HARMFUL_UNDER,
    }
    forbidden_states = {
        MemoryRelationVerificationStateV1.EFFECT_VERIFIED,
        MemoryRelationVerificationStateV1.HARM_VERIFIED,
    }

    for relation in relations:
        if relation.relation_type in forbidden_types:
            raise ValueError("future-authority relation forbidden in Unit 3")
        if relation.verification_state in forbidden_states:
            raise ValueError("future verification state forbidden in Unit 3")

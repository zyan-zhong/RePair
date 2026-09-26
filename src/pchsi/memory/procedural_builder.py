from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    strict_json_loads,
)
from pchsi.memory.applicability import ApplicabilityBoundarySetV1
from pchsi.memory.lifecycle_relations import (
    MemoryGovernanceStateV1,
    MemoryRelationV1,
    initial_memory_governance_state_v1,
    validate_initial_relation_set_v1,
    validate_unit3_initial_governance_state_v1,
)
from pchsi.memory.procedural_completeness import (
    ProceduralCompletenessReportV1,
    evaluate_procedural_completeness_v1,
)
from pchsi.memory.procedural_record import (
    AssemblyRegistrationBindingV1,
    FactualSequenceBindingV1,
    MemoryEvidenceRefV1,
    PreviousProceduralRecordBindingV1,
    ProceduralMemoryLineageV1,
    ProceduralMemoryProvenanceV1,
    record_id_for_lineage_version_v1,
)
from pchsi.memory.semantic_recovery import (
    ObservedRecoveryBindingV1,
    ProposedRecoveryV1,
    SemanticHypothesisAnnotationV1,
)
from pchsi.memory.sequence_failure_experience import SequenceFailureExperienceV1


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


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True, slots=True)
class ProceduralMemoryAssemblyInputV1:
    schema_id: str
    schema_version: int
    registration_id: str
    lineage: ProceduralMemoryLineageV1
    creation_event_id: str
    creator_role: str
    source_experience_refs: tuple[MemoryEvidenceRefV1, ...]
    applicability: ApplicabilityBoundarySetV1
    semantic_hypotheses: tuple[SemanticHypothesisAnnotationV1, ...]
    observed_recovery_bindings: tuple[ObservedRecoveryBindingV1, ...]
    proposed_recoveries: tuple[ProposedRecoveryV1, ...]
    relations: tuple[MemoryRelationV1, ...]
    created_snapshot_candidate: None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "schema_version",
            "registration_id",
            "lineage",
            "creation_event_id",
            "creator_role",
            "source_experience_refs",
            "applicability",
            "semantic_hypotheses",
            "observed_recovery_bindings",
            "proposed_recoveries",
            "relations",
            "created_snapshot_candidate",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != "PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1":
            raise ValueError("assembly input schema_id mismatch")
        if self.schema_version != 1:
            raise ValueError("assembly input schema_version mismatch")
        _require_text("registration_id", self.registration_id)
        _require_text("creation_event_id", self.creation_event_id)
        _require_text("creator_role", self.creator_role)
        if not isinstance(self.lineage, ProceduralMemoryLineageV1):
            raise TypeError("lineage type mismatch")
        if not isinstance(self.applicability, ApplicabilityBoundarySetV1):
            raise TypeError("applicability type mismatch")
        if type(self.source_experience_refs) is not tuple or not self.source_experience_refs:
            raise ValueError("source_experience_refs must be nonempty tuple")
        for ref in self.source_experience_refs:
            if not isinstance(ref, MemoryEvidenceRefV1):
                raise TypeError("source_experience_refs contain invalid ref")
            if ref.source_kind != "SEQUENCE_FAILURE_EXPERIENCE_V1":
                raise ValueError("source experience ref kind mismatch")
        source_ids = tuple(ref.source_id for ref in self.source_experience_refs)
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("duplicate source experience ref ID")

        tuple_fields = (
            ("semantic_hypotheses", self.semantic_hypotheses, SemanticHypothesisAnnotationV1),
            ("observed_recovery_bindings", self.observed_recovery_bindings, ObservedRecoveryBindingV1),
            ("proposed_recoveries", self.proposed_recoveries, ProposedRecoveryV1),
            ("relations", self.relations, MemoryRelationV1),
        )
        for name, items, item_type in tuple_fields:
            if type(items) is not tuple:
                raise TypeError(f"{name} must be tuple")
            if any(not isinstance(item, item_type) for item in items):
                raise TypeError(f"{name} contains invalid item")

        def require_unique(name: str, values: tuple[str, ...]) -> None:
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {name}")

        require_unique(
            "annotation_id",
            tuple(item.annotation_id for item in self.semantic_hypotheses),
        )
        require_unique(
            "proposal_id",
            tuple(item.proposal_id for item in self.proposed_recoveries),
        )
        require_unique(
            "observed recovery source_experience_id",
            tuple(
                item.source_experience_id
                for item in self.observed_recovery_bindings
            ),
        )

        validate_initial_relation_set_v1(self.relations)

        if self.created_snapshot_candidate is not None:
            raise ValueError("created_snapshot_candidate must be None")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "registration_id": self.registration_id,
            "lineage": self.lineage.to_dict(),
            "creation_event_id": self.creation_event_id,
            "creator_role": self.creator_role,
            "source_experience_refs": [
                item.to_dict() for item in self.source_experience_refs
            ],
            "applicability": self.applicability.to_dict(),
            "semantic_hypotheses": [
                item.to_dict() for item in self.semantic_hypotheses
            ],
            "observed_recovery_bindings": [
                item.to_dict() for item in self.observed_recovery_bindings
            ],
            "proposed_recoveries": [
                item.to_dict() for item in self.proposed_recoveries
            ],
            "relations": [item.to_dict() for item in self.relations],
            "created_snapshot_candidate": None,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> "ProceduralMemoryAssemblyInputV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "procedural memory assembly input",
        )

        def parse_list(name: str, parser):
            raw = payload[name]
            if not isinstance(raw, list):
                raise TypeError(f"{name} must be JSON array")
            return tuple(parser(item) for item in raw)

        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            registration_id=payload["registration_id"],
            lineage=ProceduralMemoryLineageV1.from_dict(payload["lineage"]),
            creation_event_id=payload["creation_event_id"],
            creator_role=payload["creator_role"],
            source_experience_refs=parse_list(
                "source_experience_refs",
                MemoryEvidenceRefV1.from_dict,
            ),
            applicability=ApplicabilityBoundarySetV1.from_dict(
                payload["applicability"]
            ),
            semantic_hypotheses=parse_list(
                "semantic_hypotheses",
                SemanticHypothesisAnnotationV1.from_dict,
            ),
            observed_recovery_bindings=parse_list(
                "observed_recovery_bindings",
                ObservedRecoveryBindingV1.from_dict,
            ),
            proposed_recoveries=parse_list(
                "proposed_recoveries",
                ProposedRecoveryV1.from_dict,
            ),
            relations=parse_list(
                "relations",
                MemoryRelationV1.from_dict,
            ),
            created_snapshot_candidate=payload[
                "created_snapshot_candidate"
            ],
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "ProceduralMemoryAssemblyInputV1":
        return cls.from_dict(strict_json_loads(value))


@dataclass(frozen=True, slots=True)
class ProceduralFailureMemoryRecordV1:
    record_id: str | None
    memory_lineage_id: str
    record_version: int
    previous_record_binding: PreviousProceduralRecordBindingV1 | None
    record_content_sha256: str | None
    canonical_record_sha256: str | None
    provenance: ProceduralMemoryProvenanceV1
    applicability: ApplicabilityBoundarySetV1
    semantic_hypotheses: tuple[SemanticHypothesisAnnotationV1, ...]
    observed_recovery_bindings: tuple[ObservedRecoveryBindingV1, ...]
    proposed_recoveries: tuple[ProposedRecoveryV1, ...]
    governance_state: MemoryGovernanceStateV1
    relations: tuple[MemoryRelationV1, ...]
    procedural_completeness: ProceduralCompletenessReportV1
    created_snapshot_candidate: None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "record_id",
            "memory_lineage_id",
            "record_version",
            "previous_record_binding",
            "record_content_sha256",
            "canonical_record_sha256",
            "provenance",
            "applicability",
            "semantic_hypotheses",
            "observed_recovery_bindings",
            "proposed_recoveries",
            "governance_state",
            "relations",
            "procedural_completeness",
            "created_snapshot_candidate",
        }
    )

    def __post_init__(self) -> None:
        lineage = ProceduralMemoryLineageV1(
            memory_lineage_id=self.memory_lineage_id,
            record_version=self.record_version,
            previous_record_binding=self.previous_record_binding,
        )
        del lineage

        if not isinstance(self.provenance, ProceduralMemoryProvenanceV1):
            raise TypeError("provenance type mismatch")
        if not isinstance(self.applicability, ApplicabilityBoundarySetV1):
            raise TypeError("applicability type mismatch")
        if not isinstance(self.governance_state, MemoryGovernanceStateV1):
            raise TypeError("governance_state type mismatch")
        if not isinstance(
            self.procedural_completeness,
            ProceduralCompletenessReportV1,
        ):
            raise TypeError("procedural_completeness type mismatch")

        tuple_fields = (
            ("semantic_hypotheses", self.semantic_hypotheses, SemanticHypothesisAnnotationV1),
            ("observed_recovery_bindings", self.observed_recovery_bindings, ObservedRecoveryBindingV1),
            ("proposed_recoveries", self.proposed_recoveries, ProposedRecoveryV1),
            ("relations", self.relations, MemoryRelationV1),
        )
        for name, items, item_type in tuple_fields:
            if type(items) is not tuple:
                raise TypeError(f"{name} must be tuple")
            if any(not isinstance(item, item_type) for item in items):
                raise TypeError(f"{name} contains invalid item")

        identity_sets = (
            (
                "annotation_id",
                tuple(item.annotation_id for item in self.semantic_hypotheses),
            ),
            (
                "proposal_id",
                tuple(item.proposal_id for item in self.proposed_recoveries),
            ),
            (
                "observed recovery source_experience_id",
                tuple(
                    item.source_experience_id
                    for item in self.observed_recovery_bindings
                ),
            ),
            (
                "relation_id",
                tuple(item.relation_id for item in self.relations),
            ),
        )
        for label, values in identity_sets:
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label}")

        if self.created_snapshot_candidate is not None:
            raise ValueError("created_snapshot_candidate must be None")
        if self.provenance.created_snapshot_candidate is not None:
            raise ValueError("provenance snapshot candidate must be None")

        expected_record_id = record_id_for_lineage_version_v1(
            self.memory_lineage_id,
            self.record_version,
        )
        if self.record_id is None:
            object.__setattr__(self, "record_id", expected_record_id)
        elif self.record_id != expected_record_id:
            raise ValueError("record_id does not match lineage/version")

        expected_content = self._computed_content_sha256()
        if self.record_content_sha256 is None:
            object.__setattr__(
                self,
                "record_content_sha256",
                expected_content,
            )
        elif self.record_content_sha256 != expected_content:
            raise ValueError("record_content_sha256 mismatch")

        expected_canonical = self._computed_canonical_record_sha256()
        if self.canonical_record_sha256 is None:
            object.__setattr__(
                self,
                "canonical_record_sha256",
                expected_canonical,
            )
        elif self.canonical_record_sha256 != expected_canonical:
            raise ValueError("canonical_record_sha256 mismatch")

    def _content_payload(self) -> dict[str, object]:
        return {
            "provenance": self.provenance.to_dict(),
            "applicability": self.applicability.to_dict(),
            "semantic_hypotheses": [
                item.to_dict() for item in self.semantic_hypotheses
            ],
            "observed_recovery_bindings": [
                item.to_dict() for item in self.observed_recovery_bindings
            ],
            "proposed_recoveries": [
                item.to_dict() for item in self.proposed_recoveries
            ],
            "governance_state": self.governance_state.to_dict(),
            "relations": [item.to_dict() for item in self.relations],
            "procedural_completeness": self.procedural_completeness.to_dict(),
        }

    def _computed_content_sha256(self) -> str:
        return _sha(
            b"PROCEDURAL_FAILURE_MEMORY_CONTENT_V1"
            + b"\0"
            + canonical_json_bytes(self._content_payload())
        )

    def _payload_without_canonical_record_sha256(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "memory_lineage_id": self.memory_lineage_id,
            "record_version": self.record_version,
            "previous_record_binding": (
                None
                if self.previous_record_binding is None
                else self.previous_record_binding.to_dict()
            ),
            "record_content_sha256": self.record_content_sha256,
            "provenance": self.provenance.to_dict(),
            "applicability": self.applicability.to_dict(),
            "semantic_hypotheses": [
                item.to_dict() for item in self.semantic_hypotheses
            ],
            "observed_recovery_bindings": [
                item.to_dict() for item in self.observed_recovery_bindings
            ],
            "proposed_recoveries": [
                item.to_dict() for item in self.proposed_recoveries
            ],
            "governance_state": self.governance_state.to_dict(),
            "relations": [item.to_dict() for item in self.relations],
            "procedural_completeness": self.procedural_completeness.to_dict(),
            "created_snapshot_candidate": None,
        }

    def _computed_canonical_record_sha256(self) -> str:
        return _sha(
            b"PROCEDURAL_FAILURE_MEMORY_RECORD_V1"
            + b"\0"
            + canonical_json_bytes(
                self._payload_without_canonical_record_sha256()
            )
        )

    def to_dict(self) -> dict[str, object]:
        payload = self._payload_without_canonical_record_sha256()
        payload["canonical_record_sha256"] = self.canonical_record_sha256
        return payload

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    def to_json(self) -> str:
        return self.canonical_bytes().decode("utf-8")

    @classmethod
    def from_dict(cls, value: object) -> "ProceduralFailureMemoryRecordV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "procedural failure memory record",
        )

        def parse_list(name: str, parser):
            raw = payload[name]
            if not isinstance(raw, list):
                raise TypeError(f"{name} must be JSON array")
            return tuple(parser(item) for item in raw)

        previous = payload["previous_record_binding"]
        return cls(
            record_id=payload["record_id"],
            memory_lineage_id=payload["memory_lineage_id"],
            record_version=payload["record_version"],
            previous_record_binding=(
                None
                if previous is None
                else PreviousProceduralRecordBindingV1.from_dict(previous)
            ),
            record_content_sha256=payload["record_content_sha256"],
            canonical_record_sha256=payload["canonical_record_sha256"],
            provenance=ProceduralMemoryProvenanceV1.from_dict(
                payload["provenance"]
            ),
            applicability=ApplicabilityBoundarySetV1.from_dict(
                payload["applicability"]
            ),
            semantic_hypotheses=parse_list(
                "semantic_hypotheses",
                SemanticHypothesisAnnotationV1.from_dict,
            ),
            observed_recovery_bindings=parse_list(
                "observed_recovery_bindings",
                ObservedRecoveryBindingV1.from_dict,
            ),
            proposed_recoveries=parse_list(
                "proposed_recoveries",
                ProposedRecoveryV1.from_dict,
            ),
            governance_state=MemoryGovernanceStateV1.from_dict(
                payload["governance_state"]
            ),
            relations=parse_list(
                "relations",
                MemoryRelationV1.from_dict,
            ),
            procedural_completeness=ProceduralCompletenessReportV1.from_dict(
                payload["procedural_completeness"]
            ),
            created_snapshot_candidate=payload[
                "created_snapshot_candidate"
            ],
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "ProceduralFailureMemoryRecordV1":
        return cls.from_dict(strict_json_loads(value))


def _validate_source_experiences(
    assembly_input: ProceduralMemoryAssemblyInputV1,
    source_experiences: tuple[SequenceFailureExperienceV1, ...],
) -> None:
    if type(source_experiences) is not tuple:
        raise TypeError("source_experiences must be tuple")
    if len(source_experiences) != len(assembly_input.source_experience_refs):
        raise ValueError("source experience count mismatch")

    for expected_ref, experience in zip(
        assembly_input.source_experience_refs,
        source_experiences,
        strict=True,
    ):
        if not isinstance(experience, SequenceFailureExperienceV1):
            raise TypeError("invalid source experience")
        if expected_ref.source_id != experience.experience_id:
            raise ValueError("source experience ID/order mismatch")
        if expected_ref.source_sha256 != _sha(experience.canonical_bytes()):
            raise ValueError("source experience canonical SHA mismatch")


def _validate_previous_record(
    lineage: ProceduralMemoryLineageV1,
    previous_record: ProceduralFailureMemoryRecordV1 | None,
) -> None:
    if lineage.record_version == 1:
        if previous_record is not None:
            raise ValueError("version 1 rejects previous record")
        return

    if previous_record is None:
        raise ValueError("version >1 requires previous record")
    if previous_record.memory_lineage_id != lineage.memory_lineage_id:
        raise ValueError("previous record lineage mismatch")
    if previous_record.record_version + 1 != lineage.record_version:
        raise ValueError("previous record version mismatch")
    binding = lineage.previous_record_binding
    if binding is None:
        raise ValueError("missing previous record binding")
    if binding.memory_lineage_id != previous_record.memory_lineage_id:
        raise ValueError("previous binding lineage mismatch")
    if binding.record_version != previous_record.record_version:
        raise ValueError("previous binding version mismatch")
    if (
        binding.canonical_record_sha256
        != previous_record.canonical_record_sha256
    ):
        raise ValueError("previous binding canonical SHA mismatch")


def _validate_recovery_bindings(
    *,
    source_experiences: tuple[SequenceFailureExperienceV1, ...],
    bindings: tuple[ObservedRecoveryBindingV1, ...],
) -> None:
    by_id = {item.experience_id: item for item in source_experiences}
    for binding in bindings:
        experience = by_id.get(binding.source_experience_id)
        if experience is None:
            raise ValueError("observed recovery source experience missing")
        registration = experience.registration_binding
        start = registration.registered_recovery_start_model_call_index
        final = registration.registered_recovery_final_model_call_index
        if start is None or final is None:
            raise ValueError("source experience has no registered recovery")
        if (
            binding.registered_recovery_start_model_call_index != start
            or binding.registered_recovery_final_model_call_index != final
        ):
            raise ValueError("observed recovery range mismatch")


def build_procedural_failure_memory_record_v1(
    *,
    assembly_input: ProceduralMemoryAssemblyInputV1,
    assembly_registration_binding: AssemblyRegistrationBindingV1,
    source_experiences: tuple[SequenceFailureExperienceV1, ...],
    previous_record: ProceduralFailureMemoryRecordV1 | None,
) -> ProceduralFailureMemoryRecordV1:
    if not isinstance(assembly_input, ProceduralMemoryAssemblyInputV1):
        raise TypeError("assembly_input type mismatch")
    if not isinstance(
        assembly_registration_binding,
        AssemblyRegistrationBindingV1,
    ):
        raise TypeError("assembly_registration_binding type mismatch")

    expected_registration_sha = _sha(assembly_input.canonical_bytes())
    if (
        assembly_registration_binding.registration_id
        != assembly_input.registration_id
    ):
        raise ValueError("assembly registration ID mismatch")
    if (
        assembly_registration_binding.assembly_registration_sha256
        != expected_registration_sha
    ):
        raise ValueError("assembly registration SHA mismatch")

    _validate_source_experiences(assembly_input, source_experiences)
    _validate_previous_record(assembly_input.lineage, previous_record)
    _validate_recovery_bindings(
        source_experiences=source_experiences,
        bindings=assembly_input.observed_recovery_bindings,
    )
    validate_initial_relation_set_v1(assembly_input.relations)

    factual_bindings = tuple(
        FactualSequenceBindingV1.from_experience(item)
        for item in source_experiences
    )

    provenance = ProceduralMemoryProvenanceV1(
        creation_event_id=assembly_input.creation_event_id,
        creator_role=assembly_input.creator_role,
        assembly_registration_binding=assembly_registration_binding,
        factual_sequence_bindings=factual_bindings,
        created_snapshot_candidate=None,
    )

    governance = initial_memory_governance_state_v1()
    validate_unit3_initial_governance_state_v1(governance)

    completeness = evaluate_procedural_completeness_v1(
        source_experiences=source_experiences,
        factual_bindings=factual_bindings,
        applicability=assembly_input.applicability,
        governance_state=governance,
    )

    return ProceduralFailureMemoryRecordV1(
        record_id=None,
        memory_lineage_id=assembly_input.lineage.memory_lineage_id,
        record_version=assembly_input.lineage.record_version,
        previous_record_binding=assembly_input.lineage.previous_record_binding,
        record_content_sha256=None,
        canonical_record_sha256=None,
        provenance=provenance,
        applicability=assembly_input.applicability,
        semantic_hypotheses=assembly_input.semantic_hypotheses,
        observed_recovery_bindings=assembly_input.observed_recovery_bindings,
        proposed_recoveries=assembly_input.proposed_recoveries,
        governance_state=governance,
        relations=assembly_input.relations,
        procedural_completeness=completeness,
        created_snapshot_candidate=None,
    )

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import re
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import canonical_json_bytes
from pchsi.memory.sequence_failure_experience import SequenceFailureExperienceV1


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_SOURCE_KINDS = frozenset(
    {
        "SEQUENCE_FAILURE_EXPERIENCE_V1",
        "UNIT2_SOURCE_RECORD",
        "REGISTERED_BOUNDARY_ARTIFACT",
        "SEMANTIC_ANNOTATION_ARTIFACT",
        "RECOVERY_PROPOSAL_ARTIFACT",
        "GOVERNANCE_ARTIFACT",
        "PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1",
        "PROCEDURAL_FAILURE_MEMORY_RECORD_V1",
    }
)


def _expect_exact_keys(
    *,
    value: object,
    expected: frozenset[str],
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be object")
    observed = frozenset(value)
    if observed != expected:
        missing = sorted(expected - observed)
        unknown = sorted(observed - expected)
        raise ValueError(
            f"{label} fields do not match contract: "
            f"missing={missing}, unknown={unknown}"
        )
    return value


def _require_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be nonempty str")
    if any(ch in value for ch in ("\x00", "\r", "\n")):
        raise ValueError(f"{name} contains forbidden control character")
    return value


def _require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be 64 lowercase hex")
    return value


def _require_positive_version(name: str, value: object) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be positive integer")
    return value


class MemoryAuthorityTypeV1(str, Enum):
    FACT_AUTHORITY = "FACT_AUTHORITY"
    REGISTERED_BOUNDARY = "REGISTERED_BOUNDARY"
    SEMANTIC_HYPOTHESIS = "SEMANTIC_HYPOTHESIS"
    RECOVERY_PROPOSAL = "RECOVERY_PROPOSAL"
    EFFECT_EVIDENCE = "EFFECT_EVIDENCE"
    GOVERNANCE_AUTHORITY = "GOVERNANCE_AUTHORITY"


@dataclass(frozen=True, slots=True)
class MemoryEvidenceRefV1:
    source_kind: str
    source_id: str
    source_sha256: str

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {"source_kind", "source_id", "source_sha256"}
    )

    def __post_init__(self) -> None:
        if self.source_kind not in _SOURCE_KINDS:
            raise ValueError("source_kind is outside frozen vocabulary")
        _require_text("source_id", self.source_id)
        _require_sha256("source_sha256", self.source_sha256)

    def to_dict(self) -> dict[str, object]:
        return {
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> "MemoryEvidenceRefV1":
        payload = _expect_exact_keys(
            value=value,
            expected=cls._KEYS,
            label="memory evidence ref",
        )
        return cls(
            source_kind=payload["source_kind"],
            source_id=payload["source_id"],
            source_sha256=payload["source_sha256"],
        )


@dataclass(frozen=True, slots=True)
class FactualSequenceBindingV1:
    authority_type: MemoryAuthorityTypeV1
    experience_id: str
    canonical_experience_sha256: str
    source_bundle_sha256: str
    source_attempt_id: str
    source_task_id: str

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "authority_type",
            "experience_id",
            "canonical_experience_sha256",
            "source_bundle_sha256",
            "source_attempt_id",
            "source_task_id",
        }
    )

    def __post_init__(self) -> None:
        if self.authority_type is not MemoryAuthorityTypeV1.FACT_AUTHORITY:
            raise ValueError("factual binding authority must be FACT_AUTHORITY")
        _require_sha256("experience_id", self.experience_id)
        _require_sha256(
            "canonical_experience_sha256",
            self.canonical_experience_sha256,
        )
        _require_sha256("source_bundle_sha256", self.source_bundle_sha256)
        _require_text("source_attempt_id", self.source_attempt_id)
        _require_text("source_task_id", self.source_task_id)

    @classmethod
    def from_experience(
        cls,
        experience: SequenceFailureExperienceV1,
    ) -> "FactualSequenceBindingV1":
        if not isinstance(experience, SequenceFailureExperienceV1):
            raise TypeError("experience must be SequenceFailureExperienceV1")
        return cls(
            authority_type=MemoryAuthorityTypeV1.FACT_AUTHORITY,
            experience_id=experience.experience_id,
            canonical_experience_sha256=hashlib.sha256(
                experience.canonical_bytes()
            ).hexdigest(),
            source_bundle_sha256=experience.source_bundle_sha256,
            source_attempt_id=experience.source_attempt_id,
            source_task_id=experience.source_task_id,
        )

    def validate_against(
        self,
        experience: SequenceFailureExperienceV1,
    ) -> None:
        expected = type(self).from_experience(experience)
        if self != expected:
            raise ValueError("factual binding does not match source experience")

    def to_dict(self) -> dict[str, object]:
        return {
            "authority_type": self.authority_type.value,
            "experience_id": self.experience_id,
            "canonical_experience_sha256": self.canonical_experience_sha256,
            "source_bundle_sha256": self.source_bundle_sha256,
            "source_attempt_id": self.source_attempt_id,
            "source_task_id": self.source_task_id,
        }

    @classmethod
    def from_dict(cls, value: object) -> "FactualSequenceBindingV1":
        payload = _expect_exact_keys(
            value=value,
            expected=cls._KEYS,
            label="factual sequence binding",
        )
        return cls(
            authority_type=MemoryAuthorityTypeV1(payload["authority_type"]),
            experience_id=payload["experience_id"],
            canonical_experience_sha256=payload[
                "canonical_experience_sha256"
            ],
            source_bundle_sha256=payload["source_bundle_sha256"],
            source_attempt_id=payload["source_attempt_id"],
            source_task_id=payload["source_task_id"],
        )


@dataclass(frozen=True, slots=True)
class AssemblyRegistrationBindingV1:
    schema_id: str
    registration_id: str
    assembly_registration_sha256: str
    lineage_registration_ref: MemoryEvidenceRefV1

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "registration_id",
            "assembly_registration_sha256",
            "lineage_registration_ref",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != "PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1":
            raise ValueError("assembly registration schema_id mismatch")
        _require_text("registration_id", self.registration_id)
        _require_sha256(
            "assembly_registration_sha256",
            self.assembly_registration_sha256,
        )
        if not isinstance(self.lineage_registration_ref, MemoryEvidenceRefV1):
            raise TypeError(
                "lineage_registration_ref must be MemoryEvidenceRefV1"
            )
        ref = self.lineage_registration_ref
        if (
            ref.source_kind
            != "PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1"
        ):
            raise ValueError("lineage registration source_kind mismatch")
        if ref.source_id != self.registration_id:
            raise ValueError("lineage registration source_id mismatch")
        if ref.source_sha256 != self.assembly_registration_sha256:
            raise ValueError("lineage registration source_sha256 mismatch")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "registration_id": self.registration_id,
            "assembly_registration_sha256": self.assembly_registration_sha256,
            "lineage_registration_ref": self.lineage_registration_ref.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> "AssemblyRegistrationBindingV1":
        payload = _expect_exact_keys(
            value=value,
            expected=cls._KEYS,
            label="assembly registration binding",
        )
        return cls(
            schema_id=payload["schema_id"],
            registration_id=payload["registration_id"],
            assembly_registration_sha256=payload[
                "assembly_registration_sha256"
            ],
            lineage_registration_ref=MemoryEvidenceRefV1.from_dict(
                payload["lineage_registration_ref"]
            ),
        )


@dataclass(frozen=True, slots=True)
class PreviousProceduralRecordBindingV1:
    memory_lineage_id: str
    record_version: int
    canonical_record_sha256: str

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "memory_lineage_id",
            "record_version",
            "canonical_record_sha256",
        }
    )

    def __post_init__(self) -> None:
        _require_sha256("memory_lineage_id", self.memory_lineage_id)
        _require_positive_version("record_version", self.record_version)
        _require_sha256(
            "canonical_record_sha256",
            self.canonical_record_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "memory_lineage_id": self.memory_lineage_id,
            "record_version": self.record_version,
            "canonical_record_sha256": self.canonical_record_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> "PreviousProceduralRecordBindingV1":
        payload = _expect_exact_keys(
            value=value,
            expected=cls._KEYS,
            label="previous procedural record binding",
        )
        return cls(
            memory_lineage_id=payload["memory_lineage_id"],
            record_version=payload["record_version"],
            canonical_record_sha256=payload["canonical_record_sha256"],
        )


@dataclass(frozen=True, slots=True)
class ProceduralMemoryLineageV1:
    memory_lineage_id: str
    record_version: int
    previous_record_binding: PreviousProceduralRecordBindingV1 | None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "memory_lineage_id",
            "record_version",
            "previous_record_binding",
        }
    )

    def __post_init__(self) -> None:
        _require_sha256("memory_lineage_id", self.memory_lineage_id)
        _require_positive_version("record_version", self.record_version)

        previous = self.previous_record_binding
        if self.record_version == 1:
            if previous is not None:
                raise ValueError("version 1 must not bind previous record")
            return

        if not isinstance(previous, PreviousProceduralRecordBindingV1):
            raise ValueError("version >1 requires previous record binding")
        if previous.memory_lineage_id != self.memory_lineage_id:
            raise ValueError("previous record lineage mismatch")
        if previous.record_version + 1 != self.record_version:
            raise ValueError("previous record version is not consecutive")

    def to_dict(self) -> dict[str, object]:
        return {
            "memory_lineage_id": self.memory_lineage_id,
            "record_version": self.record_version,
            "previous_record_binding": (
                None
                if self.previous_record_binding is None
                else self.previous_record_binding.to_dict()
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> "ProceduralMemoryLineageV1":
        payload = _expect_exact_keys(
            value=value,
            expected=cls._KEYS,
            label="procedural memory lineage",
        )
        previous_value = payload["previous_record_binding"]
        return cls(
            memory_lineage_id=payload["memory_lineage_id"],
            record_version=payload["record_version"],
            previous_record_binding=(
                None
                if previous_value is None
                else PreviousProceduralRecordBindingV1.from_dict(
                    previous_value
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class ProceduralMemoryProvenanceV1:
    creation_event_id: str
    creator_role: str
    assembly_registration_binding: AssemblyRegistrationBindingV1
    factual_sequence_bindings: tuple[FactualSequenceBindingV1, ...]
    created_snapshot_candidate: None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "creation_event_id",
            "creator_role",
            "assembly_registration_binding",
            "factual_sequence_bindings",
            "created_snapshot_candidate",
        }
    )

    def __post_init__(self) -> None:
        _require_text("creation_event_id", self.creation_event_id)
        _require_text("creator_role", self.creator_role)
        if not isinstance(
            self.assembly_registration_binding,
            AssemblyRegistrationBindingV1,
        ):
            raise TypeError(
                "assembly_registration_binding type mismatch"
            )
        if (
            type(self.factual_sequence_bindings) is not tuple
            or not self.factual_sequence_bindings
        ):
            raise ValueError("factual_sequence_bindings must be nonempty tuple")
        if any(
            not isinstance(item, FactualSequenceBindingV1)
            for item in self.factual_sequence_bindings
        ):
            raise TypeError("invalid factual sequence binding")
        ids = tuple(
            item.experience_id for item in self.factual_sequence_bindings
        )
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate factual experience_id")
        if self.created_snapshot_candidate is not None:
            raise ValueError("created_snapshot_candidate must be None")

    def to_dict(self) -> dict[str, object]:
        return {
            "creation_event_id": self.creation_event_id,
            "creator_role": self.creator_role,
            "assembly_registration_binding": (
                self.assembly_registration_binding.to_dict()
            ),
            "factual_sequence_bindings": [
                item.to_dict() for item in self.factual_sequence_bindings
            ],
            "created_snapshot_candidate": None,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ProceduralMemoryProvenanceV1":
        payload = _expect_exact_keys(
            value=value,
            expected=cls._KEYS,
            label="procedural memory provenance",
        )
        bindings = payload["factual_sequence_bindings"]
        if not isinstance(bindings, list):
            raise TypeError("factual_sequence_bindings must be JSON array")
        return cls(
            creation_event_id=payload["creation_event_id"],
            creator_role=payload["creator_role"],
            assembly_registration_binding=(
                AssemblyRegistrationBindingV1.from_dict(
                    payload["assembly_registration_binding"]
                )
            ),
            factual_sequence_bindings=tuple(
                FactualSequenceBindingV1.from_dict(item)
                for item in bindings
            ),
            created_snapshot_candidate=payload[
                "created_snapshot_candidate"
            ],
        )


def record_id_for_lineage_version_v1(
    memory_lineage_id: str,
    record_version: int,
) -> str:
    _require_sha256("memory_lineage_id", memory_lineage_id)
    _require_positive_version("record_version", record_version)
    payload = (
        b"PROCEDURAL_FAILURE_MEMORY_RECORD_ID_V1"
        + b"\0"
        + memory_lineage_id.encode("ascii")
        + b"\0"
        + str(record_version).encode("ascii")
    )
    return hashlib.sha256(payload).hexdigest()


def canonical_payload_sha256_v1(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()

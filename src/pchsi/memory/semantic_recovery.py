from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from pchsi.memory.procedural_record import (
    MemoryAuthorityTypeV1,
    MemoryEvidenceRefV1,
)


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


def _require_nonnegative(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be nonnegative int")
    return value


class SemanticAnnotationTypeV1(str, Enum):
    CANDIDATE_MECHANISM = "CANDIDATE_MECHANISM"
    CAPABILITY_COMPONENT = "CAPABILITY_COMPONENT"
    TASK_FAMILY_HYPOTHESIS = "TASK_FAMILY_HYPOTHESIS"
    CRITICAL_REGION = "CRITICAL_REGION"
    ALTERNATIVE_EXPLANATION = "ALTERNATIVE_EXPLANATION"


class SemanticConfidenceV1(str, Enum):
    UNSPECIFIED = "UNSPECIFIED"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True, slots=True)
class SemanticHypothesisAnnotationV1:
    annotation_id: str
    annotation_type: SemanticAnnotationTypeV1
    authority_type: MemoryAuthorityTypeV1
    text: str
    supporting_refs: tuple[MemoryEvidenceRefV1, ...]
    counterevidence_refs: tuple[MemoryEvidenceRefV1, ...]
    semantic_confidence: SemanticConfidenceV1
    origin_role: str
    origin_identity: str
    origin_artifact_ref: MemoryEvidenceRefV1

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "annotation_id",
            "annotation_type",
            "authority_type",
            "text",
            "supporting_refs",
            "counterevidence_refs",
            "semantic_confidence",
            "origin_role",
            "origin_identity",
            "origin_artifact_ref",
        }
    )

    def __post_init__(self) -> None:
        _require_text("annotation_id", self.annotation_id)
        _require_text("text", self.text)
        _require_text("origin_role", self.origin_role)
        _require_text("origin_identity", self.origin_identity)
        if self.authority_type is not MemoryAuthorityTypeV1.SEMANTIC_HYPOTHESIS:
            raise ValueError("semantic annotation authority mismatch")
        for name, refs in (
            ("supporting_refs", self.supporting_refs),
            ("counterevidence_refs", self.counterevidence_refs),
        ):
            if type(refs) is not tuple:
                raise TypeError(f"{name} must be tuple")
            if any(not isinstance(item, MemoryEvidenceRefV1) for item in refs):
                raise TypeError(f"{name} contains invalid ref")
        if not isinstance(self.origin_artifact_ref, MemoryEvidenceRefV1):
            raise TypeError("origin_artifact_ref type mismatch")
        if (
            self.origin_artifact_ref.source_kind
            != "SEMANTIC_ANNOTATION_ARTIFACT"
        ):
            raise ValueError("semantic origin source_kind mismatch")
        if self.origin_artifact_ref.source_id != self.annotation_id:
            raise ValueError("semantic origin source_id mismatch")

    def to_dict(self) -> dict[str, object]:
        return {
            "annotation_id": self.annotation_id,
            "annotation_type": self.annotation_type.value,
            "authority_type": self.authority_type.value,
            "text": self.text,
            "supporting_refs": [item.to_dict() for item in self.supporting_refs],
            "counterevidence_refs": [
                item.to_dict() for item in self.counterevidence_refs
            ],
            "semantic_confidence": self.semantic_confidence.value,
            "origin_role": self.origin_role,
            "origin_identity": self.origin_identity,
            "origin_artifact_ref": self.origin_artifact_ref.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> "SemanticHypothesisAnnotationV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "semantic hypothesis annotation",
        )

        def refs(name: str) -> tuple[MemoryEvidenceRefV1, ...]:
            raw = payload[name]
            if not isinstance(raw, list):
                raise TypeError(f"{name} must be JSON array")
            return tuple(MemoryEvidenceRefV1.from_dict(item) for item in raw)

        return cls(
            annotation_id=payload["annotation_id"],
            annotation_type=SemanticAnnotationTypeV1(
                payload["annotation_type"]
            ),
            authority_type=MemoryAuthorityTypeV1(payload["authority_type"]),
            text=payload["text"],
            supporting_refs=refs("supporting_refs"),
            counterevidence_refs=refs("counterevidence_refs"),
            semantic_confidence=SemanticConfidenceV1(
                payload["semantic_confidence"]
            ),
            origin_role=payload["origin_role"],
            origin_identity=payload["origin_identity"],
            origin_artifact_ref=MemoryEvidenceRefV1.from_dict(
                payload["origin_artifact_ref"]
            ),
        )


@dataclass(frozen=True, slots=True)
class ObservedRecoveryBindingV1:
    authority_type: MemoryAuthorityTypeV1
    source_experience_id: str
    registered_recovery_start_model_call_index: int
    registered_recovery_final_model_call_index: int
    source_refs: tuple[MemoryEvidenceRefV1, ...]

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "authority_type",
            "source_experience_id",
            "registered_recovery_start_model_call_index",
            "registered_recovery_final_model_call_index",
            "source_refs",
        }
    )

    def __post_init__(self) -> None:
        if self.authority_type is not MemoryAuthorityTypeV1.REGISTERED_BOUNDARY:
            raise ValueError("observed recovery authority mismatch")
        if (
            not isinstance(self.source_experience_id, str)
            or len(self.source_experience_id) != 64
            or any(ch not in "0123456789abcdef" for ch in self.source_experience_id)
        ):
            raise ValueError("source_experience_id must be 64 lowercase hex")
        start = _require_nonnegative(
            "registered_recovery_start_model_call_index",
            self.registered_recovery_start_model_call_index,
        )
        final = _require_nonnegative(
            "registered_recovery_final_model_call_index",
            self.registered_recovery_final_model_call_index,
        )
        if final < start:
            raise ValueError("observed recovery range is reversed")
        if type(self.source_refs) is not tuple or not self.source_refs:
            raise ValueError("observed recovery source_refs must be nonempty")
        if any(not isinstance(item, MemoryEvidenceRefV1) for item in self.source_refs):
            raise TypeError("observed recovery source_refs invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "authority_type": self.authority_type.value,
            "source_experience_id": self.source_experience_id,
            "registered_recovery_start_model_call_index": (
                self.registered_recovery_start_model_call_index
            ),
            "registered_recovery_final_model_call_index": (
                self.registered_recovery_final_model_call_index
            ),
            "source_refs": [item.to_dict() for item in self.source_refs],
        }

    @classmethod
    def from_dict(cls, value: object) -> "ObservedRecoveryBindingV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "observed recovery binding",
        )
        refs = payload["source_refs"]
        if not isinstance(refs, list):
            raise TypeError("observed recovery source_refs must be JSON array")
        return cls(
            authority_type=MemoryAuthorityTypeV1(payload["authority_type"]),
            source_experience_id=payload["source_experience_id"],
            registered_recovery_start_model_call_index=payload[
                "registered_recovery_start_model_call_index"
            ],
            registered_recovery_final_model_call_index=payload[
                "registered_recovery_final_model_call_index"
            ],
            source_refs=tuple(
                MemoryEvidenceRefV1.from_dict(item) for item in refs
            ),
        )


@dataclass(frozen=True, slots=True)
class ProposedRecoveryV1:
    proposal_id: str
    authority_type: MemoryAuthorityTypeV1
    procedure_steps: tuple[str, ...]
    source_refs: tuple[MemoryEvidenceRefV1, ...]
    origin_role: str
    origin_identity: str
    origin_artifact_ref: MemoryEvidenceRefV1

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "proposal_id",
            "authority_type",
            "procedure_steps",
            "source_refs",
            "origin_role",
            "origin_identity",
            "origin_artifact_ref",
        }
    )

    def __post_init__(self) -> None:
        _require_text("proposal_id", self.proposal_id)
        if self.authority_type is not MemoryAuthorityTypeV1.RECOVERY_PROPOSAL:
            raise ValueError("proposed recovery authority mismatch")
        if type(self.procedure_steps) is not tuple or not self.procedure_steps:
            raise ValueError("procedure_steps must be nonempty tuple")
        for step in self.procedure_steps:
            _require_text("procedure step", step)
        if type(self.source_refs) is not tuple or not self.source_refs:
            raise ValueError("proposed recovery source_refs must be nonempty")
        if any(not isinstance(item, MemoryEvidenceRefV1) for item in self.source_refs):
            raise TypeError("proposed recovery source_refs invalid")
        _require_text("origin_role", self.origin_role)
        _require_text("origin_identity", self.origin_identity)
        if not isinstance(self.origin_artifact_ref, MemoryEvidenceRefV1):
            raise TypeError("origin_artifact_ref type mismatch")
        if self.origin_artifact_ref.source_kind != "RECOVERY_PROPOSAL_ARTIFACT":
            raise ValueError("recovery origin source_kind mismatch")
        if self.origin_artifact_ref.source_id != self.proposal_id:
            raise ValueError("recovery origin source_id mismatch")

    def to_dict(self) -> dict[str, object]:
        return {
            "proposal_id": self.proposal_id,
            "authority_type": self.authority_type.value,
            "procedure_steps": list(self.procedure_steps),
            "source_refs": [item.to_dict() for item in self.source_refs],
            "origin_role": self.origin_role,
            "origin_identity": self.origin_identity,
            "origin_artifact_ref": self.origin_artifact_ref.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> "ProposedRecoveryV1":
        payload = _expect_exact_keys(value, cls._KEYS, "proposed recovery")
        steps = payload["procedure_steps"]
        refs = payload["source_refs"]
        if not isinstance(steps, list):
            raise TypeError("procedure_steps must be JSON array")
        if not isinstance(refs, list):
            raise TypeError("source_refs must be JSON array")
        return cls(
            proposal_id=payload["proposal_id"],
            authority_type=MemoryAuthorityTypeV1(payload["authority_type"]),
            procedure_steps=tuple(steps),
            source_refs=tuple(
                MemoryEvidenceRefV1.from_dict(item) for item in refs
            ),
            origin_role=payload["origin_role"],
            origin_identity=payload["origin_identity"],
            origin_artifact_ref=MemoryEvidenceRefV1.from_dict(
                payload["origin_artifact_ref"]
            ),
        )

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


class BoundaryTypeV1(str, Enum):
    ACTIVATION = "ACTIVATION"
    CONTINUATION = "CONTINUATION"
    REVALIDATION = "REVALIDATION"
    RELEASE = "RELEASE"
    TERMINATION = "TERMINATION"
    NON_APPLICABILITY = "NON_APPLICABILITY"
    POLICY_VISIBLE_STATE_CHANGE_TRIGGER = "POLICY_VISIBLE_STATE_CHANGE_TRIGGER"


class BoundaryVerificationStatusV1(str, Enum):
    REGISTERED_UNVERIFIED = "REGISTERED_UNVERIFIED"


class RevalidationRequirementV1(str, Enum):
    REQUIRED = "REQUIRED"
    NOT_REQUIRED = "NOT_REQUIRED"
    UNRESOLVED = "UNRESOLVED"


class NonApplicabilityDispositionV1(str, Enum):
    REGISTERED_CONDITIONS = "REGISTERED_CONDITIONS"
    UNRESOLVED_NO_REGISTERED_CONDITION = (
        "UNRESOLVED_NO_REGISTERED_CONDITION"
    )


@dataclass(frozen=True, slots=True)
class MemoryBoundaryClauseV1:
    boundary_type: BoundaryTypeV1
    boundary_authority: MemoryAuthorityTypeV1
    origin_role: str
    registration_id: str
    origin_artifact_ref: MemoryEvidenceRefV1
    condition_text: str
    source_refs: tuple[MemoryEvidenceRefV1, ...]
    verification_status: BoundaryVerificationStatusV1

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "boundary_type",
            "boundary_authority",
            "origin_role",
            "registration_id",
            "origin_artifact_ref",
            "condition_text",
            "source_refs",
            "verification_status",
        }
    )

    def __post_init__(self) -> None:
        if self.boundary_authority is not MemoryAuthorityTypeV1.REGISTERED_BOUNDARY:
            raise ValueError("boundary authority must be REGISTERED_BOUNDARY")
        if (
            self.verification_status
            is not BoundaryVerificationStatusV1.REGISTERED_UNVERIFIED
        ):
            raise ValueError("boundary verification must remain unverified")
        _require_text("origin_role", self.origin_role)
        _require_text("registration_id", self.registration_id)
        _require_text("condition_text", self.condition_text)
        if not isinstance(self.origin_artifact_ref, MemoryEvidenceRefV1):
            raise TypeError("origin_artifact_ref type mismatch")
        if (
            self.origin_artifact_ref.source_kind
            != "REGISTERED_BOUNDARY_ARTIFACT"
        ):
            raise ValueError("boundary origin source_kind mismatch")
        if self.origin_artifact_ref.source_id != self.registration_id:
            raise ValueError("boundary origin source_id mismatch")
        if type(self.source_refs) is not tuple or not self.source_refs:
            raise ValueError("boundary source_refs must be nonempty tuple")
        if any(not isinstance(item, MemoryEvidenceRefV1) for item in self.source_refs):
            raise TypeError("boundary source_refs contain invalid item")

    def to_dict(self) -> dict[str, object]:
        return {
            "boundary_type": self.boundary_type.value,
            "boundary_authority": self.boundary_authority.value,
            "origin_role": self.origin_role,
            "registration_id": self.registration_id,
            "origin_artifact_ref": self.origin_artifact_ref.to_dict(),
            "condition_text": self.condition_text,
            "source_refs": [item.to_dict() for item in self.source_refs],
            "verification_status": self.verification_status.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> "MemoryBoundaryClauseV1":
        payload = _expect_exact_keys(value, cls._KEYS, "memory boundary clause")
        refs = payload["source_refs"]
        if not isinstance(refs, list):
            raise TypeError("boundary source_refs must be JSON array")
        return cls(
            boundary_type=BoundaryTypeV1(payload["boundary_type"]),
            boundary_authority=MemoryAuthorityTypeV1(
                payload["boundary_authority"]
            ),
            origin_role=payload["origin_role"],
            registration_id=payload["registration_id"],
            origin_artifact_ref=MemoryEvidenceRefV1.from_dict(
                payload["origin_artifact_ref"]
            ),
            condition_text=payload["condition_text"],
            source_refs=tuple(
                MemoryEvidenceRefV1.from_dict(item) for item in refs
            ),
            verification_status=BoundaryVerificationStatusV1(
                payload["verification_status"]
            ),
        )


@dataclass(frozen=True, slots=True)
class ApplicabilityBoundarySetV1:
    activation: tuple[MemoryBoundaryClauseV1, ...]
    continuation: tuple[MemoryBoundaryClauseV1, ...]
    revalidation_requirement: RevalidationRequirementV1
    revalidation: tuple[MemoryBoundaryClauseV1, ...]
    release: tuple[MemoryBoundaryClauseV1, ...]
    termination: tuple[MemoryBoundaryClauseV1, ...]
    non_applicability_disposition: NonApplicabilityDispositionV1
    non_applicability: tuple[MemoryBoundaryClauseV1, ...]
    policy_visible_state_change_trigger: tuple[MemoryBoundaryClauseV1, ...]

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "activation",
            "continuation",
            "revalidation_requirement",
            "revalidation",
            "release",
            "termination",
            "non_applicability_disposition",
            "non_applicability",
            "policy_visible_state_change_trigger",
        }
    )

    def __post_init__(self) -> None:
        fields = (
            ("activation", self.activation, BoundaryTypeV1.ACTIVATION),
            ("continuation", self.continuation, BoundaryTypeV1.CONTINUATION),
            ("revalidation", self.revalidation, BoundaryTypeV1.REVALIDATION),
            ("release", self.release, BoundaryTypeV1.RELEASE),
            ("termination", self.termination, BoundaryTypeV1.TERMINATION),
            (
                "non_applicability",
                self.non_applicability,
                BoundaryTypeV1.NON_APPLICABILITY,
            ),
            (
                "policy_visible_state_change_trigger",
                self.policy_visible_state_change_trigger,
                BoundaryTypeV1.POLICY_VISIBLE_STATE_CHANGE_TRIGGER,
            ),
        )
        for name, items, expected_type in fields:
            if type(items) is not tuple:
                raise TypeError(f"{name} must be tuple")
            for item in items:
                if not isinstance(item, MemoryBoundaryClauseV1):
                    raise TypeError(f"{name} contains invalid boundary")
                if item.boundary_type is not expected_type:
                    raise ValueError(f"{name} contains wrong boundary_type")

        if not self.activation:
            raise ValueError("activation boundary must be nonempty")
        if not self.release and not self.termination:
            raise ValueError("release or termination boundary is required")

        if (
            self.revalidation_requirement is RevalidationRequirementV1.REQUIRED
            and not self.revalidation
        ):
            raise ValueError("required revalidation needs clauses")

        if (
            self.non_applicability_disposition
            is NonApplicabilityDispositionV1.REGISTERED_CONDITIONS
        ):
            if not self.non_applicability:
                raise ValueError(
                    "registered non-applicability requires conditions"
                )
        else:
            if self.non_applicability:
                raise ValueError(
                    "unresolved non-applicability must not carry conditions"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "activation": [item.to_dict() for item in self.activation],
            "continuation": [item.to_dict() for item in self.continuation],
            "revalidation_requirement": self.revalidation_requirement.value,
            "revalidation": [item.to_dict() for item in self.revalidation],
            "release": [item.to_dict() for item in self.release],
            "termination": [item.to_dict() for item in self.termination],
            "non_applicability_disposition": (
                self.non_applicability_disposition.value
            ),
            "non_applicability": [
                item.to_dict() for item in self.non_applicability
            ],
            "policy_visible_state_change_trigger": [
                item.to_dict()
                for item in self.policy_visible_state_change_trigger
            ],
        }

    @classmethod
    def from_dict(cls, value: object) -> "ApplicabilityBoundarySetV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "applicability boundary set",
        )

        def clauses(name: str) -> tuple[MemoryBoundaryClauseV1, ...]:
            raw = payload[name]
            if not isinstance(raw, list):
                raise TypeError(f"{name} must be JSON array")
            return tuple(MemoryBoundaryClauseV1.from_dict(item) for item in raw)

        return cls(
            activation=clauses("activation"),
            continuation=clauses("continuation"),
            revalidation_requirement=RevalidationRequirementV1(
                payload["revalidation_requirement"]
            ),
            revalidation=clauses("revalidation"),
            release=clauses("release"),
            termination=clauses("termination"),
            non_applicability_disposition=NonApplicabilityDispositionV1(
                payload["non_applicability_disposition"]
            ),
            non_applicability=clauses("non_applicability"),
            policy_visible_state_change_trigger=clauses(
                "policy_visible_state_change_trigger"
            ),
        )

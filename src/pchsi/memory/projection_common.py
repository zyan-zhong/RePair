"""Common contracts for Failure Memory V1 Policy projections.

This module is pure/offline. It does not load a tokenizer, call a model,
perform retrieval, execute an environment, or mutate Memory authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Protocol

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    strict_json_loads,
)
from pchsi.memory.lifecycle_relations import (
    AccessScopeV1,
    DescriptiveEligibilityStatusV1,
    EvaluationContaminationStatusV1,
    LifecycleStatusV1,
    MemoryGovernanceStateV1,
    SourceIntegrityStatusV1,
)


class ProjectionClassV1(str, Enum):
    FM1 = "FM1"
    FM2 = "FM2"
    FM3 = "FM3"


class ProjectionBuildDispositionV1(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    PROJECTION_INELIGIBLE_SOURCE_INTEGRITY = (
        "PROJECTION_INELIGIBLE_SOURCE_INTEGRITY"
    )
    PROJECTION_INELIGIBLE_DESCRIPTIVE_ELIGIBILITY = (
        "PROJECTION_INELIGIBLE_DESCRIPTIVE_ELIGIBILITY"
    )
    PROJECTION_INELIGIBLE_ACCESS_SCOPE = (
        "PROJECTION_INELIGIBLE_ACCESS_SCOPE"
    )
    PROJECTION_INELIGIBLE_EVALUATION_CONTAMINATION = (
        "PROJECTION_INELIGIBLE_EVALUATION_CONTAMINATION"
    )
    PROJECTION_INELIGIBLE_LIFECYCLE = (
        "PROJECTION_INELIGIBLE_LIFECYCLE"
    )
    PROJECTION_INELIGIBLE_POLICY_VIEW_SAFETY = (
        "PROJECTION_INELIGIBLE_POLICY_VIEW_SAFETY"
    )
    PROJECTION_INELIGIBLE_TOKEN_BUDGET = (
        "PROJECTION_INELIGIBLE_TOKEN_BUDGET"
    )
    PROJECTION_INELIGIBLE_FM1_SOURCE_AMBIGUOUS = (
        "PROJECTION_INELIGIBLE_FM1_SOURCE_AMBIGUOUS"
    )


class FM3RecoveryDispositionV1(str, Enum):
    RECOVERY_VISIBLE = "RECOVERY_VISIBLE"
    FM3_NO_RECOVERY_PROPOSAL = "FM3_NO_RECOVERY_PROPOSAL"
    FM3_PRESCRIPTIVE_AUTHORITY_NOT_ESTABLISHED = (
        "FM3_PRESCRIPTIVE_AUTHORITY_NOT_ESTABLISHED"
    )
    FM3_RECOVERY_PROPOSAL_AMBIGUOUS = (
        "FM3_RECOVERY_PROPOSAL_AMBIGUOUS"
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


def _require_positive_int(name: str, value: object) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be positive int")
    return value


def _require_nonnegative_int(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be nonnegative int")
    return value


@dataclass(frozen=True, slots=True)
class ProjectionRecordBindingV1:
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
        require_lower_sha256("memory_lineage_id", self.memory_lineage_id)
        _require_positive_int("record_version", self.record_version)
        require_lower_sha256(
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
    def from_dict(cls, value: object) -> "ProjectionRecordBindingV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "projection record binding",
        )
        return cls(
            memory_lineage_id=payload["memory_lineage_id"],
            record_version=payload["record_version"],
            canonical_record_sha256=payload["canonical_record_sha256"],
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> "ProjectionRecordBindingV1":
        return cls.from_dict(strict_json_loads(value))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


class PolicyTokenizerCounterV1(Protocol):
    tokenizer_id: str
    tokenizer_revision: str

    def count_tokens(self, text: str) -> int:
        ...


@dataclass(frozen=True, slots=True)
class ProjectionTokenCountV1:
    tokenizer_id: str
    tokenizer_revision: str
    policy_visible_token_count: int
    hard_ceiling: int

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "tokenizer_id",
            "tokenizer_revision",
            "policy_visible_token_count",
            "hard_ceiling",
        }
    )

    def __post_init__(self) -> None:
        _require_text("tokenizer_id", self.tokenizer_id)
        _require_text("tokenizer_revision", self.tokenizer_revision)
        _require_nonnegative_int(
            "policy_visible_token_count",
            self.policy_visible_token_count,
        )
        ceiling = _require_positive_int("hard_ceiling", self.hard_ceiling)
        if ceiling > 4096:
            raise ValueError("hard_ceiling must not exceed 4096")

    def to_dict(self) -> dict[str, object]:
        return {
            "tokenizer_id": self.tokenizer_id,
            "tokenizer_revision": self.tokenizer_revision,
            "policy_visible_token_count": self.policy_visible_token_count,
            "hard_ceiling": self.hard_ceiling,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ProjectionTokenCountV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "projection token count",
        )
        return cls(
            tokenizer_id=payload["tokenizer_id"],
            tokenizer_revision=payload["tokenizer_revision"],
            policy_visible_token_count=payload[
                "policy_visible_token_count"
            ],
            hard_ceiling=payload["hard_ceiling"],
        )


def count_policy_visible_tokens_v1(
    *,
    policy_visible_payload: object,
    tokenizer: PolicyTokenizerCounterV1,
    hard_ceiling: int,
) -> ProjectionTokenCountV1:
    if not isinstance(tokenizer, object):
        raise TypeError("tokenizer must implement PolicyTokenizerCounterV1")
    ceiling = _require_positive_int("hard_ceiling", hard_ceiling)
    if ceiling > 4096:
        raise ValueError("hard_ceiling must not exceed 4096")

    tokenizer_id = _require_text(
        "tokenizer.tokenizer_id",
        getattr(tokenizer, "tokenizer_id", None),
    )
    tokenizer_revision = _require_text(
        "tokenizer.tokenizer_revision",
        getattr(tokenizer, "tokenizer_revision", None),
    )
    count_fn = getattr(tokenizer, "count_tokens", None)
    if not callable(count_fn):
        raise TypeError("tokenizer.count_tokens must be callable")

    canonical_text = canonical_json_bytes(
        policy_visible_payload
    ).decode("utf-8")
    count = count_fn(canonical_text)
    _require_nonnegative_int("count_tokens result", count)
    return ProjectionTokenCountV1(
        tokenizer_id=tokenizer_id,
        tokenizer_revision=tokenizer_revision,
        policy_visible_token_count=count,
        hard_ceiling=ceiling,
    )


def policy_view_governance_disposition_v1(
    state: MemoryGovernanceStateV1,
) -> ProjectionBuildDispositionV1:
    if not isinstance(state, MemoryGovernanceStateV1):
        raise TypeError("state must be MemoryGovernanceStateV1")

    if state.source_integrity is not SourceIntegrityStatusV1.VERIFIED:
        return (
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_SOURCE_INTEGRITY
        )

    if (
        state.descriptive_eligibility
        is not
        DescriptiveEligibilityStatusV1.RETRIEVAL_ELIGIBLE_DESCRIPTIVE
    ):
        return (
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_DESCRIPTIVE_ELIGIBILITY
        )

    if state.access_scope is AccessScopeV1.STAGING_ONLY:
        return (
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_ACCESS_SCOPE
        )

    if state.evaluation_contamination_status in {
        EvaluationContaminationStatusV1.NOT_EVALUATED,
        EvaluationContaminationStatusV1.CONTAMINATED,
    }:
        return (
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_EVALUATION_CONTAMINATION
        )

    if state.lifecycle_status in {
        LifecycleStatusV1.QUARANTINE,
        LifecycleStatusV1.DISABLED,
        LifecycleStatusV1.SUPERSEDED,
    }:
        return (
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_LIFECYCLE
        )

    return ProjectionBuildDispositionV1.ELIGIBLE

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .common import hashed_payload, require_nonnegative_int, require_sha256, require_text


class RoundStageV1(str, Enum):
    ROUND_CREATED = "ROUND_CREATED"
    EVIDENCE_READY = "EVIDENCE_READY"
    ANALYSIS_READY = "ANALYSIS_READY"
    PRE_PLAN_FROZEN = "PRE_PLAN_FROZEN"
    EXPERIMENTS_COMPLETED = "EXPERIMENTS_COMPLETED"
    POST_PLAN_FROZEN = "POST_PLAN_FROZEN"
    NO_TRAINING_UPDATE = "NO_TRAINING_UPDATE"
    TRAINING_DATA_READY = "TRAINING_DATA_READY"
    TRAINING_COMPLETED = "TRAINING_COMPLETED"
    INTERNAL_EVALUATION_COMPLETED = "INTERNAL_EVALUATION_COMPLETED"
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"
    ROUND_CLOSED = "ROUND_CLOSED"


_ALLOWED_NEXT: dict[RoundStageV1, frozenset[RoundStageV1]] = {
    RoundStageV1.ROUND_CREATED: frozenset({RoundStageV1.EVIDENCE_READY}),
    RoundStageV1.EVIDENCE_READY: frozenset({RoundStageV1.ANALYSIS_READY}),
    RoundStageV1.ANALYSIS_READY: frozenset({RoundStageV1.PRE_PLAN_FROZEN}),
    RoundStageV1.PRE_PLAN_FROZEN: frozenset({RoundStageV1.EXPERIMENTS_COMPLETED}),
    RoundStageV1.EXPERIMENTS_COMPLETED: frozenset({RoundStageV1.POST_PLAN_FROZEN}),
    RoundStageV1.POST_PLAN_FROZEN: frozenset(
        {RoundStageV1.TRAINING_DATA_READY, RoundStageV1.NO_TRAINING_UPDATE}
    ),
    RoundStageV1.NO_TRAINING_UPDATE: frozenset({RoundStageV1.ROUND_CLOSED}),
    RoundStageV1.TRAINING_DATA_READY: frozenset({RoundStageV1.TRAINING_COMPLETED}),
    RoundStageV1.TRAINING_COMPLETED: frozenset(
        {RoundStageV1.INTERNAL_EVALUATION_COMPLETED}
    ),
    RoundStageV1.INTERNAL_EVALUATION_COMPLETED: frozenset(
        {RoundStageV1.PROMOTED, RoundStageV1.ROLLED_BACK}
    ),
    RoundStageV1.PROMOTED: frozenset({RoundStageV1.ROUND_CLOSED}),
    RoundStageV1.ROLLED_BACK: frozenset({RoundStageV1.ROUND_CLOSED}),
    RoundStageV1.ROUND_CLOSED: frozenset(),
}


@dataclass(frozen=True)
class RoundLifecycleV1:
    round_id: str
    parent_policy_id: str
    current_stage: RoundStageV1
    transition_index: int
    last_evidence_sha256: str | None
    lifecycle_sha256: str

    @classmethod
    def new(
        cls,
        *,
        round_id: str,
        parent_policy_id: str,
    ) -> "RoundLifecycleV1":
        require_text("round_id", round_id)
        require_text("parent_policy_id", parent_policy_id)
        payload = {
            "schema_id": "ROUND_LIFECYCLE_V1",
            "schema_version": 1,
            "round_id": round_id,
            "parent_policy_id": parent_policy_id,
            "current_stage": RoundStageV1.ROUND_CREATED.value,
            "transition_index": 0,
            "last_evidence_sha256": None,
        }
        hashed = hashed_payload(
            domain="ROUND_LIFECYCLE_V1",
            hash_field="lifecycle_sha256",
            payload=payload,
        )
        return cls(
            round_id=round_id,
            parent_policy_id=parent_policy_id,
            current_stage=RoundStageV1.ROUND_CREATED,
            transition_index=0,
            last_evidence_sha256=None,
            lifecycle_sha256=hashed["lifecycle_sha256"],
        )

    def advance(
        self,
        next_stage: RoundStageV1,
        *,
        evidence_sha256: str,
    ) -> "RoundLifecycleV1":
        if not isinstance(next_stage, RoundStageV1):
            raise TypeError("next_stage must be RoundStageV1")
        require_sha256("evidence_sha256", evidence_sha256)
        allowed = _ALLOWED_NEXT[self.current_stage]
        if next_stage not in allowed:
            raise ValueError(
                "invalid lifecycle transition: "
                f"{self.current_stage.value} -> {next_stage.value}"
            )
        next_index = self.transition_index + 1
        require_nonnegative_int("transition_index", next_index)
        payload = {
            "schema_id": "ROUND_LIFECYCLE_V1",
            "schema_version": 1,
            "round_id": self.round_id,
            "parent_policy_id": self.parent_policy_id,
            "current_stage": next_stage.value,
            "transition_index": next_index,
            "last_evidence_sha256": evidence_sha256,
        }
        hashed = hashed_payload(
            domain="ROUND_LIFECYCLE_V1",
            hash_field="lifecycle_sha256",
            payload=payload,
        )
        return replace(
            self,
            current_stage=next_stage,
            transition_index=next_index,
            last_evidence_sha256=evidence_sha256,
            lifecycle_sha256=hashed["lifecycle_sha256"],
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "ROUND_LIFECYCLE_V1",
            "schema_version": 1,
            "round_id": self.round_id,
            "parent_policy_id": self.parent_policy_id,
            "current_stage": self.current_stage.value,
            "transition_index": self.transition_index,
            "last_evidence_sha256": self.last_evidence_sha256,
            "lifecycle_sha256": self.lifecycle_sha256,
        }

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .common import hashed_payload, require_sha256, require_text
from .role_authority import ResearchRoleV1


class ActorV1(str, Enum):
    HUMAN = "HUMAN"
    STRONG = "STRONG"
    LOCAL = "LOCAL"


class AuthorityModeV1(str, Enum):
    PRIMARY = "PRIMARY"
    SHADOW = "SHADOW"
    AUDITOR = "AUDITOR"


@dataclass(frozen=True)
class RoleTraceRecordV1:
    round_id: str
    role: ResearchRoleV1
    actor: ActorV1
    authority_mode: AuthorityModeV1
    input_artifact_sha256: str
    output_artifact_sha256: str
    access_class: str
    structured_output_only: bool
    provider_reasoning_artifact_required: bool

    def validate(self) -> None:
        require_text("round_id", self.round_id)
        require_sha256("input_artifact_sha256", self.input_artifact_sha256)
        require_sha256("output_artifact_sha256", self.output_artifact_sha256)
        require_text("access_class", self.access_class)
        if self.access_class not in {
            "TRAIN_REFERENCE_ROUND",
            "TRAIN_RESEARCH_INTELLIGENCE",
            "TRAIN_AUTONOMOUS_ROUND",
        }:
            raise ValueError("role trace must be train-side")
        if self.structured_output_only is not True:
            raise ValueError("role trace must use structured output")
        if self.provider_reasoning_artifact_required is not False:
            raise ValueError("provider hidden reasoning must not be required")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema_id": "ROLE_TRACE_RECORD_V1",
            "schema_version": 1,
            "round_id": self.round_id,
            "role": self.role.value,
            "actor": self.actor.value,
            "authority_mode": self.authority_mode.value,
            "input_artifact_sha256": self.input_artifact_sha256,
            "output_artifact_sha256": self.output_artifact_sha256,
            "access_class": self.access_class,
            "structured_output_only": self.structured_output_only,
            "provider_reasoning_artifact_required": (
                self.provider_reasoning_artifact_required
            ),
        }
        return hashed_payload(
            domain="ROLE_TRACE_RECORD_V1",
            hash_field="trace_record_sha256",
            payload=payload,
        )


@dataclass(frozen=True)
class RoundTraceLedgerV1:
    round_id: str
    records: tuple[RoleTraceRecordV1, ...]

    def validate(
        self,
        *,
        require_strong_pre: bool,
        require_strong_post: bool,
    ) -> None:
        require_text("round_id", self.round_id)
        seen: set[tuple[str, str, str]] = set()
        for record in self.records:
            record.validate()
            if record.round_id != self.round_id:
                raise ValueError("trace round mismatch")
            key = (
                record.role.value,
                record.actor.value,
                record.authority_mode.value,
            )
            if key in seen:
                raise ValueError("duplicate role/actor/authority trace")
            seen.add(key)
        if require_strong_pre and not any(
            record.role is ResearchRoleV1.RESEARCH_PLANNER_PRE
            and record.actor is ActorV1.STRONG
            for record in self.records
        ):
            raise ValueError("strong PRE trace is required")
        if require_strong_post and not any(
            record.role is ResearchRoleV1.RESEARCH_PLANNER_POST
            and record.actor is ActorV1.STRONG
            for record in self.records
        ):
            raise ValueError("strong POST trace is required")

    def localization_teacher_records(self) -> tuple[RoleTraceRecordV1, ...]:
        return tuple(
            record
            for record in self.records
            if record.actor is ActorV1.STRONG
            and record.role
            in {
                ResearchRoleV1.ANALYZER,
                ResearchRoleV1.RESEARCH_PLANNER_PRE,
                ResearchRoleV1.RESEARCH_PLANNER_POST,
            }
        )

    def to_dict(self) -> dict[str, object]:
        payload = {
            "schema_id": "ROUND_TRACE_LEDGER_V1",
            "schema_version": 1,
            "round_id": self.round_id,
            "records": [record.to_dict() for record in self.records],
            "strong_trace_storage_required": True,
            "localization_distillation_compatible": True,
        }
        return hashed_payload(
            domain="ROUND_TRACE_LEDGER_V1",
            hash_field="trace_ledger_sha256",
            payload=payload,
        )

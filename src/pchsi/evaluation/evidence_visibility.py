"""Machine-verifiable P1-B evidence visibility projections."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Sequence

from .canonical_evidence import canonical_json_text
from .distillation_access import DistillationAccessClass
from .policy_call_evidence import (
    PolicyCallEvidenceV1,
    semantic_policy_call_payload,
)
from .schema_contract import validate_payload_against_schema


class EvidenceVisibilityClass(str, Enum):
    POLICY_VISIBLE_AT_DECISION = (
        "POLICY_VISIBLE_AT_DECISION"
    )
    POST_ACTION_PUBLIC_AUDIT = (
        "POST_ACTION_PUBLIC_AUDIT"
    )
    EPISODE_TERMINAL_OUTCOME = (
        "EPISODE_TERMINAL_OUTCOME"
    )
    OFFLINE_TEACHER_VISIBLE_DEV_ONLY = (
        "OFFLINE_TEACHER_VISIBLE_DEV_ONLY"
    )
    OPERATIONAL_PROVENANCE_ONLY = (
        "OPERATIONAL_PROVENANCE_ONLY"
    )
    SEALED_ORACLE_AUDIT_ONLY = (
        "SEALED_ORACLE_AUDIT_ONLY"
    )


@dataclass(frozen=True, slots=True)
class EvidenceVisibilityRecordV1:
    field_name: str
    visibility_class: EvidenceVisibilityClass
    student_input_eligible: bool
    teacher_input_eligible: bool
    q2_replay_required: bool
    select_export_permitted: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "field_name": self.field_name,
            "visibility_class": self.visibility_class.value,
            "student_input_eligible": (
                self.student_input_eligible
            ),
            "teacher_input_eligible": (
                self.teacher_input_eligible
            ),
            "q2_replay_required": self.q2_replay_required,
            "select_export_permitted": (
                self.select_export_permitted
            ),
        }


@dataclass(frozen=True, slots=True)
class EvidenceVisibilityMatrixV1:
    SCHEMA_ID: ClassVar[str] = (
        "EVIDENCE_VISIBILITY_MATRIX_V1"
    )

    schema_id: str = "EVIDENCE_VISIBILITY_MATRIX_V1"
    schema_version: int = 1
    matrix_id: str = "EVIDENCE_VISIBILITY_MATRIX_V1"
    record_count: int = 0
    records: tuple[EvidenceVisibilityRecordV1, ...] = ()

    def __post_init__(self) -> None:
        if self.record_count != len(self.records):
            raise ValueError("record_count mismatch")
        validate_payload_against_schema(
            schema_id=self.SCHEMA_ID,
            payload=self.to_dict(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "matrix_id": self.matrix_id,
            "record_count": self.record_count,
            "records": [
                record.to_dict()
                for record in self.records
            ],
        }

    def to_json(self) -> str:
        return canonical_json_text(self.to_dict())


def build_visibility_matrix(
) -> EvidenceVisibilityMatrixV1:
    rows = (
        EvidenceVisibilityRecordV1(
            "policy_call.predecision",
            EvidenceVisibilityClass.POLICY_VISIBLE_AT_DECISION,
            True,
            True,
            True,
            False,
        ),
        EvidenceVisibilityRecordV1(
            "public_transition.result",
            EvidenceVisibilityClass.POST_ACTION_PUBLIC_AUDIT,
            False,
            True,
            True,
            True,
        ),
        EvidenceVisibilityRecordV1(
            "episode.terminal_outcome",
            EvidenceVisibilityClass.EPISODE_TERMINAL_OUTCOME,
            False,
            True,
            False,
            True,
        ),
        EvidenceVisibilityRecordV1(
            "teacher.rationale",
            EvidenceVisibilityClass.OFFLINE_TEACHER_VISIBLE_DEV_ONLY,
            False,
            True,
            False,
            False,
        ),
        EvidenceVisibilityRecordV1(
            "transport.latency",
            EvidenceVisibilityClass.OPERATIONAL_PROVENANCE_ONLY,
            False,
            False,
            False,
            False,
        ),
        EvidenceVisibilityRecordV1(
            "oracle.hidden_state",
            EvidenceVisibilityClass.SEALED_ORACLE_AUDIT_ONLY,
            False,
            False,
            False,
            False,
        ),
    )
    return EvidenceVisibilityMatrixV1(
        record_count=len(rows),
        records=rows,
    )


def validate_visibility_matrix(
    matrix: EvidenceVisibilityMatrixV1,
) -> None:
    if not isinstance(matrix, EvidenceVisibilityMatrixV1):
        raise TypeError(
            "matrix must be EvidenceVisibilityMatrixV1"
        )

    seen: set[str] = set()
    for record in matrix.records:
        if record.field_name in seen:
            raise ValueError("duplicate visibility field")
        seen.add(record.field_name)

        if (
            record.visibility_class
            is EvidenceVisibilityClass.SEALED_ORACLE_AUDIT_ONLY
            and (
                record.student_input_eligible
                or record.teacher_input_eligible
                or record.select_export_permitted
            )
        ):
            raise ValueError(
                "sealed oracle evidence cannot be exported"
            )

        if (
            record.student_input_eligible
            and record.visibility_class
            is not EvidenceVisibilityClass.POLICY_VISIBLE_AT_DECISION
        ):
            raise ValueError(
                "student input must be policy-visible at decision"
            )


def build_student_decision_projection(
    policy_call: PolicyCallEvidenceV1,
) -> dict[str, object]:
    required = (
        "public_task_goal",
        "observation",
        "admissible_commands",
        "executed_history",
        "interface_feedback_before",
        "prompt_text",
        "rendered_prompt_text",
    )
    missing = tuple(
        name
        for name in required
        if not hasattr(policy_call, name)
    )
    if missing:
        raise TypeError(
            "policy_call is missing projection fields: "
            + ",".join(missing)
        )

    return {
        "public_task_goal": policy_call.public_task_goal,
        "observation": policy_call.observation,
        "admissible_commands": list(
            policy_call.admissible_commands
        ),
        "executed_history": [
            {
                "action": action,
                "resulting_observation": observation,
            }
            # MEMORY_M0_V1 is the only executed-history window
            # policy-visible at decision time.
            for action, observation
            in policy_call.executed_history[-8:]
        ],
        "interface_feedback": (
            policy_call.interface_feedback_before
        ),
        "prompt_text": policy_call.prompt_text,
        "rendered_prompt_text": (
            policy_call.rendered_prompt_text
        ),
    }


def _episode_field(
    episode: object,
    name: str,
) -> object:
    if isinstance(episode, dict):
        return episode.get(name)
    return getattr(episode, name, None)


def build_dev_teacher_projection(
    *,
    access_class: DistillationAccessClass,
    episode: object,
    policy_calls: Sequence[PolicyCallEvidenceV1],
    action_traces: Sequence[object],
    public_transitions: Sequence[object],
) -> dict[str, object]:
    if access_class is not DistillationAccessClass.DEV_VISIBLE:
        raise PermissionError(
            "teacher projection requires DEV_VISIBLE"
        )

    if _episode_field(episode, "access_class") != "DEV_VISIBLE":
        raise PermissionError(
            "episode is not bound to DEV_VISIBLE"
        )
    if (
        _episode_field(episode, "policy_condition_id")
        != "P4-R0-PI0"
    ):
        raise PermissionError(
            "episode is not bound to P4-R0-PI0"
        )
    identity_names = (
        "task_access_manifest_sha256",
        "policy_condition_manifest_sha256",
        "condition_run_schedule_sha256",
        "condition_cell_id",
    )
    episode_identity = {
        name: _episode_field(episode, name)
        for name in identity_names
    }
    for name, value in episode_identity.items():
        if not isinstance(value, str) or not value:
            raise PermissionError(
                f"episode {name} is missing"
            )

    episode_condition_cell = episode_identity[
        "condition_cell_id"
    ]

    for trace in action_traces:
        provenance = getattr(trace, "provenance", None)
        if provenance is None:
            raise PermissionError(
                "ActionTrace provenance is missing"
            )
        if getattr(
            provenance,
            "access_class",
            None,
        ) != "DEV_VISIBLE":
            raise PermissionError(
                "ActionTrace is not DEV_VISIBLE"
            )
        if getattr(
            provenance,
            "policy_condition_id",
            None,
        ) != "P4-R0-PI0":
            raise PermissionError(
                "ActionTrace policy identity mismatch"
            )
        for name, expected in episode_identity.items():
            if getattr(provenance, name, None) != expected:
                raise PermissionError(
                    "ActionTrace condition identity mismatch"
                )

    for transition in public_transitions:
        if getattr(
            transition,
            "scheduled_cell_id",
            episode_condition_cell,
        ) != episode_condition_cell:
            raise PermissionError(
                "PublicTransition condition identity mismatch"
            )

    return {
        "episode": (
            episode.to_dict()
            if hasattr(episode, "to_dict")
            else episode
        ),
        "policy_calls": [
            semantic_policy_call_payload(policy_call)
            for policy_call in policy_calls
        ],
        "action_traces": [
            (
                trace.to_dict()
                if hasattr(trace, "to_dict")
                else trace
            )
            for trace in action_traces
        ],
        "public_transitions": [
            (
                transition.to_dict()
                if hasattr(transition, "to_dict")
                else transition
            )
            for transition in public_transitions
        ],
    }

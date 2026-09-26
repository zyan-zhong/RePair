"""Fail-closed P1-B complete-trajectory evidence validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Sequence

from .canonical_evidence import canonical_json_text
from .evidence_visibility import (
    build_student_decision_projection,
    build_visibility_matrix,
    validate_visibility_matrix,
)
from .schema_contract import validate_payload_against_schema


class EvidenceRequirementStatus(str, Enum):
    PRESENT_AND_VALIDATED = "PRESENT_AND_VALIDATED"
    PRESENT_BUT_UNVALIDATED = "PRESENT_BUT_UNVALIDATED"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    NOT_APPLICABLE_WITH_JUSTIFICATION = (
        "NOT_APPLICABLE_WITH_JUSTIFICATION"
    )


@dataclass(frozen=True, slots=True)
class EvidenceRequirementV1:
    requirement_id: str
    status: EvidenceRequirementStatus
    critical: bool
    source_reference: str | None
    justification: str

    def to_dict(self) -> dict[str, object]:
        return {
            "requirement_id": self.requirement_id,
            "status": self.status.value,
            "critical": self.critical,
            "source_reference": self.source_reference,
            "justification": self.justification,
        }


@dataclass(frozen=True, slots=True)
class EvidenceCompletenessReportV1:
    SCHEMA_ID: ClassVar[str] = (
        "P1_B_EVIDENCE_COMPLETENESS_REPORT_V1"
    )

    schema_id: str
    schema_version: int
    report_id: str
    requirement_count: int
    requirements: tuple[EvidenceRequirementV1, ...]

    def __post_init__(self) -> None:
        if self.schema_id != self.SCHEMA_ID:
            raise ValueError("report schema identity mismatch")
        if self.schema_version != 1:
            raise ValueError("report schema version mismatch")
        if self.requirement_count != len(self.requirements):
            raise ValueError("requirement_count mismatch")
        if not self.requirements:
            raise ValueError("requirements must not be empty")
        validate_payload_against_schema(
            schema_id=self.SCHEMA_ID,
            payload=self.to_dict(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "report_id": self.report_id,
            "requirement_count": self.requirement_count,
            "requirements": [
                requirement.to_dict()
                for requirement in self.requirements
            ],
        }

    def to_json(self) -> str:
        return canonical_json_text(self.to_dict())

    def status_for(
        self,
        requirement_id: str,
    ) -> EvidenceRequirementStatus:
        for requirement in self.requirements:
            if requirement.requirement_id == requirement_id:
                return requirement.status
        raise KeyError(requirement_id)

    @property
    def critical_missing(self) -> tuple[str, ...]:
        return tuple(
            requirement.requirement_id
            for requirement in self.requirements
            if (
                requirement.critical
                and requirement.status
                is not EvidenceRequirementStatus.PRESENT_AND_VALIDATED
            )
        )


CRITICAL_REQUIREMENTS: tuple[str, ...] = (
    "policy_call.exact_request_bytes",
    "policy_call.rendered_prompt",
    "policy_call.raw_response_body",
    "policy_call.token_ids",
    "policy_call.finish_reason_usage_latency",
    "policy_call.predecision_state",
    "policy_call.executed_history",
    "runtime.nonexecuted_attempts",
    "environment.public_transition",
    "episode.condition_identity",
    "visibility.student_no_future_leak",
    "visibility.select_teacher_block",
    "sequence.budget_continuity",
    "sequence.observation_menu_chain",
    "bundle.policy_call_trace_alignment",
)

INELIGIBLE_DISTILLATION_EVIDENCE_INCOMPLETE = (
    "INELIGIBLE_DISTILLATION_EVIDENCE_INCOMPLETE"
)

_COUNTER_NAMES = (
    "policy_attempt_count",
    "environment_step_count",
    "protocol_failure_count",
    "inadmissible_action_count",
    "consecutive_nonexecuted_attempt_count",
)

_STUDENT_PROJECTION_KEYS = {
    "public_task_goal",
    "observation",
    "admissible_commands",
    "executed_history",
    "interface_feedback",
    "prompt_text",
    "rendered_prompt_text",
}


def _fail(message: str) -> None:
    raise ValueError(
        f"{INELIGIBLE_DISTILLATION_EVIDENCE_INCOMPLETE}:"
        f"{message}"
    )


def _enum_text(value: object) -> str | None:
    if value is None:
        return None
    enum_value = getattr(value, "value", value)
    if not isinstance(enum_value, str):
        _fail("enum-like field is not text")
    return enum_value


def _before_budget(trace: object) -> dict[str, int]:
    return {
        "policy_attempt_count": getattr(
            trace,
            "policy_attempt_count_before",
        ),
        "environment_step_count": getattr(
            trace,
            "environment_step_count_before",
        ),
        "protocol_failure_count": getattr(
            trace,
            "protocol_failure_count_before",
        ),
        "inadmissible_action_count": getattr(
            trace,
            "inadmissible_action_count_before",
        ),
        "consecutive_nonexecuted_attempt_count": getattr(
            trace,
            "consecutive_nonexecuted_attempt_count_before",
        ),
    }


def _after_budget(trace: object) -> dict[str, int]:
    return {
        "policy_attempt_count": getattr(
            trace,
            "policy_attempt_count_after",
        ),
        "environment_step_count": getattr(
            trace,
            "environment_step_count_after",
        ),
        "protocol_failure_count": getattr(
            trace,
            "protocol_failure_count",
        ),
        "inadmissible_action_count": getattr(
            trace,
            "inadmissible_action_count",
        ),
        "consecutive_nonexecuted_attempt_count": getattr(
            trace,
            "consecutive_nonexecuted_attempt_count",
        ),
    }


def _episode_final_budget(episode: object) -> dict[str, int]:
    budget = getattr(episode, "final_budget", None)
    if budget is None:
        _fail("episode final_budget missing")
    return {
        name: getattr(budget, name)
        for name in _COUNTER_NAMES
    }


def _report(
    *,
    status: EvidenceRequirementStatus,
    source_reference: str | None,
    justification: str,
    report_id: str,
) -> EvidenceCompletenessReportV1:
    rows = tuple(
        EvidenceRequirementV1(
            requirement_id=requirement_id,
            status=status,
            critical=True,
            source_reference=source_reference,
            justification=justification,
        )
        for requirement_id in CRITICAL_REQUIREMENTS
    )
    return EvidenceCompletenessReportV1(
        schema_id=EvidenceCompletenessReportV1.SCHEMA_ID,
        schema_version=1,
        report_id=report_id,
        requirement_count=len(rows),
        requirements=rows,
    )


def audit_current_evidence_contract(
) -> EvidenceCompletenessReportV1:
    """Return a code-level inventory that cannot self-certify an episode."""

    return _report(
        status=(
            EvidenceRequirementStatus.PRESENT_BUT_UNVALIDATED
        ),
        source_reference="P1-B2 code contract",
        justification=(
            "implementation exists but no concrete episode bundle "
            "was supplied to the validator"
        ),
        report_id="P1_B_EVIDENCE_CODE_INVENTORY_V1",
    )


def require_no_critical_missing(
    report: EvidenceCompletenessReportV1,
) -> None:
    if not isinstance(report, EvidenceCompletenessReportV1):
        raise TypeError(
            "report must be EvidenceCompletenessReportV1"
        )
    if report.critical_missing:
        raise ValueError(
            f"{INELIGIBLE_DISTILLATION_EVIDENCE_INCOMPLETE}:"
            + ",".join(report.critical_missing)
        )


def validate_distillation_evidence_complete(
    *,
    episode: object,
    policy_calls: Sequence[object],
    action_traces: Sequence[object],
    public_transitions: Sequence[object],
) -> None:
    calls = tuple(policy_calls)
    traces = tuple(action_traces)
    transitions = tuple(public_transitions)

    if not calls:
        _fail("policy calls missing")
    if len(calls) != len(traces):
        _fail("policy call/trace count mismatch")
    if getattr(episode, "trace_count", None) != len(traces):
        _fail("episode trace_count mismatch")
    if (
        getattr(episode, "public_transition_count", None)
        != len(transitions)
    ):
        _fail("episode public_transition_count mismatch")

    if getattr(episode, "access_class", None) != "DEV_VISIBLE":
        _fail("access_class")
    if (
        getattr(episode, "policy_condition_id", None)
        != "P4-R0-PI0"
    ):
        _fail("policy_condition_id")

    identity_names = (
        "task_access_manifest_sha256",
        "policy_condition_manifest_sha256",
        "condition_run_schedule_sha256",
        "condition_cell_id",
    )
    for name in identity_names:
        value = getattr(episode, name, None)
        if not isinstance(value, str) or not value:
            _fail(f"episode {name} missing")

    if (
        getattr(episode, "condition_cell_id", None)
        != getattr(episode, "scheduled_cell_id", None)
    ):
        _fail("episode condition_cell_id mismatch")
    if (
        getattr(episode, "task_access_manifest_sha256", None)
        != getattr(episode, "split_access_sha256", None)
    ):
        _fail("episode task-access hash alias mismatch")

    call_indices = tuple(
        getattr(call, "model_call_index", None)
        for call in calls
    )
    trace_indices = tuple(
        getattr(trace, "model_call_index", None)
        for trace in traces
    )
    expected_indices = tuple(range(len(calls)))
    if call_indices != expected_indices:
        _fail("policy call index continuity")
    if trace_indices != expected_indices:
        _fail("trace index continuity")

    transition_indices = tuple(
        getattr(item, "environment_step_index", None)
        for item in transitions
    )
    if transition_indices != tuple(sorted(transition_indices)):
        _fail("public transition order")
    if len(transition_indices) != len(set(transition_indices)):
        _fail("duplicate public transition index")
    transition_by_index = {
        getattr(item, "environment_step_index"): item
        for item in transitions
    }
    consumed_transition_indices: set[int] = set()

    expected_history: list[tuple[str, str]] = []
    expected_observation = getattr(calls[0], "observation", None)
    expected_menu = tuple(
        getattr(calls[0], "admissible_commands", ())
    )
    expected_feedback: str | None = None
    previous_after: dict[str, int] | None = None
    environment_call_count = 0

    validate_visibility_matrix(build_visibility_matrix())

    for call, trace in zip(calls, traces, strict=True):
        if getattr(call, "observation", None) != expected_observation:
            _fail("observation chain mismatch")
        if tuple(
            getattr(call, "admissible_commands", ())
        ) != expected_menu:
            _fail("menu chain mismatch")
        if (
            getattr(call, "interface_feedback_before", None)
            != expected_feedback
        ):
            _fail("interface feedback chain mismatch")

        if getattr(call, "prompt_text", None) != getattr(
            trace,
            "prompt_text",
            None,
        ):
            _fail("policy call prompt differs from ActionTrace")
        if getattr(call, "public_task_goal", None) != getattr(
            trace,
            "public_task_goal",
            None,
        ):
            _fail("policy call task goal differs from ActionTrace")
        if getattr(call, "observation", None) != getattr(
            trace,
            "observation",
            None,
        ):
            _fail("policy call observation differs from ActionTrace")
        if tuple(
            getattr(call, "admissible_commands", ())
        ) != tuple(
            getattr(trace, "admissible_commands", ())
        ):
            _fail("policy call menu differs from ActionTrace")
        if getattr(call, "raw_response_text", None) != getattr(
            trace,
            "raw_model_response",
            None,
        ):
            _fail("policy call raw response differs from ActionTrace")

        provenance = getattr(trace, "provenance", None)
        if provenance is None:
            _fail("TraceProvenance missing")
        if getattr(
            call,
            "provider_request_id",
            None,
        ) != getattr(
            provenance,
            "provider_request_id",
            None,
        ):
            _fail(
                "policy call provider request ID differs "
                "from TraceProvenance"
            )

        call_budget = dict(
            getattr(call, "budget_before", ())
        )
        trace_before = _before_budget(trace)
        if call_budget != trace_before:
            _fail(
                "policy call budget_before differs "
                "from ActionTrace counters"
            )
        if (
            getattr(call, "environment_step_count_before", None)
            != trace_before["environment_step_count"]
        ):
            _fail("policy call environment step count mismatch")

        if previous_after is not None:
            if trace_before != previous_after:
                _fail("budget continuity")
        trace_after = _after_budget(trace)
        previous_after = trace_after

        # PolicyCallEvidence keeps the complete accumulated
        # executed history for audit/provenance. MEMORY_M0_V1
        # truncation occurs only at the policy-visible boundary.
        if tuple(
            getattr(call, "executed_history", ())
        ) != tuple(expected_history):
            _fail("executed history mismatch")

        for name in (
            "task_access_manifest_sha256",
            "policy_condition_manifest_sha256",
            "condition_run_schedule_sha256",
            "access_class",
            "policy_condition_id",
            "condition_cell_id",
        ):
            if getattr(provenance, name, None) != getattr(
                episode,
                name,
                None,
            ):
                _fail(
                    "condition identity differs across "
                    "episode and trace"
                )

        projection = build_student_decision_projection(call)
        if set(projection) != _STUDENT_PROJECTION_KEYS:
            _fail("student projection field set mismatch")
        forbidden_projection_keys = {
            "success",
            "termination_reason",
            "final_done",
            "final_won",
            "teacher_rationale",
            "q2_result",
            "next_observation",
            "future_menu",
        }
        if forbidden_projection_keys.intersection(projection):
            _fail("student projection contains future information")

        status = _enum_text(
            getattr(trace, "execution_status", None)
        )
        if status == "executed":
            environment_call_count += 1
            step_index = getattr(
                trace,
                "environment_step_index",
                None,
            )
            if step_index not in transition_by_index:
                _fail("missing transition for executed action")
            transition = transition_by_index[step_index]
            consumed_transition_indices.add(step_index)

            if getattr(
                trace,
                "submitted_environment_action",
                None,
            ) != getattr(
                transition,
                "submitted_action",
                None,
            ):
                _fail(
                    "ActionTrace action differs "
                    "from PublicTransition"
                )
            if getattr(
                trace,
                "resulting_observation",
                None,
            ) != getattr(
                transition,
                "resulting_observation",
                None,
            ):
                _fail(
                    "ActionTrace result differs "
                    "from PublicTransition"
                )
            if getattr(
                call,
                "observation",
                None,
            ) != getattr(
                transition,
                "pre_action_observation",
                None,
            ):
                _fail("transition pre-observation mismatch")
            if tuple(
                getattr(call, "admissible_commands", ())
            ) != tuple(
                getattr(
                    transition,
                    "pre_action_admissible_commands",
                    (),
                )
            ):
                _fail("transition pre-menu mismatch")

            submitted_action = getattr(
                transition,
                "submitted_action",
            )
            resulting_observation = getattr(
                transition,
                "resulting_observation",
            )
            expected_history.append(
                (
                    submitted_action,
                    resulting_observation,
                )
            )
            expected_observation = resulting_observation
            expected_menu = tuple(
                getattr(
                    transition,
                    "resulting_admissible_commands",
                    (),
                )
            )
            expected_feedback = None

        elif status == "not_executed":
            expected_feedback = _enum_text(
                getattr(trace, "feedback_code", None)
            )

        elif status == "environment_error":
            _fail(
                "environment-error episode is not eligible "
                "for distillation"
            )

        else:
            _fail("unknown execution status")

    if consumed_transition_indices != set(transition_by_index):
        _fail("orphan public transition")

    if (
        getattr(
            episode,
            "environment_call_trace_count",
            None,
        )
        != environment_call_count
    ):
        _fail("episode environment call count mismatch")

    if previous_after is None:
        _fail("final budget unavailable")
    if _episode_final_budget(episode) != previous_after:
        _fail("episode final budget mismatch")


def build_evidence_completeness_report(
    *,
    episode: object,
    policy_calls: Sequence[object],
    action_traces: Sequence[object],
    public_transitions: Sequence[object],
) -> EvidenceCompletenessReportV1:
    validate_distillation_evidence_complete(
        episode=episode,
        policy_calls=policy_calls,
        action_traces=action_traces,
        public_transitions=public_transitions,
    )
    return _report(
        status=EvidenceRequirementStatus.PRESENT_AND_VALIDATED,
        source_reference="validated P1 episode evidence",
        justification=(
            "validated against the complete cross-file "
            "episode evidence gate"
        ),
        report_id="P1_B_VALIDATED_EPISODE_EVIDENCE_V1",
    )

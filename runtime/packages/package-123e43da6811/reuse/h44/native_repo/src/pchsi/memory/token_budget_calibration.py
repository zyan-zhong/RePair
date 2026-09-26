"""Calibration-only representation builders for Failure Memory token budgets.

This module creates no active Memory authority. Analyzer outputs remain
CALIBRATION_ONLY_ANALYZER_PROPOSAL.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.matched_raw_view import (
    FM1PolicyVisiblePayloadV1,
    FM1VisibleEventV1,
    FM1VisibleRelevantStartV1,
)
from pchsi.memory.policy_projection import (
    FailureMemoryPolicyVisiblePayloadV1,
    PolicyVisibleFailurePatternItemV1,
)
from pchsi.memory.policy_view_safety import (
    audit_policy_visible_payload_v1,
)
from pchsi.memory.projection_common import (
    ProjectionClassV1,
)


ANALYZER_RESULT_SCHEMA_V1 = (
    "FAILURE_MEMORY_TOKEN_BUDGET_ANALYZER_RESULT_V1"
)
ANALYZER_AUTHORITY = "CALIBRATION_ONLY_ANALYZER_PROPOSAL"


@dataclass(frozen=True, slots=True)
class TokenBudgetAnalyzerResultV1:
    schema_id: str
    schema_version: int
    failure_id: str
    status: str
    relevant_start_model_call_index: int | None
    failure_onset_model_call_index: int | None
    final_model_call_index: int | None
    activation_cues: tuple[str, ...]
    failure_pattern: str
    release_cues: tuple[str, ...]
    non_applicability_cues: tuple[str, ...]
    authority: str
    request_id: str | None
    response_model: str
    response_sha256: str

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "schema_version",
            "failure_id",
            "status",
            "relevant_start_model_call_index",
            "failure_onset_model_call_index",
            "final_model_call_index",
            "activation_cues",
            "failure_pattern",
            "release_cues",
            "non_applicability_cues",
            "authority",
            "request_id",
            "response_model",
            "response_sha256",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != ANALYZER_RESULT_SCHEMA_V1:
            raise ValueError("analyzer result schema mismatch")
        if self.schema_version != 1:
            raise ValueError("analyzer result version mismatch")
        if not isinstance(self.failure_id, str) or not self.failure_id:
            raise ValueError("failure_id must be nonempty str")
        if self.status not in {"ANALYZED", "ABSTAIN"}:
            raise ValueError("status must be ANALYZED or ABSTAIN")
        if self.authority != ANALYZER_AUTHORITY:
            raise ValueError("calibration analyzer authority mismatch")
        if (
            not isinstance(self.response_model, str)
            or not self.response_model
        ):
            raise ValueError("response_model must be nonempty str")
        if (
            not isinstance(self.response_sha256, str)
            or len(self.response_sha256) != 64
            or any(
                ch not in "0123456789abcdef"
                for ch in self.response_sha256
            )
        ):
            raise ValueError("response_sha256 invalid")
        if self.request_id is not None and (
            not isinstance(self.request_id, str)
            or not self.request_id
        ):
            raise ValueError("request_id must be nonempty str or None")

        if self.status == "ABSTAIN":
            if any(
                value is not None
                for value in (
                    self.relevant_start_model_call_index,
                    self.failure_onset_model_call_index,
                    self.final_model_call_index,
                )
            ):
                raise ValueError("ABSTAIN must null all indices")
            if any(
                (
                    self.activation_cues,
                    self.failure_pattern,
                    self.release_cues,
                    self.non_applicability_cues,
                )
            ):
                raise ValueError("ABSTAIN must not carry semantic fields")
            return

        values = (
            self.relevant_start_model_call_index,
            self.failure_onset_model_call_index,
            self.final_model_call_index,
        )
        if any(type(value) is not int or value < 0 for value in values):
            raise ValueError("ANALYZED indices must be nonnegative ints")
        start, onset, final = values
        if not start <= onset <= final:
            raise ValueError("analyzer indices must satisfy start<=onset<=final")

        for name in (
            "activation_cues",
            "release_cues",
            "non_applicability_cues",
        ):
            value = getattr(self, name)
            if type(value) is not tuple:
                raise TypeError(f"{name} must be tuple")
            if any(not isinstance(item, str) or not item for item in value):
                raise ValueError(f"{name} entries must be nonempty str")

        if not isinstance(self.failure_pattern, str) or not self.failure_pattern:
            raise ValueError("ANALYZED result requires failure_pattern")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "failure_id": self.failure_id,
            "status": self.status,
            "relevant_start_model_call_index": (
                self.relevant_start_model_call_index
            ),
            "failure_onset_model_call_index": (
                self.failure_onset_model_call_index
            ),
            "final_model_call_index": self.final_model_call_index,
            "activation_cues": list(self.activation_cues),
            "failure_pattern": self.failure_pattern,
            "release_cues": list(self.release_cues),
            "non_applicability_cues": list(
                self.non_applicability_cues
            ),
            "authority": self.authority,
            "request_id": self.request_id,
            "response_model": self.response_model,
            "response_sha256": self.response_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> "TokenBudgetAnalyzerResultV1":
        if not isinstance(value, dict):
            raise TypeError("analyzer result must be object")
        if frozenset(value) != cls._KEYS:
            raise ValueError("analyzer result fields mismatch")
        return cls(
            schema_id=value["schema_id"],
            schema_version=value["schema_version"],
            failure_id=value["failure_id"],
            status=value["status"],
            relevant_start_model_call_index=value[
                "relevant_start_model_call_index"
            ],
            failure_onset_model_call_index=value[
                "failure_onset_model_call_index"
            ],
            final_model_call_index=value["final_model_call_index"],
            activation_cues=tuple(value["activation_cues"]),
            failure_pattern=value["failure_pattern"],
            release_cues=tuple(value["release_cues"]),
            non_applicability_cues=tuple(
                value["non_applicability_cues"]
            ),
            authority=value["authority"],
            request_id=value["request_id"],
            response_model=value["response_model"],
            response_sha256=value["response_sha256"],
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "TokenBudgetAnalyzerResultV1":
        return cls.from_dict(strict_json_loads(value))


def _calibration_visible_state_change_disposition_v1(
    *,
    trace,
    transition,
) -> str:
    """Derive visible state change from immutable trace/transition facts.

    This mirrors the frozen SequenceFailureExperience factual
    reconstruction rule. It creates no semantic Analyzer authority.
    """

    status = trace.execution_status.value

    if status == "not_executed":
        if transition is not None:
            raise ValueError(
                "nonexecuted trace must not bind a public transition"
            )
        return "NONEXECUTED"

    if status == "environment_error":
        if transition is not None:
            raise ValueError(
                "environment-error trace must not bind "
                "a public transition"
            )
        return "ENVIRONMENT_ERROR"

    if status != "executed":
        raise ValueError(
            "unknown trace execution status: "
            + repr(status)
        )

    if transition is None:
        raise ValueError(
            "executed trace requires a public transition"
        )

    observation_changed = (
        transition.resulting_observation
        != transition.pre_action_observation
    )

    menu_changed = (
        transition.resulting_admissible_commands
        != transition.pre_action_admissible_commands
    )

    if observation_changed and menu_changed:
        return "OBSERVATION_AND_MENU_CHANGED"

    if observation_changed:
        return "OBSERVATION_CHANGED"

    if menu_changed:
        return "MENU_CHANGED"

    return "NO_VISIBLE_STATE_CHANGE"


def build_complete_window_fm1_payload_v1(
    *,
    source,
    analyzer_result: TokenBudgetAnalyzerResultV1,
) -> FM1PolicyVisiblePayloadV1:
    if analyzer_result.status != "ANALYZED":
        raise ValueError("cannot build FM1 calibration payload from ABSTAIN")

    start = analyzer_result.relevant_start_model_call_index
    final = analyzer_result.final_model_call_index

    policy_calls = {
        item.model_call_index: item
        for item in source.policy_calls
    }

    traces = {
        item.model_call_index: item
        for item in source.traces
    }

    transitions = {
        item.model_call_index: item
        for item in source.public_transitions
    }

    if start not in policy_calls:
        raise ValueError("relevant-start policy call missing")

    events = []
    for index in range(start, final + 1):
        call = policy_calls.get(index)
        trace = traces.get(index)
        if call is None or trace is None:
            raise ValueError(
                "complete calibration window contains missing call/trace"
            )
        transition = transitions.get(index)
        events.append(
            FM1VisibleEventV1(
                model_call_index=index,
                pre_observation=call.observation,
                literal_action=trace.literal_action,
                normalized_action=trace.normalized_action,
                submitted_environment_action=(
                    trace.submitted_environment_action
                ),
                execution_status=trace.execution_status.value,
                interface_feedback_before=(
                    call.interface_feedback_before
                ),
                resulting_observation=(
                    None
                    if transition is None
                    else transition.resulting_observation
                ),
                visible_state_change_disposition=(
                    _calibration_visible_state_change_disposition_v1(
                        trace=trace,
                        transition=transition,
                    )
                ),
            )
        )

    payload = FM1PolicyVisiblePayloadV1(
        relevant_start=FM1VisibleRelevantStartV1(
            model_call_index=start,
            pre_observation=policy_calls[start].observation,
            interface_feedback_before=(
                policy_calls[start].interface_feedback_before
            ),
        ),
        events=tuple(events),
    )

    # Exact calibration payload must contain every index in the proposed window.
    observed = tuple(
        item.model_call_index
        for item in payload.events
    )
    if observed != tuple(range(start, final + 1)):
        raise RuntimeError("FM1 calibration payload is not a complete window")

    return payload


def build_calibration_fm2_payload_v1(
    analyzer_result: TokenBudgetAnalyzerResultV1,
) -> FailureMemoryPolicyVisiblePayloadV1:
    if analyzer_result.status != "ANALYZED":
        raise ValueError("cannot build FM2 calibration payload from ABSTAIN")

    return FailureMemoryPolicyVisiblePayloadV1(
        activation_cues=analyzer_result.activation_cues,
        failure_pattern=(
            PolicyVisibleFailurePatternItemV1(
                authority="SEMANTIC_HYPOTHESIS",
                annotation_type="CANDIDATE_MECHANISM",
                text=analyzer_result.failure_pattern,
            ),
        ),
        revalidate_on=(),
        release_cues=analyzer_result.release_cues,
        non_applicability_cues=(
            analyzer_result.non_applicability_cues
        ),
        recovery_procedure=(),
    )


def calibration_payload_safety_v1(
    *,
    fm1_payload: FM1PolicyVisiblePayloadV1,
    fm2_payload: FailureMemoryPolicyVisiblePayloadV1,
):
    fm1_report = audit_policy_visible_payload_v1(
        projection_class=ProjectionClassV1.FM1,
        policy_visible_payload=fm1_payload.to_dict(),
        has_nonempty_recovery=False,
    )
    fm2_report = audit_policy_visible_payload_v1(
        projection_class=ProjectionClassV1.FM2,
        policy_visible_payload=fm2_payload.to_dict(),
        has_nonempty_recovery=False,
    )
    return fm1_report, fm2_report


def exact_token_count_v1(
    *,
    payload: object,
    tokenizer,
) -> int:
    text = canonical_json_bytes(payload).decode("utf-8")
    count = tokenizer.count_tokens(text)
    if type(count) is not int or count < 0:
        raise ValueError("tokenizer returned invalid count")
    return count


def exact_library_pack_count_v1(
    *,
    payloads: tuple[dict[str, object], ...],
    tokenizer,
) -> int:
    if len(payloads) != 3:
        raise ValueError("calibration library pack requires exactly 3 payloads")

    text = json.dumps(
        list(payloads),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    count = tokenizer.count_tokens(text)
    if type(count) is not int or count < 0:
        raise ValueError("tokenizer returned invalid count")
    return count

"""FM1 matched raw episodic Policy view for Failure Memory V1."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    strict_json_loads,
)
from pchsi.memory.procedural_builder import (
    ProceduralFailureMemoryRecordV1,
)
from pchsi.memory.projection_common import (
    PolicyTokenizerCounterV1,
    ProjectionBuildDispositionV1,
    ProjectionClassV1,
    ProjectionRecordBindingV1,
    ProjectionTokenCountV1,
    count_policy_visible_tokens_v1,
    policy_view_governance_disposition_v1,
)
from pchsi.memory.policy_view_safety import (
    PolicyViewSafetyReportV1,
    PolicyViewStaticFailureCodeV1,
    audit_policy_visible_payload_v1,
    policy_visible_contains_bound_identity_v1,
)
from pchsi.memory.sequence_failure_experience import (
    SequenceFailureEventV1,
    SequenceFailureExperienceV1,
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


def _optional_nonnegative_int(
    name: str,
    value: object,
) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be nonnegative int or None")
    return value


def _optional_sha(
    name: str,
    value: object,
) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be 64 lowercase hex or None")
    return value


@dataclass(frozen=True, slots=True)
class FM1VisibleEventV1:
    model_call_index: int
    pre_observation: str
    literal_action: str
    normalized_action: str | None
    submitted_environment_action: str | None
    execution_status: str
    interface_feedback_before: str | None
    resulting_observation: str | None
    visible_state_change_disposition: str

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "model_call_index",
            "pre_observation",
            "literal_action",
            "normalized_action",
            "submitted_environment_action",
            "execution_status",
            "interface_feedback_before",
            "resulting_observation",
            "visible_state_change_disposition",
        }
    )

    def __post_init__(self) -> None:
        if type(self.model_call_index) is not int or self.model_call_index < 0:
            raise ValueError("model_call_index must be nonnegative int")
        for name in (
            "pre_observation",
            "literal_action",
            "execution_status",
            "visible_state_change_disposition",
        ):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f"{name} must be str")
        for name in (
            "normalized_action",
            "submitted_environment_action",
            "interface_feedback_before",
            "resulting_observation",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be str or None")

    @classmethod
    def from_sequence_event_v1(
        cls,
        event: SequenceFailureEventV1,
    ) -> "FM1VisibleEventV1":
        if not isinstance(event, SequenceFailureEventV1):
            raise TypeError("event must be SequenceFailureEventV1")
        return cls(
            model_call_index=event.model_call_index,
            pre_observation=event.pre_observation,
            literal_action=event.literal_action,
            normalized_action=event.normalized_action,
            submitted_environment_action=event.submitted_environment_action,
            execution_status=event.execution_status,
            interface_feedback_before=event.interface_feedback_before,
            resulting_observation=event.resulting_observation,
            visible_state_change_disposition=(
                event.visible_state_change_disposition
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "model_call_index": self.model_call_index,
            "pre_observation": self.pre_observation,
            "literal_action": self.literal_action,
            "normalized_action": self.normalized_action,
            "submitted_environment_action": (
                self.submitted_environment_action
            ),
            "execution_status": self.execution_status,
            "interface_feedback_before": self.interface_feedback_before,
            "resulting_observation": self.resulting_observation,
            "visible_state_change_disposition": (
                self.visible_state_change_disposition
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> "FM1VisibleEventV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "FM1 visible event",
        )
        return cls(
            model_call_index=payload["model_call_index"],
            pre_observation=payload["pre_observation"],
            literal_action=payload["literal_action"],
            normalized_action=payload["normalized_action"],
            submitted_environment_action=payload[
                "submitted_environment_action"
            ],
            execution_status=payload["execution_status"],
            interface_feedback_before=payload[
                "interface_feedback_before"
            ],
            resulting_observation=payload["resulting_observation"],
            visible_state_change_disposition=payload[
                "visible_state_change_disposition"
            ],
        )


@dataclass(frozen=True, slots=True)
class FM1VisibleRelevantStartV1:
    model_call_index: int
    pre_observation: str
    interface_feedback_before: str | None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "model_call_index",
            "pre_observation",
            "interface_feedback_before",
        }
    )

    def __post_init__(self) -> None:
        if type(self.model_call_index) is not int or self.model_call_index < 0:
            raise ValueError("model_call_index must be nonnegative int")
        if not isinstance(self.pre_observation, str):
            raise TypeError("pre_observation must be str")
        if (
            self.interface_feedback_before is not None
            and not isinstance(self.interface_feedback_before, str)
        ):
            raise TypeError(
                "interface_feedback_before must be str or None"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "model_call_index": self.model_call_index,
            "pre_observation": self.pre_observation,
            "interface_feedback_before": self.interface_feedback_before,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "FM1VisibleRelevantStartV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "FM1 visible relevant start",
        )
        return cls(
            model_call_index=payload["model_call_index"],
            pre_observation=payload["pre_observation"],
            interface_feedback_before=payload[
                "interface_feedback_before"
            ],
        )


@dataclass(frozen=True, slots=True)
class FM1PolicyVisiblePayloadV1:
    relevant_start: FM1VisibleRelevantStartV1
    events: tuple[FM1VisibleEventV1, ...]

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {"relevant_start", "events"}
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.relevant_start,
            FM1VisibleRelevantStartV1,
        ):
            raise TypeError("relevant_start type mismatch")
        if type(self.events) is not tuple or not self.events:
            raise ValueError("events must be nonempty tuple")
        if any(
            not isinstance(item, FM1VisibleEventV1)
            for item in self.events
        ):
            raise TypeError("events contain invalid item")
        indices = tuple(item.model_call_index for item in self.events)
        if indices != tuple(sorted(indices)) or len(indices) != len(
            set(indices)
        ):
            raise ValueError("FM1 events must be unique chronological calls")

    def to_dict(self) -> dict[str, object]:
        return {
            "relevant_start": self.relevant_start.to_dict(),
            "events": [item.to_dict() for item in self.events],
        }

    @classmethod
    def from_dict(cls, value: object) -> "FM1PolicyVisiblePayloadV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "FM1 Policy-visible payload",
        )
        raw_events = payload["events"]
        if not isinstance(raw_events, list):
            raise TypeError("events must be JSON array")
        return cls(
            relevant_start=FM1VisibleRelevantStartV1.from_dict(
                payload["relevant_start"]
            ),
            events=tuple(
                FM1VisibleEventV1.from_dict(item)
                for item in raw_events
            ),
        )


@dataclass(frozen=True, slots=True)
class FM1MatchedRawEpisodicViewV1:
    schema_id: str
    schema_version: int
    record_binding: ProjectionRecordBindingV1
    source_experience_id: str | None
    source_experience_canonical_sha256: str | None
    relevant_start_model_call_index: int | None
    failure_onset_model_call_index: int | None
    final_model_call_index: int | None
    policy_visible_payload: FM1PolicyVisiblePayloadV1 | None
    policy_visible_payload_sha256: str | None
    token_count: ProjectionTokenCountV1 | None
    build_disposition: ProjectionBuildDispositionV1
    safety_report: PolicyViewSafetyReportV1 | None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "schema_version",
            "record_binding",
            "source_experience_id",
            "source_experience_canonical_sha256",
            "relevant_start_model_call_index",
            "failure_onset_model_call_index",
            "final_model_call_index",
            "policy_visible_payload",
            "policy_visible_payload_sha256",
            "token_count",
            "build_disposition",
            "safety_report",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != "FM1_MATCHED_RAW_EPISODIC_VIEW_V1":
            raise ValueError("schema_id mismatch")
        if self.schema_version != 1:
            raise ValueError("schema_version mismatch")
        if not isinstance(
            self.record_binding,
            ProjectionRecordBindingV1,
        ):
            raise TypeError("record_binding type mismatch")
        _optional_sha("source_experience_id", self.source_experience_id)
        _optional_sha(
            "source_experience_canonical_sha256",
            self.source_experience_canonical_sha256,
        )
        _optional_nonnegative_int(
            "relevant_start_model_call_index",
            self.relevant_start_model_call_index,
        )
        _optional_nonnegative_int(
            "failure_onset_model_call_index",
            self.failure_onset_model_call_index,
        )
        _optional_nonnegative_int(
            "final_model_call_index",
            self.final_model_call_index,
        )
        if not isinstance(
            self.build_disposition,
            ProjectionBuildDispositionV1,
        ):
            raise TypeError("build_disposition type mismatch")

        if self.policy_visible_payload is not None and not isinstance(
            self.policy_visible_payload,
            FM1PolicyVisiblePayloadV1,
        ):
            raise TypeError("policy_visible_payload type mismatch")
        _optional_sha(
            "policy_visible_payload_sha256",
            self.policy_visible_payload_sha256,
        )
        if self.token_count is not None and not isinstance(
            self.token_count,
            ProjectionTokenCountV1,
        ):
            raise TypeError("token_count type mismatch")
        if self.safety_report is not None and not isinstance(
            self.safety_report,
            PolicyViewSafetyReportV1,
        ):
            raise TypeError("safety_report type mismatch")

        source_fields = (
            self.source_experience_id,
            self.source_experience_canonical_sha256,
            self.relevant_start_model_call_index,
            self.failure_onset_model_call_index,
            self.final_model_call_index,
        )
        ambiguous = (
            self.build_disposition
            is ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_FM1_SOURCE_AMBIGUOUS
        )
        if ambiguous:
            if any(value is not None for value in source_fields):
                raise ValueError(
                    "ambiguous FM1 must null all source-specific fields"
                )
        elif any(value is None for value in source_fields):
            raise ValueError(
                "unique-source FM1 requires all source-specific fields"
            )

        if self.safety_report is not None:
            if (
                self.safety_report.projection_class
                is not ProjectionClassV1.FM1
            ):
                raise ValueError(
                    "FM1 safety_report projection_class must be FM1"
                )

        governance_ineligible = {
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_SOURCE_INTEGRITY,
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_DESCRIPTIVE_ELIGIBILITY,
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_ACCESS_SCOPE,
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_EVALUATION_CONTAMINATION,
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_LIFECYCLE,
        }

        if (
            self.build_disposition in governance_ineligible
            or ambiguous
        ):
            if any(
                value is not None
                for value in (
                    self.policy_visible_payload,
                    self.policy_visible_payload_sha256,
                    self.token_count,
                    self.safety_report,
                )
            ):
                raise ValueError(
                    "governance/ambiguous FM1 must not carry projection evidence"
                )
            return

        if (
            self.build_disposition
            is ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_POLICY_VIEW_SAFETY
        ):
            if (
                self.policy_visible_payload is not None
                or self.policy_visible_payload_sha256 is not None
                or self.token_count is not None
            ):
                raise ValueError(
                    "safety-ineligible FM1 must not carry payload/hash/token"
                )
            if (
                self.safety_report is None
                or self.safety_report.static_status != "FAIL"
                or not self.safety_report.critical_safety_failure
                or not self.safety_report.static_failure_codes
            ):
                raise ValueError(
                    "safety-ineligible FM1 requires critical FAIL report"
                )
            return

        if (
            self.build_disposition
            is ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_TOKEN_BUDGET
        ):
            if (
                self.policy_visible_payload is not None
                or self.policy_visible_payload_sha256 is not None
            ):
                raise ValueError(
                    "token-ineligible FM1 must not carry payload/hash"
                )
            if self.token_count is None:
                raise ValueError(
                    "token-ineligible FM1 requires measured token count"
                )
            if (
                self.token_count.policy_visible_token_count
                <= self.token_count.hard_ceiling
            ):
                raise ValueError(
                    "token-ineligible FM1 requires count above ceiling"
                )
            if (
                self.safety_report is None
                or self.safety_report.static_status != "PASS"
                or self.safety_report.critical_safety_failure
                or self.safety_report.static_failure_codes
            ):
                raise ValueError(
                    "token-ineligible FM1 requires clean PASS safety report"
                )
            return

        if self.build_disposition is not ProjectionBuildDispositionV1.ELIGIBLE:
            raise ValueError("unsupported FM1 build disposition")

        if self.policy_visible_payload is None:
            raise ValueError("eligible FM1 requires Policy payload")
        if self.policy_visible_payload_sha256 is None:
            raise ValueError("eligible FM1 requires payload SHA")
        if self.token_count is None:
            raise ValueError("eligible FM1 requires token count")
        if (
            self.token_count.policy_visible_token_count
            > self.token_count.hard_ceiling
        ):
            raise ValueError("eligible FM1 exceeds token ceiling")
        if (
            self.safety_report is None
            or self.safety_report.static_status != "PASS"
            or self.safety_report.critical_safety_failure
            or self.safety_report.static_failure_codes
        ):
            raise ValueError(
                "eligible FM1 requires clean PASS safety report"
            )

        recomputed_report = audit_policy_visible_payload_v1(
            projection_class=ProjectionClassV1.FM1,
            policy_visible_payload=(
                self.policy_visible_payload.to_dict()
            ),
            has_nonempty_recovery=False,
        )
        if (
            self.policy_visible_payload_sha256
            != recomputed_report.projection_sha256
        ):
            raise ValueError(
                "FM1 policy-visible payload SHA mismatch"
            )
        if (
            self.safety_report.projection_sha256
            != recomputed_report.projection_sha256
        ):
            raise ValueError(
                "FM1 safety report SHA mismatch"
            )
        if self.safety_report != recomputed_report:
            raise ValueError(
                "FM1 deterministic safety report mismatch"
            )

        if (
            self.relevant_start_model_call_index
            != self.policy_visible_payload.relevant_start.model_call_index
        ):
            raise ValueError("FM1 relevant-start outer/payload mismatch")

        event_indices = tuple(
            item.model_call_index
            for item in self.policy_visible_payload.events
        )
        for label, anchor in (
            ("failure onset", self.failure_onset_model_call_index),
            ("final", self.final_model_call_index),
        ):
            if anchor not in event_indices:
                raise ValueError(
                    f"FM1 {label} anchor missing from Policy-visible events"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "record_binding": self.record_binding.to_dict(),
            "source_experience_id": self.source_experience_id,
            "source_experience_canonical_sha256": (
                self.source_experience_canonical_sha256
            ),
            "relevant_start_model_call_index": (
                self.relevant_start_model_call_index
            ),
            "failure_onset_model_call_index": (
                self.failure_onset_model_call_index
            ),
            "final_model_call_index": self.final_model_call_index,
            "policy_visible_payload": (
                None
                if self.policy_visible_payload is None
                else self.policy_visible_payload.to_dict()
            ),
            "policy_visible_payload_sha256": (
                self.policy_visible_payload_sha256
            ),
            "token_count": (
                None
                if self.token_count is None
                else self.token_count.to_dict()
            ),
            "build_disposition": self.build_disposition.value,
            "safety_report": (
                None
                if self.safety_report is None
                else self.safety_report.to_dict()
            ),
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "FM1MatchedRawEpisodicViewV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "FM1 matched raw episodic view",
        )
        visible = payload["policy_visible_payload"]
        token = payload["token_count"]
        report = payload["safety_report"]
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            record_binding=ProjectionRecordBindingV1.from_dict(
                payload["record_binding"]
            ),
            source_experience_id=payload["source_experience_id"],
            source_experience_canonical_sha256=payload[
                "source_experience_canonical_sha256"
            ],
            relevant_start_model_call_index=payload[
                "relevant_start_model_call_index"
            ],
            failure_onset_model_call_index=payload[
                "failure_onset_model_call_index"
            ],
            final_model_call_index=payload["final_model_call_index"],
            policy_visible_payload=(
                None
                if visible is None
                else FM1PolicyVisiblePayloadV1.from_dict(visible)
            ),
            policy_visible_payload_sha256=payload[
                "policy_visible_payload_sha256"
            ],
            token_count=(
                None
                if token is None
                else ProjectionTokenCountV1.from_dict(token)
            ),
            build_disposition=ProjectionBuildDispositionV1(
                payload["build_disposition"]
            ),
            safety_report=(
                None
                if report is None
                else PolicyViewSafetyReportV1.from_dict(report)
            ),
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "FM1MatchedRawEpisodicViewV1":
        return cls.from_dict(strict_json_loads(value))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


def _append_exact_identity_v1(
    values: list[str],
    value: object,
) -> None:
    if isinstance(value, str) and value and value not in values:
        values.append(value)


def _append_evidence_ref_identities_v1(
    values: list[str],
    ref,
) -> None:
    _append_exact_identity_v1(values, ref.source_id)
    _append_exact_identity_v1(values, ref.source_sha256)


def _append_source_pointer_identities_v1(
    values: list[str],
    pointer,
) -> None:
    if pointer is None:
        return
    _append_exact_identity_v1(values, pointer.bundle_member_name)
    _append_exact_identity_v1(values, pointer.exact_record_sha256)
    _append_exact_identity_v1(values, pointer.whole_member_sha256)


def _unit2_forbidden_exact_identities_v1(
    experience: SequenceFailureExperienceV1,
) -> tuple[str, ...]:
    values: list[str] = []

    for value in (
        experience.experience_id,
        experience.source_round,
        experience.source_condition,
        experience.source_task_id,
        experience.source_gamefile_group_id,
        experience.source_bundle_sha256,
        experience.source_attempt_id,
    ):
        _append_exact_identity_v1(values, value)

    access = experience.task_access_binding
    for value in (
        access.task_access_protected_manifest_sha256,
        access.task_access_record_sha256,
        access.task_gamefile_group_id,
        access.dataset_relative_gamefile,
        access.gamefile_sha256,
    ):
        _append_exact_identity_v1(values, value)

    registration = experience.registration_binding
    for value in (
        registration.registration_id,
        registration.registration_protocol_id,
        registration.registration_artifact_sha256,
        registration.registration_record_sha256,
        registration.source_bundle_sha256,
        registration.source_attempt_id,
        registration.source_task_id,
        registration.source_round,
        registration.source_condition,
    ):
        _append_exact_identity_v1(values, value)

    for member_name, member_sha in experience.source_bundle_member_sha256:
        _append_exact_identity_v1(values, member_name)
        _append_exact_identity_v1(values, member_sha)

    start = experience.relevant_start
    for value in (
        start.public_task_goal_sha256,
        start.observation_sha256,
        start.admissible_commands_sha256,
    ):
        _append_exact_identity_v1(values, value)
    for pointer in start.required_preceding_prefix_source_binding:
        _append_source_pointer_identities_v1(values, pointer)

    for event in experience.observed_sequence:
        for value in (
            event.pre_observation_sha256,
            event.pre_admissible_commands_sha256,
            event.raw_model_response_sha256,
            event.resulting_observation_sha256,
            event.resulting_admissible_commands_sha256,
        ):
            _append_exact_identity_v1(values, value)
        _append_source_pointer_identities_v1(
            values,
            event.trace_source_pointer,
        )
        _append_source_pointer_identities_v1(
            values,
            event.policy_call_source_pointer,
        )
        _append_source_pointer_identities_v1(
            values,
            event.public_transition_source_pointer,
        )

    return tuple(values)


def _unit3_forbidden_exact_identities_v1(
    record: ProceduralFailureMemoryRecordV1,
) -> tuple[str, ...]:
    values: list[str] = []

    for value in (
        record.memory_lineage_id,
        record.record_id,
        record.record_content_sha256,
        record.canonical_record_sha256,
        record.provenance.creation_event_id,
    ):
        _append_exact_identity_v1(values, value)

    previous = record.previous_record_binding
    if previous is not None:
        _append_exact_identity_v1(
            values,
            previous.memory_lineage_id,
        )
        _append_exact_identity_v1(
            values,
            previous.canonical_record_sha256,
        )

    for binding in record.provenance.factual_sequence_bindings:
        for value in (
            binding.experience_id,
            binding.canonical_experience_sha256,
            binding.source_bundle_sha256,
            binding.source_attempt_id,
            binding.source_task_id,
        ):
            _append_exact_identity_v1(values, value)

    assembly = record.provenance.assembly_registration_binding
    for value in (
        assembly.registration_id,
        assembly.assembly_registration_sha256,
    ):
        _append_exact_identity_v1(values, value)
    _append_evidence_ref_identities_v1(
        values,
        assembly.lineage_registration_ref,
    )

    for field_name in (
        "activation",
        "continuation",
        "revalidation",
        "release",
        "termination",
        "non_applicability",
        "policy_visible_state_change_trigger",
    ):
        for clause in getattr(record.applicability, field_name):
            _append_exact_identity_v1(
                values,
                clause.registration_id,
            )
            _append_evidence_ref_identities_v1(
                values,
                clause.origin_artifact_ref,
            )
            for ref in clause.source_refs:
                _append_evidence_ref_identities_v1(values, ref)

    for annotation in record.semantic_hypotheses:
        _append_exact_identity_v1(values, annotation.annotation_id)
        _append_exact_identity_v1(values, annotation.origin_identity)
        _append_evidence_ref_identities_v1(
            values,
            annotation.origin_artifact_ref,
        )
        for ref in annotation.supporting_refs:
            _append_evidence_ref_identities_v1(values, ref)
        for ref in annotation.counterevidence_refs:
            _append_evidence_ref_identities_v1(values, ref)

    for proposal in record.proposed_recoveries:
        _append_exact_identity_v1(values, proposal.proposal_id)
        _append_exact_identity_v1(values, proposal.origin_identity)
        _append_evidence_ref_identities_v1(
            values,
            proposal.origin_artifact_ref,
        )
        for ref in proposal.source_refs:
            _append_evidence_ref_identities_v1(values, ref)

    for observed in record.observed_recovery_bindings:
        _append_exact_identity_v1(
            values,
            observed.source_experience_id,
        )
        for ref in observed.source_refs:
            _append_evidence_ref_identities_v1(values, ref)

    for relation in record.relations:
        _append_exact_identity_v1(values, relation.relation_id)
        _append_exact_identity_v1(
            values,
            relation.source_memory_lineage_id,
        )
        _append_exact_identity_v1(
            values,
            relation.target.target_id,
        )
        _append_exact_identity_v1(
            values,
            relation.target.target_canonical_record_sha256,
        )
        for ref in relation.source_refs:
            _append_evidence_ref_identities_v1(values, ref)

    for value in record.governance_state.paired_effect_observation_ids:
        _append_exact_identity_v1(values, value)
    for value in record.governance_state.known_harm_ids:
        _append_exact_identity_v1(values, value)

    return tuple(values)


def _fm1_forbidden_exact_identities_v1(
    *,
    record: ProceduralFailureMemoryRecordV1,
    experience: SequenceFailureExperienceV1,
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            (
                *_unit2_forbidden_exact_identities_v1(experience),
                *_unit3_forbidden_exact_identities_v1(record),
            )
        )
    )


def _bound_identity_augmented_report_v1(
    *,
    report: PolicyViewSafetyReportV1,
) -> PolicyViewSafetyReportV1:
    codes = set(report.static_failure_codes)
    codes.add(
        PolicyViewStaticFailureCodeV1.SOURCE_IDENTITY_EXPOSURE
    )
    ordered = tuple(
        code
        for code in PolicyViewStaticFailureCodeV1
        if code in codes
    )
    return PolicyViewSafetyReportV1(
        schema_id=report.schema_id,
        schema_version=report.schema_version,
        projection_class=report.projection_class,
        projection_sha256=report.projection_sha256,
        static_status="FAIL",
        static_failure_codes=ordered,
        contextual_menu_check_required=(
            report.contextual_menu_check_required
        ),
        critical_safety_failure=True,
    )


def _binding(
    record: ProceduralFailureMemoryRecordV1,
) -> ProjectionRecordBindingV1:
    if record.canonical_record_sha256 is None:
        raise ValueError("record lacks canonical_record_sha256")
    return ProjectionRecordBindingV1(
        memory_lineage_id=record.memory_lineage_id,
        record_version=record.record_version,
        canonical_record_sha256=record.canonical_record_sha256,
    )


def _ineligible_without_source(
    *,
    record: ProceduralFailureMemoryRecordV1,
    disposition: ProjectionBuildDispositionV1,
) -> FM1MatchedRawEpisodicViewV1:
    return FM1MatchedRawEpisodicViewV1(
        schema_id="FM1_MATCHED_RAW_EPISODIC_VIEW_V1",
        schema_version=1,
        record_binding=_binding(record),
        source_experience_id=None,
        source_experience_canonical_sha256=None,
        relevant_start_model_call_index=None,
        failure_onset_model_call_index=None,
        final_model_call_index=None,
        policy_visible_payload=None,
        policy_visible_payload_sha256=None,
        token_count=None,
        build_disposition=disposition,
        safety_report=None,
    )


def _visible_payload(
    experience: SequenceFailureExperienceV1,
    events: tuple[FM1VisibleEventV1, ...],
) -> FM1PolicyVisiblePayloadV1:
    return FM1PolicyVisiblePayloadV1(
        relevant_start=FM1VisibleRelevantStartV1(
            model_call_index=experience.relevant_start.model_call_index,
            pre_observation=experience.relevant_start.observation,
            interface_feedback_before=(
                experience.relevant_start.interface_feedback_before
            ),
        ),
        events=events,
    )


def build_fm1_matched_raw_episodic_view_v1(
    *,
    record: ProceduralFailureMemoryRecordV1,
    experience: SequenceFailureExperienceV1,
    tokenizer: PolicyTokenizerCounterV1,
    hard_ceiling: int = 256,
) -> FM1MatchedRawEpisodicViewV1:
    if not isinstance(record, ProceduralFailureMemoryRecordV1):
        raise TypeError("record type mismatch")
    if not isinstance(experience, SequenceFailureExperienceV1):
        raise TypeError("experience type mismatch")

    source_bindings = record.provenance.factual_sequence_bindings
    if len(source_bindings) != 1:
        return _ineligible_without_source(
            record=record,
            disposition=(
                ProjectionBuildDispositionV1
                .PROJECTION_INELIGIBLE_FM1_SOURCE_AMBIGUOUS
            ),
        )

    sole = source_bindings[0]
    sole.validate_against(experience)
    source_sha = hashlib.sha256(
        experience.canonical_bytes()
    ).hexdigest()

    relevant_index = (
        experience.registration_binding
        .relevant_start_model_call_index
    )
    failure_index = (
        experience.registration_binding
        .registered_failure_onset_model_call_index
    )
    final_index = experience.registration_binding.final_model_call_index

    governance = policy_view_governance_disposition_v1(
        record.governance_state
    )
    if governance is not ProjectionBuildDispositionV1.ELIGIBLE:
        return FM1MatchedRawEpisodicViewV1(
            schema_id="FM1_MATCHED_RAW_EPISODIC_VIEW_V1",
            schema_version=1,
            record_binding=_binding(record),
            source_experience_id=experience.experience_id,
            source_experience_canonical_sha256=source_sha,
            relevant_start_model_call_index=relevant_index,
            failure_onset_model_call_index=failure_index,
            final_model_call_index=final_index,
            policy_visible_payload=None,
            policy_visible_payload_sha256=None,
            token_count=None,
            build_disposition=governance,
            safety_report=None,
        )

    all_events = tuple(
        FM1VisibleEventV1.from_sequence_event_v1(item)
        for item in experience.observed_sequence
    )
    event_by_index = {
        item.model_call_index: item for item in all_events
    }
    for anchor in (relevant_index, failure_index, final_index):
        if anchor not in event_by_index:
            raise ValueError(
                "FM1 mandatory anchor is missing from observed sequence"
            )

    full_payload = _visible_payload(experience, all_events)
    full_count = count_policy_visible_tokens_v1(
        policy_visible_payload=full_payload.to_dict(),
        tokenizer=tokenizer,
        hard_ceiling=hard_ceiling,
    )

    # Package-B FM1 is the complete registered raw window. The historical
    # event-dropping fallback is retired: no event truncation, LLM compression,
    # or post-hoc excerpt selection is allowed for the raw representation arm.
    candidate = full_payload
    measured = full_count

    report = audit_policy_visible_payload_v1(
        projection_class=ProjectionClassV1.FM1,
        policy_visible_payload=candidate.to_dict(),
        has_nonempty_recovery=False,
    )
    if policy_visible_contains_bound_identity_v1(
        policy_visible_payload=candidate.to_dict(),
        forbidden_exact_identities=_fm1_forbidden_exact_identities_v1(
            record=record,
            experience=experience,
        ),
    ):
        report = _bound_identity_augmented_report_v1(
            report=report,
        )
    if report.static_status == "FAIL":
        return FM1MatchedRawEpisodicViewV1(
            schema_id="FM1_MATCHED_RAW_EPISODIC_VIEW_V1",
            schema_version=1,
            record_binding=_binding(record),
            source_experience_id=experience.experience_id,
            source_experience_canonical_sha256=source_sha,
            relevant_start_model_call_index=relevant_index,
            failure_onset_model_call_index=failure_index,
            final_model_call_index=final_index,
            policy_visible_payload=None,
            policy_visible_payload_sha256=None,
            token_count=None,
            build_disposition=(
                ProjectionBuildDispositionV1
                .PROJECTION_INELIGIBLE_POLICY_VIEW_SAFETY
            ),
            safety_report=report,
        )

    if measured.policy_visible_token_count > hard_ceiling:
        return FM1MatchedRawEpisodicViewV1(
            schema_id="FM1_MATCHED_RAW_EPISODIC_VIEW_V1",
            schema_version=1,
            record_binding=_binding(record),
            source_experience_id=experience.experience_id,
            source_experience_canonical_sha256=source_sha,
            relevant_start_model_call_index=relevant_index,
            failure_onset_model_call_index=failure_index,
            final_model_call_index=final_index,
            policy_visible_payload=None,
            policy_visible_payload_sha256=None,
            token_count=measured,
            build_disposition=(
                ProjectionBuildDispositionV1
                .PROJECTION_INELIGIBLE_TOKEN_BUDGET
            ),
            safety_report=report,
        )

    return FM1MatchedRawEpisodicViewV1(
        schema_id="FM1_MATCHED_RAW_EPISODIC_VIEW_V1",
        schema_version=1,
        record_binding=_binding(record),
        source_experience_id=experience.experience_id,
        source_experience_canonical_sha256=source_sha,
        relevant_start_model_call_index=relevant_index,
        failure_onset_model_call_index=failure_index,
        final_model_call_index=final_index,
        policy_visible_payload=candidate,
        policy_visible_payload_sha256=report.projection_sha256,
        token_count=measured,
        build_disposition=ProjectionBuildDispositionV1.ELIGIBLE,
        safety_report=report,
    )

"""FM2/FM3 structured Policy projections for Failure Memory V1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.lifecycle_relations import (
    AccessScopeV1,
    EffectEvidenceScopeV1,
    EffectStatusV1,
    LifecycleStatusV1,
    RepairValidityStatusV1,
    SourceIntegrityStatusV1,
    DescriptiveEligibilityStatusV1,
)
from pchsi.memory.procedural_builder import (
    ProceduralFailureMemoryRecordV1,
)
from pchsi.memory.projection_common import (
    FM3RecoveryDispositionV1,
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
from pchsi.memory.semantic_recovery import (
    SemanticAnnotationTypeV1,
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


def _require_string_tuple(
    name: str,
    value: object,
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be tuple")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{name} items must be nonempty str")
    return value


@dataclass(frozen=True, slots=True)
class PolicyVisibleFailurePatternItemV1:
    authority: str
    annotation_type: str
    text: str

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {"authority", "annotation_type", "text"}
    )

    def __post_init__(self) -> None:
        if self.authority != "SEMANTIC_HYPOTHESIS":
            raise ValueError(
                "failure-pattern authority must be SEMANTIC_HYPOTHESIS"
            )
        if self.annotation_type not in {
            SemanticAnnotationTypeV1.CANDIDATE_MECHANISM.value,
            SemanticAnnotationTypeV1.CAPABILITY_COMPONENT.value,
            SemanticAnnotationTypeV1.CRITICAL_REGION.value,
        }:
            raise ValueError("annotation_type is not Policy-visible")
        if not isinstance(self.text, str) or not self.text:
            raise ValueError("text must be nonempty str")

    def to_dict(self) -> dict[str, object]:
        return {
            "authority": self.authority,
            "annotation_type": self.annotation_type,
            "text": self.text,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "PolicyVisibleFailurePatternItemV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "Policy-visible failure pattern item",
        )
        return cls(
            authority=payload["authority"],
            annotation_type=payload["annotation_type"],
            text=payload["text"],
        )


@dataclass(frozen=True, slots=True)
class FailureMemoryPolicyVisiblePayloadV1:
    activation_cues: tuple[str, ...]
    failure_pattern: tuple[PolicyVisibleFailurePatternItemV1, ...]
    revalidate_on: tuple[str, ...]
    release_cues: tuple[str, ...]
    non_applicability_cues: tuple[str, ...]
    recovery_procedure: tuple[str, ...]

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "activation_cues",
            "failure_pattern",
            "revalidate_on",
            "release_cues",
            "non_applicability_cues",
            "recovery_procedure",
        }
    )

    def __post_init__(self) -> None:
        for name in (
            "activation_cues",
            "revalidate_on",
            "release_cues",
            "non_applicability_cues",
            "recovery_procedure",
        ):
            _require_string_tuple(name, getattr(self, name))
        if type(self.failure_pattern) is not tuple:
            raise TypeError("failure_pattern must be tuple")
        if any(
            not isinstance(item, PolicyVisibleFailurePatternItemV1)
            for item in self.failure_pattern
        ):
            raise TypeError("failure_pattern contains invalid item")

    def to_dict(self) -> dict[str, object]:
        return {
            "activation_cues": list(self.activation_cues),
            "failure_pattern": [
                item.to_dict() for item in self.failure_pattern
            ],
            "revalidate_on": list(self.revalidate_on),
            "release_cues": list(self.release_cues),
            "non_applicability_cues": list(
                self.non_applicability_cues
            ),
            "recovery_procedure": list(self.recovery_procedure),
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "FailureMemoryPolicyVisiblePayloadV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "Failure Memory Policy-visible payload",
        )

        def items(name: str) -> tuple[str, ...]:
            raw = payload[name]
            if not isinstance(raw, list):
                raise TypeError(f"{name} must be JSON array")
            return tuple(raw)

        raw_pattern = payload["failure_pattern"]
        if not isinstance(raw_pattern, list):
            raise TypeError("failure_pattern must be JSON array")
        return cls(
            activation_cues=items("activation_cues"),
            failure_pattern=tuple(
                PolicyVisibleFailurePatternItemV1.from_dict(item)
                for item in raw_pattern
            ),
            revalidate_on=items("revalidate_on"),
            release_cues=items("release_cues"),
            non_applicability_cues=items(
                "non_applicability_cues"
            ),
            recovery_procedure=items("recovery_procedure"),
        )


@dataclass(frozen=True, slots=True)
class FailureMemoryPolicyProjectionV1:
    schema_id: str
    schema_version: int
    projection_class: ProjectionClassV1
    record_binding: ProjectionRecordBindingV1
    policy_visible_payload: FailureMemoryPolicyVisiblePayloadV1 | None
    policy_visible_payload_sha256: str | None
    token_count: ProjectionTokenCountV1 | None
    build_disposition: ProjectionBuildDispositionV1
    fm3_recovery_disposition: FM3RecoveryDispositionV1 | None
    safety_report: PolicyViewSafetyReportV1 | None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "schema_version",
            "projection_class",
            "record_binding",
            "policy_visible_payload",
            "policy_visible_payload_sha256",
            "token_count",
            "build_disposition",
            "fm3_recovery_disposition",
            "safety_report",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != "FAILURE_MEMORY_POLICY_PROJECTION_V1":
            raise ValueError("schema_id mismatch")
        if self.schema_version != 1:
            raise ValueError("schema_version mismatch")
        if self.projection_class not in {
            ProjectionClassV1.FM2,
            ProjectionClassV1.FM3,
        }:
            raise ValueError("structured builder supports FM2/FM3 only")
        if not isinstance(
            self.record_binding,
            ProjectionRecordBindingV1,
        ):
            raise TypeError("record_binding type mismatch")
        if self.policy_visible_payload is not None and not isinstance(
            self.policy_visible_payload,
            FailureMemoryPolicyVisiblePayloadV1,
        ):
            raise TypeError("policy_visible_payload type mismatch")
        if self.policy_visible_payload_sha256 is not None:
            value = self.policy_visible_payload_sha256
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(ch not in "0123456789abcdef" for ch in value)
            ):
                raise ValueError(
                    "policy_visible_payload_sha256 invalid"
                )
        if self.token_count is not None and not isinstance(
            self.token_count,
            ProjectionTokenCountV1,
        ):
            raise TypeError("token_count type mismatch")
        if not isinstance(
            self.build_disposition,
            ProjectionBuildDispositionV1,
        ):
            raise TypeError("build_disposition type mismatch")
        if (
            self.fm3_recovery_disposition is not None
            and not isinstance(
                self.fm3_recovery_disposition,
                FM3RecoveryDispositionV1,
            )
        ):
            raise TypeError("fm3_recovery_disposition type mismatch")
        if self.safety_report is not None and not isinstance(
            self.safety_report,
            PolicyViewSafetyReportV1,
        ):
            raise TypeError("safety_report type mismatch")
        if (
            self.safety_report is not None
            and self.safety_report.projection_class
            is not self.projection_class
        ):
            raise ValueError(
                "safety_report projection_class must match projection envelope"
            )

        if (
            self.build_disposition
            is ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_FM1_SOURCE_AMBIGUOUS
        ):
            raise ValueError(
                "FM1 source ambiguity disposition is invalid for FM2/FM3"
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

        if self.projection_class is ProjectionClassV1.FM2:
            if self.fm3_recovery_disposition is not None:
                raise ValueError(
                    "FM2 must not carry FM3 recovery disposition"
                )
            if (
                self.policy_visible_payload is not None
                and self.policy_visible_payload.recovery_procedure
            ):
                raise ValueError("FM2 recovery_procedure must be empty")
            if (
                self.safety_report is not None
                and self.safety_report.contextual_menu_check_required
            ):
                raise ValueError(
                    "FM2 must not require contextual menu checking"
                )

        if self.build_disposition in governance_ineligible:
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
                    "governance-ineligible projection must not carry evidence"
                )
            if (
                self.projection_class is ProjectionClassV1.FM3
                and self.fm3_recovery_disposition is not None
            ):
                raise ValueError(
                    "governance-ineligible FM3 must not classify recovery"
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
                    "safety-ineligible projection must not carry payload/hash/token"
                )
            if (
                self.safety_report is None
                or self.safety_report.static_status != "FAIL"
                or not self.safety_report.critical_safety_failure
                or not self.safety_report.static_failure_codes
            ):
                raise ValueError(
                    "safety-ineligible projection requires critical FAIL report"
                )
        elif (
            self.build_disposition
            is ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_TOKEN_BUDGET
        ):
            if (
                self.policy_visible_payload is not None
                or self.policy_visible_payload_sha256 is not None
            ):
                raise ValueError(
                    "token-ineligible projection must not carry payload/hash"
                )
            if self.token_count is None:
                raise ValueError(
                    "token-ineligible projection requires measured token count"
                )
            if (
                self.token_count.policy_visible_token_count
                <= self.token_count.hard_ceiling
            ):
                raise ValueError(
                    "token-ineligible projection requires count above ceiling"
                )
            if (
                self.safety_report is None
                or self.safety_report.static_status != "PASS"
                or self.safety_report.critical_safety_failure
                or self.safety_report.static_failure_codes
            ):
                raise ValueError(
                    "token-ineligible projection requires clean PASS report"
                )
        elif self.build_disposition is ProjectionBuildDispositionV1.ELIGIBLE:
            if self.policy_visible_payload is None:
                raise ValueError(
                    "eligible projection requires Policy payload"
                )
            if self.policy_visible_payload_sha256 is None:
                raise ValueError(
                    "eligible projection requires payload SHA"
                )
            if self.token_count is None:
                raise ValueError(
                    "eligible projection requires token count"
                )
            if (
                self.token_count.policy_visible_token_count
                > self.token_count.hard_ceiling
            ):
                raise ValueError("eligible projection exceeds token ceiling")
            if (
                self.safety_report is None
                or self.safety_report.static_status != "PASS"
                or self.safety_report.critical_safety_failure
                or self.safety_report.static_failure_codes
            ):
                raise ValueError(
                    "eligible projection requires clean PASS report"
                )

            recomputed_report = audit_policy_visible_payload_v1(
                projection_class=self.projection_class,
                policy_visible_payload=(
                    self.policy_visible_payload.to_dict()
                ),
                has_nonempty_recovery=bool(
                    self.policy_visible_payload.recovery_procedure
                ),
            )
            if (
                self.policy_visible_payload_sha256
                != recomputed_report.projection_sha256
            ):
                raise ValueError(
                    "policy-visible payload SHA mismatch"
                )
            if (
                self.safety_report.projection_sha256
                != recomputed_report.projection_sha256
            ):
                raise ValueError(
                    "safety report SHA does not bind actual payload"
                )
        else:
            raise ValueError("unsupported structured build disposition")

        if self.projection_class is ProjectionClassV1.FM3:
            if self.fm3_recovery_disposition is None:
                raise ValueError(
                    "resolved FM3 projection requires recovery disposition"
                )
            recovery_visible = (
                self.fm3_recovery_disposition
                is FM3RecoveryDispositionV1.RECOVERY_VISIBLE
            )
            if self.policy_visible_payload is not None:
                has_recovery = bool(
                    self.policy_visible_payload.recovery_procedure
                )
                if has_recovery != recovery_visible:
                    raise ValueError(
                        "FM3 recovery content/disposition mismatch"
                    )
            if self.safety_report is not None:
                if (
                    self.safety_report.contextual_menu_check_required
                    != recovery_visible
                ):
                    raise ValueError(
                        "FM3 contextual-menu flag/recovery disposition mismatch"
                    )

        if self.build_disposition is ProjectionBuildDispositionV1.ELIGIBLE:
            if self.safety_report != recomputed_report:
                raise ValueError(
                    "deterministic safety report mismatch"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "projection_class": self.projection_class.value,
            "record_binding": self.record_binding.to_dict(),
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
            "fm3_recovery_disposition": (
                None
                if self.fm3_recovery_disposition is None
                else self.fm3_recovery_disposition.value
            ),
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
    ) -> "FailureMemoryPolicyProjectionV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "Failure Memory Policy projection",
        )
        visible = payload["policy_visible_payload"]
        token = payload["token_count"]
        report = payload["safety_report"]
        recovery_disposition = payload["fm3_recovery_disposition"]
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            projection_class=ProjectionClassV1(
                payload["projection_class"]
            ),
            record_binding=ProjectionRecordBindingV1.from_dict(
                payload["record_binding"]
            ),
            policy_visible_payload=(
                None
                if visible is None
                else FailureMemoryPolicyVisiblePayloadV1.from_dict(
                    visible
                )
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
            fm3_recovery_disposition=(
                None
                if recovery_disposition is None
                else FM3RecoveryDispositionV1(
                    recovery_disposition
                )
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
    ) -> "FailureMemoryPolicyProjectionV1":
        return cls.from_dict(strict_json_loads(value))

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


def descriptive_policy_payload_v1(
    payload: FailureMemoryPolicyVisiblePayloadV1,
) -> dict[str, object]:
    if not isinstance(payload, FailureMemoryPolicyVisiblePayloadV1):
        raise TypeError("payload type mismatch")
    return {
        "activation_cues": list(payload.activation_cues),
        "failure_pattern": [
            item.to_dict() for item in payload.failure_pattern
        ],
        "revalidate_on": list(payload.revalidate_on),
        "release_cues": list(payload.release_cues),
        "non_applicability_cues": list(
            payload.non_applicability_cues
        ),
    }


def _record_binding(
    record: ProceduralFailureMemoryRecordV1,
) -> ProjectionRecordBindingV1:
    if record.canonical_record_sha256 is None:
        raise ValueError("record lacks canonical_record_sha256")
    return ProjectionRecordBindingV1(
        memory_lineage_id=record.memory_lineage_id,
        record_version=record.record_version,
        canonical_record_sha256=record.canonical_record_sha256,
    )


def _failure_pattern(
    record: ProceduralFailureMemoryRecordV1,
) -> tuple[PolicyVisibleFailurePatternItemV1, ...]:
    allowed = {
        SemanticAnnotationTypeV1.CANDIDATE_MECHANISM,
        SemanticAnnotationTypeV1.CAPABILITY_COMPONENT,
        SemanticAnnotationTypeV1.CRITICAL_REGION,
    }
    result = []
    for annotation in record.semantic_hypotheses:
        if annotation.annotation_type in allowed:
            result.append(
                PolicyVisibleFailurePatternItemV1(
                    authority="SEMANTIC_HYPOTHESIS",
                    annotation_type=annotation.annotation_type.value,
                    text=annotation.text,
                )
            )
    return tuple(result)


def _descriptive(
    record: ProceduralFailureMemoryRecordV1,
) -> dict[str, object]:
    return {
        "activation_cues": tuple(
            clause.condition_text
            for clause in record.applicability.activation
        ),
        "failure_pattern": _failure_pattern(record),
        "revalidate_on": (
            tuple(
                clause.condition_text
                for clause in record.applicability.revalidation
            )
            + tuple(
                clause.condition_text
                for clause
                in record.applicability.policy_visible_state_change_trigger
            )
        ),
        "release_cues": (
            tuple(
                clause.condition_text
                for clause in record.applicability.release
            )
            + tuple(
                clause.condition_text
                for clause in record.applicability.termination
            )
        ),
        "non_applicability_cues": tuple(
            clause.condition_text
            for clause in record.applicability.non_applicability
        ),
    }


def _prescriptive_gate(
    record: ProceduralFailureMemoryRecordV1,
) -> bool:
    state = record.governance_state
    return (
        state.source_integrity is SourceIntegrityStatusV1.VERIFIED
        and state.descriptive_eligibility
        is DescriptiveEligibilityStatusV1.RETRIEVAL_ELIGIBLE_DESCRIPTIVE
        and state.repair_validity is RepairValidityStatusV1.EXECUTABLE
        and state.effect_status is EffectStatusV1.POSITIVE
        and state.effect_evidence_scope
        in {
            EffectEvidenceScopeV1.SOURCE_STATE_PAIRED,
            EffectEvidenceScopeV1.REPLICATED_CONTEXT,
            EffectEvidenceScopeV1.CROSS_TASK_REPLICATED,
            EffectEvidenceScopeV1.FRESH_TASK,
            EffectEvidenceScopeV1.LIBRARY_LEVEL,
        }
        and state.access_scope
        in {
            AccessScopeV1.SAME_TASK_DEV_ALLOWED,
            AccessScopeV1.CROSS_TASK_ALLOWED,
        }
        and state.lifecycle_status
        not in {
            LifecycleStatusV1.QUARANTINE,
            LifecycleStatusV1.DISABLED,
            LifecycleStatusV1.SUPERSEDED,
        }
        and state.known_harm_ids == ()
    )


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


def _source_identity_augmented_report(
    *,
    record: ProceduralFailureMemoryRecordV1,
    payload: FailureMemoryPolicyVisiblePayloadV1,
    report: PolicyViewSafetyReportV1,
) -> PolicyViewSafetyReportV1:
    if not policy_visible_contains_bound_identity_v1(
        policy_visible_payload=payload.to_dict(),
        forbidden_exact_identities=(
            _unit3_forbidden_exact_identities_v1(record)
        ),
    ):
        return report

    codes = set(report.static_failure_codes)
    codes.add(
        PolicyViewStaticFailureCodeV1.SOURCE_IDENTITY_EXPOSURE
    )
    ordered = tuple(
        code for code in PolicyViewStaticFailureCodeV1
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


def _invalid(
    *,
    record: ProceduralFailureMemoryRecordV1,
    projection_class: ProjectionClassV1,
    disposition: ProjectionBuildDispositionV1,
) -> FailureMemoryPolicyProjectionV1:
    return FailureMemoryPolicyProjectionV1(
        schema_id="FAILURE_MEMORY_POLICY_PROJECTION_V1",
        schema_version=1,
        projection_class=projection_class,
        record_binding=_record_binding(record),
        policy_visible_payload=None,
        policy_visible_payload_sha256=None,
        token_count=None,
        build_disposition=disposition,
        fm3_recovery_disposition=None,
        safety_report=None,
    )


def build_failure_memory_policy_projection_v1(
    *,
    record: ProceduralFailureMemoryRecordV1,
    projection_class: ProjectionClassV1,
    tokenizer: PolicyTokenizerCounterV1,
    hard_ceiling: int = 256,
) -> FailureMemoryPolicyProjectionV1:
    if not isinstance(record, ProceduralFailureMemoryRecordV1):
        raise TypeError("record type mismatch")
    if projection_class not in {
        ProjectionClassV1.FM2,
        ProjectionClassV1.FM3,
    }:
        raise ValueError("structured builder accepts FM2/FM3 only")

    governance = policy_view_governance_disposition_v1(
        record.governance_state
    )
    if governance is not ProjectionBuildDispositionV1.ELIGIBLE:
        return _invalid(
            record=record,
            projection_class=projection_class,
            disposition=governance,
        )

    descriptive = _descriptive(record)
    recovery: tuple[str, ...] = ()
    recovery_disposition: FM3RecoveryDispositionV1 | None = None

    if projection_class is ProjectionClassV1.FM3:
        count = len(record.proposed_recoveries)
        if count == 0:
            recovery_disposition = (
                FM3RecoveryDispositionV1.FM3_NO_RECOVERY_PROPOSAL
            )
        elif count > 1:
            recovery_disposition = (
                FM3RecoveryDispositionV1
                .FM3_RECOVERY_PROPOSAL_AMBIGUOUS
            )
        elif not _prescriptive_gate(record):
            recovery_disposition = (
                FM3RecoveryDispositionV1
                .FM3_PRESCRIPTIVE_AUTHORITY_NOT_ESTABLISHED
            )
        else:
            recovery = tuple(
                record.proposed_recoveries[0].procedure_steps
            )
            recovery_disposition = (
                FM3RecoveryDispositionV1.RECOVERY_VISIBLE
            )

    payload = FailureMemoryPolicyVisiblePayloadV1(
        activation_cues=descriptive["activation_cues"],
        failure_pattern=descriptive["failure_pattern"],
        revalidate_on=descriptive["revalidate_on"],
        release_cues=descriptive["release_cues"],
        non_applicability_cues=descriptive[
            "non_applicability_cues"
        ],
        recovery_procedure=recovery,
    )

    report = audit_policy_visible_payload_v1(
        projection_class=projection_class,
        policy_visible_payload=payload.to_dict(),
        has_nonempty_recovery=bool(recovery),
    )
    report = _source_identity_augmented_report(
        record=record,
        payload=payload,
        report=report,
    )

    if report.static_status == "FAIL":
        return FailureMemoryPolicyProjectionV1(
            schema_id="FAILURE_MEMORY_POLICY_PROJECTION_V1",
            schema_version=1,
            projection_class=projection_class,
            record_binding=_record_binding(record),
            policy_visible_payload=None,
            policy_visible_payload_sha256=None,
            token_count=None,
            build_disposition=(
                ProjectionBuildDispositionV1
                .PROJECTION_INELIGIBLE_POLICY_VIEW_SAFETY
            ),
            fm3_recovery_disposition=(
                recovery_disposition
                if projection_class is ProjectionClassV1.FM3
                else None
            ),
            safety_report=report,
        )

    token_count = count_policy_visible_tokens_v1(
        policy_visible_payload=payload.to_dict(),
        tokenizer=tokenizer,
        hard_ceiling=hard_ceiling,
    )
    if token_count.policy_visible_token_count > hard_ceiling:
        return FailureMemoryPolicyProjectionV1(
            schema_id="FAILURE_MEMORY_POLICY_PROJECTION_V1",
            schema_version=1,
            projection_class=projection_class,
            record_binding=_record_binding(record),
            policy_visible_payload=None,
            policy_visible_payload_sha256=None,
            token_count=token_count,
            build_disposition=(
                ProjectionBuildDispositionV1
                .PROJECTION_INELIGIBLE_TOKEN_BUDGET
            ),
            fm3_recovery_disposition=(
                recovery_disposition
                if projection_class is ProjectionClassV1.FM3
                else None
            ),
            safety_report=report,
        )

    return FailureMemoryPolicyProjectionV1(
        schema_id="FAILURE_MEMORY_POLICY_PROJECTION_V1",
        schema_version=1,
        projection_class=projection_class,
        record_binding=_record_binding(record),
        policy_visible_payload=payload,
        policy_visible_payload_sha256=report.projection_sha256,
        token_count=token_count,
        build_disposition=ProjectionBuildDispositionV1.ELIGIBLE,
        fm3_recovery_disposition=(
            recovery_disposition
            if projection_class is ProjectionClassV1.FM3
            else None
        ),
        safety_report=report,
    )

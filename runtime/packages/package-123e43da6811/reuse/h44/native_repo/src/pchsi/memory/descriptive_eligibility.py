from __future__ import annotations

from dataclasses import dataclass, replace

from pchsi.evaluation.canonical_evidence import sha256_bytes
from pchsi.memory.lifecycle_relations import (
    AccessScopeV1,
    DescriptiveEligibilityStatusV1,
    EffectEvidenceScopeV1,
    EffectStatusV1,
    EvaluationContaminationStatusV1,
    LifecycleStatusV1,
    MemoryGovernanceStateV1,
    SourceIntegrityStatusV1,
)
from pchsi.memory.matched_raw_view import build_fm1_matched_raw_episodic_view_v1
from pchsi.memory.policy_projection import build_failure_memory_policy_projection_v1
from pchsi.memory.procedural_builder import ProceduralFailureMemoryRecordV1
from pchsi.memory.procedural_completeness import ProceduralCompletenessDispositionV1
from pchsi.memory.procedural_record import PreviousProceduralRecordBindingV1
from pchsi.memory.projection_common import (
    PolicyTokenizerCounterV1,
    ProjectionBuildDispositionV1,
    ProjectionClassV1,
    ProjectionRecordBindingV1,
)
from pchsi.memory.sequence_failure_experience import SequenceFailureExperienceV1
from pchsi.memory.source_integrity import MemorySourceIntegrityReportV1


@dataclass(frozen=True, slots=True)
class DescriptiveEligibilityBundleV1:
    governed_record: ProceduralFailureMemoryRecordV1 | None
    fm1: object | None
    fm2: object | None
    status: str
    failure_codes: tuple[str, ...]


def _binding(record: ProceduralFailureMemoryRecordV1) -> ProjectionRecordBindingV1:
    return ProjectionRecordBindingV1(
        memory_lineage_id=record.memory_lineage_id,
        record_version=record.record_version,
        canonical_record_sha256=record.canonical_record_sha256,
    )


def govern_descriptive_dev_record_v1(
    *,
    record: ProceduralFailureMemoryRecordV1,
    source_report: MemorySourceIntegrityReportV1,
    source_experience: SequenceFailureExperienceV1,
    tokenizer: PolicyTokenizerCounterV1,
    evaluation_contamination_status: EvaluationContaminationStatusV1,
) -> DescriptiveEligibilityBundleV1:
    failures = []
    if source_report.status != "VERIFIED" or source_report.record_binding != _binding(record):
        failures.append("SOURCE_INTEGRITY_NOT_VERIFIED")
    if record.procedural_completeness.disposition is not ProceduralCompletenessDispositionV1.ESTABLISHED:
        failures.append("PROCEDURAL_COMPLETENESS_NOT_ESTABLISHED")
    if (
        record.governance_state.effect_status is not EffectStatusV1.UNTESTED
        or record.governance_state.effect_evidence_scope is not EffectEvidenceScopeV1.UNTESTED
    ):
        failures.append("EFFECT_AUTHORITY_ALREADY_PRESENT")
    if record.governance_state.known_harm_ids:
        failures.append("KNOWN_HARM_PRESENT")
    if evaluation_contamination_status not in {
        EvaluationContaminationStatusV1.CLEAN,
        EvaluationContaminationStatusV1.HISTORICALLY_EXPOSED,
    }:
        failures.append("CONTAMINATION_STATUS_NOT_ALLOWED")
    if failures:
        return DescriptiveEligibilityBundleV1(
            governed_record=None, fm1=None, fm2=None,
            status="INELIGIBLE", failure_codes=tuple(failures),
        )

    previous = PreviousProceduralRecordBindingV1(
        memory_lineage_id=record.memory_lineage_id,
        record_version=record.record_version,
        canonical_record_sha256=record.canonical_record_sha256,
    )
    old = record.governance_state
    governance = MemoryGovernanceStateV1(
        factual_binding_status=old.factual_binding_status,
        source_integrity=SourceIntegrityStatusV1.VERIFIED,
        descriptive_eligibility=DescriptiveEligibilityStatusV1.RETRIEVAL_ELIGIBLE_DESCRIPTIVE,
        repair_validity=old.repair_validity,
        effect_status=EffectStatusV1.UNTESTED,
        effect_evidence_scope=EffectEvidenceScopeV1.UNTESTED,
        access_scope=AccessScopeV1.SAME_TASK_DEV_ALLOWED,
        lifecycle_status=LifecycleStatusV1.STAGING,
        evaluation_contamination_status=evaluation_contamination_status,
        paired_effect_observation_ids=(),
        known_harm_ids=(),
    )
    governed = replace(
        record,
        record_id=None,
        record_version=record.record_version + 1,
        previous_record_binding=previous,
        record_content_sha256=None,
        canonical_record_sha256=None,
        governance_state=governance,
    )
    fm1 = build_fm1_matched_raw_episodic_view_v1(
        record=governed,
        experience=source_experience,
        tokenizer=tokenizer,
        hard_ceiling=256,
    )
    fm2 = build_failure_memory_policy_projection_v1(
        record=governed,
        projection_class=ProjectionClassV1.FM2,
        tokenizer=tokenizer,
        hard_ceiling=256,
    )
    failures = []

    # FM1 and FM2 are independent Policy-view representations of the same
    # governed record. A raw episodic view that is too large for the frozen
    # 256-token FM1 ceiling is an unavailable representation, not evidence
    # that the descriptive record or the independently safe FM2 view is
    # invalid. Preserve that FM1 artifact fail-closed; do not truncate it and
    # do not synthesize a replacement.
    allowed_fm1_dispositions = {
        ProjectionBuildDispositionV1.ELIGIBLE,
        (
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_TOKEN_BUDGET
        ),
    }
    if fm1.build_disposition not in allowed_fm1_dispositions:
        failures.append("FM1_NOT_ELIGIBLE")
    if fm2.build_disposition is not ProjectionBuildDispositionV1.ELIGIBLE:
        failures.append("FM2_NOT_ELIGIBLE")
    if failures:
        return DescriptiveEligibilityBundleV1(
            governed_record=None, fm1=None, fm2=None,
            status="INELIGIBLE", failure_codes=tuple(failures),
        )
    return DescriptiveEligibilityBundleV1(
        governed_record=governed,
        fm1=fm1,
        fm2=fm2,
        status="ELIGIBLE",
        failure_codes=(),
    )

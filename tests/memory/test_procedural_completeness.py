from __future__ import annotations

import copy
from dataclasses import replace
import importlib
import importlib.util
from pathlib import Path

import pytest

from pchsi.evaluation.budget import BudgetState
from pchsi.memory import sequence_failure_experience as sequence_module
from pchsi.memory.applicability import (
    ApplicabilityBoundarySetV1,
    BoundaryTypeV1,
    BoundaryVerificationStatusV1,
    MemoryBoundaryClauseV1,
    NonApplicabilityDispositionV1,
    RevalidationRequirementV1,
)
from pchsi.memory.lifecycle_relations import (
    initial_memory_governance_state_v1,
)
from pchsi.memory.procedural_record import (
    FactualSequenceBindingV1,
    MemoryAuthorityTypeV1,
    MemoryEvidenceRefV1,
)


TARGET = "pchsi.memory.procedural_completeness"


def _load_target():
    try:
        spec = importlib.util.find_spec(TARGET)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        pytest.fail("TASK10_RED_MISSING_PROCEDURAL_COMPLETENESS")
    return importlib.import_module(TARGET)


def _load_task6_helpers():
    path = Path("tests/memory/test_procedural_record.py")
    spec = importlib.util.spec_from_file_location("_unit3_task6_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_experience():
    return _load_task6_helpers()._experience()


def _evidence():
    return MemoryEvidenceRefV1(
        source_kind="UNIT2_SOURCE_RECORD",
        source_id="source-1",
        source_sha256="a" * 64,
    )


def _clause(kind, rid):
    return MemoryBoundaryClauseV1(
        boundary_type=kind,
        boundary_authority=MemoryAuthorityTypeV1.REGISTERED_BOUNDARY,
        origin_role="HUMAN_REGISTERED",
        registration_id=rid,
        origin_artifact_ref=MemoryEvidenceRefV1(
            source_kind="REGISTERED_BOUNDARY_ARTIFACT",
            source_id=rid,
            source_sha256="b" * 64,
        ),
        condition_text=f"condition:{rid}",
        source_refs=(_evidence(),),
        verification_status=(
            BoundaryVerificationStatusV1.REGISTERED_UNVERIFIED
        ),
    )


def _applicability(*, revalidation=RevalidationRequirementV1.NOT_REQUIRED):
    revalidation_clauses = (
        (_clause(BoundaryTypeV1.REVALIDATION, "REVALIDATE-1"),)
        if revalidation is RevalidationRequirementV1.REQUIRED
        else ()
    )
    return ApplicabilityBoundarySetV1(
        activation=(_clause(BoundaryTypeV1.ACTIVATION, "ACTIVATE-1"),),
        continuation=(),
        revalidation_requirement=revalidation,
        revalidation=revalidation_clauses,
        release=(_clause(BoundaryTypeV1.RELEASE, "RELEASE-1"),),
        termination=(),
        non_applicability_disposition=(
            NonApplicabilityDispositionV1
            .UNRESOLVED_NO_REGISTERED_CONDITION
        ),
        non_applicability=(),
        policy_visible_state_change_trigger=(),
    )


def _second_nonexecuted_event(first):
    helpers = _load_task6_helpers()
    return sequence_module.SequenceFailureEventV1(
        model_call_index=3,
        execution_status="not_executed",
        attempt_outcome="FORMAT_ERROR",
        parser_status="failure",
        parser_error="format",
        literal_action="",
        normalized_action=None,
        admissibility_status="not_checked",
        interface_feedback_before="FORMAT_ERROR_V1",
        policy_attempt_count_before=3,
        policy_attempt_count_after=4,
        environment_step_count_before=2,
        environment_step_count_after=2,
        protocol_failure_count_before=0,
        protocol_failure_count_after=1,
        inadmissible_action_count_before=0,
        inadmissible_action_count_after=0,
        consecutive_nonexecuted_attempt_count_before=0,
        consecutive_nonexecuted_attempt_count_after=1,
        pre_observation=first.resulting_observation,
        pre_observation_sha256=first.resulting_observation_sha256,
        pre_admissible_commands=first.resulting_admissible_commands,
        pre_admissible_commands_sha256=(
            first.resulting_admissible_commands_sha256
        ),
        raw_model_response="not-json",
        raw_model_response_sha256="4" * 64,
        submitted_environment_action=None,
        resulting_observation=None,
        resulting_observation_sha256=None,
        resulting_admissible_commands=None,
        resulting_admissible_commands_sha256=None,
        environment_step_index=None,
        score=None,
        done=None,
        won=None,
        visible_state_change_disposition="NONEXECUTED",
        trace_source_pointer=helpers._pointer(
            "action_traces.jsonl", 3, "1", "7"
        ),
        policy_call_source_pointer=helpers._pointer(
            "policy_calls.jsonl", 3, "2", "9"
        ),
        public_transition_source_pointer=None,
    )


def _multi_event_experience():
    base = _base_experience()
    first = base.observed_sequence[0]
    second = _second_nonexecuted_event(first)
    registration = replace(
        base.registration_binding,
        final_model_call_index=3,
    )
    end = sequence_module.SequenceFailureObservedEndV1(
        model_call_index=3,
        budget_state_after=BudgetState(
            policy_attempt_count=4,
            environment_step_count=2,
            protocol_failure_count=1,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=1,
        ),
        episode_terminal_disposition="OUTSIDE_REGISTERED_WINDOW",
        termination_reason=None,
        final_success=None,
        final_done=None,
        final_won=None,
        final_budget=None,
    )
    return sequence_module.SequenceFailureExperienceV1(
        experience_id=None,
        schema_id=base.schema_id,
        schema_version=base.schema_version,
        source_round=base.source_round,
        source_condition=base.source_condition,
        source_task_id=base.source_task_id,
        source_gamefile_group_id=base.source_gamefile_group_id,
        source_bundle_sha256=base.source_bundle_sha256,
        source_attempt_id=base.source_attempt_id,
        task_access_binding=base.task_access_binding,
        registration_binding=registration,
        relevant_start=base.relevant_start,
        observed_sequence=(first, second),
        observed_end=end,
        included_environment_step_indices=(1,),
        source_bundle_member_sha256=base.source_bundle_member_sha256,
    )


def _no_state_change_experience():
    base = _base_experience()
    original = base.observed_sequence[0]
    event = replace(
        original,
        resulting_observation=original.pre_observation,
        resulting_observation_sha256=original.pre_observation_sha256,
        resulting_admissible_commands=original.pre_admissible_commands,
        resulting_admissible_commands_sha256=(
            original.pre_admissible_commands_sha256
        ),
        visible_state_change_disposition="NO_VISIBLE_STATE_CHANGE",
    )
    return replace(
        base,
        experience_id=None,
        observed_sequence=(event,),
    )


def _terminal_experience():
    base = _no_state_change_experience()
    end = sequence_module.SequenceFailureObservedEndV1(
        model_call_index=2,
        budget_state_after=base.observed_end.budget_state_after,
        episode_terminal_disposition="INCLUDED_REGISTERED_WINDOW",
        termination_reason="ENVIRONMENT_TERMINATED",
        final_success=False,
        final_done=True,
        final_won=False,
        final_budget=base.observed_end.budget_state_after,
    )
    return replace(base, experience_id=None, observed_end=end)


def _infrastructure_experience():
    base = _base_experience()
    event = replace(
        base.observed_sequence[0],
        execution_status="environment_error",
        attempt_outcome="ENVIRONMENT_ERROR",
        submitted_environment_action=None,
        resulting_observation=None,
        resulting_observation_sha256=None,
        resulting_admissible_commands=None,
        resulting_admissible_commands_sha256=None,
        environment_step_index=None,
        score=None,
        done=None,
        won=None,
        visible_state_change_disposition="ENVIRONMENT_ERROR",
        public_transition_source_pointer=None,
        environment_step_count_after=1,
    )
    end = sequence_module.SequenceFailureObservedEndV1(
        model_call_index=2,
        budget_state_after=BudgetState(
            policy_attempt_count=3,
            environment_step_count=1,
            protocol_failure_count=0,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        ),
        episode_terminal_disposition="OUTSIDE_REGISTERED_WINDOW",
        termination_reason=None,
        final_success=None,
        final_done=None,
        final_won=None,
        final_budget=None,
    )
    return replace(
        base,
        experience_id=None,
        observed_sequence=(event,),
        observed_end=end,
        included_environment_step_indices=(),
    )


def _evaluate(module, experience, applicability=None):
    if applicability is None:
        applicability = _applicability()
    return module.evaluate_procedural_completeness_v1(
        source_experiences=(experience,),
        factual_bindings=(
            FactualSequenceBindingV1.from_experience(experience),
        ),
        applicability=applicability,
        governance_state=initial_memory_governance_state_v1(),
    )


def test_task10_symbols_exist() -> None:
    module = _load_target()
    for name in (
        "ProceduralCompletenessDispositionV1",
        "ProceduralCompletenessFailureCodeV1",
        "ProcessEvidenceModeV1",
        "ProceduralCompletenessReportV1",
        "evaluate_procedural_completeness_v1",
    ):
        assert hasattr(module, name)


def test_task10_report_contract_is_strict_and_ordered() -> None:
    module = _load_target()
    report = module.ProceduralCompletenessReportV1(
        schema_id="PROCEDURAL_COMPLETENESS_REPORT_V1",
        schema_version=1,
        disposition=(
            module.ProceduralCompletenessDispositionV1.NOT_ESTABLISHED
        ),
        failure_codes=(
            module.ProceduralCompletenessFailureCodeV1.NO_SOURCE_EXPERIENCE,
            module.ProceduralCompletenessFailureCodeV1.NO_PROCESS_EVIDENCE,
        ),
        process_evidence_mode=module.ProcessEvidenceModeV1.NONE,
        registered_unresolved_end_present=False,
    )
    assert module.ProceduralCompletenessReportV1.from_dict(
        report.to_dict()
    ) == report

    with pytest.raises(ValueError):
        replace(
            report,
            failure_codes=(
                module.ProceduralCompletenessFailureCodeV1.NO_PROCESS_EVIDENCE,
                module.ProceduralCompletenessFailureCodeV1.NO_SOURCE_EXPERIENCE,
            ),
        )

    with pytest.raises(ValueError):
        replace(
            report,
            failure_codes=(
                module.ProceduralCompletenessFailureCodeV1.NO_PROCESS_EVIDENCE,
                module.ProceduralCompletenessFailureCodeV1.NO_PROCESS_EVIDENCE,
            ),
        )


def test_task10_established_report_requires_real_process_mode() -> None:
    module = _load_target()
    with pytest.raises(ValueError):
        module.ProceduralCompletenessReportV1(
            schema_id="PROCEDURAL_COMPLETENESS_REPORT_V1",
            schema_version=1,
            disposition=module.ProceduralCompletenessDispositionV1.ESTABLISHED,
            failure_codes=(),
            process_evidence_mode=module.ProcessEvidenceModeV1.NONE,
            registered_unresolved_end_present=False,
        )


def test_task10_single_visible_consequence_passes_without_semantics_or_recovery() -> None:
    module = _load_target()
    report = _evaluate(module, _base_experience())
    assert (
        report.disposition
        is module.ProceduralCompletenessDispositionV1.ESTABLISHED
    )
    assert (
        report.process_evidence_mode
        is module.ProcessEvidenceModeV1
        .SINGLE_EVENT_CONSEQUENTIAL_POLICY_PROCESS
    )


def test_task10_single_no_state_change_unresolved_end_fails_process() -> None:
    module = _load_target()
    report = _evaluate(module, _no_state_change_experience())
    assert (
        report.disposition
        is module.ProceduralCompletenessDispositionV1.NOT_ESTABLISHED
    )
    assert (
        module.ProceduralCompletenessFailureCodeV1.NO_PROCESS_EVIDENCE
        in report.failure_codes
    )
    assert report.registered_unresolved_end_present is True


def test_task10_single_genuine_terminal_consequence_can_pass() -> None:
    module = _load_target()
    report = _evaluate(module, _terminal_experience())
    assert (
        report.disposition
        is module.ProceduralCompletenessDispositionV1.ESTABLISHED
    )
    assert report.registered_unresolved_end_present is False


def test_task10_infrastructure_error_only_never_establishes_policy_process() -> None:
    module = _load_target()
    report = _evaluate(module, _infrastructure_experience())
    assert (
        report.disposition
        is module.ProceduralCompletenessDispositionV1.NOT_ESTABLISHED
    )
    assert (
        module.ProceduralCompletenessFailureCodeV1.INFRASTRUCTURE_ERROR_ONLY
        in report.failure_codes
    )
    assert report.process_evidence_mode is module.ProcessEvidenceModeV1.NONE


def test_task10_multi_event_process_can_pass_with_registered_unresolved_end() -> None:
    module = _load_target()
    report = _evaluate(module, _multi_event_experience())
    assert (
        report.disposition
        is module.ProceduralCompletenessDispositionV1.ESTABLISHED
    )
    assert (
        report.process_evidence_mode
        is module.ProcessEvidenceModeV1.MULTI_EVENT_POLICY_PROCESS
    )
    assert report.registered_unresolved_end_present is True


def test_task10_binding_mismatch_fails() -> None:
    module = _load_target()
    experience = _base_experience()
    other = _load_task6_helpers()._experience(
        source_condition="P4-R1-Q2-BAD-TRAIN31"
    )
    report = module.evaluate_procedural_completeness_v1(
        source_experiences=(experience,),
        factual_bindings=(
            FactualSequenceBindingV1.from_experience(other),
        ),
        applicability=_applicability(),
        governance_state=initial_memory_governance_state_v1(),
    )
    assert (
        module.ProceduralCompletenessFailureCodeV1.SOURCE_BINDING_MISMATCH
        in report.failure_codes
    )


def test_task10_missing_activation_and_release_are_mechanical_failures() -> None:
    module = _load_target()
    value = _applicability()

    missing_activation = copy.copy(value)
    object.__setattr__(missing_activation, "activation", ())
    report = _evaluate(module, _base_experience(), missing_activation)
    assert (
        module.ProceduralCompletenessFailureCodeV1.NO_ACTIVATION_BOUNDARY
        in report.failure_codes
    )

    missing_release = copy.copy(value)
    object.__setattr__(missing_release, "release", ())
    object.__setattr__(missing_release, "termination", ())
    report = _evaluate(module, _base_experience(), missing_release)
    assert (
        module.ProceduralCompletenessFailureCodeV1
        .NO_RELEASE_OR_TERMINATION_BOUNDARY
        in report.failure_codes
    )


def test_task10_unresolved_revalidation_blocks_completeness() -> None:
    module = _load_target()
    report = _evaluate(
        module,
        _base_experience(),
        _applicability(revalidation=RevalidationRequirementV1.UNRESOLVED),
    )
    assert (
        module.ProceduralCompletenessFailureCodeV1.REVALIDATION_UNRESOLVED
        in report.failure_codes
    )


def test_task10_pass_does_not_mutate_governance_state() -> None:
    module = _load_target()
    state = initial_memory_governance_state_v1()
    report = module.evaluate_procedural_completeness_v1(
        source_experiences=(_base_experience(),),
        factual_bindings=(
            FactualSequenceBindingV1.from_experience(_base_experience()),
        ),
        applicability=_applicability(),
        governance_state=state,
    )
    assert report.disposition is module.ProceduralCompletenessDispositionV1.ESTABLISHED
    assert state == initial_memory_governance_state_v1()

# ==========================================================================
# UNIT3_FIXED_HEAD_MIXED_ENV_REVIEW_V1
# Fixed-head source-review regression:
# a later infrastructure error cannot be the only later event establishing
# a multi-event policy process.
# ==========================================================================


def _review_mixed_policy_then_environment_error_experience():
    base = _base_experience()
    first = base.observed_sequence[0]
    infra = _infrastructure_experience()
    infra_event = infra.observed_sequence[0]
    helpers = _load_task6_helpers()

    second = replace(
        infra_event,
        model_call_index=3,
        policy_attempt_count_before=3,
        policy_attempt_count_after=4,
        environment_step_count_before=2,
        environment_step_count_after=2,
        pre_observation=first.resulting_observation,
        pre_observation_sha256=first.resulting_observation_sha256,
        pre_admissible_commands=first.resulting_admissible_commands,
        pre_admissible_commands_sha256=(
            first.resulting_admissible_commands_sha256
        ),
        raw_model_response='{"action":"look"}',
        raw_model_response_sha256="5" * 64,
        trace_source_pointer=helpers._pointer(
            "action_traces.jsonl",
            3,
            "6",
            "7",
        ),
        policy_call_source_pointer=helpers._pointer(
            "policy_calls.jsonl",
            3,
            "8",
            "9",
        ),
    )

    registration = replace(
        base.registration_binding,
        final_model_call_index=3,
    )

    end = sequence_module.SequenceFailureObservedEndV1(
        model_call_index=3,
        budget_state_after=BudgetState(
            policy_attempt_count=4,
            environment_step_count=2,
            protocol_failure_count=0,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        ),
        episode_terminal_disposition="OUTSIDE_REGISTERED_WINDOW",
        termination_reason=None,
        final_success=None,
        final_done=None,
        final_won=None,
        final_budget=None,
    )

    return replace(
        base,
        experience_id=None,
        registration_binding=registration,
        observed_sequence=(first, second),
        observed_end=end,
        included_environment_step_indices=(1,),
    )


def test_task10_mixed_policy_then_environment_error_does_not_establish_process():
    module = _load_target()

    report = _evaluate(
        module,
        _review_mixed_policy_then_environment_error_experience(),
    )

    assert (
        report.disposition
        is module.ProceduralCompletenessDispositionV1.NOT_ESTABLISHED
    )

    assert (
        module.ProceduralCompletenessFailureCodeV1.NO_PROCESS_EVIDENCE
        in report.failure_codes
    )

    assert (
        report.process_evidence_mode
        is module.ProcessEvidenceModeV1.NONE
    )

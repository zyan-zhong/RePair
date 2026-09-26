from dataclasses import replace
import importlib.util
from pathlib import Path

from pchsi.memory.descriptive_eligibility import (
    govern_descriptive_dev_record_v1,
)
from pchsi.memory.lifecycle_relations import (
    EffectStatusV1,
    EvaluationContaminationStatusV1,
)
from pchsi.memory.source_integrity import (
    audit_memory_source_integrity_v1,
)


def _helpers():
    path = Path("tests/memory/package_a_test_helpers.py")
    spec = importlib.util.spec_from_file_location(
        "_pa_helpers",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _safe_record(existing, builder_module, experience):
    assembly = existing._assembly_input(
        builder_module,
        (experience,),
    )
    applicability = assembly.applicability

    safe_activation = tuple(
        replace(
            clause,
            condition_text="activation condition is satisfied",
        )
        for clause in applicability.activation
    )
    safe_release = tuple(
        replace(
            clause,
            condition_text="release condition becomes satisfied",
        )
        for clause in applicability.release
    )

    safe_applicability = replace(
        applicability,
        activation=safe_activation,
        release=safe_release,
    )
    safe_assembly = replace(
        assembly,
        applicability=safe_applicability,
    )

    return builder_module.build_procedural_failure_memory_record_v1(
        assembly_input=safe_assembly,
        assembly_registration_binding=existing._registration_binding(
            builder_module,
            safe_assembly,
        ),
        source_experiences=(experience,),
        previous_record=None,
    )


def test_source_integrity_and_versioned_dev_governance():
    h = _helpers()
    existing = h.load_existing_helpers()
    builder_module = existing._load_target()
    experience = existing._experience()
    record = _safe_record(
        existing,
        builder_module,
        experience,
    )

    report = audit_memory_source_integrity_v1(
        record=record,
        registered_experiences=(experience,),
    )
    assert report.status == "VERIFIED"

    bundle = govern_descriptive_dev_record_v1(
        record=record,
        source_report=report,
        source_experience=experience,
        tokenizer=h.TinyTokenizer(),
        evaluation_contamination_status=(
            EvaluationContaminationStatusV1.CLEAN
        ),
    )

    assert bundle.status == "ELIGIBLE"
    assert bundle.failure_codes == ()
    assert bundle.governed_record is not None
    assert (
        bundle.governed_record.record_version
        == record.record_version + 1
    )
    assert (
        bundle.governed_record.governance_state.effect_status
        is EffectStatusV1.UNTESTED
    )
    assert bundle.fm1 is not None
    assert bundle.fm2 is not None
    assert bundle.fm1.policy_visible_payload is not None
    assert bundle.fm2.policy_visible_payload is not None


def test_registration_id_leaking_boundary_text_is_not_dev_eligible():
    h = _helpers()
    existing = h.load_existing_helpers()
    builder_module = existing._load_target()
    experience = existing._experience()

    unsafe_record = existing._record(
        builder_module,
        experience=experience,
    )

    activation = unsafe_record.applicability.activation
    release = unsafe_record.applicability.release

    assert any(
        clause.registration_id in clause.condition_text
        for clause in (*activation, *release)
    )

    report = audit_memory_source_integrity_v1(
        record=unsafe_record,
        registered_experiences=(experience,),
    )
    assert report.status == "VERIFIED"

    bundle = govern_descriptive_dev_record_v1(
        record=unsafe_record,
        source_report=report,
        source_experience=experience,
        tokenizer=h.TinyTokenizer(),
        evaluation_contamination_status=(
            EvaluationContaminationStatusV1.CLEAN
        ),
    )

    assert bundle.status == "INELIGIBLE"
    assert bundle.failure_codes == ("FM2_NOT_ELIGIBLE",)
    assert bundle.governed_record is None
    assert bundle.fm1 is None
    assert bundle.fm2 is None

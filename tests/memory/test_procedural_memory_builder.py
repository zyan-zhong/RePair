from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

from pchsi.evaluation.canonical_evidence import (
    strict_json_loads,
)
from pchsi.evaluation.schema_contract import (
    _validate_payload_node,
    validate_schema_definition,
)
from pchsi.memory.applicability import (
    ApplicabilityBoundarySetV1,
    BoundaryTypeV1,
    BoundaryVerificationStatusV1,
    MemoryBoundaryClauseV1,
    NonApplicabilityDispositionV1,
    RevalidationRequirementV1,
)
from pchsi.memory.lifecycle_relations import (
    AccessScopeV1,
    DescriptiveEligibilityStatusV1,
    EffectEvidenceScopeV1,
    EffectStatusV1,
    EvaluationContaminationStatusV1,
    FactualBindingStatusV1,
    LifecycleStatusV1,
    MemoryGovernanceStateV1,
    MemoryRelationTargetKindV1,
    MemoryRelationTargetV1,
    MemoryRelationTypeV1,
    MemoryRelationV1,
    MemoryRelationVerificationStateV1,
    RepairValidityStatusV1,
    SourceIntegrityStatusV1,
)
from pchsi.memory.procedural_record import (
    MemoryAuthorityTypeV1,
    MemoryEvidenceRefV1,
    PreviousProceduralRecordBindingV1,
    ProceduralMemoryLineageV1,
)
from pchsi.memory.semantic_recovery import (
    ObservedRecoveryBindingV1,
    ProposedRecoveryV1,
    SemanticAnnotationTypeV1,
    SemanticConfidenceV1,
    SemanticHypothesisAnnotationV1,
)


TARGET = "pchsi.memory.procedural_builder"
MATERIALIZER = Path(
    "scripts/memory/materialize_procedural_failure_memory_v1.py"
)
RECORD_SCHEMA = Path(
    "configs/memory/schemas/procedural_failure_memory_record_v1.json"
)
ASSEMBLY_SCHEMA = Path(
    "configs/memory/schemas/procedural_memory_assembly_registration_v1.json"
)


def _load_target():
    try:
        spec = importlib.util.find_spec(TARGET)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        pytest.fail("TASK11_RED_MISSING_PROCEDURAL_BUILDER")
    return importlib.import_module(TARGET)


def _load_materializer():
    _load_target()
    if not MATERIALIZER.is_file():
        pytest.fail("TASK11_RED_MISSING_PROCEDURAL_BUILDER")
    spec = importlib.util.spec_from_file_location(
        "_task11_materializer",
        MATERIALIZER,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_task6_helpers():
    path = Path("tests/memory/test_procedural_record.py")
    spec = importlib.util.spec_from_file_location("_task6_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_task10_helpers():
    path = Path("tests/memory/test_procedural_completeness.py")
    spec = importlib.util.spec_from_file_location("_task10_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _experience(*, source_condition="P4-R1-Q2-BAD-TRAIN17"):
    return _load_task6_helpers()._experience(
        source_condition=source_condition
    )


def _source_ref(experience):
    return MemoryEvidenceRefV1(
        source_kind="SEQUENCE_FAILURE_EXPERIENCE_V1",
        source_id=experience.experience_id,
        source_sha256=hashlib.sha256(
            experience.canonical_bytes()
        ).hexdigest(),
    )


def _generic_ref(kind="UNIT2_SOURCE_RECORD", sid="source-1", char="a"):
    return MemoryEvidenceRefV1(
        source_kind=kind,
        source_id=sid,
        source_sha256=char * 64,
    )


def _boundary(kind, rid):
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
        source_refs=(_generic_ref(),),
        verification_status=(
            BoundaryVerificationStatusV1.REGISTERED_UNVERIFIED
        ),
    )


def _applicability():
    return ApplicabilityBoundarySetV1(
        activation=(_boundary(BoundaryTypeV1.ACTIVATION, "ACT-1"),),
        continuation=(),
        revalidation_requirement=RevalidationRequirementV1.NOT_REQUIRED,
        revalidation=(),
        release=(_boundary(BoundaryTypeV1.RELEASE, "REL-1"),),
        termination=(),
        non_applicability_disposition=(
            NonApplicabilityDispositionV1
            .UNRESOLVED_NO_REGISTERED_CONDITION
        ),
        non_applicability=(),
        policy_visible_state_change_trigger=(),
    )


def _lineage(*, version=1, previous=None):
    return ProceduralMemoryLineageV1(
        memory_lineage_id="1" * 64,
        record_version=version,
        previous_record_binding=previous,
    )


def _assembly_input(module, experiences, *, lineage=None, rid="ASSEMBLY-1",
                    semantic=(), recoveries=(), observed=(), relations=()):
    if lineage is None:
        lineage = _lineage()
    return module.ProceduralMemoryAssemblyInputV1(
        schema_id="PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1",
        schema_version=1,
        registration_id=rid,
        lineage=lineage,
        creation_event_id="CREATE-1",
        creator_role="REGISTERED_BUILDER",
        source_experience_refs=tuple(_source_ref(item) for item in experiences),
        applicability=_applicability(),
        semantic_hypotheses=tuple(semantic),
        observed_recovery_bindings=tuple(observed),
        proposed_recoveries=tuple(recoveries),
        relations=tuple(relations),
        created_snapshot_candidate=None,
    )


def _registration_binding(module, assembly):
    sha = hashlib.sha256(assembly.canonical_bytes()).hexdigest()
    from pchsi.memory.procedural_record import AssemblyRegistrationBindingV1

    return AssemblyRegistrationBindingV1(
        schema_id="PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1",
        registration_id=assembly.registration_id,
        assembly_registration_sha256=sha,
        lineage_registration_ref=MemoryEvidenceRefV1(
            source_kind="PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1",
            source_id=assembly.registration_id,
            source_sha256=sha,
        ),
    )


def _record(module, *, experience=None):
    if experience is None:
        experience = _experience()
    assembly = _assembly_input(module, (experience,))
    return module.build_procedural_failure_memory_record_v1(
        assembly_input=assembly,
        assembly_registration_binding=_registration_binding(module, assembly),
        source_experiences=(experience,),
        previous_record=None,
    )


def test_task11_symbols_exist() -> None:
    module = _load_target()
    for name in (
        "ProceduralMemoryAssemblyInputV1",
        "ProceduralFailureMemoryRecordV1",
        "build_procedural_failure_memory_record_v1",
    ):
        assert hasattr(module, name)


def test_task11_assembly_input_strict_round_trip_and_source_manifest() -> None:
    module = _load_target()
    first = _experience()
    second = _experience(source_condition="P4-R1-Q2-BAD-TRAIN31")
    assembly = _assembly_input(module, (first, second))

    rebuilt = module.ProceduralMemoryAssemblyInputV1.from_json(
        assembly.canonical_bytes()
    )
    assert tuple(
        ref.source_id for ref in rebuilt.source_experience_refs
    ) == (first.experience_id, second.experience_id)


def test_task11_builder_rejects_source_count_order_id_and_sha_mismatch() -> None:
    module = _load_target()
    first = _experience()
    second = _experience(source_condition="P4-R1-Q2-BAD-TRAIN31")
    assembly = _assembly_input(module, (first, second))
    binding = _registration_binding(module, assembly)

    with pytest.raises(ValueError):
        module.build_procedural_failure_memory_record_v1(
            assembly_input=assembly,
            assembly_registration_binding=binding,
            source_experiences=(first,),
            previous_record=None,
        )

    with pytest.raises(ValueError):
        module.build_procedural_failure_memory_record_v1(
            assembly_input=assembly,
            assembly_registration_binding=binding,
            source_experiences=(second, first),
            previous_record=None,
        )

    payload = assembly.to_dict()
    payload["source_experience_refs"][0]["source_sha256"] = "0" * 64
    tampered = module.ProceduralMemoryAssemblyInputV1.from_dict(payload)
    with pytest.raises(ValueError):
        module.build_procedural_failure_memory_record_v1(
            assembly_input=tampered,
            assembly_registration_binding=_registration_binding(module, tampered),
            source_experiences=(first, second),
            previous_record=None,
        )


def test_task11_builder_binds_registration_and_is_byte_deterministic() -> None:
    module = _load_target()
    experience = _experience()
    assembly = _assembly_input(module, (experience,))
    binding = _registration_binding(module, assembly)

    first = module.build_procedural_failure_memory_record_v1(
        assembly_input=assembly,
        assembly_registration_binding=binding,
        source_experiences=(experience,),
        previous_record=None,
    )
    second = module.build_procedural_failure_memory_record_v1(
        assembly_input=assembly,
        assembly_registration_binding=binding,
        source_experiences=(experience,),
        previous_record=None,
    )

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.provenance.assembly_registration_binding == binding
    assert len(first.record_id) == 64
    assert len(first.record_content_sha256) == 64
    assert len(first.canonical_record_sha256) == 64


def test_task11_optional_semantics_and_recovery_do_not_block_complete_record() -> None:
    module = _load_target()
    record = _record(module)
    assert record.semantic_hypotheses == ()
    assert record.proposed_recoveries == ()
    assert (
        record.procedural_completeness.disposition.value
        == "PROCEDURAL_COMPLETENESS_ESTABLISHED"
    )


def test_task11_incomplete_process_stays_staging_candidate() -> None:
    module = _load_target()
    experience = _load_task10_helpers()._no_state_change_experience()
    record = _record(module, experience=experience)
    assert (
        record.procedural_completeness.disposition.value
        == "PROCEDURAL_COMPLETENESS_NOT_ESTABLISHED"
    )
    assert record.governance_state.access_scope is AccessScopeV1.STAGING_ONLY
    assert record.governance_state.effect_status is EffectStatusV1.UNTESTED


def test_task11_duplicate_annotation_proposal_and_recovery_ids_are_rejected() -> None:
    module = _load_target()
    experience = _experience()
    ann = SemanticHypothesisAnnotationV1(
        annotation_id="ANN-1",
        annotation_type=SemanticAnnotationTypeV1.CANDIDATE_MECHANISM,
        authority_type=MemoryAuthorityTypeV1.SEMANTIC_HYPOTHESIS,
        text="candidate",
        supporting_refs=(_generic_ref(),),
        counterevidence_refs=(),
        semantic_confidence=SemanticConfidenceV1.LOW,
        origin_role="HUMAN",
        origin_identity="reviewer",
        origin_artifact_ref=_generic_ref(
            "SEMANTIC_ANNOTATION_ARTIFACT", "ANN-1", "c"
        ),
    )
    proposal = ProposedRecoveryV1(
        proposal_id="PROP-1",
        authority_type=MemoryAuthorityTypeV1.RECOVERY_PROPOSAL,
        procedure_steps=("revalidate",),
        source_refs=(_generic_ref(),),
        origin_role="HUMAN",
        origin_identity="reviewer",
        origin_artifact_ref=_generic_ref(
            "RECOVERY_PROPOSAL_ARTIFACT", "PROP-1", "d"
        ),
    )
    observed = ObservedRecoveryBindingV1(
        authority_type=MemoryAuthorityTypeV1.REGISTERED_BOUNDARY,
        source_experience_id=experience.experience_id,
        registered_recovery_start_model_call_index=2,
        registered_recovery_final_model_call_index=2,
        source_refs=(_generic_ref(),),
    )

    for kwargs in (
        {"semantic": (ann, ann)},
        {"recoveries": (proposal, proposal)},
        {"observed": (observed, observed)},
    ):
        with pytest.raises(ValueError):
            _assembly_input(module, (experience,), **kwargs)


def test_task11_observed_recovery_must_match_unit2_registered_range() -> None:
    module = _load_target()
    experience = _experience()
    observed = ObservedRecoveryBindingV1(
        authority_type=MemoryAuthorityTypeV1.REGISTERED_BOUNDARY,
        source_experience_id=experience.experience_id,
        registered_recovery_start_model_call_index=2,
        registered_recovery_final_model_call_index=2,
        source_refs=(_generic_ref(),),
    )
    assembly = _assembly_input(module, (experience,), observed=(observed,))
    with pytest.raises(ValueError, match="no registered recovery"):
        module.build_procedural_failure_memory_record_v1(
            assembly_input=assembly,
            assembly_registration_binding=_registration_binding(module, assembly),
            source_experiences=(experience,),
            previous_record=None,
        )


def test_task11_previous_record_chain_is_verified_against_exact_record() -> None:
    module = _load_target()
    experience = _experience()
    v1 = _record(module, experience=experience)
    previous_binding = PreviousProceduralRecordBindingV1(
        memory_lineage_id=v1.memory_lineage_id,
        record_version=v1.record_version,
        canonical_record_sha256=v1.canonical_record_sha256,
    )
    assembly = _assembly_input(
        module,
        (experience,),
        lineage=_lineage(version=2, previous=previous_binding),
        rid="ASSEMBLY-2",
    )
    v2 = module.build_procedural_failure_memory_record_v1(
        assembly_input=assembly,
        assembly_registration_binding=_registration_binding(module, assembly),
        source_experiences=(experience,),
        previous_record=v1,
    )
    assert v2.record_version == 2
    assert v2.record_id != v1.record_id

    wrong = replace(
        v1,
        memory_lineage_id="9" * 64,
        record_id=None,
        record_content_sha256=None,
        canonical_record_sha256=None,
    )
    with pytest.raises(ValueError):
        module.build_procedural_failure_memory_record_v1(
            assembly_input=assembly,
            assembly_registration_binding=_registration_binding(module, assembly),
            source_experiences=(experience,),
            previous_record=wrong,
        )


@pytest.mark.parametrize(
    "field",
    ["record_id", "record_content_sha256", "canonical_record_sha256"],
)
def test_task11_parser_recomputes_and_rejects_derived_identity_tamper(field) -> None:
    module = _load_target()
    record = _record(module)
    payload = record.to_dict()
    payload[field] = "0" * 64
    with pytest.raises(ValueError):
        module.ProceduralFailureMemoryRecordV1.from_dict(payload)


def test_task11_full_governance_vocab_is_parseable_but_builder_is_initial_only() -> None:
    module = _load_target()
    record = _record(module)
    future = MemoryGovernanceStateV1(
        factual_binding_status=(
            FactualBindingStatusV1.BOUND_TO_CODE_APPROVED_UNIT2_OBJECT
        ),
        source_integrity=SourceIntegrityStatusV1.VERIFIED,
        descriptive_eligibility=(
            DescriptiveEligibilityStatusV1.RETRIEVAL_ELIGIBLE_DESCRIPTIVE
        ),
        repair_validity=RepairValidityStatusV1.EXECUTABLE,
        effect_status=EffectStatusV1.POSITIVE,
        effect_evidence_scope=EffectEvidenceScopeV1.SOURCE_STATE_PAIRED,
        access_scope=AccessScopeV1.SAME_TASK_DEV_ALLOWED,
        lifecycle_status=LifecycleStatusV1.ACTIVE,
        evaluation_contamination_status=EvaluationContaminationStatusV1.CLEAN,
        paired_effect_observation_ids=("effect-1",),
        known_harm_ids=(),
    )
    future_record = replace(
        record,
        governance_state=future,
        record_content_sha256=None,
        canonical_record_sha256=None,
    )
    rebuilt = module.ProceduralFailureMemoryRecordV1.from_dict(
        future_record.to_dict()
    )
    assert rebuilt.governance_state.effect_status is EffectStatusV1.POSITIVE

    # Assembly registration has no governance field, so injection is rejected.
    payload = _assembly_input(module, (_experience(),)).to_dict()
    payload["governance_state"] = future.to_dict()
    with pytest.raises(ValueError):
        module.ProceduralMemoryAssemblyInputV1.from_dict(payload)


def test_task11_future_authority_relation_is_record_representable_but_not_assembly_allowed() -> None:
    module = _load_target()
    relation = MemoryRelationV1(
        relation_id="REL-V",
        relation_type=MemoryRelationTypeV1.VERIFIED_BY,
        source_memory_lineage_id="1" * 64,
        target=MemoryRelationTargetV1(
            target_kind=MemoryRelationTargetKindV1.REGISTERED_ARTIFACT,
            target_id="effect-artifact",
            target_canonical_record_sha256=None,
        ),
        authority_type=MemoryAuthorityTypeV1.EFFECT_EVIDENCE,
        origin_role="EFFECT_VERIFIER",
        source_refs=(_generic_ref("GOVERNANCE_ARTIFACT"),),
        verification_state=MemoryRelationVerificationStateV1.EFFECT_VERIFIED,
        created_version=2,
    )
    record = _record(module)
    future_record = replace(
        record,
        relations=(relation,),
        record_content_sha256=None,
        canonical_record_sha256=None,
    )
    assert (
        module.ProceduralFailureMemoryRecordV1.from_dict(
            future_record.to_dict()
        ).relations[0].relation_type
        is MemoryRelationTypeV1.VERIFIED_BY
    )

    with pytest.raises(ValueError):
        _assembly_input(module, (_experience(),), relations=(relation,))


def test_task11_memory_record_relation_target_is_exact_content_binding() -> None:
    _load_target()
    with pytest.raises(ValueError):
        MemoryRelationTargetV1(
            target_kind=MemoryRelationTargetKindV1.MEMORY_RECORD,
            target_id="1" * 64,
            target_canonical_record_sha256=None,
        )
    target = MemoryRelationTargetV1(
        target_kind=MemoryRelationTargetKindV1.MEMORY_RECORD,
        target_id="1" * 64,
        target_canonical_record_sha256="a" * 64,
    )
    assert target.target_canonical_record_sha256 == "a" * 64


def test_task11_strict_record_and_assembly_schemas_accept_canonical_payloads() -> None:
    module = _load_target()
    record = _record(module)
    assembly = _assembly_input(module, (_experience(),))

    for path, payload in (
        (RECORD_SCHEMA, record.to_dict()),
        (ASSEMBLY_SCHEMA, assembly.to_dict()),
    ):
        assert path.is_file()
        schema = strict_json_loads(path.read_bytes())
        validate_schema_definition(schema)
        _validate_payload_node(payload, schema, "$")


def test_task11_strict_schemas_reject_unknown_nested_future_fields() -> None:
    module = _load_target()
    record = _record(module).to_dict()
    record["governance_state"]["promotion_status"] = "PROMOTED"

    schema = strict_json_loads(RECORD_SCHEMA.read_bytes())
    with pytest.raises(ValueError, match="unknown fields"):
        _validate_payload_node(record, schema, "$")

    assembly = _assembly_input(module, (_experience(),)).to_dict()
    assembly["applicability"]["effect_status"] = "POSITIVE"
    schema = strict_json_loads(ASSEMBLY_SCHEMA.read_bytes())
    with pytest.raises(ValueError, match="unknown fields"):
        _validate_payload_node(assembly, schema, "$")


def test_task11_strict_json_rejects_duplicate_keys_and_nonfinite_numbers() -> None:
    module = _load_target()
    assembly = _assembly_input(module, (_experience(),))
    text = assembly.canonical_bytes().decode("utf-8").rstrip()
    duplicate = text[:-1] + ',"schema_id":"OTHER"}'
    with pytest.raises(ValueError, match="duplicate"):
        module.ProceduralMemoryAssemblyInputV1.from_json(duplicate)

    with pytest.raises(ValueError, match="non-standard"):
        module.ProceduralMemoryAssemblyInputV1.from_json(
            '{"schema_id":NaN}'
        )


def test_task11_materializer_writes_exact_canonical_bytes_once(tmp_path) -> None:
    module = _load_target()
    materializer = _load_materializer()
    experience = _experience()
    assembly = _assembly_input(module, (experience,))

    source = tmp_path / "source.json"
    registration = tmp_path / "registration.json"
    source.write_bytes(experience.canonical_bytes())
    registration.write_bytes(assembly.canonical_bytes())

    output = tmp_path / (
        f"{assembly.lineage.memory_lineage_id}."
        f"v{assembly.lineage.record_version}.json"
    )
    record = materializer.materialize_files_v1(
        source_experience_paths=(source,),
        assembly_registration_path=registration,
        previous_record_path=None,
        output_path=output,
    )
    assert output.read_bytes() == record.canonical_bytes()

    with pytest.raises(FileExistsError):
        materializer.materialize_files_v1(
            source_experience_paths=(source,),
            assembly_registration_path=registration,
            previous_record_path=None,
            output_path=output,
        )


def test_task11_materializer_rejects_alias_and_noncanonical_previous(tmp_path) -> None:
    module = _load_target()
    materializer = _load_materializer()
    experience = _experience()
    assembly = _assembly_input(module, (experience,))

    source = tmp_path / "source.json"
    registration = tmp_path / "registration.json"
    source.write_bytes(experience.canonical_bytes())
    registration.write_bytes(assembly.canonical_bytes())

    with pytest.raises(ValueError, match="basename"):
        materializer.materialize_files_v1(
            source_experience_paths=(source,),
            assembly_registration_path=registration,
            previous_record_path=None,
            output_path=tmp_path / "alias.json",
        )


def test_task11_materializer_rejects_symlink_inputs_and_parent(tmp_path) -> None:
    module = _load_target()
    materializer = _load_materializer()
    experience = _experience()
    assembly = _assembly_input(module, (experience,))

    source_real = tmp_path / "source-real.json"
    source_real.write_bytes(experience.canonical_bytes())
    source_link = tmp_path / "source-link.json"
    source_link.symlink_to(source_real)

    registration = tmp_path / "registration.json"
    registration.write_bytes(assembly.canonical_bytes())

    output = tmp_path / (
        f"{assembly.lineage.memory_lineage_id}."
        f"v{assembly.lineage.record_version}.json"
    )

    with pytest.raises(ValueError, match="symlink"):
        materializer.materialize_files_v1(
            source_experience_paths=(source_link,),
            assembly_registration_path=registration,
            previous_record_path=None,
            output_path=output,
        )

    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    link_parent = tmp_path / "link-parent"
    link_parent.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(ValueError, match="parent"):
        materializer.materialize_files_v1(
            source_experience_paths=(source_real,),
            assembly_registration_path=registration,
            previous_record_path=None,
            output_path=link_parent / output.name,
        )


def test_task11_record_strict_json_rejects_duplicate_keys() -> None:
    module = _load_target()
    record = _record(module)
    text = record.canonical_bytes().decode("utf-8").rstrip()
    duplicate = text[:-1] + ',"record_id":"' + record.record_id + '"}'
    with pytest.raises(ValueError, match="duplicate"):
        module.ProceduralFailureMemoryRecordV1.from_json(duplicate)


def test_task11_materializer_rejects_noncanonical_registration_and_previous_bytes(
    tmp_path,
) -> None:
    module = _load_target()
    materializer = _load_materializer()
    experience = _experience()
    assembly = _assembly_input(module, (experience,))

    source = tmp_path / "source.json"
    source.write_bytes(experience.canonical_bytes())

    registration = tmp_path / "registration.json"
    registration.write_bytes(b" " + assembly.canonical_bytes())

    output = tmp_path / (
        f"{assembly.lineage.memory_lineage_id}."
        f"v{assembly.lineage.record_version}.json"
    )
    with pytest.raises(ValueError, match="canonical"):
        materializer.materialize_files_v1(
            source_experience_paths=(source,),
            assembly_registration_path=registration,
            previous_record_path=None,
            output_path=output,
        )

    previous = _record(module)
    previous_path = tmp_path / "previous.json"
    previous_path.write_bytes(b" " + previous.canonical_bytes())
    with pytest.raises(ValueError, match="canonical"):
        materializer._load_previous_record(previous_path)


def test_task11_materializer_rejects_registration_and_output_symlinks(
    tmp_path,
) -> None:
    module = _load_target()
    materializer = _load_materializer()
    experience = _experience()
    assembly = _assembly_input(module, (experience,))

    source = tmp_path / "source.json"
    source.write_bytes(experience.canonical_bytes())

    registration_real = tmp_path / "registration-real.json"
    registration_real.write_bytes(assembly.canonical_bytes())
    registration_link = tmp_path / "registration-link.json"
    registration_link.symlink_to(registration_real)

    output = tmp_path / (
        f"{assembly.lineage.memory_lineage_id}."
        f"v{assembly.lineage.record_version}.json"
    )
    with pytest.raises(ValueError, match="symlink"):
        materializer.materialize_files_v1(
            source_experience_paths=(source,),
            assembly_registration_path=registration_link,
            previous_record_path=None,
            output_path=output,
        )

    target = tmp_path / "existing-target"
    target.write_text("x", encoding="utf-8")
    output.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        materializer.materialize_files_v1(
            source_experience_paths=(source,),
            assembly_registration_path=registration_real,
            previous_record_path=None,
            output_path=output,
        )


def test_task11_content_change_changes_content_and_canonical_hash_not_lineage_id() -> None:
    module = _load_target()
    record = _record(module)
    changed_app = record.applicability.to_dict()
    changed_app["activation"][0]["condition_text"] = "changed condition"
    changed_record = replace(
        record,
        applicability=ApplicabilityBoundarySetV1.from_dict(changed_app),
        record_content_sha256=None,
        canonical_record_sha256=None,
    )
    assert changed_record.record_id == record.record_id
    assert changed_record.record_content_sha256 != record.record_content_sha256
    assert changed_record.canonical_record_sha256 != record.canonical_record_sha256



def test_task11_materializer_static_surface_has_no_discovery_or_execution_integrations() -> None:
    _load_target()
    _load_materializer()
    tree = ast.parse(MATERIALIZER.read_text(encoding="utf-8"))
    forbidden_imports = {
        "subprocess",
        "socket",
        "requests",
        "httpx",
        "urllib",
        "glob",
        "alfworld",
        "openai",
        "anthropic",
        "torch",
        "transformers",
        "vllm",
    }
    imports = set()
    forbidden_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in {
                    "glob",
                    "rglob",
                    "walk",
                    "system",
                    "popen",
                    "Popen",
                    "run",
                    "step",
                    "reset",
                }
            ):
                forbidden_calls.append(func.attr)
    assert not (imports & forbidden_imports)
    assert not forbidden_calls

# ==========================================================================
# UNIT3_FIXED_HEAD_SCHEMA_DURABILITY_REVIEW_V1
# Fixed-head source-review schema and write-once durability hardenings.
# ==========================================================================


def _review_validate_schema_payload(
    path: Path,
    payload,
) -> None:
    schema = strict_json_loads(path.read_bytes())
    validate_schema_definition(schema)
    _validate_payload_node(payload, schema, "$")


def test_task11_final_schema_rejects_wrong_activation_boundary_type():
    module = _load_target()
    payload = _record(module).to_dict()
    payload["applicability"]["activation"][0]["boundary_type"] = "RELEASE"

    with pytest.raises(ValueError):
        _review_validate_schema_payload(
            RECORD_SCHEMA,
            payload,
        )


def test_task11_assembly_schema_rejects_wrong_activation_boundary_type():
    module = _load_target()
    payload = _assembly_input(
        module,
        (_experience(),),
    ).to_dict()
    payload["applicability"]["activation"][0]["boundary_type"] = "RELEASE"

    with pytest.raises(ValueError):
        _review_validate_schema_payload(
            ASSEMBLY_SCHEMA,
            payload,
        )


def _review_future_verified_relation():
    return MemoryRelationV1(
        relation_id="REL-FUTURE-SCHEMA",
        relation_type=MemoryRelationTypeV1.VERIFIED_BY,
        source_memory_lineage_id="1" * 64,
        target=MemoryRelationTargetV1(
            target_kind=MemoryRelationTargetKindV1.REGISTERED_ARTIFACT,
            target_id="effect-artifact",
            target_canonical_record_sha256=None,
        ),
        authority_type=MemoryAuthorityTypeV1.EFFECT_EVIDENCE,
        origin_role="EFFECT_VERIFIER",
        source_refs=(
            _generic_ref("GOVERNANCE_ARTIFACT"),
        ),
        verification_state=(
            MemoryRelationVerificationStateV1.EFFECT_VERIFIED
        ),
        created_version=2,
    )


def test_task11_final_schema_accepts_future_governance_and_verified_relation():
    module = _load_target()

    future = MemoryGovernanceStateV1(
        factual_binding_status=(
            FactualBindingStatusV1.BOUND_TO_CODE_APPROVED_UNIT2_OBJECT
        ),
        source_integrity=SourceIntegrityStatusV1.VERIFIED,
        descriptive_eligibility=(
            DescriptiveEligibilityStatusV1.RETRIEVAL_ELIGIBLE_DESCRIPTIVE
        ),
        repair_validity=RepairValidityStatusV1.EXECUTABLE,
        effect_status=EffectStatusV1.POSITIVE,
        effect_evidence_scope=EffectEvidenceScopeV1.SOURCE_STATE_PAIRED,
        access_scope=AccessScopeV1.CROSS_TASK_ALLOWED,
        lifecycle_status=LifecycleStatusV1.ACTIVE,
        evaluation_contamination_status=(
            EvaluationContaminationStatusV1.CLEAN
        ),
        paired_effect_observation_ids=(
            "effect-observation-1",
        ),
        known_harm_ids=(),
    )

    base = _record(module)
    record = replace(
        base,
        governance_state=future,
        relations=(_review_future_verified_relation(),),
        record_content_sha256=None,
        canonical_record_sha256=None,
    )

    _review_validate_schema_payload(
        RECORD_SCHEMA,
        record.to_dict(),
    )


def test_task11_assembly_schema_rejects_future_verified_relation():
    module = _load_target()
    payload = _assembly_input(
        module,
        (_experience(),),
    ).to_dict()

    payload["relations"] = [
        _review_future_verified_relation().to_dict()
    ]

    with pytest.raises(ValueError):
        _review_validate_schema_payload(
            ASSEMBLY_SCHEMA,
            payload,
        )


def test_task11_parent_directory_fsync_failure_is_fail_closed_and_write_once(
    tmp_path,
    monkeypatch,
):
    module = _load_target()
    materializer = _load_materializer()

    experience = _experience()
    assembly = _assembly_input(
        module,
        (experience,),
    )

    source = tmp_path / "source.json"
    registration = tmp_path / "registration.json"

    source.write_bytes(experience.canonical_bytes())
    registration.write_bytes(assembly.canonical_bytes())

    expected = module.build_procedural_failure_memory_record_v1(
        assembly_input=assembly,
        assembly_registration_binding=_registration_binding(
            module,
            assembly,
        ),
        source_experiences=(experience,),
        previous_record=None,
    )

    output = tmp_path / (
        f"{assembly.lineage.memory_lineage_id}."
        f"v{assembly.lineage.record_version}.json"
    )

    real_fsync = materializer.os.fsync
    calls = {"count": 0}

    def injected_fsync(fd):
        calls["count"] += 1

        if calls["count"] == 2:
            raise OSError(
                "INJECTED_PARENT_DIRECTORY_FSYNC_FAILURE"
            )

        return real_fsync(fd)

    monkeypatch.setattr(
        materializer.os,
        "fsync",
        injected_fsync,
    )

    with pytest.raises(
        OSError,
        match="INJECTED_PARENT_DIRECTORY_FSYNC_FAILURE",
    ):
        materializer.materialize_files_v1(
            source_experience_paths=(source,),
            assembly_registration_path=registration,
            previous_record_path=None,
            output_path=output,
        )

    assert output.is_file()
    assert output.read_bytes() == expected.canonical_bytes()

    monkeypatch.setattr(
        materializer.os,
        "fsync",
        real_fsync,
    )

    with pytest.raises(FileExistsError):
        materializer.materialize_files_v1(
            source_experience_paths=(source,),
            assembly_registration_path=registration,
            previous_record_path=None,
            output_path=output,
        )

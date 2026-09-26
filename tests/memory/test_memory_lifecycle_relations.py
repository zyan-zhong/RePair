from __future__ import annotations

from dataclasses import replace
import importlib
import importlib.util

import pytest

from pchsi.memory.procedural_record import (
    MemoryAuthorityTypeV1,
    MemoryEvidenceRefV1,
)


TARGET = "pchsi.memory.lifecycle_relations"


def _load_target():
    try:
        spec = importlib.util.find_spec(TARGET)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        pytest.fail("TASK9_RED_MISSING_LIFECYCLE_RELATIONS")
    return importlib.import_module(TARGET)


def _ref(kind="UNIT2_SOURCE_RECORD"):
    return MemoryEvidenceRefV1(
        source_kind=kind,
        source_id="source-1",
        source_sha256="a" * 64,
    )


def _target(module, kind=None):
    if kind is None:
        kind = module.MemoryRelationTargetKindV1.SEQUENCE_EXPERIENCE
    target_id = (
        "1" * 64
        if kind in {
            module.MemoryRelationTargetKindV1.SEQUENCE_EXPERIENCE,
            module.MemoryRelationTargetKindV1.MEMORY_LINEAGE,
            module.MemoryRelationTargetKindV1.MEMORY_RECORD,
        }
        else "target-1"
    )
    return module.MemoryRelationTargetV1(
        target_kind=kind,
        target_id=target_id,
        target_canonical_record_sha256=(
            "b" * 64
            if kind is module.MemoryRelationTargetKindV1.MEMORY_RECORD
            else None
        ),
    )


def test_task9_symbols_exist() -> None:
    module = _load_target()
    for name in (
        "MemoryGovernanceStateV1",
        "initial_memory_governance_state_v1",
        "validate_unit3_initial_governance_state_v1",
        "MemoryRelationTypeV1",
        "MemoryRelationTargetKindV1",
        "MemoryRelationTargetV1",
        "MemoryRelationVerificationStateV1",
        "MemoryRelationV1",
        "validate_initial_relation_set_v1",
    ):
        assert hasattr(module, name)


def test_task9_full_governance_vocabulary_is_representable() -> None:
    module = _load_target()
    state = module.MemoryGovernanceStateV1(
        factual_binding_status=(
            module.FactualBindingStatusV1.BOUND_TO_CODE_APPROVED_UNIT2_OBJECT
        ),
        source_integrity=module.SourceIntegrityStatusV1.VERIFIED,
        descriptive_eligibility=(
            module.DescriptiveEligibilityStatusV1
            .RETRIEVAL_ELIGIBLE_DESCRIPTIVE
        ),
        repair_validity=module.RepairValidityStatusV1.EXECUTABLE,
        effect_status=module.EffectStatusV1.POSITIVE,
        effect_evidence_scope=module.EffectEvidenceScopeV1.SOURCE_STATE_PAIRED,
        access_scope=module.AccessScopeV1.SAME_TASK_DEV_ALLOWED,
        lifecycle_status=module.LifecycleStatusV1.ACTIVE,
        evaluation_contamination_status=(
            module.EvaluationContaminationStatusV1.CLEAN
        ),
        paired_effect_observation_ids=("effect-1",),
        known_harm_ids=(),
    )
    assert module.MemoryGovernanceStateV1.from_dict(state.to_dict()) == state


def test_task9_unit3_initial_governance_gate_is_exact() -> None:
    module = _load_target()
    initial = module.initial_memory_governance_state_v1()
    module.validate_unit3_initial_governance_state_v1(initial)

    assert initial.source_integrity is module.SourceIntegrityStatusV1.NOT_EVALUATED
    assert initial.effect_status is module.EffectStatusV1.UNTESTED
    assert initial.access_scope is module.AccessScopeV1.STAGING_ONLY

    with pytest.raises(ValueError):
        module.validate_unit3_initial_governance_state_v1(
            replace(
                initial,
                effect_status=module.EffectStatusV1.POSITIVE,
            )
        )

    with pytest.raises(ValueError):
        module.validate_unit3_initial_governance_state_v1(
            replace(initial, paired_effect_observation_ids=("effect-1",))
        )


def test_task9_memory_record_target_requires_exact_canonical_sha() -> None:
    module = _load_target()

    with pytest.raises(ValueError):
        module.MemoryRelationTargetV1(
            target_kind=module.MemoryRelationTargetKindV1.MEMORY_RECORD,
            target_id="record-1",
            target_canonical_record_sha256=None,
        )

    with pytest.raises(ValueError):
        module.MemoryRelationTargetV1(
            target_kind=module.MemoryRelationTargetKindV1.MEMORY_RECORD,
            target_id="record-1",
            target_canonical_record_sha256="BAD",
        )

    value = _target(module, module.MemoryRelationTargetKindV1.MEMORY_RECORD)
    assert module.MemoryRelationTargetV1.from_dict(value.to_dict()) == value

    with pytest.raises(ValueError):
        module.MemoryRelationTargetV1(
            target_kind=module.MemoryRelationTargetKindV1.MEMORY_LINEAGE,
            target_id="1" * 64,
            target_canonical_record_sha256="b" * 64,
        )


def test_task9_deterministic_derived_from_round_trips() -> None:
    module = _load_target()
    relation = module.MemoryRelationV1(
        relation_id="REL-1",
        relation_type=module.MemoryRelationTypeV1.DERIVED_FROM,
        source_memory_lineage_id="1" * 64,
        target=_target(module),
        authority_type=MemoryAuthorityTypeV1.FACT_AUTHORITY,
        origin_role="DETERMINISTIC_BUILDER",
        source_refs=(_ref(),),
        verification_state=(
            module.MemoryRelationVerificationStateV1.DETERMINISTIC
        ),
        created_version=1,
    )
    assert module.MemoryRelationV1.from_dict(relation.to_dict()) == relation
    module.validate_initial_relation_set_v1((relation,))


def test_task9_semantic_relation_cannot_claim_deterministic() -> None:
    module = _load_target()
    with pytest.raises(ValueError):
        module.MemoryRelationV1(
            relation_id="REL-1",
            relation_type=module.MemoryRelationTypeV1.SUPPORTS,
            source_memory_lineage_id="1" * 64,
            target=_target(module),
            authority_type=MemoryAuthorityTypeV1.SEMANTIC_HYPOTHESIS,
            origin_role="REGISTERED",
            source_refs=(_ref(),),
            verification_state=(
                module.MemoryRelationVerificationStateV1.DETERMINISTIC
            ),
            created_version=1,
        )


def test_task9_supersedes_requires_governance_evidence() -> None:
    module = _load_target()
    with pytest.raises(ValueError):
        module.MemoryRelationV1(
            relation_id="REL-S",
            relation_type=module.MemoryRelationTypeV1.SUPERSEDES,
            source_memory_lineage_id="1" * 64,
            target=_target(module, module.MemoryRelationTargetKindV1.MEMORY_RECORD),
            authority_type=MemoryAuthorityTypeV1.GOVERNANCE_AUTHORITY,
            origin_role="GOVERNANCE",
            source_refs=(_ref(),),
            verification_state=(
                module.MemoryRelationVerificationStateV1.REGISTERED_UNVERIFIED
            ),
            created_version=2,
        )

    relation = module.MemoryRelationV1(
        relation_id="REL-S",
        relation_type=module.MemoryRelationTypeV1.SUPERSEDES,
        source_memory_lineage_id="1" * 64,
        target=_target(module, module.MemoryRelationTargetKindV1.MEMORY_RECORD),
        authority_type=MemoryAuthorityTypeV1.GOVERNANCE_AUTHORITY,
        origin_role="GOVERNANCE",
        source_refs=(_ref("GOVERNANCE_ARTIFACT"),),
        verification_state=(
            module.MemoryRelationVerificationStateV1.REGISTERED_UNVERIFIED
        ),
        created_version=2,
    )
    module.validate_initial_relation_set_v1((relation,))


def test_task9_future_relations_are_representable_but_initially_forbidden() -> None:
    module = _load_target()
    verified = module.MemoryRelationV1(
        relation_id="REL-V",
        relation_type=module.MemoryRelationTypeV1.VERIFIED_BY,
        source_memory_lineage_id="1" * 64,
        target=_target(module, module.MemoryRelationTargetKindV1.REGISTERED_ARTIFACT),
        authority_type=MemoryAuthorityTypeV1.EFFECT_EVIDENCE,
        origin_role="EFFECT_VERIFIER",
        source_refs=(_ref("GOVERNANCE_ARTIFACT"),),
        verification_state=(
            module.MemoryRelationVerificationStateV1.EFFECT_VERIFIED
        ),
        created_version=2,
    )
    assert module.MemoryRelationV1.from_dict(verified.to_dict()) == verified
    with pytest.raises(ValueError):
        module.validate_initial_relation_set_v1((verified,))

    harmful = module.MemoryRelationV1(
        relation_id="REL-H",
        relation_type=module.MemoryRelationTypeV1.HARMFUL_UNDER,
        source_memory_lineage_id="1" * 64,
        target=_target(module, module.MemoryRelationTargetKindV1.REGISTERED_ARTIFACT),
        authority_type=MemoryAuthorityTypeV1.EFFECT_EVIDENCE,
        origin_role="HARM_VERIFIER",
        source_refs=(_ref("GOVERNANCE_ARTIFACT"),),
        verification_state=(
            module.MemoryRelationVerificationStateV1.HARM_VERIFIED
        ),
        created_version=2,
    )
    assert module.MemoryRelationV1.from_dict(harmful.to_dict()) == harmful
    with pytest.raises(ValueError):
        module.validate_initial_relation_set_v1((harmful,))


def test_task9_duplicate_relation_ids_fail_initial_gate() -> None:
    module = _load_target()
    relation = module.MemoryRelationV1(
        relation_id="REL-1",
        relation_type=module.MemoryRelationTypeV1.DERIVED_FROM,
        source_memory_lineage_id="1" * 64,
        target=_target(module),
        authority_type=MemoryAuthorityTypeV1.FACT_AUTHORITY,
        origin_role="DETERMINISTIC_BUILDER",
        source_refs=(_ref(),),
        verification_state=(
            module.MemoryRelationVerificationStateV1.DETERMINISTIC
        ),
        created_version=1,
    )
    with pytest.raises(ValueError):
        module.validate_initial_relation_set_v1((relation, relation))


def test_task9_relation_order_is_preserved() -> None:
    module = _load_target()

    def rel(rid):
        return module.MemoryRelationV1(
            relation_id=rid,
            relation_type=module.MemoryRelationTypeV1.DERIVED_FROM,
            source_memory_lineage_id="1" * 64,
            target=_target(module),
            authority_type=MemoryAuthorityTypeV1.FACT_AUTHORITY,
            origin_role="DETERMINISTIC_BUILDER",
            source_refs=(_ref(),),
            verification_state=(
                module.MemoryRelationVerificationStateV1.DETERMINISTIC
            ),
            created_version=1,
        )

    values = (rel("REL-2"), rel("REL-1"))
    module.validate_initial_relation_set_v1(values)
    assert tuple(item.relation_id for item in values) == ("REL-2", "REL-1")


def test_task9_has_no_automatic_relation_generation_api() -> None:
    module = _load_target()
    forbidden = {
        "cluster",
        "infer_relations",
        "auto_relations",
        "similarity_graph",
    }
    assert forbidden.isdisjoint(set(dir(module)))

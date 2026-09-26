from __future__ import annotations

import importlib
import importlib.util

import pytest

from pchsi.memory.procedural_record import (
    MemoryAuthorityTypeV1,
    MemoryEvidenceRefV1,
)


TARGET = "pchsi.memory.semantic_recovery"


def _load_target():
    try:
        spec = importlib.util.find_spec(TARGET)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        pytest.fail("TASK8_RED_MISSING_SEMANTIC_RECOVERY")
    return importlib.import_module(TARGET)


def _source_ref():
    return MemoryEvidenceRefV1(
        source_kind="UNIT2_SOURCE_RECORD",
        source_id="source-1",
        source_sha256="a" * 64,
    )


def test_task8_symbols_exist() -> None:
    module = _load_target()
    for name in (
        "SemanticAnnotationTypeV1",
        "SemanticConfidenceV1",
        "SemanticHypothesisAnnotationV1",
        "ObservedRecoveryBindingV1",
        "ProposedRecoveryV1",
    ):
        assert hasattr(module, name)


def test_task8_semantic_hypothesis_is_typed_and_optional_by_contract() -> None:
    module = _load_target()
    annotation = module.SemanticHypothesisAnnotationV1(
        annotation_id="ANN-1",
        annotation_type=module.SemanticAnnotationTypeV1.CANDIDATE_MECHANISM,
        authority_type=MemoryAuthorityTypeV1.SEMANTIC_HYPOTHESIS,
        text="candidate explanation only",
        supporting_refs=(_source_ref(),),
        counterevidence_refs=(),
        semantic_confidence=module.SemanticConfidenceV1.LOW,
        origin_role="HUMAN_REGISTERED",
        origin_identity="reviewer-1",
        origin_artifact_ref=MemoryEvidenceRefV1(
            source_kind="SEMANTIC_ANNOTATION_ARTIFACT",
            source_id="ANN-1",
            source_sha256="b" * 64,
        ),
    )
    assert (
        module.SemanticHypothesisAnnotationV1.from_dict(annotation.to_dict())
        == annotation
    )


def test_task8_semantic_fact_authority_is_rejected() -> None:
    module = _load_target()
    with pytest.raises(ValueError):
        module.SemanticHypothesisAnnotationV1(
            annotation_id="ANN-1",
            annotation_type=module.SemanticAnnotationTypeV1.CANDIDATE_MECHANISM,
            authority_type=MemoryAuthorityTypeV1.FACT_AUTHORITY,
            text="bad promotion",
            supporting_refs=(),
            counterevidence_refs=(),
            semantic_confidence=module.SemanticConfidenceV1.UNSPECIFIED,
            origin_role="X",
            origin_identity="X",
            origin_artifact_ref=MemoryEvidenceRefV1(
                source_kind="SEMANTIC_ANNOTATION_ARTIFACT",
                source_id="ANN-1",
                source_sha256="b" * 64,
            ),
        )


def test_task8_semantic_origin_artifact_type_and_id_are_exact() -> None:
    module = _load_target()
    base = {
        "annotation_id": "ANN-1",
        "annotation_type": "CANDIDATE_MECHANISM",
        "authority_type": "SEMANTIC_HYPOTHESIS",
        "text": "candidate",
        "supporting_refs": [],
        "counterevidence_refs": [],
        "semantic_confidence": "UNSPECIFIED",
        "origin_role": "X",
        "origin_identity": "X",
        "origin_artifact_ref": {
            "source_kind": "RECOVERY_PROPOSAL_ARTIFACT",
            "source_id": "ANN-1",
            "source_sha256": "b" * 64,
        },
    }
    with pytest.raises(ValueError):
        module.SemanticHypothesisAnnotationV1.from_dict(base)

    base["origin_artifact_ref"]["source_kind"] = "SEMANTIC_ANNOTATION_ARTIFACT"
    base["origin_artifact_ref"]["source_id"] = "OTHER"
    with pytest.raises(ValueError):
        module.SemanticHypothesisAnnotationV1.from_dict(base)


def test_task8_observed_recovery_is_registered_boundary_not_fact() -> None:
    module = _load_target()
    value = module.ObservedRecoveryBindingV1(
        authority_type=MemoryAuthorityTypeV1.REGISTERED_BOUNDARY,
        source_experience_id="1" * 64,
        registered_recovery_start_model_call_index=4,
        registered_recovery_final_model_call_index=6,
        source_refs=(_source_ref(),),
    )
    assert module.ObservedRecoveryBindingV1.from_dict(value.to_dict()) == value

    with pytest.raises(ValueError):
        module.ObservedRecoveryBindingV1(
            authority_type=MemoryAuthorityTypeV1.FACT_AUTHORITY,
            source_experience_id="1" * 64,
            registered_recovery_start_model_call_index=4,
            registered_recovery_final_model_call_index=6,
            source_refs=(_source_ref(),),
        )


def test_task8_observed_recovery_rejects_reversed_range() -> None:
    module = _load_target()
    with pytest.raises(ValueError):
        module.ObservedRecoveryBindingV1(
            authority_type=MemoryAuthorityTypeV1.REGISTERED_BOUNDARY,
            source_experience_id="1" * 64,
            registered_recovery_start_model_call_index=7,
            registered_recovery_final_model_call_index=6,
            source_refs=(_source_ref(),),
        )


def test_task8_recovery_proposal_preserves_order_and_authority() -> None:
    module = _load_target()
    proposal = module.ProposedRecoveryV1(
        proposal_id="REC-1",
        authority_type=MemoryAuthorityTypeV1.RECOVERY_PROPOSAL,
        procedure_steps=("inspect state", "revalidate", "continue"),
        source_refs=(_source_ref(),),
        origin_role="HUMAN_REGISTERED",
        origin_identity="reviewer-1",
        origin_artifact_ref=MemoryEvidenceRefV1(
            source_kind="RECOVERY_PROPOSAL_ARTIFACT",
            source_id="REC-1",
            source_sha256="c" * 64,
        ),
    )
    rebuilt = module.ProposedRecoveryV1.from_dict(proposal.to_dict())
    assert rebuilt.procedure_steps == proposal.procedure_steps

    with pytest.raises(ValueError):
        module.ProposedRecoveryV1(
            proposal_id="REC-1",
            authority_type=MemoryAuthorityTypeV1.EFFECT_EVIDENCE,
            procedure_steps=("x",),
            source_refs=(_source_ref(),),
            origin_role="X",
            origin_identity="X",
            origin_artifact_ref=proposal.origin_artifact_ref,
        )


def test_task8_recovery_origin_artifact_is_exact() -> None:
    module = _load_target()
    with pytest.raises(ValueError):
        module.ProposedRecoveryV1(
            proposal_id="REC-1",
            authority_type=MemoryAuthorityTypeV1.RECOVERY_PROPOSAL,
            procedure_steps=("x",),
            source_refs=(_source_ref(),),
            origin_role="X",
            origin_identity="X",
            origin_artifact_ref=MemoryEvidenceRefV1(
                source_kind="SEMANTIC_ANNOTATION_ARTIFACT",
                source_id="REC-1",
                source_sha256="c" * 64,
            ),
        )


def test_task8_recovery_proposal_rejects_empty_steps() -> None:
    module = _load_target()
    with pytest.raises(ValueError):
        module.ProposedRecoveryV1(
            proposal_id="REC-1",
            authority_type=MemoryAuthorityTypeV1.RECOVERY_PROPOSAL,
            procedure_steps=(),
            source_refs=(_source_ref(),),
            origin_role="X",
            origin_identity="X",
            origin_artifact_ref=MemoryEvidenceRefV1(
                source_kind="RECOVERY_PROPOSAL_ARTIFACT",
                source_id="REC-1",
                source_sha256="c" * 64,
            ),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("verified_recovery", True),
        ("beneficial", True),
        ("correct_action", "look"),
        ("repair_validity", "VERIFIED"),
    ],
)
def test_task8_future_authority_fields_are_rejected(field, value) -> None:
    module = _load_target()
    proposal = module.ProposedRecoveryV1(
        proposal_id="REC-1",
        authority_type=MemoryAuthorityTypeV1.RECOVERY_PROPOSAL,
        procedure_steps=("x",),
        source_refs=(_source_ref(),),
        origin_role="X",
        origin_identity="X",
        origin_artifact_ref=MemoryEvidenceRefV1(
            source_kind="RECOVERY_PROPOSAL_ARTIFACT",
            source_id="REC-1",
            source_sha256="c" * 64,
        ),
    )
    payload = proposal.to_dict()
    payload[field] = value
    with pytest.raises(ValueError):
        module.ProposedRecoveryV1.from_dict(payload)


def test_task8_has_no_analyzer_or_model_api() -> None:
    module = _load_target()
    forbidden = {
        "analyze",
        "call_model",
        "retrieve",
        "infer_mechanism",
        "generate_recovery",
    }
    assert forbidden.isdisjoint(set(dir(module)))

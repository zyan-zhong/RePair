from __future__ import annotations

import importlib
import importlib.util

import pytest

from pchsi.memory.procedural_record import (
    MemoryAuthorityTypeV1,
    MemoryEvidenceRefV1,
)


TARGET = "pchsi.memory.applicability"


def _load_target():
    try:
        spec = importlib.util.find_spec(TARGET)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        pytest.fail("TASK7_RED_MISSING_APPLICABILITY")
    return importlib.import_module(TARGET)


def _evidence():
    return MemoryEvidenceRefV1(
        source_kind="UNIT2_SOURCE_RECORD",
        source_id="source-1",
        source_sha256="a" * 64,
    )


def _clause(module, kind, *, rid="BOUNDARY-1", source_kind=None):
    if source_kind is None:
        source_kind = "REGISTERED_BOUNDARY_ARTIFACT"
    return module.MemoryBoundaryClauseV1(
        boundary_type=kind,
        boundary_authority=MemoryAuthorityTypeV1.REGISTERED_BOUNDARY,
        origin_role="HUMAN_REGISTERED",
        registration_id=rid,
        origin_artifact_ref=MemoryEvidenceRefV1(
            source_kind=source_kind,
            source_id=rid,
            source_sha256="b" * 64,
        ),
        condition_text=f"condition:{kind.value}",
        source_refs=(_evidence(),),
        verification_status=(
            module.BoundaryVerificationStatusV1.REGISTERED_UNVERIFIED
        ),
    )


def _valid_set(module):
    return module.ApplicabilityBoundarySetV1(
        activation=(_clause(module, module.BoundaryTypeV1.ACTIVATION),),
        continuation=(),
        revalidation_requirement=(
            module.RevalidationRequirementV1.NOT_REQUIRED
        ),
        revalidation=(),
        release=(_clause(module, module.BoundaryTypeV1.RELEASE),),
        termination=(),
        non_applicability_disposition=(
            module.NonApplicabilityDispositionV1
            .UNRESOLVED_NO_REGISTERED_CONDITION
        ),
        non_applicability=(),
        policy_visible_state_change_trigger=(),
    )


def test_task7_symbols_exist() -> None:
    module = _load_target()
    for name in (
        "BoundaryTypeV1",
        "BoundaryVerificationStatusV1",
        "RevalidationRequirementV1",
        "NonApplicabilityDispositionV1",
        "MemoryBoundaryClauseV1",
        "ApplicabilityBoundarySetV1",
    ):
        assert hasattr(module, name)


def test_task7_valid_boundary_set_round_trips() -> None:
    module = _load_target()
    value = _valid_set(module)
    assert module.ApplicabilityBoundarySetV1.from_dict(value.to_dict()) == value


def test_task7_activation_is_required() -> None:
    module = _load_target()
    value = _valid_set(module).to_dict()
    value["activation"] = []
    with pytest.raises(ValueError):
        module.ApplicabilityBoundarySetV1.from_dict(value)


def test_task7_release_or_termination_is_required() -> None:
    module = _load_target()
    value = _valid_set(module).to_dict()
    value["release"] = []
    value["termination"] = []
    with pytest.raises(ValueError):
        module.ApplicabilityBoundarySetV1.from_dict(value)


def test_task7_boundary_authority_and_origin_are_typed() -> None:
    module = _load_target()
    with pytest.raises(ValueError):
        module.MemoryBoundaryClauseV1(
            boundary_type=module.BoundaryTypeV1.ACTIVATION,
            boundary_authority=MemoryAuthorityTypeV1.SEMANTIC_HYPOTHESIS,
            origin_role="X",
            registration_id="BOUNDARY-1",
            origin_artifact_ref=MemoryEvidenceRefV1(
                source_kind="REGISTERED_BOUNDARY_ARTIFACT",
                source_id="BOUNDARY-1",
                source_sha256="b" * 64,
            ),
            condition_text="x",
            source_refs=(_evidence(),),
            verification_status=(
                module.BoundaryVerificationStatusV1.REGISTERED_UNVERIFIED
            ),
        )

    with pytest.raises(ValueError):
        _clause(
            module,
            module.BoundaryTypeV1.ACTIVATION,
            source_kind="SEMANTIC_ANNOTATION_ARTIFACT",
        )

    good = _clause(module, module.BoundaryTypeV1.ACTIVATION)
    payload = good.to_dict()
    payload["origin_artifact_ref"]["source_id"] = "DIFFERENT"
    with pytest.raises(ValueError):
        module.MemoryBoundaryClauseV1.from_dict(payload)


def test_task7_boundary_tuple_type_is_not_repaired() -> None:
    module = _load_target()
    value = _valid_set(module).to_dict()
    value["activation"] = [
        _clause(module, module.BoundaryTypeV1.RELEASE).to_dict()
    ]
    with pytest.raises(ValueError):
        module.ApplicabilityBoundarySetV1.from_dict(value)


def test_task7_required_revalidation_requires_clause() -> None:
    module = _load_target()
    value = _valid_set(module).to_dict()
    value["revalidation_requirement"] = "REQUIRED"
    value["revalidation"] = []
    with pytest.raises(ValueError):
        module.ApplicabilityBoundarySetV1.from_dict(value)


def test_task7_unresolved_revalidation_is_representable() -> None:
    module = _load_target()
    value = _valid_set(module).to_dict()
    value["revalidation_requirement"] = "UNRESOLVED"
    rebuilt = module.ApplicabilityBoundarySetV1.from_dict(value)
    assert (
        rebuilt.revalidation_requirement
        is module.RevalidationRequirementV1.UNRESOLVED
    )


def test_task7_non_applicability_disposition_is_fail_closed() -> None:
    module = _load_target()
    value = _valid_set(module).to_dict()
    value["non_applicability_disposition"] = "REGISTERED_CONDITIONS"
    value["non_applicability"] = []
    with pytest.raises(ValueError):
        module.ApplicabilityBoundarySetV1.from_dict(value)

    value = _valid_set(module).to_dict()
    value["non_applicability"] = [
        _clause(module, module.BoundaryTypeV1.NON_APPLICABILITY).to_dict()
    ]
    with pytest.raises(ValueError):
        module.ApplicabilityBoundarySetV1.from_dict(value)


def test_task7_state_change_trigger_round_trips() -> None:
    module = _load_target()
    value = _valid_set(module).to_dict()
    value["policy_visible_state_change_trigger"] = [
        _clause(
            module,
            module.BoundaryTypeV1.POLICY_VISIBLE_STATE_CHANGE_TRIGGER,
        ).to_dict()
    ]
    rebuilt = module.ApplicabilityBoundarySetV1.from_dict(value)
    assert len(rebuilt.policy_visible_state_change_trigger) == 1


def test_task7_has_no_online_matching_api() -> None:
    module = _load_target()
    forbidden = {
        "is_applicable",
        "match_current_state",
        "evaluate_current_state",
        "retrieve_applicable",
    }
    assert forbidden.isdisjoint(set(dir(module)))

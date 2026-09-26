from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib
import importlib.util
from pathlib import Path

import pytest

from pchsi.evaluation.canonical_evidence import strict_json_loads
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
from pchsi.memory.procedural_record import (
    MemoryAuthorityTypeV1,
    MemoryEvidenceRefV1,
)
from pchsi.memory.semantic_recovery import (
    ProposedRecoveryV1,
    SemanticAnnotationTypeV1,
    SemanticConfidenceV1,
    SemanticHypothesisAnnotationV1,
)


TARGET = "pchsi.memory.retrieval_key"
SCHEMA = Path(
    "configs/memory/schemas/memory_retrieval_key_v1.json"
)


def _load_target():
    try:
        spec = importlib.util.find_spec(TARGET)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        pytest.fail("UNIT4_TASK2_RED_MISSING_RETRIEVAL_KEY")
    return importlib.import_module(TARGET)


def _helpers():
    path = Path("tests/memory/test_procedural_memory_builder.py")
    spec = importlib.util.spec_from_file_location(
        "_unit4_task2_helpers",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _generic_ref(
    kind="UNIT2_SOURCE_RECORD",
    sid="source-1",
    char="a",
):
    return MemoryEvidenceRefV1(
        source_kind=kind,
        source_id=sid,
        source_sha256=char * 64,
    )


def _annotation(
    kind: SemanticAnnotationTypeV1,
    text: str,
    *,
    aid: str,
):
    return SemanticHypothesisAnnotationV1(
        annotation_id=aid,
        annotation_type=kind,
        authority_type=MemoryAuthorityTypeV1.SEMANTIC_HYPOTHESIS,
        text=text,
        supporting_refs=(_generic_ref(),),
        counterevidence_refs=(),
        semantic_confidence=SemanticConfidenceV1.LOW,
        origin_role="HUMAN",
        origin_identity="reviewer",
        origin_artifact_ref=_generic_ref(
            "SEMANTIC_ANNOTATION_ARTIFACT",
            aid,
            "c",
        ),
    )


def _proposal(step="revalidate visible state"):
    return ProposedRecoveryV1(
        proposal_id="PROP-UNIT4-1",
        authority_type=MemoryAuthorityTypeV1.RECOVERY_PROPOSAL,
        procedure_steps=(step,),
        source_refs=(_generic_ref(),),
        origin_role="ANALYZER",
        origin_identity="analyzer-v1",
        origin_artifact_ref=_generic_ref(
            "RECOVERY_PROPOSAL_ARTIFACT",
            "PROP-UNIT4-1",
            "d",
        ),
    )


def _boundary(kind, rid, text):
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
        condition_text=text,
        source_refs=(_generic_ref(),),
        verification_status=(
            BoundaryVerificationStatusV1.REGISTERED_UNVERIFIED
        ),
    )


def _record_with_semantics(
    *,
    activation="activation line",
    continuation="continuation line",
    state_change="state change line",
    annotations=(),
    recoveries=(),
):
    helpers = _helpers()
    builder = helpers._load_target()
    experience = helpers._experience()
    applicability = ApplicabilityBoundarySetV1(
        activation=(
            _boundary(
                BoundaryTypeV1.ACTIVATION,
                "ACT-UNIT4",
                activation,
            ),
        ),
        continuation=(
            _boundary(
                BoundaryTypeV1.CONTINUATION,
                "CONT-UNIT4",
                continuation,
            ),
        ),
        revalidation_requirement=RevalidationRequirementV1.NOT_REQUIRED,
        revalidation=(),
        release=(
            _boundary(
                BoundaryTypeV1.RELEASE,
                "REL-UNIT4",
                "release line",
            ),
        ),
        termination=(),
        non_applicability_disposition=(
            NonApplicabilityDispositionV1
            .UNRESOLVED_NO_REGISTERED_CONDITION
        ),
        non_applicability=(),
        policy_visible_state_change_trigger=(
            _boundary(
                BoundaryTypeV1.POLICY_VISIBLE_STATE_CHANGE_TRIGGER,
                "STATE-UNIT4",
                state_change,
            ),
        ),
    )
    assembly = helpers._assembly_input(
        builder,
        (experience,),
        semantic=tuple(annotations),
        recoveries=tuple(recoveries),
    )
    assembly = replace(assembly, applicability=applicability)
    return builder.build_procedural_failure_memory_record_v1(
        assembly_input=assembly,
        assembly_registration_binding=helpers._registration_binding(
            builder,
            assembly,
        ),
        source_experiences=(experience,),
        previous_record=None,
    )


def test_task2_deterministic_key_and_schema() -> None:
    module = _load_target()
    record = _record_with_semantics(
        annotations=(
            _annotation(
                SemanticAnnotationTypeV1.CANDIDATE_MECHANISM,
                "candidate mechanism",
                aid="ANN-1",
            ),
            _annotation(
                SemanticAnnotationTypeV1.CAPABILITY_COMPONENT,
                "progress tracking",
                aid="ANN-2",
            ),
            _annotation(
                SemanticAnnotationTypeV1.TASK_FAMILY_HYPOTHESIS,
                "family-only hypothesis",
                aid="ANN-3",
            ),
            _annotation(
                SemanticAnnotationTypeV1.CRITICAL_REGION,
                "critical region",
                aid="ANN-4",
            ),
            _annotation(
                SemanticAnnotationTypeV1.ALTERNATIVE_EXPLANATION,
                "alternative explanation",
                aid="ANN-5",
            ),
        )
    )
    first = module.build_memory_retrieval_key_v1(record)
    second = module.build_memory_retrieval_key_v1(record)
    assert first.canonical_bytes() == second.canonical_bytes()
    assert (
        first.record_binding.canonical_record_sha256
        == record.canonical_record_sha256
    )
    assert (
        first.hard_filter_metadata.access_scope
        == record.governance_state.access_scope
    )
    assert first.scoring_payload.required_feedback_codes == ()
    assert first.scoring_payload.recent_action_repetition_signature == ()

    expected = "\n".join(
        (
            "activation line",
            "continuation line",
            "state change line",
            "SEMANTIC_HYPOTHESIS:CANDIDATE_MECHANISM:candidate mechanism",
            "SEMANTIC_HYPOTHESIS:CAPABILITY_COMPONENT:progress tracking",
            "SEMANTIC_HYPOTHESIS:CRITICAL_REGION:critical region",
        )
    )
    assert first.scoring_payload.semantic_retrieval_text == expected
    assert "family-only" not in expected
    assert "alternative explanation" not in expected

    schema = strict_json_loads(SCHEMA.read_bytes())
    validate_schema_definition(schema)
    _validate_payload_node(first.to_dict(), schema, "$")


def test_task2_hard_filters_never_change_scoring_hash() -> None:
    module = _load_target()
    record = _record_with_semantics()
    first = module.build_memory_retrieval_key_v1(record)

    from pchsi.memory.lifecycle_relations import (
        AccessScopeV1,
        LifecycleStatusV1,
    )
    future_governance = replace(
        record.governance_state,
        access_scope=AccessScopeV1.CROSS_TASK_ALLOWED,
        lifecycle_status=LifecycleStatusV1.ACTIVE,
    )
    changed = replace(
        record,
        governance_state=future_governance,
        record_content_sha256=None,
        canonical_record_sha256=None,
    )
    second = module.build_memory_retrieval_key_v1(changed)

    assert first.hard_filter_metadata != second.hard_filter_metadata
    assert first.scoring_payload == second.scoring_payload
    assert (
        first.scoring_payload_sha256
        == second.scoring_payload_sha256
    )


@pytest.mark.parametrize(
    ("text_kind", "text_value", "code"),
    [
        (
            "activation",
            "TASK_SYNTHETIC_001",
            "SOURCE_TASK_IDENTITY_EXPOSURE",
        ),
        (
            "activation",
            "ATTEMPT_SYNTHETIC_001",
            "SOURCE_ATTEMPT_IDENTITY_EXPOSURE",
        ),
        (
            "activation",
            "source_gamefile=/hidden/game.tw-pddl",
            "SOURCE_GAMEFILE_MARKER",
        ),
        (
            "activation",
            "source_seed=17",
            "SOURCE_SEED_MARKER",
        ),
        (
            "activation",
            "the correct action is go to cabinet 1",
            "ACTION_ORACLE_INSTRUCTION",
        ),
        (
            "activation",
            "oracle path goes through cabinet 1",
            "ORACLE_PATH_MARKER",
        ),
        (
            "activation",
            "effect_status=POSITIVE",
            "EFFECT_OR_PROMOTION_MARKER",
        ),
    ],
)
def test_task2_scoring_free_text_shortcuts_fail_closed(
    text_kind,
    text_value,
    code,
) -> None:
    module = _load_target()
    kwargs = {text_kind: text_value}
    record = _record_with_semantics(**kwargs)
    with pytest.raises(
        ValueError,
        match="RETRIEVAL_SCORING_PAYLOAD_UNSAFE:" + code,
    ):
        module.build_memory_retrieval_key_v1(record)


def test_task2_exact_recovery_line_is_not_allowed_in_scoring_text() -> None:
    module = _load_target()
    proposal = _proposal("revalidate visible state")
    record = _record_with_semantics(
        activation="revalidate visible state",
        recoveries=(proposal,),
    )
    with pytest.raises(
        ValueError,
        match="RECOVERY_PROCEDURE_EXPOSURE",
    ):
        module.build_memory_retrieval_key_v1(record)

    safe = _record_with_semantics(
        activation="revalidate the visible state before continuing",
        recoveries=(proposal,),
    )
    key = module.build_memory_retrieval_key_v1(safe)
    assert key.scoring_payload.semantic_retrieval_text.startswith(
        "revalidate the visible state"
    )


def test_task2_retrieval_payload_omits_forbidden_authority_fields() -> None:
    module = _load_target()
    record = _record_with_semantics(
        recoveries=(_proposal(),)
    )
    key = module.build_memory_retrieval_key_v1(record)
    wire = key.to_dict()
    scoring = wire["scoring_payload"]
    serialized = str(scoring)
    for forbidden in (
        "effect_status",
        "repair_validity",
        "known_harm_ids",
        "proposed_recoveries",
        "source_task_id",
        "source_attempt_id",
    ):
        assert forbidden not in serialized


def test_task2_parser_recomputes_scoring_payload_sha_and_rejects_unknown() -> None:
    module = _load_target()
    key = module.build_memory_retrieval_key_v1(
        _record_with_semantics()
    )
    payload = key.to_dict()
    payload["scoring_payload_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="sha256 mismatch"):
        module.MemoryRetrievalKeyV1.from_dict(payload)

    payload = key.to_dict()
    payload["future_field"] = 1
    with pytest.raises(ValueError, match="unknown"):
        module.MemoryRetrievalKeyV1.from_dict(payload)

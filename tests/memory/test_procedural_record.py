from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import importlib
import importlib.util

import pytest

from pchsi.evaluation.budget import BudgetState
from pchsi.memory import sequence_failure_experience as sequence_module


TARGET = "pchsi.memory.procedural_record"


def _load_target():
    try:
        spec = importlib.util.find_spec(TARGET)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        pytest.fail("TASK6_RED_MISSING_PROCEDURAL_RECORD")
    return importlib.import_module(TARGET)


def _group_id(relative: str, game_sha: str) -> str:
    return hashlib.sha256(
        (
            "ALFWORLD_TASK_GAMEFILE_GROUP_V1\0"
            + relative
            + "\0"
            + game_sha
        ).encode("utf-8")
    ).hexdigest()


def _pointer(member: str, index: int, a: str, b: str):
    return sequence_module.SourceRecordPointerV1(
        bundle_member_name=member,
        zero_based_line_index=index,
        exact_record_sha256=a * 64,
        whole_member_sha256=b * 64,
    )


def _experience(*, source_condition: str = "P4-R1-Q2-BAD-TRAIN17"):
    relative = (
        "train/pick_and_place_simple-Apple-None-CounterTop-1/"
        "trial_T2026/game.tw-pddl"
    )
    game_sha = "b" * 64

    binding = sequence_module.SequenceSourceTaskAccessBindingV1(
        schema_id="SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V1",
        schema_version=1,
        task_access_protected_manifest_sha256=(
            "260766366d72a9af7b0b4809d30a45bb"
            "56f42134dad66b29a4b61ff7ed4793ea"
        ),
        task_access_record_line_index=17,
        task_access_record_sha256="a" * 64,
        task_gamefile_group_id=_group_id(relative, game_sha),
        dataset_relative_gamefile=relative,
        gamefile_sha256=game_sha,
        task_type="pick_and_place_simple",
        split="train",
        access_class="TRAIN_MEMORY_SOURCE",
    )

    registration = sequence_module.RegisteredFailureSequenceWindowV1(
        schema_id="REGISTERED_FAILURE_SEQUENCE_WINDOW_V1",
        schema_version=1,
        registration_id="REGISTRATION_SYNTHETIC_001",
        registration_authority_type="REGISTERED_BOUNDARY_LABEL",
        registration_protocol_id="HUMAN_REGISTERED_RANGE_V1",
        registration_artifact_sha256="c" * 64,
        registration_record_sha256="d" * 64,
        source_bundle_sha256="e" * 64,
        source_attempt_id="ATTEMPT_SYNTHETIC_001",
        source_task_id="TASK_SYNTHETIC_001",
        source_round="ROUND1",
        source_condition=source_condition,
        relevant_start_model_call_index=2,
        registered_failure_onset_model_call_index=2,
        final_model_call_index=2,
        registered_recovery_start_model_call_index=None,
        registered_recovery_final_model_call_index=None,
    )

    event = sequence_module.SequenceFailureEventV1(
        model_call_index=2,
        execution_status="executed",
        attempt_outcome="ACTION_EXECUTED",
        parser_status="success",
        parser_error=None,
        literal_action="look",
        normalized_action="look",
        admissibility_status="exact_member",
        interface_feedback_before=None,
        policy_attempt_count_before=2,
        policy_attempt_count_after=3,
        environment_step_count_before=1,
        environment_step_count_after=2,
        protocol_failure_count_before=0,
        protocol_failure_count_after=0,
        inadmissible_action_count_before=0,
        inadmissible_action_count_after=0,
        consecutive_nonexecuted_attempt_count_before=0,
        consecutive_nonexecuted_attempt_count_after=0,
        pre_observation="You are in a room.",
        pre_observation_sha256="1" * 64,
        pre_admissible_commands=("look", "inventory"),
        pre_admissible_commands_sha256="2" * 64,
        raw_model_response='{"action":"look"}',
        raw_model_response_sha256="3" * 64,
        submitted_environment_action="look",
        resulting_observation="You see a countertop.",
        resulting_observation_sha256="4" * 64,
        resulting_admissible_commands=("look", "inventory"),
        resulting_admissible_commands_sha256="5" * 64,
        environment_step_index=1,
        score=0.0,
        done=False,
        won=False,
        visible_state_change_disposition="OBSERVATION_CHANGED",
        trace_source_pointer=_pointer(
            "action_traces.jsonl", 2, "6", "7"
        ),
        policy_call_source_pointer=_pointer(
            "policy_calls.jsonl", 2, "8", "9"
        ),
        public_transition_source_pointer=_pointer(
            "public_transitions.jsonl", 1, "a", "b"
        ),
    )

    relevant_start = sequence_module.SequenceFailureRelevantStartV1(
        model_call_index=2,
        public_task_goal="Put the apple on the countertop.",
        public_task_goal_sha256="c" * 64,
        observation="You are in a room.",
        observation_sha256="1" * 64,
        admissible_commands=("look", "inventory"),
        admissible_commands_sha256="2" * 64,
        interface_feedback_before=None,
        budget_state_before=BudgetState(
            policy_attempt_count=2,
            environment_step_count=1,
            protocol_failure_count=0,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        ),
        required_preceding_model_call_range=(0, 1),
        required_preceding_environment_step_indices=(0,),
        required_preceding_prefix_source_binding=(
            _pointer("policy_calls.jsonl", 0, "d", "9"),
            _pointer("policy_calls.jsonl", 1, "e", "9"),
        ),
    )

    observed_end = sequence_module.SequenceFailureObservedEndV1(
        model_call_index=2,
        budget_state_after=BudgetState(
            policy_attempt_count=3,
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

    return sequence_module.SequenceFailureExperienceV1(
        experience_id=None,
        schema_id="SEQUENCE_FAILURE_EXPERIENCE_V1",
        schema_version=1,
        source_round="ROUND1",
        source_condition=source_condition,
        source_task_id="TASK_SYNTHETIC_001",
        source_gamefile_group_id=binding.task_gamefile_group_id,
        source_bundle_sha256="e" * 64,
        source_attempt_id="ATTEMPT_SYNTHETIC_001",
        task_access_binding=binding,
        registration_binding=registration,
        relevant_start=relevant_start,
        observed_sequence=(event,),
        observed_end=observed_end,
        included_environment_step_indices=(1,),
        source_bundle_member_sha256=(
            ("attempt.json", "1" * 64),
            ("action_traces.jsonl", "7" * 64),
            ("policy_calls.jsonl", "9" * 64),
            ("public_transitions.jsonl", "b" * 64),
            ("SHA256SUMS", "f" * 64),
        ),
    )


def _registration_binding(module, *, rid="REG-PROC-001", sha="a" * 64):
    return module.AssemblyRegistrationBindingV1(
        schema_id="PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1",
        registration_id=rid,
        assembly_registration_sha256=sha,
        lineage_registration_ref=module.MemoryEvidenceRefV1(
            source_kind="PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1",
            source_id=rid,
            source_sha256=sha,
        ),
    )


def test_task6_symbols_exist() -> None:
    module = _load_target()
    for name in (
        "MemoryAuthorityTypeV1",
        "MemoryEvidenceRefV1",
        "FactualSequenceBindingV1",
        "AssemblyRegistrationBindingV1",
        "PreviousProceduralRecordBindingV1",
        "ProceduralMemoryLineageV1",
        "ProceduralMemoryProvenanceV1",
        "record_id_for_lineage_version_v1",
    ):
        assert hasattr(module, name)


def test_task6_evidence_ref_strict_validation() -> None:
    module = _load_target()

    good = module.MemoryEvidenceRefV1(
        source_kind="UNIT2_SOURCE_RECORD",
        source_id="source-1",
        source_sha256="a" * 64,
    )
    assert module.MemoryEvidenceRefV1.from_dict(good.to_dict()) == good

    with pytest.raises(ValueError):
        module.MemoryEvidenceRefV1(
            source_kind="UNKNOWN",
            source_id="source-1",
            source_sha256="a" * 64,
        )

    with pytest.raises(ValueError):
        module.MemoryEvidenceRefV1(
            source_kind="UNIT2_SOURCE_RECORD",
            source_id="bad\nid",
            source_sha256="a" * 64,
        )

    with pytest.raises(ValueError):
        module.MemoryEvidenceRefV1(
            source_kind="UNIT2_SOURCE_RECORD",
            source_id="source-1",
            source_sha256="A" * 64,
        )


def test_task6_factual_binding_is_exact_and_immutable() -> None:
    module = _load_target()
    experience = _experience()
    binding = module.FactualSequenceBindingV1.from_experience(experience)
    binding.validate_against(experience)

    assert (
        binding.canonical_experience_sha256
        == hashlib.sha256(experience.canonical_bytes()).hexdigest()
    )
    assert module.FactualSequenceBindingV1.from_dict(binding.to_dict()) == binding

    with pytest.raises((FrozenInstanceError, AttributeError)):
        binding.source_task_id = "mutated"  # type: ignore[misc]


def test_task6_factual_binding_rejects_wrong_authority() -> None:
    module = _load_target()
    experience = _experience()
    binding = module.FactualSequenceBindingV1.from_experience(experience)

    with pytest.raises(ValueError):
        module.FactualSequenceBindingV1(
            authority_type=module.MemoryAuthorityTypeV1.SEMANTIC_HYPOTHESIS,
            experience_id=binding.experience_id,
            canonical_experience_sha256=binding.canonical_experience_sha256,
            source_bundle_sha256=binding.source_bundle_sha256,
            source_attempt_id=binding.source_attempt_id,
            source_task_id=binding.source_task_id,
        )


def test_task6_assembly_registration_binding_has_single_exact_identity() -> None:
    module = _load_target()
    binding = _registration_binding(module)
    assert (
        module.AssemblyRegistrationBindingV1.from_dict(binding.to_dict())
        == binding
    )

    payload = binding.to_dict()
    payload["registration_id"] = "DIFFERENT"
    with pytest.raises(ValueError):
        module.AssemblyRegistrationBindingV1.from_dict(payload)

    payload = binding.to_dict()
    payload["assembly_registration_sha256"] = "b" * 64
    with pytest.raises(ValueError):
        module.AssemblyRegistrationBindingV1.from_dict(payload)


def test_task6_lineage_version_chain_is_consecutive_and_same_lineage() -> None:
    module = _load_target()
    lineage_id = "1" * 64
    v1 = module.ProceduralMemoryLineageV1(
        memory_lineage_id=lineage_id,
        record_version=1,
        previous_record_binding=None,
    )
    assert module.ProceduralMemoryLineageV1.from_dict(v1.to_dict()) == v1

    previous = module.PreviousProceduralRecordBindingV1(
        memory_lineage_id=lineage_id,
        record_version=1,
        canonical_record_sha256="2" * 64,
    )
    v2 = module.ProceduralMemoryLineageV1(
        memory_lineage_id=lineage_id,
        record_version=2,
        previous_record_binding=previous,
    )
    assert v2.previous_record_binding == previous

    with pytest.raises(ValueError):
        module.ProceduralMemoryLineageV1(
            memory_lineage_id=lineage_id,
            record_version=2,
            previous_record_binding=None,
        )

    with pytest.raises(ValueError):
        module.ProceduralMemoryLineageV1(
            memory_lineage_id=lineage_id,
            record_version=3,
            previous_record_binding=previous,
        )

    with pytest.raises(ValueError):
        module.ProceduralMemoryLineageV1(
            memory_lineage_id=lineage_id,
            record_version=2,
            previous_record_binding=module.PreviousProceduralRecordBindingV1(
                memory_lineage_id="3" * 64,
                record_version=1,
                canonical_record_sha256="2" * 64,
            ),
        )


def test_task6_version1_rejects_previous_binding() -> None:
    module = _load_target()
    previous = module.PreviousProceduralRecordBindingV1(
        memory_lineage_id="1" * 64,
        record_version=1,
        canonical_record_sha256="2" * 64,
    )
    with pytest.raises(ValueError):
        module.ProceduralMemoryLineageV1(
            memory_lineage_id="1" * 64,
            record_version=1,
            previous_record_binding=previous,
        )


def test_task6_provenance_preserves_source_order_and_rejects_duplicates() -> None:
    module = _load_target()
    first = module.FactualSequenceBindingV1.from_experience(_experience())
    second = module.FactualSequenceBindingV1.from_experience(
        _experience(source_condition="P4-R1-Q2-BAD-TRAIN31")
    )
    # The Unit-2 experience ID changes with condition.
    assert first.experience_id != second.experience_id

    provenance = module.ProceduralMemoryProvenanceV1(
        creation_event_id="CREATE-001",
        creator_role="REGISTERED_BUILDER",
        assembly_registration_binding=_registration_binding(module),
        factual_sequence_bindings=(second, first),
        created_snapshot_candidate=None,
    )
    rebuilt = module.ProceduralMemoryProvenanceV1.from_dict(
        provenance.to_dict()
    )
    assert tuple(
        item.experience_id for item in rebuilt.factual_sequence_bindings
    ) == (second.experience_id, first.experience_id)

    with pytest.raises(ValueError):
        module.ProceduralMemoryProvenanceV1(
            creation_event_id="CREATE-001",
            creator_role="REGISTERED_BUILDER",
            assembly_registration_binding=_registration_binding(module),
            factual_sequence_bindings=(first, first),
            created_snapshot_candidate=None,
        )


def test_task6_provenance_rejects_snapshot_candidate() -> None:
    module = _load_target()
    first = module.FactualSequenceBindingV1.from_experience(_experience())

    with pytest.raises(ValueError):
        module.ProceduralMemoryProvenanceV1(
            creation_event_id="CREATE-001",
            creator_role="REGISTERED_BUILDER",
            assembly_registration_binding=_registration_binding(module),
            factual_sequence_bindings=(first,),
            created_snapshot_candidate="SNAPSHOT-1",
        )


def test_task6_record_id_is_domain_separated_and_versioned() -> None:
    module = _load_target()
    lineage = "1" * 64
    one = module.record_id_for_lineage_version_v1(lineage, 1)
    two = module.record_id_for_lineage_version_v1(lineage, 2)
    assert one != two
    assert one == module.record_id_for_lineage_version_v1(lineage, 1)
    assert len(one) == 64


def test_task6_strict_from_dict_rejects_semantic_field_injection() -> None:
    module = _load_target()
    first = module.FactualSequenceBindingV1.from_experience(_experience())
    provenance = module.ProceduralMemoryProvenanceV1(
        creation_event_id="CREATE-001",
        creator_role="REGISTERED_BUILDER",
        assembly_registration_binding=_registration_binding(module),
        factual_sequence_bindings=(first,),
        created_snapshot_candidate=None,
    )
    payload = provenance.to_dict()
    payload["effect_status"] = "POSITIVE"

    with pytest.raises(ValueError):
        module.ProceduralMemoryProvenanceV1.from_dict(payload)

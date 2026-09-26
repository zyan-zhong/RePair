from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import importlib
import importlib.util

import pytest


TARGET_MODULE = (
    "pchsi.memory.sequence_failure_experience"
)

PROTECTED_TASK_ACCESS_SHA256 = (
    "260766366d72a9af7b0b4809d30a45bb"
    "56f42134dad66b29a4b61ff7ed4793ea"
)

GROUP_DOMAIN = (
    "ALFWORLD_TASK_GAMEFILE_GROUP_V1"
)


def _load_target():
    try:
        spec = importlib.util.find_spec(
            TARGET_MODULE
        )
    except ModuleNotFoundError:
        spec = None

    if spec is None:
        pytest.fail(
            "TASK1_RED_MISSING_"
            "SOURCE_REGISTRATION_CONTRACTS"
        )

    return importlib.import_module(
        TARGET_MODULE
    )


def _group_id(
    relative_gamefile: str,
    gamefile_sha256: str,
) -> str:
    payload = (
        GROUP_DOMAIN
        + "\0"
        + relative_gamefile
        + "\0"
        + gamefile_sha256
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def _binding_kwargs(
    *,
    access_class: str = "TRAIN_MEMORY_SOURCE",
    manifest_sha256: str = (
        PROTECTED_TASK_ACCESS_SHA256
    ),
    line_index: int = 17,
    group_id: str | None = None,
):
    relative = (
        "train/"
        "pick_and_place_simple-Apple-"
        "None-CounterTop-1/"
        "trial_T2026/"
        "game.tw-pddl"
    )

    game_sha = "b" * 64

    if group_id is None:
        group_id = _group_id(
            relative,
            game_sha,
        )

    return {
        "schema_id":
            "SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V1",
        "schema_version": 1,

        "task_access_protected_manifest_sha256":
            manifest_sha256,

        "task_access_record_line_index":
            line_index,

        "task_access_record_sha256":
            "a" * 64,

        "task_gamefile_group_id":
            group_id,

        "dataset_relative_gamefile":
            relative,

        "gamefile_sha256":
            game_sha,

        "task_type":
            "pick_and_place_simple",

        "split":
            "train",

        "access_class":
            access_class,
    }


def _registration_kwargs(
    *,
    authority_type: str = (
        "REGISTERED_BOUNDARY_LABEL"
    ),
    relevant_start: int = 2,
    failure_onset: int = 3,
    final_call: int = 7,
    recovery_start: int | None = 5,
    recovery_final: int | None = 7,
):
    return {
        "schema_id":
            "REGISTERED_FAILURE_SEQUENCE_WINDOW_V1",
        "schema_version": 1,

        "registration_id":
            "REGISTRATION_SYNTHETIC_001",

        "registration_authority_type":
            authority_type,

        "registration_protocol_id":
            "HUMAN_REGISTERED_RANGE_V1",

        "registration_artifact_sha256":
            "c" * 64,

        "registration_record_sha256":
            "d" * 64,

        "source_bundle_sha256":
            "e" * 64,

        "source_attempt_id":
            "ATTEMPT_SYNTHETIC_001",

        "source_task_id":
            "TASK_SYNTHETIC_001",

        "source_round":
            "ROUND1",

        "source_condition":
            "P4-R1-Q2-BAD-TRAIN17",

        "relevant_start_model_call_index":
            relevant_start,

        "registered_failure_onset_model_call_index":
            failure_onset,

        "final_model_call_index":
            final_call,

        "registered_recovery_start_model_call_index":
            recovery_start,

        "registered_recovery_final_model_call_index":
            recovery_final,
    }


def test_task1_contract_symbols_exist() -> None:
    module = _load_target()

    assert hasattr(
        module,
        "SequenceSourceTaskAccessBindingV1",
    )

    assert hasattr(
        module,
        "RegisteredFailureSequenceWindowV1",
    )

    assert hasattr(
        module,
        "SourceRecordPointerV1",
    )


def test_source_binding_accepts_exact_active_source() -> None:
    module = _load_target()

    contract = (
        module.SequenceSourceTaskAccessBindingV1(
            **_binding_kwargs()
        )
    )

    payload = contract.to_dict()

    assert payload[
        "task_access_protected_manifest_sha256"
    ] == PROTECTED_TASK_ACCESS_SHA256

    assert payload[
        "access_class"
    ] == "TRAIN_MEMORY_SOURCE"

    assert payload[
        "split"
    ] == "train"

    assert (
        module
        .SequenceSourceTaskAccessBindingV1
        .from_dict(payload)
        == contract
    )


def test_source_binding_is_immutable() -> None:
    module = _load_target()

    contract = (
        module.SequenceSourceTaskAccessBindingV1(
            **_binding_kwargs()
        )
    )

    with pytest.raises(
        (FrozenInstanceError, AttributeError),
    ):
        contract.access_class = (  # type: ignore[misc]
            "TRAIN_RETRIEVAL_DEV"
        )


def test_source_binding_rejects_non_memory_source() -> None:
    module = _load_target()

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.SequenceSourceTaskAccessBindingV1(
            **_binding_kwargs(
                access_class=(
                    "TRAIN_RETRIEVAL_DEV"
                )
            )
        )


def test_source_binding_rejects_wrong_manifest_authority() -> None:
    module = _load_target()

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.SequenceSourceTaskAccessBindingV1(
            **_binding_kwargs(
                manifest_sha256="0" * 64
            )
        )


def test_source_binding_rejects_group_id_mismatch() -> None:
    module = _load_target()

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.SequenceSourceTaskAccessBindingV1(
            **_binding_kwargs(
                group_id="0" * 64
            )
        )


def test_source_binding_rejects_negative_record_index() -> None:
    module = _load_target()

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.SequenceSourceTaskAccessBindingV1(
            **_binding_kwargs(
                line_index=-1
            )
        )


def test_source_binding_rejects_path_escape() -> None:
    module = _load_target()

    kwargs = _binding_kwargs()

    kwargs[
        "dataset_relative_gamefile"
    ] = (
        "../train/"
        "trial_x/game.tw-pddl"
    )

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.SequenceSourceTaskAccessBindingV1(
            **kwargs
        )


def test_source_record_pointer_accepts_exact_jsonl_record() -> None:
    module = _load_target()

    pointer = module.SourceRecordPointerV1(
        bundle_member_name=(
            "policy_calls.jsonl"
        ),
        zero_based_line_index=3,
        exact_record_sha256="1" * 64,
        whole_member_sha256="2" * 64,
    )

    payload = pointer.to_dict()

    assert payload[
        "bundle_member_name"
    ] == "policy_calls.jsonl"

    assert payload[
        "zero_based_line_index"
    ] == 3

    assert (
        module.SourceRecordPointerV1
        .from_dict(payload)
        == pointer
    )


def test_source_record_pointer_rejects_unknown_member() -> None:
    module = _load_target()

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.SourceRecordPointerV1(
            bundle_member_name=(
                "unregistered.jsonl"
            ),
            zero_based_line_index=0,
            exact_record_sha256="1" * 64,
            whole_member_sha256="2" * 64,
        )


def test_source_record_pointer_rejects_negative_index() -> None:
    module = _load_target()

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.SourceRecordPointerV1(
            bundle_member_name=(
                "action_traces.jsonl"
            ),
            zero_based_line_index=-1,
            exact_record_sha256="1" * 64,
            whole_member_sha256="2" * 64,
        )


def test_registration_accepts_registered_boundary_label() -> None:
    module = _load_target()

    registration = (
        module.RegisteredFailureSequenceWindowV1(
            **_registration_kwargs()
        )
    )

    payload = registration.to_dict()

    assert payload[
        "registration_authority_type"
    ] == "REGISTERED_BOUNDARY_LABEL"

    assert payload[
        "registered_failure_onset_model_call_index"
    ] == 3

    assert (
        module.RegisteredFailureSequenceWindowV1
        .from_dict(payload)
        == registration
    )


def test_registration_rejects_fact_authority_promotion() -> None:
    module = _load_target()

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.RegisteredFailureSequenceWindowV1(
            **_registration_kwargs(
                authority_type="FACT_AUTHORITY"
            )
        )


def test_registration_rejects_half_null_recovery_range() -> None:
    module = _load_target()

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.RegisteredFailureSequenceWindowV1(
            **_registration_kwargs(
                recovery_start=5,
                recovery_final=None,
            )
        )


def test_registration_rejects_recovery_before_failure_marker() -> None:
    module = _load_target()

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.RegisteredFailureSequenceWindowV1(
            **_registration_kwargs(
                failure_onset=4,
                recovery_start=3,
                recovery_final=6,
            )
        )


def test_registration_rejects_invalid_call_order() -> None:
    module = _load_target()

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.RegisteredFailureSequenceWindowV1(
            **_registration_kwargs(
                relevant_start=4,
                failure_onset=3,
                final_call=7,
            )
        )


def test_registration_from_dict_rejects_extra_fields() -> None:
    module = _load_target()

    payload = _registration_kwargs()

    payload["failure_mechanism"] = (
        "must-not-enter-unit2"
    )

    with pytest.raises(
        (TypeError, ValueError),
    ):
        (
            module
            .RegisteredFailureSequenceWindowV1
            .from_dict(payload)
        )


# ===========================================================================
# Unit 2 / Task 2 — Canonical factual experience wire contract
# ===========================================================================

import copy
import re

from pchsi.evaluation.budget import BudgetState
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
)


def _require_task2_symbols():
    module = _load_target()

    required = (
        "SequenceFailureEventV1",
        "SequenceFailureRelevantStartV1",
        "SequenceFailureObservedEndV1",
        "SequenceFailureExperienceV1",
    )

    missing = [
        name
        for name in required
        if not hasattr(module, name)
    ]

    if missing:
        pytest.fail(
            "TASK2_RED_MISSING_FACTUAL_WIRE_CONTRACTS:"
            + ",".join(missing)
        )

    return module


def _task2_source_pointer(
    module,
    *,
    member: str,
    line_index: int,
    record_char: str,
    member_char: str,
):
    return module.SourceRecordPointerV1(
        bundle_member_name=member,
        zero_based_line_index=line_index,
        exact_record_sha256=record_char * 64,
        whole_member_sha256=member_char * 64,
    )


def _task2_binding(module):
    relative = (
        "train/"
        "pick_and_place_simple-Apple-"
        "None-CounterTop-1/"
        "trial_T2026/"
        "game.tw-pddl"
    )

    game_sha = "b" * 64

    return module.SequenceSourceTaskAccessBindingV1(
        schema_id=(
            "SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V1"
        ),
        schema_version=1,
        task_access_protected_manifest_sha256=(
            "260766366d72a9af7b0b4809d30a45bb"
            "56f42134dad66b29a4b61ff7ed4793ea"
        ),
        task_access_record_line_index=17,
        task_access_record_sha256="a" * 64,
        task_gamefile_group_id=_group_id(
            relative,
            game_sha,
        ),
        dataset_relative_gamefile=relative,
        gamefile_sha256=game_sha,
        task_type="pick_and_place_simple",
        split="train",
        access_class="TRAIN_MEMORY_SOURCE",
    )


def _task2_registration(module):
    return module.RegisteredFailureSequenceWindowV1(
        schema_id=(
            "REGISTERED_FAILURE_SEQUENCE_WINDOW_V1"
        ),
        schema_version=1,
        registration_id=(
            "REGISTRATION_SYNTHETIC_001"
        ),
        registration_authority_type=(
            "REGISTERED_BOUNDARY_LABEL"
        ),
        registration_protocol_id=(
            "HUMAN_REGISTERED_RANGE_V1"
        ),
        registration_artifact_sha256="c" * 64,
        registration_record_sha256="d" * 64,
        source_bundle_sha256="e" * 64,
        source_attempt_id=(
            "ATTEMPT_SYNTHETIC_001"
        ),
        source_task_id=(
            "TASK_SYNTHETIC_001"
        ),
        source_round="ROUND1",
        source_condition=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
        relevant_start_model_call_index=2,
        registered_failure_onset_model_call_index=2,
        final_model_call_index=2,
        registered_recovery_start_model_call_index=None,
        registered_recovery_final_model_call_index=None,
    )


def _task2_event(module):
    return module.SequenceFailureEventV1(
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

        pre_admissible_commands=(
            "look",
            "inventory",
        ),
        pre_admissible_commands_sha256="2" * 64,

        raw_model_response='{"action":"look"}',
        raw_model_response_sha256="3" * 64,

        submitted_environment_action="look",

        resulting_observation=(
            "You see a countertop."
        ),
        resulting_observation_sha256="4" * 64,

        resulting_admissible_commands=(
            "look",
            "inventory",
        ),
        resulting_admissible_commands_sha256="5" * 64,

        environment_step_index=1,

        score=0.0,
        done=False,
        won=False,

        visible_state_change_disposition=(
            "OBSERVATION_CHANGED"
        ),

        trace_source_pointer=(
            _task2_source_pointer(
                module,
                member="action_traces.jsonl",
                line_index=2,
                record_char="6",
                member_char="7",
            )
        ),

        policy_call_source_pointer=(
            _task2_source_pointer(
                module,
                member="policy_calls.jsonl",
                line_index=2,
                record_char="8",
                member_char="9",
            )
        ),

        public_transition_source_pointer=(
            _task2_source_pointer(
                module,
                member="public_transitions.jsonl",
                line_index=1,
                record_char="a",
                member_char="b",
            )
        ),
    )


def _task2_relevant_start(module):
    return module.SequenceFailureRelevantStartV1(
        model_call_index=2,

        public_task_goal=(
            "Put the apple on the countertop."
        ),
        public_task_goal_sha256="c" * 64,

        observation="You are in a room.",
        observation_sha256="1" * 64,

        admissible_commands=(
            "look",
            "inventory",
        ),
        admissible_commands_sha256="2" * 64,

        interface_feedback_before=None,

        budget_state_before=BudgetState(
            policy_attempt_count=2,
            environment_step_count=1,
            protocol_failure_count=0,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        ),

        required_preceding_model_call_range=(
            0,
            1,
        ),

        required_preceding_environment_step_indices=(
            0,
        ),

        required_preceding_prefix_source_binding=(
            _task2_source_pointer(
                module,
                member="policy_calls.jsonl",
                line_index=0,
                record_char="d",
                member_char="9",
            ),
            _task2_source_pointer(
                module,
                member="policy_calls.jsonl",
                line_index=1,
                record_char="e",
                member_char="9",
            ),
        ),
    )


def _task2_observed_end(
    module,
    *,
    disposition=(
        "OUTSIDE_REGISTERED_WINDOW"
    ),
):
    if disposition == "OUTSIDE_REGISTERED_WINDOW":
        termination_reason = None
        final_success = None
        final_done = None
        final_won = None
        final_budget = None

    else:
        termination_reason = (
            "ENVIRONMENT_TERMINATED"
        )
        final_success = True
        final_done = True
        final_won = True
        final_budget = BudgetState(
            policy_attempt_count=3,
            environment_step_count=2,
            protocol_failure_count=0,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        )

    return module.SequenceFailureObservedEndV1(
        model_call_index=2,

        budget_state_after=BudgetState(
            policy_attempt_count=3,
            environment_step_count=2,
            protocol_failure_count=0,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        ),

        episode_terminal_disposition=(
            disposition
        ),

        termination_reason=termination_reason,
        final_success=final_success,
        final_done=final_done,
        final_won=final_won,
        final_budget=final_budget,
    )


def _task2_experience(
    module,
    *,
    source_condition=(
        "P4-R1-Q2-BAD-TRAIN17"
    ),
):
    binding = _task2_binding(module)
    registration = _task2_registration(module)

    return module.SequenceFailureExperienceV1(
        experience_id=None,

        schema_id=(
            "SEQUENCE_FAILURE_EXPERIENCE_V1"
        ),
        schema_version=1,

        source_round="ROUND1",
        source_condition=source_condition,

        source_task_id=(
            "TASK_SYNTHETIC_001"
        ),

        source_gamefile_group_id=(
            binding.task_gamefile_group_id
        ),

        source_bundle_sha256="e" * 64,

        source_attempt_id=(
            "ATTEMPT_SYNTHETIC_001"
        ),

        task_access_binding=binding,

        registration_binding=registration,

        relevant_start=(
            _task2_relevant_start(module)
        ),

        observed_sequence=(
            _task2_event(module),
        ),

        observed_end=(
            _task2_observed_end(module)
        ),

        included_environment_step_indices=(
            1,
        ),

        source_bundle_member_sha256=(
            (
                "attempt.json",
                "1" * 64,
            ),
            (
                "action_traces.jsonl",
                "7" * 64,
            ),
            (
                "policy_calls.jsonl",
                "9" * 64,
            ),
            (
                "public_transitions.jsonl",
                "b" * 64,
            ),
            (
                "SHA256SUMS",
                "f" * 64,
            ),
        ),
    )


def test_task2_factual_wire_symbols_exist() -> None:
    _require_task2_symbols()


def test_task2_event_round_trip_and_immutable() -> None:
    module = _require_task2_symbols()

    event = _task2_event(module)

    assert (
        module.SequenceFailureEventV1
        .from_dict(
            event.to_dict()
        )
        == event
    )

    with pytest.raises(
        (FrozenInstanceError, AttributeError),
    ):
        event.model_call_index = 3  # type: ignore[misc]


def test_task2_event_rejects_semantic_field() -> None:
    module = _require_task2_symbols()

    payload = _task2_event(
        module
    ).to_dict()

    payload["failure_mechanism"] = (
        "progress blindness"
    )

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.SequenceFailureEventV1.from_dict(
            payload
        )


def test_task2_relevant_start_binds_complete_prefix() -> None:
    module = _require_task2_symbols()

    start = _task2_relevant_start(module)

    assert (
        start.required_preceding_model_call_range
        == (0, 1)
    )

    assert (
        module.SequenceFailureRelevantStartV1
        .from_dict(
            start.to_dict()
        )
        == start
    )


def test_task2_relevant_start_rejects_wrong_prefix_range() -> None:
    module = _require_task2_symbols()

    payload = _task2_relevant_start(
        module
    ).to_dict()

    payload[
        "required_preceding_model_call_range"
    ] = [0, 0]

    with pytest.raises(
        (TypeError, ValueError),
    ):
        (
            module.SequenceFailureRelevantStartV1
            .from_dict(payload)
        )


def test_task2_observed_end_excludes_future_terminal_fields() -> None:
    module = _require_task2_symbols()

    end = _task2_observed_end(module)

    payload = end.to_dict()

    assert (
        payload["episode_terminal_disposition"]
        == "OUTSIDE_REGISTERED_WINDOW"
    )

    assert payload["termination_reason"] is None
    assert payload["final_success"] is None
    assert payload["final_done"] is None
    assert payload["final_won"] is None
    assert payload["final_budget"] is None


def test_task2_observed_end_rejects_future_terminal_leak() -> None:
    module = _require_task2_symbols()

    payload = _task2_observed_end(
        module
    ).to_dict()

    payload["final_success"] = False

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.SequenceFailureObservedEndV1.from_dict(
            payload
        )


def test_task2_included_terminal_requires_complete_terminal_fields() -> None:
    module = _require_task2_symbols()

    end = _task2_observed_end(
        module,
        disposition="INCLUDED_REGISTERED_WINDOW",
    )

    payload = end.to_dict()

    assert payload["final_success"] is True
    assert payload["final_done"] is True
    assert payload["final_won"] is True
    assert payload["final_budget"] is not None


def test_task2_experience_is_canonical_and_reproducible() -> None:
    module = _require_task2_symbols()

    first = _task2_experience(module)
    second = _task2_experience(module)

    assert first == second

    assert (
        first.experience_id
        == second.experience_id
    )

    assert re.fullmatch(
        r"[0-9a-f]{64}",
        first.experience_id,
    )

    first_bytes = first.canonical_bytes()
    second_bytes = second.canonical_bytes()

    assert first_bytes == second_bytes
    assert first_bytes.endswith(b"\n")

    assert (
        module.SequenceFailureExperienceV1
        .from_json(first_bytes)
        == first
    )


def test_task2_experience_id_uses_frozen_domain_separation() -> None:
    module = _require_task2_symbols()

    experience = _task2_experience(module)

    payload = experience.to_dict()

    observed_id = payload.pop(
        "experience_id"
    )

    expected_id = hashlib.sha256(
        (
            b"SEQUENCE_FAILURE_EXPERIENCE_V1"
            + b"\0"
            + canonical_json_bytes(payload)
        )
    ).hexdigest()

    assert observed_id == expected_id


def test_task2_changed_factual_payload_changes_identity() -> None:
    module = _require_task2_symbols()

    first = _task2_experience(
        module,
        source_condition=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
    )

    second = _task2_experience(
        module,
        source_condition=(
            "P4-R1-Q2-BAD-TRAIN31"
        ),
    )

    assert (
        first.experience_id
        != second.experience_id
    )


def test_task2_experience_rejects_empty_sequence() -> None:
    module = _require_task2_symbols()

    experience = _task2_experience(module)

    payload = experience.to_dict()

    payload["observed_sequence"] = []

    payload.pop(
        "experience_id"
    )

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.SequenceFailureExperienceV1.from_dict(
            payload
        )


def test_task2_strict_json_rejects_duplicate_keys() -> None:
    module = _require_task2_symbols()

    raw = (
        '{"experience_id":"'
        + ("a" * 64)
        + '","experience_id":"'
        + ("b" * 64)
        + '"}'
    )

    with pytest.raises(ValueError):
        module.SequenceFailureExperienceV1.from_json(
            raw
        )


def test_task2_strict_json_rejects_nonfinite_numbers() -> None:
    module = _require_task2_symbols()

    with pytest.raises(ValueError):
        module.SequenceFailureExperienceV1.from_json(
            '{"score":NaN}'
        )


def test_task2_experience_rejects_semantic_top_level_field() -> None:
    module = _require_task2_symbols()

    experience = _task2_experience(module)

    payload = experience.to_dict()

    payload["failure_mechanism"] = (
        "not-authorized"
    )

    payload.pop(
        "experience_id"
    )

    with pytest.raises(
        (TypeError, ValueError),
    ):
        module.SequenceFailureExperienceV1.from_dict(
            payload
        )

# ==========================================================================
# Unit 2 / Task 3 — Source evidence binding
# ==========================================================================

import base64 as _t3_base64
from dataclasses import replace as _t3_replace

from pchsi.evaluation.action_trace import (
    ActionTrace as _T3ActionTrace,
    ExecutionStatus as _T3ExecutionStatus,
    PipelineVariant as _T3PipelineVariant,
    TraceProvenance as _T3TraceProvenance,
    sha256_string_sequence as _t3_sha256_string_sequence,
)
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes as _t3_canonical_json_bytes,
    canonical_json_text as _t3_canonical_json_text,
    sha256_bytes as _t3_sha256_bytes,
    sha256_text as _t3_sha256_text,
)
from pchsi.evaluation.episode_artifact import (
    build_attempt_bundle_bytes as _t3_build_attempt_bundle_bytes,
)
from pchsi.evaluation.policy_call_evidence import (
    PolicyCallEvidenceV1 as _T3PolicyCallEvidenceV1,
    allowlisted_response_headers as _t3_allowlisted_response_headers,
)
from pchsi.evaluation.raw_policy_prompt import (
    build_raw_policy_prompt as _t3_build_raw_policy_prompt,
    sha256_executed_transitions as _t3_sha256_executed_transitions,
)
from pchsi.evaluation.schema_models import (
    BudgetSnapshotV1 as _T3BudgetSnapshotV1,
    EpisodeArtifactV1 as _T3EpisodeArtifactV1,
)


def _require_task3_symbols():
    module = _load_target()
    required = (
        "SequenceSourceEvidenceV1",
        "validate_sequence_source_evidence_v1",
        "source_record_pointer_from_bundle_v1",
    )
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        pytest.fail(
            "TASK3_RED_MISSING_SOURCE_BINDING:" + ",".join(missing)
        )
    return module


def _t3_policy_call(*, raw_text: str, prompt: str):
    request_dict = {"model": "m", "request_id": "client-0"}
    request_bytes = _t3_canonical_json_bytes(request_dict)
    semantic_json = _t3_canonical_json_text({"model": "m"})
    body = _t3_canonical_json_bytes(
        {
            "id": "provider-0",
            "choices": [
                {
                    "message": {"content": raw_text},
                    "finish_reason": "stop",
                    "token_ids": [3],
                }
            ],
            "usage": {"prompt_tokens": 2, "completion_tokens": 1},
            "prompt_token_ids": [1, 2],
        }
    )
    rendered = "<rendered>" + prompt
    return _T3PolicyCallEvidenceV1(
        "POLICY_CALL_EVIDENCE_V1",
        1,
        0,
        0,
        "client-0",
        "provider-0",
        prompt,
        _t3_sha256_text(prompt),
        rendered,
        _t3_sha256_text(rendered),
        (1, 2),
        2,
        semantic_json,
        _t3_sha256_text(semantic_json),
        _t3_base64.b64encode(request_bytes).decode("ascii"),
        _t3_sha256_bytes(request_bytes),
        200,
        tuple(
            _t3_allowlisted_response_headers(
                {
                    "x-request-id": "provider-0",
                    "content-type": "application/json",
                }
            ).items()
        ),
        _t3_base64.b64encode(body).decode("ascii"),
        _t3_sha256_bytes(body),
        raw_text,
        _t3_sha256_text(raw_text),
        "stop",
        2,
        1,
        (1, 2),
        (3,),
        7,
        "goal",
        _t3_sha256_text("goal"),
        "obs",
        _t3_sha256_text("obs"),
        ("look",),
        _t3_sha256_string_sequence(("look",)),
        (),
        _t3_sha256_executed_transitions(()),
        None,
        (
            ("policy_attempt_count", 0),
            ("environment_step_count", 0),
            ("protocol_failure_count", 0),
            ("inadmissible_action_count", 0),
            ("consecutive_nonexecuted_attempt_count", 0),
        ),
    )


def _t3_fixture(module):
    prompt = _t3_build_raw_policy_prompt(
        public_task_goal="goal",
        observation="obs",
        executed_transitions=(),
        admissible_commands=("look",),
        interface_feedback=None,
    )
    provenance = _T3TraceProvenance(
        run_id="run",
        task_id="TASK_SYNTHETIC_001",
        episode_id="ATTEMPT_SYNTHETIC_001",
        replicate_id=0,
        arm_id="R0",
        code_commit="commit",
        config_sha256="1" * 64,
        provider="vllm",
        model_name="model",
        model_version="revision",
        provider_request_id="provider-0",
        retry_count=0,
        timestamp_utc="2026-08-17T00:00:00Z",
        split_and_access_version="SPLIT_AND_ACCESS_V1",
        split_name="E1-Dev",
        access_mode="development_visible",
        policy_version="pi0",
        seed=17,
        memory_version="MEMORY_M0_V1",
        memory_state_sha256=_t3_sha256_executed_transitions(()),
    )
    trace = _T3ActionTrace.build(
        provenance=provenance,
        pipeline_variant=_T3PipelineVariant.RAW_V1,
        model_call_index=0,
        environment_step_index=None,
        execution_status=_T3ExecutionStatus.NOT_EXECUTED,
        public_task_goal="goal",
        observation="obs",
        prompt_text=prompt,
        admissible_commands=("look",),
        raw_model_response="not-json",
        literal_action="",
        parsed_phase=None,
        model_reason=None,
        parser_status="failed",
        parser_error="ENVELOPE_INVALID_JSON",
        parser_metadata={},
        literal_action_exactly_admissible=False,
        literal_action_casefold_admissible=False,
        stages=(),
        final_executed_action=None,
        final_action_admissible=None,
        attempt_outcome="FORMAT_PROTOCOL_FAILURE",
        failure_stage="envelope",
        failure_code="ENVELOPE_INVALID_JSON",
        normalized_action=None,
        admissibility_status="not_checked",
        feedback_code="FORMAT_ERROR_V1",
        policy_attempt_count_before=0,
        policy_attempt_count_after=1,
        environment_step_count_before=0,
        environment_step_count_after=0,
        protocol_failure_count=1,
        inadmissible_action_count=0,
        consecutive_nonexecuted_attempt_count=1,
        episode_termination_reason="POLICY_ATTEMPT_BUDGET_EXHAUSTED",
        submitted_environment_action=None,
        resulting_observation=None,
        protocol_failure_count_before=0,
        inadmissible_action_count_before=0,
        consecutive_nonexecuted_attempt_count_before=0,
    )
    policy_call = _t3_policy_call(raw_text="not-json", prompt=prompt)
    episode = _T3EpisodeArtifactV1(
        schema_id="E1_EPISODE_ARTIFACT_V1",
        schema_version=1,
        run_id="run",
        scheduled_cell_id="cell",
        execution_attempt_id="ATTEMPT_SYNTHETIC_001",
        attempt_ordinal=0,
        task_index=0,
        task_id="TASK_SYNTHETIC_001",
        task_type="pick_and_place_simple",
        gamefile_sha1="2" * 40,
        gamefile_sha256="b" * 64,
        seed=17,
        evaluator_commit="eval",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        raw_protocol_sha256="3" * 64,
        split_access_sha256="4" * 64,
        gamefile_identity_manifest_sha256="5" * 64,
        environment_runtime_manifest_sha256="6" * 64,
        policy_runtime_manifest_sha256="7" * 64,
        policy_request_schema_sha256="8" * 64,
        scientific_outcome_status="SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE",
        operational_finalization_status="PUBLISHED",
        success=False,
        termination_reason="POLICY_ATTEMPT_BUDGET_EXHAUSTED",
        final_score=None,
        final_done=False,
        final_won=False,
        final_budget=_T3BudgetSnapshotV1(
            policy_attempt_count=1,
            environment_step_count=0,
            protocol_failure_count=1,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=1,
        ),
        trace_count=1,
        public_transition_count=0,
        environment_call_trace_count=0,
        initial_observation_sha256=_t3_sha256_text("obs"),
        final_observation_sha256=_t3_sha256_text("obs"),
        episode_semantic_sha256="9" * 64,
        started_at_utc="2026-08-17T00:00:00Z",
        completed_at_utc="2026-08-17T00:00:01Z",
    )
    bundle = _t3_build_attempt_bundle_bytes(
        episode_artifact=episode,
        traces=(trace,),
        policy_calls=(policy_call,),
        public_transitions=(),
    )
    relative = (
        "train/pick_and_place_simple-Apple-None-CounterTop-1/"
        "trial_T2026/game.tw-pddl"
    )
    group_id = _group_id(relative, "b" * 64)
    record = {
        "trial_id": "trial_T2026",
        "task_type": "pick_and_place_simple",
        "split": "train",
        "dataset_relative_gamefile": relative,
        "gamefile_sha256": "b" * 64,
        "task_gamefile_group_id": group_id,
        "access_class": "TRAIN_MEMORY_SOURCE",
    }
    record_bytes = _t3_canonical_json_bytes(record)
    binding = module.SequenceSourceTaskAccessBindingV1(
        schema_id="SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V1",
        schema_version=1,
        task_access_protected_manifest_sha256=PROTECTED_TASK_ACCESS_SHA256,
        task_access_record_line_index=17,
        task_access_record_sha256=_t3_sha256_bytes(record_bytes),
        task_gamefile_group_id=group_id,
        dataset_relative_gamefile=relative,
        gamefile_sha256="b" * 64,
        task_type="pick_and_place_simple",
        split="train",
        access_class="TRAIN_MEMORY_SOURCE",
    )
    registration = module.RegisteredFailureSequenceWindowV1(
        schema_id="REGISTERED_FAILURE_SEQUENCE_WINDOW_V1",
        schema_version=1,
        registration_id="REG-1",
        registration_authority_type="REGISTERED_BOUNDARY_LABEL",
        registration_protocol_id="SYNTHETIC_TEST_V1",
        registration_artifact_sha256="c" * 64,
        registration_record_sha256="d" * 64,
        source_bundle_sha256=bundle.attempt_bundle_sha256,
        source_attempt_id="ATTEMPT_SYNTHETIC_001",
        source_task_id="TASK_SYNTHETIC_001",
        source_round="ROUND1",
        source_condition="P4-R1-Q2-BAD-TRAIN17",
        relevant_start_model_call_index=0,
        registered_failure_onset_model_call_index=0,
        final_model_call_index=0,
        registered_recovery_start_model_call_index=None,
        registered_recovery_final_model_call_index=None,
    )
    source = module.SequenceSourceEvidenceV1(
        episode_artifact=episode,
        traces=(trace,),
        policy_calls=(policy_call,),
        public_transitions=(),
        attempt_bundle=bundle,
        task_access_record_line_index=17,
        task_access_record_bytes=record_bytes,
    )
    return source, binding, registration


def test_task3_source_binding_symbols_exist() -> None:
    _require_task3_symbols()


def test_task3_valid_source_evidence_passes() -> None:
    module = _require_task3_symbols()
    source, binding, registration = _t3_fixture(module)
    assert module.validate_sequence_source_evidence_v1(
        source=source,
        task_access_binding=binding,
        registration=registration,
    ) is source


def test_task3_rejects_wrong_bundle_identity() -> None:
    module = _require_task3_symbols()
    source, binding, registration = _t3_fixture(module)
    bad = module.RegisteredFailureSequenceWindowV1(
        **{
            **registration.to_dict(),
            "source_bundle_sha256": "0" * 64,
        }
    )
    with pytest.raises(ValueError, match="bundle"):
        module.validate_sequence_source_evidence_v1(
            source=source,
            task_access_binding=binding,
            registration=bad,
        )


def test_task3_rejects_task_access_record_hash_mismatch() -> None:
    module = _require_task3_symbols()
    source, binding, registration = _t3_fixture(module)
    bad_binding = module.SequenceSourceTaskAccessBindingV1(
        **{
            **binding.to_dict(),
            "task_access_record_sha256": "0" * 64,
        }
    )
    with pytest.raises(ValueError, match="task-access record"):
        module.validate_sequence_source_evidence_v1(
            source=source,
            task_access_binding=bad_binding,
            registration=registration,
        )


def test_task3_requires_policy_call_bundle_member() -> None:
    module = _require_task3_symbols()
    source, binding, registration = _t3_fixture(module)
    legacy_bundle = _t3_build_attempt_bundle_bytes(
        episode_artifact=source.episode_artifact,
        traces=source.traces,
        public_transitions=source.public_transitions,
        policy_calls=None,
    )
    bad_source = module.SequenceSourceEvidenceV1(
        episode_artifact=source.episode_artifact,
        traces=source.traces,
        policy_calls=source.policy_calls,
        public_transitions=source.public_transitions,
        attempt_bundle=legacy_bundle,
        task_access_record_line_index=source.task_access_record_line_index,
        task_access_record_bytes=source.task_access_record_bytes,
    )
    with pytest.raises(ValueError, match="POLICY_CALL_EVIDENCE_REQUIRED"):
        module.validate_sequence_source_evidence_v1(
            source=bad_source,
            task_access_binding=binding,
            registration=registration,
        )


def test_task3_source_record_pointer_uses_exact_line_bytes() -> None:
    module = _require_task3_symbols()
    source, binding, registration = _t3_fixture(module)
    module.validate_sequence_source_evidence_v1(
        source=source,
        task_access_binding=binding,
        registration=registration,
    )
    pointer = module.source_record_pointer_from_bundle_v1(
        source=source,
        bundle_member_name="policy_calls.jsonl",
        zero_based_line_index=0,
    )
    exact_line = source.attempt_bundle.policy_calls_jsonl
    assert exact_line is not None
    assert pointer.exact_record_sha256 == _t3_sha256_bytes(exact_line)
    assert pointer.whole_member_sha256 == _t3_sha256_bytes(exact_line)

# ==========================================================================
# TASK3_PLAN_CONFORMANCE_SUPPLEMENT_V1
#
# Supplemental frozen-plan adversarial coverage.
# These tests are replayed against the exact Task-2 parent separately.
# ==========================================================================

from pchsi.evaluation.episode_sequence import (
    EpisodeSequenceError as _T3PlanEpisodeSequenceError,
)

from pchsi.evaluation.schema_models import (
    PublicTransitionRecordV1 as _T3PlanPublicTransitionRecordV1,
)


def _t3_plan_rebind_policy_call(
    module,
    *,
    source,
    registration,
    policy_call,
):
    bundle = _t3_build_attempt_bundle_bytes(
        episode_artifact=(
            source.episode_artifact
        ),
        traces=source.traces,
        policy_calls=(policy_call,),
        public_transitions=(
            source.public_transitions
        ),
    )

    rebuilt_source = (
        module.SequenceSourceEvidenceV1(
            episode_artifact=(
                source.episode_artifact
            ),
            traces=source.traces,
            policy_calls=(policy_call,),
            public_transitions=(
                source.public_transitions
            ),
            attempt_bundle=bundle,
            task_access_record_line_index=(
                source
                .task_access_record_line_index
            ),
            task_access_record_bytes=(
                source
                .task_access_record_bytes
            ),
        )
    )

    rebuilt_registration = (
        module.RegisteredFailureSequenceWindowV1(
            **{
                **registration.to_dict(),
                "source_bundle_sha256": (
                    bundle
                    .attempt_bundle_sha256
                ),
            }
        )
    )

    return (
        rebuilt_source,
        rebuilt_registration,
    )



def _t3_plan_corrupt(value, **changes):
    """Create intentionally corrupted evidence without re-running dataclass invariants."""
    import copy

    clone = copy.copy(value)

    for name, replacement in changes.items():
        object.__setattr__(
            clone,
            name,
            replacement,
        )

    return clone


def test_task3_plan_invalid_whole_episode_rejected_before_slicing() -> None:
    module = _require_task3_symbols()

    source, binding, registration = (
        _t3_fixture(module)
    )

    bad_trace = _t3_plan_corrupt(
        source.traces[0],
        policy_attempt_count_before=1,
        policy_attempt_count_after=2,
    )

    bad_source = (
        module.SequenceSourceEvidenceV1(
            episode_artifact=(
                source.episode_artifact
            ),
            traces=(bad_trace,),
            policy_calls=(
                source.policy_calls
            ),
            public_transitions=(
                source.public_transitions
            ),
            attempt_bundle=(
                source.attempt_bundle
            ),
            task_access_record_line_index=(
                source
                .task_access_record_line_index
            ),
            task_access_record_bytes=(
                source
                .task_access_record_bytes
            ),
        )
    )

    with pytest.raises(
        _T3PlanEpisodeSequenceError,
        match="BUDGET_CONTINUITY_FAILURE",
    ):
        module.validate_sequence_source_evidence_v1(
            source=bad_source,
            task_access_binding=binding,
            registration=registration,
        )


def test_task3_plan_policy_trace_observation_mismatch_rejected() -> None:
    module = _require_task3_symbols()

    source, binding, registration = (
        _t3_fixture(module)
    )

    bad_call = _t3_replace(
        source.policy_calls[0],
        observation="different observation",
        observation_sha256=(
            _t3_sha256_text(
                "different observation"
            )
        ),
    )

    bad_source, bad_registration = (
        _t3_plan_rebind_policy_call(
            module,
            source=source,
            registration=registration,
            policy_call=bad_call,
        )
    )

    with pytest.raises(
        ValueError,
        match="observation mismatch",
    ):
        module.validate_sequence_source_evidence_v1(
            source=bad_source,
            task_access_binding=binding,
            registration=bad_registration,
        )


def test_task3_plan_policy_trace_menu_mismatch_rejected() -> None:
    module = _require_task3_symbols()

    source, binding, registration = (
        _t3_fixture(module)
    )

    bad_menu = (
        "inventory",
    )

    bad_call = _t3_replace(
        source.policy_calls[0],
        admissible_commands=bad_menu,
        admissible_commands_sequence_sha256=(
            _t3_sha256_string_sequence(
                bad_menu
            )
        ),
    )

    bad_source, bad_registration = (
        _t3_plan_rebind_policy_call(
            module,
            source=source,
            registration=registration,
            policy_call=bad_call,
        )
    )

    with pytest.raises(
        ValueError,
        match="menu mismatch",
    ):
        module.validate_sequence_source_evidence_v1(
            source=bad_source,
            task_access_binding=binding,
            registration=bad_registration,
        )


def test_task3_plan_policy_trace_raw_response_mismatch_rejected() -> None:
    module = _require_task3_symbols()

    source, binding, registration = (
        _t3_fixture(module)
    )

    bad_call = _t3_policy_call(
        raw_text='{"action":"look"}',
        prompt=(
            source.traces[0]
            .prompt_text
        ),
    )

    bad_source, bad_registration = (
        _t3_plan_rebind_policy_call(
            module,
            source=source,
            registration=registration,
            policy_call=bad_call,
        )
    )

    with pytest.raises(
        ValueError,
        match="raw-response mismatch",
    ):
        module.validate_sequence_source_evidence_v1(
            source=bad_source,
            task_access_binding=binding,
            registration=bad_registration,
        )


def test_task3_plan_policy_trace_budget_before_mismatch_rejected() -> None:
    module = _require_task3_symbols()

    source, binding, registration = (
        _t3_fixture(module)
    )

    bad_budget = (
        (
            "policy_attempt_count",
            9,
        ),
        (
            "environment_step_count",
            0,
        ),
        (
            "protocol_failure_count",
            0,
        ),
        (
            "inadmissible_action_count",
            0,
        ),
        (
            "consecutive_nonexecuted_attempt_count",
            0,
        ),
    )

    bad_call = _t3_replace(
        source.policy_calls[0],
        budget_before=bad_budget,
    )

    bad_source, bad_registration = (
        _t3_plan_rebind_policy_call(
            module,
            source=source,
            registration=registration,
            policy_call=bad_call,
        )
    )

    with pytest.raises(
        ValueError,
        match="BudgetState-before mismatch",
    ):
        module.validate_sequence_source_evidence_v1(
            source=bad_source,
            task_access_binding=binding,
            registration=bad_registration,
        )


def test_task3_plan_task_identity_mismatch_rejected() -> None:
    module = _require_task3_symbols()

    source, binding, registration = (
        _t3_fixture(module)
    )

    bad_registration = (
        module.RegisteredFailureSequenceWindowV1(
            **{
                **registration.to_dict(),
                "source_task_id": (
                    "TASK_OTHER"
                ),
            }
        )
    )

    with pytest.raises(
        ValueError,
        match="task identity mismatch",
    ):
        module.validate_sequence_source_evidence_v1(
            source=source,
            task_access_binding=binding,
            registration=bad_registration,
        )


def test_task3_plan_attempt_identity_mismatch_rejected() -> None:
    module = _require_task3_symbols()

    source, binding, registration = (
        _t3_fixture(module)
    )

    bad_registration = (
        module.RegisteredFailureSequenceWindowV1(
            **{
                **registration.to_dict(),
                "source_attempt_id": (
                    "ATTEMPT_OTHER"
                ),
            }
        )
    )

    with pytest.raises(
        ValueError,
        match="attempt identity mismatch",
    ):
        module.validate_sequence_source_evidence_v1(
            source=source,
            task_access_binding=binding,
            registration=bad_registration,
        )


def test_task3_plan_registered_range_outside_episode_rejected() -> None:
    module = _require_task3_symbols()

    source, binding, registration = (
        _t3_fixture(module)
    )

    bad_registration = (
        module.RegisteredFailureSequenceWindowV1(
            **{
                **registration.to_dict(),
                "final_model_call_index": 1,
            }
        )
    )

    with pytest.raises(
        ValueError,
        match="ends outside source episode",
    ):
        module.validate_sequence_source_evidence_v1(
            source=source,
            task_access_binding=binding,
            registration=bad_registration,
        )


def test_task3_plan_noncontiguous_source_calls_rejected_by_whole_episode_validator() -> None:
    module = _require_task3_symbols()

    source, binding, registration = (
        _t3_fixture(module)
    )

    bad_trace = _t3_plan_corrupt(
        source.traces[0],
        model_call_index=1,
    )

    bad_source = (
        module.SequenceSourceEvidenceV1(
            episode_artifact=(
                source.episode_artifact
            ),
            traces=(bad_trace,),
            policy_calls=(
                source.policy_calls
            ),
            public_transitions=(
                source.public_transitions
            ),
            attempt_bundle=(
                source.attempt_bundle
            ),
            task_access_record_line_index=(
                source
                .task_access_record_line_index
            ),
            task_access_record_bytes=(
                source
                .task_access_record_bytes
            ),
        )
    )

    with pytest.raises(
        _T3PlanEpisodeSequenceError,
        match="MODEL_CALL_INDEX_DISCONTINUITY",
    ):
        module.validate_sequence_source_evidence_v1(
            source=bad_source,
            task_access_binding=binding,
            registration=registration,
        )


def test_task3_plan_registered_recovery_outside_source_episode_rejected() -> None:
    module = _require_task3_symbols()

    source, binding, registration = (
        _t3_fixture(module)
    )

    bad_registration = (
        module.RegisteredFailureSequenceWindowV1(
            **{
                **registration.to_dict(),
                "final_model_call_index": 1,
                (
                    "registered_recovery_start_"
                    "model_call_index"
                ): 1,
                (
                    "registered_recovery_final_"
                    "model_call_index"
                ): 1,
            }
        )
    )

    with pytest.raises(
        ValueError,
        match="ends outside source episode",
    ):
        module.validate_sequence_source_evidence_v1(
            source=source,
            task_access_binding=binding,
            registration=bad_registration,
        )


def test_task3_plan_transition_model_call_binding_mismatch_rejected() -> None:
    module = _require_task3_symbols()

    source, binding, registration = (
        _t3_fixture(module)
    )

    transition = (
        _T3PlanPublicTransitionRecordV1(
            schema_id=(
                "E1_PUBLIC_TRANSITION_RECORD_V1"
            ),
            schema_version=1,
            scheduled_cell_id="cell",
            execution_attempt_id=(
                "ATTEMPT_SYNTHETIC_001"
            ),
            model_call_index=1,
            environment_step_index=0,
            submitted_action="look",
            pre_action_observation="obs",
            pre_action_observation_sha256=(
                _t3_sha256_text("obs")
            ),
            pre_action_admissible_commands=(
                "look",
            ),
            pre_action_admissible_commands_sha256=(
                _t3_sha256_string_sequence(
                    ("look",)
                )
            ),
            resulting_observation="after",
            resulting_observation_sha256=(
                _t3_sha256_text("after")
            ),
            resulting_admissible_commands=(
                "look",
            ),
            resulting_admissible_commands_sha256=(
                _t3_sha256_string_sequence(
                    ("look",)
                )
            ),
            done=False,
            won=False,
            score=0,
            pre_action_visibility=(
                "POLICY_VISIBLE_BEFORE_ACTION"
            ),
            resulting_visibility=(
                "POST_ACTION_PUBLIC_AUDIT_ONLY"
            ),
        )
    )

    bad_source = (
        module.SequenceSourceEvidenceV1(
            episode_artifact=(
                source.episode_artifact
            ),
            traces=source.traces,
            policy_calls=(
                source.policy_calls
            ),
            public_transitions=(
                transition,
            ),
            attempt_bundle=(
                source.attempt_bundle
            ),
            task_access_record_line_index=(
                source
                .task_access_record_line_index
            ),
            task_access_record_bytes=(
                source
                .task_access_record_bytes
            ),
        )
    )

    with pytest.raises(
        _T3PlanEpisodeSequenceError,
        match="EXTRA_PUBLIC_TRANSITION",
    ):
        module.validate_sequence_source_evidence_v1(
            source=bad_source,
            task_access_binding=binding,
            registration=registration,
        )

# ==========================================================================
# Unit 2 / Task 4 — Deterministic factual reconstruction
# ==========================================================================

from pchsi.evaluation.raw_policy_prompt import (
    InterfaceFeedbackCode as _T4InterfaceFeedbackCode,
)


def _require_task4_symbols():
    module = _load_target()
    if not hasattr(module, "build_sequence_failure_experience_v1"):
        pytest.fail("TASK4_RED_MISSING_RECONSTRUCTION")
    return module


def _t4_policy_call(
    *,
    index: int,
    raw_text: str,
    prompt: str,
    feedback: str | None,
    budget_before: tuple[tuple[str, int], ...],
):
    client = f"client-{index}"
    provider = f"provider-{index}"
    request_dict = {"model": "m", "request_id": client}
    request_bytes = _t3_canonical_json_bytes(request_dict)
    semantic_json = _t3_canonical_json_text({"model": "m"})
    body = _t3_canonical_json_bytes(
        {
            "id": provider,
            "choices": [
                {
                    "message": {"content": raw_text},
                    "finish_reason": "stop",
                    "token_ids": [3],
                }
            ],
            "usage": {"prompt_tokens": 2, "completion_tokens": 1},
            "prompt_token_ids": [1, 2],
        }
    )
    rendered = "<rendered>" + prompt
    return _T3PolicyCallEvidenceV1(
        "POLICY_CALL_EVIDENCE_V1",
        1,
        index,
        budget_before[1][1],
        client,
        provider,
        prompt,
        _t3_sha256_text(prompt),
        rendered,
        _t3_sha256_text(rendered),
        (1, 2),
        2,
        semantic_json,
        _t3_sha256_text(semantic_json),
        _t3_base64.b64encode(request_bytes).decode("ascii"),
        _t3_sha256_bytes(request_bytes),
        200,
        tuple(
            _t3_allowlisted_response_headers(
                {
                    "x-request-id": provider,
                    "content-type": "application/json",
                }
            ).items()
        ),
        _t3_base64.b64encode(body).decode("ascii"),
        _t3_sha256_bytes(body),
        raw_text,
        _t3_sha256_text(raw_text),
        "stop",
        2,
        1,
        (1, 2),
        (3,),
        7,
        "goal",
        _t3_sha256_text("goal"),
        "obs",
        _t3_sha256_text("obs"),
        ("look",),
        _t3_sha256_string_sequence(("look",)),
        (),
        _t3_sha256_executed_transitions(()),
        feedback,
        budget_before,
    )


def _t4_fixture(module):
    source1, binding, _ = _t3_fixture(module)
    trace0 = _t3_replace(source1.traces[0], episode_termination_reason=None)
    policy0 = source1.policy_calls[0]

    prompt1 = _t3_build_raw_policy_prompt(
        public_task_goal="goal",
        observation="obs",
        executed_transitions=(),
        admissible_commands=("look",),
        interface_feedback=_T4InterfaceFeedbackCode.FORMAT_ERROR_V1,
    )
    provenance1 = _t3_replace(
        trace0.provenance,
        provider_request_id="provider-1",
        timestamp_utc="2026-08-17T00:00:01Z",
    )
    trace1 = _T3ActionTrace.build(
        provenance=provenance1,
        pipeline_variant=_T3PipelineVariant.RAW_V1,
        model_call_index=1,
        environment_step_index=None,
        execution_status=_T3ExecutionStatus.NOT_EXECUTED,
        public_task_goal="goal",
        observation="obs",
        prompt_text=prompt1,
        admissible_commands=("look",),
        raw_model_response="not-json-2",
        literal_action="",
        parsed_phase=None,
        model_reason=None,
        parser_status="failed",
        parser_error="ENVELOPE_INVALID_JSON",
        parser_metadata={},
        literal_action_exactly_admissible=False,
        literal_action_casefold_admissible=False,
        stages=(),
        final_executed_action=None,
        final_action_admissible=None,
        attempt_outcome="FORMAT_PROTOCOL_FAILURE",
        failure_stage="envelope",
        failure_code="ENVELOPE_INVALID_JSON",
        normalized_action=None,
        admissibility_status="not_checked",
        feedback_code="FORMAT_ERROR_V1",
        policy_attempt_count_before=1,
        policy_attempt_count_after=2,
        environment_step_count_before=0,
        environment_step_count_after=0,
        protocol_failure_count=2,
        inadmissible_action_count=0,
        consecutive_nonexecuted_attempt_count=2,
        episode_termination_reason="POLICY_ATTEMPT_BUDGET_EXHAUSTED",
        submitted_environment_action=None,
        resulting_observation=None,
        protocol_failure_count_before=1,
        inadmissible_action_count_before=0,
        consecutive_nonexecuted_attempt_count_before=1,
    )
    budget1 = (
        ("policy_attempt_count", 1),
        ("environment_step_count", 0),
        ("protocol_failure_count", 1),
        ("inadmissible_action_count", 0),
        ("consecutive_nonexecuted_attempt_count", 1),
    )
    policy1 = _t4_policy_call(
        index=1,
        raw_text="not-json-2",
        prompt=prompt1,
        feedback="FORMAT_ERROR_V1",
        budget_before=budget1,
    )
    episode = _t3_replace(
        source1.episode_artifact,
        final_budget=_T3BudgetSnapshotV1(
            policy_attempt_count=2,
            environment_step_count=0,
            protocol_failure_count=2,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=2,
        ),
        trace_count=2,
        episode_semantic_sha256="9" * 64,
    )
    bundle = _t3_build_attempt_bundle_bytes(
        episode_artifact=episode,
        traces=(trace0, trace1),
        policy_calls=(policy0, policy1),
        public_transitions=(),
    )
    source = module.SequenceSourceEvidenceV1(
        episode_artifact=episode,
        traces=(trace0, trace1),
        policy_calls=(policy0, policy1),
        public_transitions=(),
        attempt_bundle=bundle,
        task_access_record_line_index=source1.task_access_record_line_index,
        task_access_record_bytes=source1.task_access_record_bytes,
    )
    terminal_registration = module.RegisteredFailureSequenceWindowV1(
        schema_id="REGISTERED_FAILURE_SEQUENCE_WINDOW_V1",
        schema_version=1,
        registration_id="REG-T4-END",
        registration_authority_type="REGISTERED_BOUNDARY_LABEL",
        registration_protocol_id="SYNTHETIC_TEST_V1",
        registration_artifact_sha256="c" * 64,
        registration_record_sha256="d" * 64,
        source_bundle_sha256=bundle.attempt_bundle_sha256,
        source_attempt_id="ATTEMPT_SYNTHETIC_001",
        source_task_id="TASK_SYNTHETIC_001",
        source_round="ROUND1",
        source_condition="P4-R1-Q2-BAD-TRAIN17",
        relevant_start_model_call_index=1,
        registered_failure_onset_model_call_index=1,
        final_model_call_index=1,
        registered_recovery_start_model_call_index=None,
        registered_recovery_final_model_call_index=None,
    )
    early_registration = module.RegisteredFailureSequenceWindowV1(
        schema_id="REGISTERED_FAILURE_SEQUENCE_WINDOW_V1",
        schema_version=1,
        registration_id="REG-T4-EARLY",
        registration_authority_type="REGISTERED_BOUNDARY_LABEL",
        registration_protocol_id="SYNTHETIC_TEST_V1",
        registration_artifact_sha256="c" * 64,
        registration_record_sha256="e" * 64,
        source_bundle_sha256=bundle.attempt_bundle_sha256,
        source_attempt_id="ATTEMPT_SYNTHETIC_001",
        source_task_id="TASK_SYNTHETIC_001",
        source_round="ROUND1",
        source_condition="P4-R1-Q2-BAD-TRAIN17",
        relevant_start_model_call_index=0,
        registered_failure_onset_model_call_index=0,
        final_model_call_index=0,
        registered_recovery_start_model_call_index=None,
        registered_recovery_final_model_call_index=None,
    )
    return source, binding, terminal_registration, early_registration


def test_task4_reconstruction_symbol_exists() -> None:
    _require_task4_symbols()


def test_task4_builds_complete_preceding_prefix_binding() -> None:
    module = _require_task4_symbols()
    source, binding, registration, _ = _t4_fixture(module)
    experience = module.build_sequence_failure_experience_v1(
        source=source,
        task_access_binding=binding,
        registration=registration,
    )
    assert experience.relevant_start.model_call_index == 1
    assert experience.relevant_start.required_preceding_model_call_range == (0, 0)
    assert len(experience.relevant_start.required_preceding_prefix_source_binding) == 1
    assert experience.observed_sequence[0].model_call_index == 1


def test_task4_terminal_fields_only_when_registered_end_is_episode_end() -> None:
    module = _require_task4_symbols()
    source, binding, terminal_registration, early_registration = _t4_fixture(module)
    terminal = module.build_sequence_failure_experience_v1(
        source=source,
        task_access_binding=binding,
        registration=terminal_registration,
    )
    assert terminal.observed_end.episode_terminal_disposition == "INCLUDED_REGISTERED_WINDOW"
    assert terminal.observed_end.final_success is False
    early = module.build_sequence_failure_experience_v1(
        source=source,
        task_access_binding=binding,
        registration=early_registration,
    )
    assert early.observed_end.episode_terminal_disposition == "OUTSIDE_REGISTERED_WINDOW"
    assert early.observed_end.final_success is None
    assert early.observed_end.final_budget is None


def test_task4_nonexecuted_event_has_no_public_transition_pointer() -> None:
    module = _require_task4_symbols()
    source, binding, registration, _ = _t4_fixture(module)
    experience = module.build_sequence_failure_experience_v1(
        source=source,
        task_access_binding=binding,
        registration=registration,
    )
    event = experience.observed_sequence[0]
    assert event.execution_status == "not_executed"
    assert event.environment_step_index is None
    assert event.public_transition_source_pointer is None
    assert event.visible_state_change_disposition == "NONEXECUTED"


def test_task4_reconstruction_is_byte_deterministic() -> None:
    module = _require_task4_symbols()
    source, binding, registration, _ = _t4_fixture(module)
    first = module.build_sequence_failure_experience_v1(
        source=source,
        task_access_binding=binding,
        registration=registration,
    )
    second = module.build_sequence_failure_experience_v1(
        source=source,
        task_access_binding=binding,
        registration=registration,
    )
    assert first == second
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.experience_id == second.experience_id

# ==========================================================================
# TASK4_PLAN_CONFORMANCE_SUPPLEMENT_V1
# Deterministic factual reconstruction frozen-plan coverage.
# ==========================================================================


def _t4_plan_full_registration(
    module,
    *,
    source,
    template,
    registration_id: str,
    recovery_start=None,
    recovery_final=None,
):
    payload = template.to_dict()

    payload.update(
        {
            "registration_id":
                registration_id,
            "registration_record_sha256":
                _t3_sha256_text(
                    registration_id
                ),
            "source_bundle_sha256":
                source.attempt_bundle.attempt_bundle_sha256,
            "relevant_start_model_call_index":
                0,
            "registered_failure_onset_model_call_index":
                0,
            "final_model_call_index":
                len(source.traces) - 1,
            "registered_recovery_start_model_call_index":
                recovery_start,
            "registered_recovery_final_model_call_index":
                recovery_final,
        }
    )

    return (
        module.RegisteredFailureSequenceWindowV1(
            **payload
        )
    )


def _t4_plan_executed_final_fixture(module):
    source, binding, terminal_registration, _ = (
        _t4_fixture(module)
    )

    trace0 = source.traces[0]
    policy0 = source.policy_calls[0]

    prompt1 = _t3_build_raw_policy_prompt(
        public_task_goal="goal",
        observation="obs",
        executed_transitions=(),
        admissible_commands=("look",),
        interface_feedback=(
            _T4InterfaceFeedbackCode
            .FORMAT_ERROR_V1
        ),
    )

    provenance1 = _t3_replace(
        trace0.provenance,
        provider_request_id="provider-1",
        timestamp_utc="2026-08-17T00:00:02Z",
    )

    trace1 = _T3ActionTrace.build(
        provenance=provenance1,
        pipeline_variant=(
            _T3PipelineVariant.RAW_V1
        ),
        model_call_index=1,
        environment_step_index=0,
        execution_status=(
            _T3ExecutionStatus.EXECUTED
        ),
        public_task_goal="goal",
        observation="obs",
        prompt_text=prompt1,
        admissible_commands=("look",),
        raw_model_response='{"action":"look"}',
        literal_action="look",
        parsed_phase=None,
        model_reason=None,
        parser_status="success",
        parser_error=None,
        parser_metadata={},
        literal_action_exactly_admissible=True,
        literal_action_casefold_admissible=True,
        stages=(),
        final_executed_action="look",
        final_action_admissible=True,
        attempt_outcome="ACTION_EXECUTED",
        failure_stage=None,
        failure_code=None,
        normalized_action="look",
        admissibility_status="exact_member",
        feedback_code=None,
        policy_attempt_count_before=1,
        policy_attempt_count_after=2,
        environment_step_count_before=0,
        environment_step_count_after=1,
        protocol_failure_count=1,
        inadmissible_action_count=0,
        consecutive_nonexecuted_attempt_count=0,
        episode_termination_reason=(
            "ENVIRONMENT_TERMINATED"
        ),
        submitted_environment_action="look",
        resulting_observation="after",
        protocol_failure_count_before=1,
        inadmissible_action_count_before=0,
        consecutive_nonexecuted_attempt_count_before=1,
    )

    budget1 = (
        ("policy_attempt_count", 1),
        ("environment_step_count", 0),
        ("protocol_failure_count", 1),
        ("inadmissible_action_count", 0),
        (
            "consecutive_nonexecuted_attempt_count",
            1,
        ),
    )

    policy1 = _t4_policy_call(
        index=1,
        raw_text='{"action":"look"}',
        prompt=prompt1,
        feedback="FORMAT_ERROR_V1",
        budget_before=budget1,
    )

    transition = (
        _T3PlanPublicTransitionRecordV1(
            schema_id=(
                "E1_PUBLIC_TRANSITION_RECORD_V1"
            ),
            schema_version=1,
            scheduled_cell_id="cell",
            execution_attempt_id=(
                "ATTEMPT_SYNTHETIC_001"
            ),
            model_call_index=1,
            environment_step_index=0,
            submitted_action="look",
            pre_action_observation="obs",
            pre_action_observation_sha256=(
                _t3_sha256_text("obs")
            ),
            pre_action_admissible_commands=(
                "look",
            ),
            pre_action_admissible_commands_sha256=(
                _t3_sha256_string_sequence(
                    ("look",)
                )
            ),
            resulting_observation="after",
            resulting_observation_sha256=(
                _t3_sha256_text("after")
            ),
            resulting_admissible_commands=(
                "inventory",
            ),
            resulting_admissible_commands_sha256=(
                _t3_sha256_string_sequence(
                    ("inventory",)
                )
            ),
            done=True,
            won=True,
            score=1,
            pre_action_visibility=(
                "POLICY_VISIBLE_BEFORE_ACTION"
            ),
            resulting_visibility=(
                "POST_ACTION_PUBLIC_AUDIT_ONLY"
            ),
        )
    )

    episode = _t3_replace(
        source.episode_artifact,
        scientific_outcome_status=(
            "SCIENTIFIC_OUTCOME_COMPLETE_TASK_SUCCESS"
        ),
        success=True,
        termination_reason=(
            "ENVIRONMENT_TERMINATED"
        ),
        final_score=1,
        final_done=True,
        final_won=True,
        final_budget=_T3BudgetSnapshotV1(
            policy_attempt_count=2,
            environment_step_count=1,
            protocol_failure_count=1,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        ),
        trace_count=2,
        public_transition_count=1,
        environment_call_trace_count=1,
        final_observation_sha256=(
            _t3_sha256_text("after")
        ),
        completed_at_utc=(
            "2026-08-17T00:00:03Z"
        ),
    )

    bundle = _t3_build_attempt_bundle_bytes(
        episode_artifact=episode,
        traces=(trace0, trace1),
        policy_calls=(policy0, policy1),
        public_transitions=(transition,),
    )

    executed_source = (
        module.SequenceSourceEvidenceV1(
            episode_artifact=episode,
            traces=(trace0, trace1),
            policy_calls=(policy0, policy1),
            public_transitions=(
                transition,
            ),
            attempt_bundle=bundle,
            task_access_record_line_index=(
                source
                .task_access_record_line_index
            ),
            task_access_record_bytes=(
                source
                .task_access_record_bytes
            ),
        )
    )

    registration = (
        module.RegisteredFailureSequenceWindowV1(
            **{
                **terminal_registration.to_dict(),
                "registration_id":
                    "REG-T4-EXECUTED",
                "registration_record_sha256":
                    _t3_sha256_text(
                        "REG-T4-EXECUTED"
                    ),
                "source_bundle_sha256":
                    bundle.attempt_bundle_sha256,
                "relevant_start_model_call_index":
                    1,
                "registered_failure_onset_model_call_index":
                    1,
                "final_model_call_index":
                    1,
            }
        )
    )

    return (
        executed_source,
        binding,
        registration,
    )


def test_task4_plan_preserves_exact_registered_call_order() -> None:
    module = _require_task4_symbols()

    source, binding, terminal, _ = (
        _t4_fixture(module)
    )

    registration = (
        _t4_plan_full_registration(
            module,
            source=source,
            template=terminal,
            registration_id=(
                "REG-T4-ORDER"
            ),
        )
    )

    experience = (
        module
        .build_sequence_failure_experience_v1(
            source=source,
            task_access_binding=binding,
            registration=registration,
        )
    )

    assert (
        experience.relevant_start.model_call_index
        == 0
    )

    assert tuple(
        event.model_call_index
        for event in experience.observed_sequence
    ) == (0, 1)

    assert tuple(
        event.raw_model_response
        for event in experience.observed_sequence
    ) == (
        "not-json",
        "not-json-2",
    )

    assert (
        experience.observed_end.model_call_index
        == 1
    )


def test_task4_plan_missing_policy_attempt_inside_range_rejected() -> None:
    module = _require_task4_symbols()

    source, binding, terminal, _ = (
        _t4_fixture(module)
    )

    registration = (
        _t4_plan_full_registration(
            module,
            source=source,
            template=terminal,
            registration_id=(
                "REG-T4-MISSING-POLICY"
            ),
        )
    )

    bad_source = _t3_plan_corrupt(
        source,
        policy_calls=(
            source.policy_calls[0],
        ),
    )

    with pytest.raises(
        ValueError,
        match="policy call count",
    ):
        module.build_sequence_failure_experience_v1(
            source=bad_source,
            task_access_binding=binding,
            registration=registration,
        )


def test_task4_plan_does_not_invent_unregistered_recovery() -> None:
    module = _require_task4_symbols()

    source, binding, terminal, _ = (
        _t4_fixture(module)
    )

    registration = (
        _t4_plan_full_registration(
            module,
            source=source,
            template=terminal,
            registration_id=(
                "REG-T4-NO-RECOVERY"
            ),
        )
    )

    experience = (
        module
        .build_sequence_failure_experience_v1(
            source=source,
            task_access_binding=binding,
            registration=registration,
        )
    )

    assert (
        experience
        .registration_binding
        .registered_recovery_start_model_call_index
        is None
    )

    assert (
        experience
        .registration_binding
        .registered_recovery_final_model_call_index
        is None
    )

    assert (
        "recovery"
        not in experience.to_dict()
    )


def test_task4_plan_preserves_registered_recovery_range_without_widening() -> None:
    module = _require_task4_symbols()

    source, binding, terminal, _ = (
        _t4_fixture(module)
    )

    registration = (
        _t4_plan_full_registration(
            module,
            source=source,
            template=terminal,
            registration_id=(
                "REG-T4-RECOVERY"
            ),
            recovery_start=1,
            recovery_final=1,
        )
    )

    experience = (
        module
        .build_sequence_failure_experience_v1(
            source=source,
            task_access_binding=binding,
            registration=registration,
        )
    )

    assert (
        experience
        .registration_binding
        .registered_recovery_start_model_call_index
        == 1
    )

    assert (
        experience
        .registration_binding
        .registered_recovery_final_model_call_index
        == 1
    )

    assert tuple(
        event.model_call_index
        for event in experience.observed_sequence
    ) == (0, 1)


def test_task4_plan_terminal_fields_are_complete_when_episode_end_included() -> None:
    module = _require_task4_symbols()

    source, binding, terminal, _ = (
        _t4_fixture(module)
    )

    experience = (
        module
        .build_sequence_failure_experience_v1(
            source=source,
            task_access_binding=binding,
            registration=terminal,
        )
    )

    end = experience.observed_end

    assert (
        end.episode_terminal_disposition
        == "INCLUDED_REGISTERED_WINDOW"
    )

    assert end.termination_reason is not None
    assert end.final_success is not None
    assert end.final_done is not None
    assert end.final_won is not None
    assert end.final_budget is not None


def test_task4_plan_source_hashes_and_record_pointers_are_exact() -> None:
    module = _require_task4_symbols()

    source, binding, terminal, _ = (
        _t4_fixture(module)
    )

    experience = (
        module
        .build_sequence_failure_experience_v1(
            source=source,
            task_access_binding=binding,
            registration=terminal,
        )
    )

    expected_member_hashes = tuple(
        (
            name,
            _t3_sha256_bytes(data),
        )
        for name, data
        in source.attempt_bundle.file_bytes()
    )

    assert (
        experience.source_bundle_member_sha256
        == expected_member_hashes
    )

    assert (
        experience
        .relevant_start
        .required_preceding_prefix_source_binding[0]
        .zero_based_line_index
        == 0
    )

    event = experience.observed_sequence[0]

    assert (
        event.trace_source_pointer
        .zero_based_line_index
        == 1
    )

    assert (
        event.policy_call_source_pointer
        .zero_based_line_index
        == 1
    )

    assert (
        event.trace_source_pointer
        .exact_record_sha256
        ==
        _t3_sha256_bytes(
            source
            .attempt_bundle
            .action_traces_jsonl
            .splitlines(
                keepends=True
            )[1]
        )
    )


def test_task4_plan_different_exact_source_bytes_change_experience_identity() -> None:
    module = _require_task4_symbols()

    source, binding, terminal, _ = (
        _t4_fixture(module)
    )

    first = (
        module
        .build_sequence_failure_experience_v1(
            source=source,
            task_access_binding=binding,
            registration=terminal,
        )
    )

    changed_episode = _t3_replace(
        source.episode_artifact,
        completed_at_utc=(
            "2026-08-17T00:00:09Z"
        ),
    )

    changed_bundle = (
        _t3_build_attempt_bundle_bytes(
            episode_artifact=changed_episode,
            traces=source.traces,
            policy_calls=source.policy_calls,
            public_transitions=(
                source.public_transitions
            ),
        )
    )

    changed_source = (
        module.SequenceSourceEvidenceV1(
            episode_artifact=changed_episode,
            traces=source.traces,
            policy_calls=source.policy_calls,
            public_transitions=(
                source.public_transitions
            ),
            attempt_bundle=changed_bundle,
            task_access_record_line_index=(
                source
                .task_access_record_line_index
            ),
            task_access_record_bytes=(
                source
                .task_access_record_bytes
            ),
        )
    )

    changed_registration = (
        module.RegisteredFailureSequenceWindowV1(
            **{
                **terminal.to_dict(),
                "source_bundle_sha256":
                    changed_bundle
                    .attempt_bundle_sha256,
            }
        )
    )

    second = (
        module
        .build_sequence_failure_experience_v1(
            source=changed_source,
            task_access_binding=binding,
            registration=changed_registration,
        )
    )

    assert (
        first.experience_id
        != second.experience_id
    )

    assert (
        first.canonical_bytes()
        != second.canonical_bytes()
    )


def test_task4_plan_environment_indices_and_visible_change_are_source_derived() -> None:
    module = _require_task4_symbols()

    source, binding, registration = (
        _t4_plan_executed_final_fixture(
            module
        )
    )

    experience = (
        module
        .build_sequence_failure_experience_v1(
            source=source,
            task_access_binding=binding,
            registration=registration,
        )
    )

    assert (
        len(experience.observed_sequence)
        == 1
    )

    event = experience.observed_sequence[0]

    # Model call 1 executed environment step 0.
    # Therefore environment-step identity is not
    # inferred from model-call arithmetic.
    assert event.model_call_index == 1
    assert event.environment_step_index == 0

    assert (
        experience
        .included_environment_step_indices
        == (0,)
    )

    assert (
        event.visible_state_change_disposition
        ==
        "OBSERVATION_AND_MENU_CHANGED"
    )

    assert event.score == 1
    assert event.done is True
    assert event.won is True

    assert (
        event
        .public_transition_source_pointer
        is not None
    )

    assert (
        event
        .public_transition_source_pointer
        .zero_based_line_index
        == 0
    )

# ==========================================================================
# Unit 2 / Task 5 — Read-only materializer candidate and static audit
# ==========================================================================

import ast as _t5_ast
import importlib.util as _t5_importlib_util
import os as _t5_os
from pathlib import Path as _T5Path


def _load_task5_materializer():
    path = _T5Path("scripts/memory/materialize_sequence_failure_experience_v1.py")
    if not path.is_file():
        pytest.fail("TASK5_RED_MISSING_MATERIALIZER")
    spec = _t5_importlib_util.spec_from_file_location("task5_materializer", path)
    assert spec is not None and spec.loader is not None
    module = _t5_importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_task5_materializer_exists() -> None:
    _load_task5_materializer()


def test_task5_prevalidated_write_is_no_clobber(tmp_path) -> None:
    module = _require_task4_symbols()
    materializer = _load_task5_materializer()
    source, binding, registration, _ = _t4_fixture(module)
    experience = module.build_sequence_failure_experience_v1(
        source=source,
        task_access_binding=binding,
        registration=registration,
    )
    output = tmp_path / "experience.json"
    materializer.materialize_prevalidated_v1(
        experience=experience,
        output_path=output,
    )
    assert output.read_bytes() == experience.canonical_bytes()
    with pytest.raises(FileExistsError):
        materializer.materialize_prevalidated_v1(
            experience=experience,
            output_path=output,
        )


def test_task5_symlink_output_is_rejected(tmp_path) -> None:
    module = _require_task4_symbols()
    materializer = _load_task5_materializer()
    source, binding, registration, _ = _t4_fixture(module)
    experience = module.build_sequence_failure_experience_v1(
        source=source,
        task_access_binding=binding,
        registration=registration,
    )
    target = tmp_path / "target.json"
    target.write_text("existing", encoding="utf-8")
    link = tmp_path / "experience.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        materializer.materialize_prevalidated_v1(
            experience=experience,
            output_path=link,
        )


def test_task5_wrong_protected_manifest_identity_is_rejected(tmp_path) -> None:
    materializer = _load_task5_materializer()
    manifest = tmp_path / "task_access.jsonl"
    manifest.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="protected task-access manifest SHA"):
        materializer.require_protected_task_access_manifest_v1(manifest)


def test_task5_missing_policy_calls_bundle_is_rejected(tmp_path) -> None:
    module = _require_task3_symbols()
    materializer = _load_task5_materializer()
    source, _, _ = _t3_fixture(module)
    legacy = _t3_build_attempt_bundle_bytes(
        episode_artifact=source.episode_artifact,
        traces=source.traces,
        public_transitions=source.public_transitions,
        policy_calls=None,
    )
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    for name, data in legacy.file_bytes():
        (attempt_dir / name).write_bytes(data)
    with pytest.raises(ValueError, match="POLICY_CALL_EVIDENCE_REQUIRED"):
        materializer.load_attempt_directory_v1(attempt_dir)


def test_task5_static_import_surface_has_no_execution_integrations() -> None:
    path = _T5Path("scripts/memory/materialize_sequence_failure_experience_v1.py")
    if not path.is_file():
        pytest.fail("TASK5_RED_MISSING_MATERIALIZER")
    tree = _t5_ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden = {"alfworld", "openai", "anthropic", "vllm", "torch", "transformers"}
    observed = set()
    for node in _t5_ast.walk(tree):
        if isinstance(node, _t5_ast.Import):
            for alias in node.names:
                observed.add(alias.name.split(".")[0])
        elif isinstance(node, _t5_ast.ImportFrom) and node.module:
            observed.add(node.module.split(".")[0])
    assert not (observed & forbidden)

# ==========================================================================
# TASK5_PLAN_CONFORMANCE_SUPPLEMENT_V1
# Read-only offline materializer frozen-plan conformance coverage.
# ==========================================================================


def _t5_plan_write_attempt_dir(
    *,
    tmp_path,
    source,
    dirname: str,
    name_order=None,
):
    materializer_files = tuple(
        source.attempt_bundle.file_bytes()
    )
    data_by_name = dict(materializer_files)

    if name_order is None:
        names = tuple(
            name
            for name, _ in materializer_files
        )
    else:
        names = tuple(name_order)

    attempt_dir = tmp_path / dirname
    attempt_dir.mkdir()

    for name in names:
        (attempt_dir / name).write_bytes(
            data_by_name[name]
        )

    return attempt_dir


def test_task5_plan_non_train_memory_source_role_is_rejected() -> None:
    materializer = _load_task5_materializer()

    record_bytes = _t3_canonical_json_bytes(
        {
            "access_class":
                "TRAIN_RETRIEVAL_DEV",
        }
    )

    with pytest.raises(
        ValueError,
        match="TRAIN_MEMORY_SOURCE",
    ):
        materializer._binding_from_manifest_line(
            manifest_bytes=record_bytes,
            line_index=0,
        )


def test_task5_plan_missing_non_policy_bundle_member_is_rejected(
    tmp_path,
) -> None:
    module = _require_task4_symbols()
    materializer = _load_task5_materializer()

    source, _, _, _ = _t4_fixture(module)

    attempt_dir = _t5_plan_write_attempt_dir(
        tmp_path=tmp_path,
        source=source,
        dirname="attempt_missing",
    )

    (attempt_dir / "attempt.json").unlink()

    with pytest.raises(
        ValueError,
        match="files mismatch",
    ):
        materializer.load_attempt_directory_v1(
            attempt_dir
        )


def test_task5_plan_extra_attempt_bundle_member_is_rejected(
    tmp_path,
) -> None:
    module = _require_task4_symbols()
    materializer = _load_task5_materializer()

    source, _, _, _ = _t4_fixture(module)

    attempt_dir = _t5_plan_write_attempt_dir(
        tmp_path=tmp_path,
        source=source,
        dirname="attempt_extra",
    )

    (attempt_dir / "unexpected.txt").write_text(
        "unexpected",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="files mismatch",
    ):
        materializer.load_attempt_directory_v1(
            attempt_dir
        )


def test_task5_plan_tampered_attempt_bundle_bytes_are_rejected(
    tmp_path,
) -> None:
    module = _require_task4_symbols()
    materializer = _load_task5_materializer()

    source, _, _, _ = _t4_fixture(module)

    attempt_dir = _t5_plan_write_attempt_dir(
        tmp_path=tmp_path,
        source=source,
        dirname="attempt_tampered",
    )

    checksum_path = (
        attempt_dir / "SHA256SUMS"
    )

    checksum_path.write_bytes(
        checksum_path.read_bytes()
        + b"#tampered\n"
    )

    with pytest.raises(
        ValueError,
        match="attempt bundle member bytes mismatch",
    ):
        materializer.load_attempt_directory_v1(
            attempt_dir
        )


def test_task5_plan_symlink_attempt_directory_is_rejected(
    tmp_path,
) -> None:
    module = _require_task4_symbols()
    materializer = _load_task5_materializer()

    source, _, _, _ = _t4_fixture(module)

    real_dir = _t5_plan_write_attempt_dir(
        tmp_path=tmp_path,
        source=source,
        dirname="attempt_real",
    )

    link = tmp_path / "attempt_link"
    link.symlink_to(
        real_dir,
        target_is_directory=True,
    )

    with pytest.raises(
        ValueError,
        match="symlink",
    ):
        materializer.load_attempt_directory_v1(
            link
        )


def test_task5_plan_filesystem_creation_order_does_not_change_source_identity(
    tmp_path,
) -> None:
    module = _require_task4_symbols()
    materializer = _load_task5_materializer()

    source, _, _, _ = _t4_fixture(module)

    names = tuple(
        name
        for name, _
        in source.attempt_bundle.file_bytes()
    )

    first_dir = _t5_plan_write_attempt_dir(
        tmp_path=tmp_path,
        source=source,
        dirname="attempt_forward",
        name_order=names,
    )

    second_dir = _t5_plan_write_attempt_dir(
        tmp_path=tmp_path,
        source=source,
        dirname="attempt_reverse",
        name_order=tuple(reversed(names)),
    )

    first = (
        materializer
        .load_attempt_directory_v1(
            first_dir
        )
    )

    second = (
        materializer
        .load_attempt_directory_v1(
            second_dir
        )
    )

    assert (
        first.attempt_bundle.attempt_bundle_sha256
        ==
        second.attempt_bundle.attempt_bundle_sha256
    )

    assert (
        first.attempt_bundle.file_bytes()
        ==
        second.attempt_bundle.file_bytes()
    )


def test_task5_plan_output_is_exact_canonical_bytes_and_round_trips(
    tmp_path,
) -> None:
    module = _require_task4_symbols()
    materializer = _load_task5_materializer()

    source, binding, registration, _ = (
        _t4_fixture(module)
    )

    experience = (
        module
        .build_sequence_failure_experience_v1(
            source=source,
            task_access_binding=binding,
            registration=registration,
        )
    )

    output = tmp_path / "experience.json"

    materializer.materialize_prevalidated_v1(
        experience=experience,
        output_path=output,
    )

    data = output.read_bytes()

    assert data == experience.canonical_bytes()
    assert data.endswith(b"\n")
    assert not data.endswith(b"\n\n")

    rebuilt = (
        module.SequenceFailureExperienceV1
        .from_json(data)
    )

    assert (
        rebuilt.canonical_bytes()
        == data
    )


def test_task5_plan_symlink_output_parent_is_rejected(
    tmp_path,
) -> None:
    module = _require_task4_symbols()
    materializer = _load_task5_materializer()

    source, binding, registration, _ = (
        _t4_fixture(module)
    )

    experience = (
        module
        .build_sequence_failure_experience_v1(
            source=source,
            task_access_binding=binding,
            registration=registration,
        )
    )

    real_parent = tmp_path / "real_parent"
    real_parent.mkdir()

    link_parent = tmp_path / "link_parent"
    link_parent.symlink_to(
        real_parent,
        target_is_directory=True,
    )

    with pytest.raises(
        ValueError,
        match="output parent",
    ):
        materializer.materialize_prevalidated_v1(
            experience=experience,
            output_path=(
                link_parent / "experience.json"
            ),
        )


def test_task5_plan_symlink_registration_is_rejected(
    tmp_path,
) -> None:
    module = _require_task4_symbols()
    materializer = _load_task5_materializer()

    _, _, registration, _ = (
        _t4_fixture(module)
    )

    target = tmp_path / "registration_real.json"
    target.write_bytes(
        _t3_canonical_json_bytes(
            registration.to_dict()
        )
    )

    link = tmp_path / "registration_link.json"
    link.symlink_to(target)

    with pytest.raises(
        ValueError,
        match="symlink",
    ):
        materializer._load_registration(
            link
        )


def test_task5_plan_registration_source_mismatch_fails_after_explicit_load(
    tmp_path,
) -> None:
    module = _require_task4_symbols()
    materializer = _load_task5_materializer()

    source, binding, registration, _ = (
        _t4_fixture(module)
    )

    attempt_dir = _t5_plan_write_attempt_dir(
        tmp_path=tmp_path,
        source=source,
        dirname="attempt_registration_mismatch",
    )

    loaded = (
        materializer
        .load_attempt_directory_v1(
            attempt_dir
        )
    )

    rebound = (
        module.SequenceSourceEvidenceV1(
            episode_artifact=(
                loaded.episode_artifact
            ),
            traces=loaded.traces,
            policy_calls=loaded.policy_calls,
            public_transitions=(
                loaded.public_transitions
            ),
            attempt_bundle=(
                loaded.attempt_bundle
            ),
            task_access_record_line_index=(
                source
                .task_access_record_line_index
            ),
            task_access_record_bytes=(
                source
                .task_access_record_bytes
            ),
        )
    )

    bad_registration = (
        module.RegisteredFailureSequenceWindowV1(
            **{
                **registration.to_dict(),
                "source_bundle_sha256":
                    "0" * 64,
            }
        )
    )

    with pytest.raises(
        ValueError,
        match="bundle",
    ):
        module.build_sequence_failure_experience_v1(
            source=rebound,
            task_access_binding=binding,
            registration=bad_registration,
        )


def test_task5_plan_static_surface_has_no_discovery_network_or_process_execution() -> None:
    materializer = _load_task5_materializer()

    script_path = _T5Path(
        materializer.__file__
    )

    tree = _t5_ast.parse(
        script_path.read_text(
            encoding="utf-8"
        ),
        filename=str(script_path),
    )

    forbidden_imports = {
        "subprocess",
        "socket",
        "requests",
        "httpx",
        "urllib",
        "glob",
    }

    observed_imports = set()

    forbidden_call_attributes = {
        "glob",
        "rglob",
        "walk",
        "system",
        "popen",
        "Popen",
        "run",
        "call",
        "check_call",
        "check_output",
    }

    observed_forbidden_calls = []

    for node in _t5_ast.walk(tree):
        if isinstance(node, _t5_ast.Import):
            for alias in node.names:
                observed_imports.add(
                    alias.name.split(".")[0]
                )

        elif (
            isinstance(node, _t5_ast.ImportFrom)
            and node.module
        ):
            observed_imports.add(
                node.module.split(".")[0]
            )

        elif isinstance(node, _t5_ast.Call):
            func = node.func

            if (
                isinstance(
                    func,
                    _t5_ast.Attribute,
                )
                and func.attr
                in forbidden_call_attributes
            ):
                observed_forbidden_calls.append(
                    func.attr
                )

    assert not (
        observed_imports
        & forbidden_imports
    )

    assert not observed_forbidden_calls


def test_task5_plan_cli_inputs_are_all_explicit_and_required() -> None:
    materializer = _load_task5_materializer()

    script_path = _T5Path(
        materializer.__file__
    )

    tree = _t5_ast.parse(
        script_path.read_text(
            encoding="utf-8"
        ),
        filename=str(script_path),
    )

    expected = {
        "--attempt-dir",
        "--registration",
        "--task-access-protected-manifest",
        "--task-access-record-line-index",
        "--output",
    }

    observed_required = set()

    for node in _t5_ast.walk(tree):
        if not isinstance(
            node,
            _t5_ast.Call,
        ):
            continue

        func = node.func

        if not (
            isinstance(
                func,
                _t5_ast.Attribute,
            )
            and func.attr
            == "add_argument"
        ):
            continue

        if not node.args:
            continue

        first = node.args[0]

        if not (
            isinstance(
                first,
                _t5_ast.Constant,
            )
            and isinstance(
                first.value,
                str,
            )
            and first.value.startswith("--")
        ):
            continue

        required = False

        for keyword in node.keywords:
            if (
                keyword.arg == "required"
                and isinstance(
                    keyword.value,
                    _t5_ast.Constant,
                )
                and keyword.value.value
                is True
            ):
                required = True

        if required:
            observed_required.add(
                first.value
            )

    assert observed_required == expected

# ==========================================================================
# UNIT2_FIXED_HEAD_SCHEMA_REVIEW_V1
#
# Independent fixed-head review correction:
# the committed Memory JSON Schema must be a strict wire contract, not only
# a shallow top-level shape.
# ==========================================================================

from pathlib import Path as _U2ReviewPath

from pchsi.evaluation.canonical_evidence import (
    strict_json_loads as _u2_review_strict_json_loads,
)
from pchsi.evaluation.schema_contract import (
    _validate_payload_node as _u2_review_validate_payload_node,
    validate_schema_definition as _u2_review_validate_schema_definition,
)


_U2_REVIEW_SCHEMA_PATH = _U2ReviewPath(
    "configs/memory/schemas/"
    "sequence_failure_experience_v1.json"
)


def _u2_review_schema():
    payload = _u2_review_strict_json_loads(
        _U2_REVIEW_SCHEMA_PATH.read_bytes()
    )

    assert isinstance(payload, dict)

    _u2_review_validate_schema_definition(
        payload
    )

    return payload


def test_unit2_review_schema_accepts_canonical_experience() -> None:
    module = _require_task2_symbols()

    schema = _u2_review_schema()

    experience = _task2_experience(module)

    _u2_review_validate_payload_node(
        experience.to_dict(),
        schema,
        "$",
    )


def test_unit2_review_schema_rejects_nested_semantic_mechanism() -> None:
    module = _require_task2_symbols()

    schema = _u2_review_schema()

    payload = _task2_experience(
        module
    ).to_dict()

    payload["observed_sequence"][0][
        "failure_mechanism"
    ] = "not-authorized"

    with pytest.raises(
        ValueError,
        match="unknown fields",
    ):
        _u2_review_validate_payload_node(
            payload,
            schema,
            "$",
        )


def test_unit2_review_schema_rejects_nested_recovery_advice() -> None:
    module = _require_task2_symbols()

    schema = _u2_review_schema()

    payload = _task2_experience(
        module
    ).to_dict()

    payload["registration_binding"][
        "recovery_advice"
    ] = "not-authorized"

    with pytest.raises(
        ValueError,
        match="unknown fields",
    ):
        _u2_review_validate_payload_node(
            payload,
            schema,
            "$",
        )


def test_unit2_review_schema_rejects_missing_event_field() -> None:
    module = _require_task2_symbols()

    schema = _u2_review_schema()

    payload = _task2_experience(
        module
    ).to_dict()

    del payload["observed_sequence"][0][
        "model_call_index"
    ]

    with pytest.raises(
        ValueError,
        match="missing required fields",
    ):
        _u2_review_validate_payload_node(
            payload,
            schema,
            "$",
        )

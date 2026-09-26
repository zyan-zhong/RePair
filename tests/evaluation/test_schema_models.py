from __future__ import annotations

from dataclasses import replace

import pytest

from pchsi.evaluation.canonical_evidence import canonical_json_bytes
from pchsi.evaluation.schema_contract import (
    load_schema,
    validate_model_against_schema,
)
from pchsi.evaluation.schema_models import (
    AttemptReceiptV1,
    BudgetSnapshotV1,
    EpisodeArtifactV1,
    PublicTransitionRecordV1,
    RunScheduleCellV1,
    RunScheduleV1,
    ScientificCellLockV1,
)


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64

P1_EPISODE_OPTIONAL_PROPERTIES = {
    "task_access_manifest_sha256",
    "policy_condition_manifest_sha256",
    "condition_run_schedule_sha256",
    "access_class",
    "policy_condition_id",
    "condition_cell_id",
}

SELECT_EPISODE_OPTIONAL_PROPERTIES = {
    "evaluation_context",
    "logical_condition_id",
    "checkpoint_instance_id",
    "training_seed",
    "select_policy_runtime_manifest_sha256",
}

ALL_EPISODE_OPTIONAL_PROPERTIES = (
    P1_EPISODE_OPTIONAL_PROPERTIES
    | SELECT_EPISODE_OPTIONAL_PROPERTIES
)


def _models() -> tuple[object, ...]:
    public = PublicTransitionRecordV1(
        schema_id="E1_PUBLIC_TRANSITION_RECORD_V1",
        schema_version=1,
        scheduled_cell_id="e1-t0000-s0000000017",
        execution_attempt_id="e1-t0000-s0000000017-a000",
        model_call_index=0,
        environment_step_index=0,
        submitted_action="look",
        pre_action_observation="before",
        pre_action_observation_sha256=DIGEST_A,
        pre_action_admissible_commands=("look", "inventory"),
        pre_action_admissible_commands_sha256=DIGEST_B,
        resulting_observation="after",
        resulting_observation_sha256=DIGEST_A,
        resulting_admissible_commands=("inventory",),
        resulting_admissible_commands_sha256=DIGEST_B,
        done=False,
        won=False,
        score=0,
        pre_action_visibility="POLICY_VISIBLE_BEFORE_ACTION",
        resulting_visibility="POST_ACTION_PUBLIC_AUDIT_ONLY",
    )

    started = AttemptReceiptV1(
        schema_id="E1_ATTEMPT_RECEIPT_V1",
        schema_version=1,
        receipt_kind="STARTED",
        run_id="run-1",
        scheduled_cell_id="e1-t0000-s0000000017",
        execution_attempt_id="e1-t0000-s0000000017-a000",
        attempt_ordinal=0,
        evaluator_commit="commit",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        run_schedule_sha256=DIGEST_A,
        scientific_outcome_status="SCIENTIFIC_OUTCOME_NOT_PRODUCED",
        operational_finalization_status="STAGING",
        episode_semantic_sha256=None,
        attempt_bundle_sha256=None,
        terminal_class=None,
        error_code=None,
        created_at_utc="2026-08-06T00:00:00Z",
    )

    lock = ScientificCellLockV1(
        schema_id="E1_SCIENTIFIC_CELL_LOCK_V1",
        schema_version=1,
        run_id="run-1",
        scheduled_cell_id="e1-t0000-s0000000017",
        execution_attempt_id="e1-t0000-s0000000017-a000",
        run_schedule_sha256=DIGEST_A,
        episode_semantic_sha256=DIGEST_B,
        attempt_bundle_sha256=DIGEST_A,
        scientific_outcome_status=(
            "SCIENTIFIC_OUTCOME_COMPLETE_SUCCESS"
        ),
        evaluator_commit="commit",
    )

    budget = BudgetSnapshotV1(
        policy_attempt_count=1,
        environment_step_count=1,
        protocol_failure_count=0,
        inadmissible_action_count=0,
        consecutive_nonexecuted_attempt_count=0,
    )

    episode = EpisodeArtifactV1(
        schema_id="E1_EPISODE_ARTIFACT_V1",
        schema_version=1,
        run_id="run-1",
        scheduled_cell_id="e1-t0000-s0000000017",
        execution_attempt_id="e1-t0000-s0000000017-a000",
        attempt_ordinal=0,
        task_index=0,
        task_id="alfworld_valid_unseen_all134_0000",
        task_type="look_at_obj_in_light",
        gamefile_sha1="a" * 40,
        gamefile_sha256=DIGEST_A,
        seed=17,
        evaluator_commit="commit",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        raw_protocol_sha256=DIGEST_A,
        split_access_sha256=DIGEST_A,
        gamefile_identity_manifest_sha256=DIGEST_A,
        environment_runtime_manifest_sha256=DIGEST_A,
        policy_runtime_manifest_sha256=DIGEST_A,
        policy_request_schema_sha256=DIGEST_A,
        scientific_outcome_status=(
            "SCIENTIFIC_OUTCOME_COMPLETE_SUCCESS"
        ),
        operational_finalization_status="PUBLISHED",
        success=True,
        termination_reason="ENVIRONMENT_TERMINATED",
        final_score=1,
        final_done=True,
        final_won=True,
        final_budget=budget,
        trace_count=1,
        public_transition_count=1,
        environment_call_trace_count=1,
        initial_observation_sha256=DIGEST_A,
        final_observation_sha256=DIGEST_B,
        episode_semantic_sha256=DIGEST_A,
        started_at_utc="2026-08-06T00:00:00Z",
        completed_at_utc="2026-08-06T00:00:01Z",
    )

    cells = tuple(
        RunScheduleCellV1(
            scheduled_cell_id=(
                f"e1-t{task_index:04d}-s{seed:010d}"
            ),
            task_index=task_index,
            task_id=(
                "alfworld_valid_unseen_all134_"
                f"{task_index:04d}"
            ),
            seed=seed,
        )
        for seed in (17, 31, 47, 73, 101)
        for task_index in range(134)
    )

    schedule = RunScheduleV1(
        schema_id="E1_RUN_SCHEDULE_V1",
        schema_version=1,
        schedule_id="E1_RUN_SCHEDULE_V1",
        task_manifest_sha256=DIGEST_A,
        replicate_seeds=(17, 31, 47, 73, 101),
        order="seed-major",
        cell_count=670,
        primary_statistical_unit="unique_task",
        replicates_are_not_independent_tasks=True,
        pooled_670_iid_headline_result="forbidden",
        cells=cells,
    )

    return public, started, lock, episode, schedule


def test_python_model_keys_equal_schema_properties() -> None:
    for model in _models():
        payload = model.to_dict()
        schema = load_schema(model.SCHEMA_ID)

        if model.SCHEMA_ID == "E1_EPISODE_ARTIFACT_V1":
            assert ALL_EPISODE_OPTIONAL_PROPERTIES.isdisjoint(
                payload
            )
            assert set(payload) == (
                set(schema["properties"])
                - ALL_EPISODE_OPTIONAL_PROPERTIES
            )
        else:
            assert set(payload) == set(schema["properties"])


def test_p1_episode_model_emits_all_condition_properties() -> None:
    legacy_episode = _models()[3]
    condition_cell_id = (
        "p4-P4-R0-PI0-t00000-s0000000017"
    )

    p1_episode = replace(
        legacy_episode,
        scheduled_cell_id=condition_cell_id,
        execution_attempt_id=(
            condition_cell_id + "-a000"
        ),
        split_access_sha256="c" * 64,
        task_access_manifest_sha256="c" * 64,
        policy_condition_manifest_sha256="d" * 64,
        condition_run_schedule_sha256="e" * 64,
        access_class="DEV_VISIBLE",
        policy_condition_id="P4-R0-PI0",
        condition_cell_id=condition_cell_id,
    )

    payload = p1_episode.to_dict()
    schema = load_schema(p1_episode.SCHEMA_ID)

    assert set(payload) == (
        set(schema["properties"])
        - SELECT_EPISODE_OPTIONAL_PROPERTIES
    )

    assert (
        P1_EPISODE_OPTIONAL_PROPERTIES
        <= set(payload)
    )

    assert (
        SELECT_EPISODE_OPTIONAL_PROPERTIES
        .isdisjoint(payload)
    )

    validate_model_against_schema(p1_episode)

    restored = EpisodeArtifactV1.from_json(
        p1_episode.to_json()
    )
    assert restored == p1_episode


def test_all_schema_required_fields_are_produced() -> None:
    for model in _models():
        payload = model.to_dict()
        schema = load_schema(model.SCHEMA_ID)
        assert set(schema["required"]) <= set(payload)
        validate_model_against_schema(model)


def test_all_models_round_trip_without_changing_canonical_bytes() -> None:
    for model in _models():
        restored = type(model).from_json(model.to_json())
        assert type(restored) is type(model)
        assert restored == model
        assert canonical_json_bytes(restored.to_dict()) == (
            canonical_json_bytes(model.to_dict())
        )


def test_model_construction_rejects_schema_mismatch() -> None:
    public = _models()[0]

    with pytest.raises(ValueError):
        replace(public, model_call_index=True)

    with pytest.raises(ValueError):
        replace(public, pre_action_observation_sha256="BAD")

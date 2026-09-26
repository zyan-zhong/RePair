from __future__ import annotations

from pchsi.evaluation.action_trace import TraceProvenance
from pchsi.evaluation.schema_models import (
    BudgetSnapshotV1,
    EpisodeArtifactV1,
)

LOGICAL = "P4-R2-HUMAN-T2-DIAGNOSTIC"
CHECKPOINT = "P4-R2-HUMAN-T2-DIAGNOSTIC-TRAIN17"


def test_generic_trained_select_trace_accepts_candidate_identity() -> None:
    trace = TraceProvenance(
        run_id="candidate-run",
        task_id="task-2",
        episode_id="episode-2",
        replicate_id=0,
        arm_id=LOGICAL,
        code_commit="evaluator",
        config_sha256="a" * 64,
        provider="vllm",
        model_name=CHECKPOINT,
        model_version="b" * 64,
        provider_request_id="request",
        retry_count=0,
        timestamp_utc="2026-09-01T00:00:00Z",
        split_and_access_version="P4_SELECT_EVALUATION_LINEAGE_V1",
        split_name="valid_unseen",
        access_mode="TASK_ACCESS_MANIFEST_V1",
        policy_version=LOGICAL,
        seed=17,
        memory_version="MEMORY_M0_V1",
        memory_state_sha256="c" * 64,
        task_access_manifest_sha256="d" * 64,
        policy_condition_manifest_sha256="e" * 64,
        condition_run_schedule_sha256="f" * 64,
        access_class="SELECT_SUMMARY_ONLY",
        policy_condition_id=CHECKPOINT,
        condition_cell_id="candidate-cell",
        evaluation_context="P4_HARNESS_OFF_SELECT",
        logical_condition_id=LOGICAL,
        checkpoint_instance_id=CHECKPOINT,
        training_seed=17,
        select_policy_runtime_manifest_sha256="1" * 64,
    )
    assert trace.logical_condition_id == LOGICAL
    assert trace.model_name == CHECKPOINT


def test_generic_trained_select_episode_accepts_candidate_identity() -> None:
    episode = EpisodeArtifactV1(
        schema_id="E1_EPISODE_ARTIFACT_V1",
        schema_version=1,
        run_id="candidate-run",
        scheduled_cell_id="candidate-cell",
        execution_attempt_id="candidate-attempt",
        attempt_ordinal=0,
        task_index=2,
        task_id="task-2",
        task_type="pick_and_place_simple",
        gamefile_sha1="a" * 40,
        gamefile_sha256="b" * 64,
        seed=17,
        evaluator_commit="evaluator",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        raw_protocol_sha256="c" * 64,
        split_access_sha256="d" * 64,
        gamefile_identity_manifest_sha256="e" * 64,
        environment_runtime_manifest_sha256="f" * 64,
        policy_runtime_manifest_sha256="1" * 64,
        policy_request_schema_sha256="2" * 64,
        scientific_outcome_status="TASK_FAILURE",
        operational_finalization_status="PUBLISHED",
        success=False,
        termination_reason="BUDGET",
        final_score=0,
        final_done=False,
        final_won=False,
        final_budget=BudgetSnapshotV1(
            policy_attempt_count=1,
            environment_step_count=1,
            protocol_failure_count=0,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        ),
        trace_count=1,
        public_transition_count=1,
        environment_call_trace_count=1,
        initial_observation_sha256="3" * 64,
        final_observation_sha256="4" * 64,
        episode_semantic_sha256="5" * 64,
        started_at_utc="2026-09-01T00:00:00Z",
        completed_at_utc="2026-09-01T00:00:01Z",
        task_access_manifest_sha256="d" * 64,
        policy_condition_manifest_sha256="6" * 64,
        condition_run_schedule_sha256="7" * 64,
        access_class="SELECT_SUMMARY_ONLY",
        policy_condition_id=CHECKPOINT,
        condition_cell_id="candidate-cell",
        evaluation_context="P4_HARNESS_OFF_SELECT",
        logical_condition_id=LOGICAL,
        checkpoint_instance_id=CHECKPOINT,
        training_seed=17,
        select_policy_runtime_manifest_sha256="8" * 64,
    )
    assert episode.logical_condition_id == LOGICAL
    assert episode.checkpoint_instance_id == CHECKPOINT
    assert episode.to_dict()["logical_condition_id"] == LOGICAL

from __future__ import annotations

from dataclasses import replace

import pytest

from pchsi.evaluation.action_trace import (
    ActionTrace,
    ExecutionStatus,
    PipelineVariant,
    TraceProvenance,
)
from pchsi.evaluation.cell_lock import (
    CellLockMismatchError,
    build_scientific_cell_lock,
    validate_cell_lock_matches_bundle,
)
from pchsi.evaluation.episode_artifact import (
    build_attempt_bundle_bytes,
)
from pchsi.evaluation.schema_models import (
    BudgetSnapshotV1,
    EpisodeArtifactV1,
)


def _episode() -> EpisodeArtifactV1:
    return EpisodeArtifactV1(
        schema_id="E1_EPISODE_ARTIFACT_V1",
        schema_version=1,
        run_id="run-e1",
        scheduled_cell_id="e1-t0000-s0000000017",
        execution_attempt_id="e1-t0000-s0000000017-a000",
        attempt_ordinal=0,
        task_index=0,
        task_id="alfworld_valid_unseen_all134_0000",
        task_type="pick_and_place_simple",
        gamefile_sha1="b" * 40,
        gamefile_sha256="c" * 64,
        seed=17,
        evaluator_commit="evaluator",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        raw_protocol_sha256="a" * 64,
        split_access_sha256="a" * 64,
        gamefile_identity_manifest_sha256="a" * 64,
        environment_runtime_manifest_sha256="a" * 64,
        policy_runtime_manifest_sha256="a" * 64,
        policy_request_schema_sha256="a" * 64,
        scientific_outcome_status=(
            "SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE"
        ),
        operational_finalization_status="PUBLISHED",
        success=False,
        termination_reason="POLICY_ATTEMPT_BUDGET_EXHAUSTED",
        final_score=None,
        final_done=False,
        final_won=False,
        final_budget=BudgetSnapshotV1(
            policy_attempt_count=1,
            environment_step_count=0,
            protocol_failure_count=1,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=1,
        ),
        trace_count=1,
        public_transition_count=0,
        environment_call_trace_count=0,
        initial_observation_sha256="d" * 64,
        final_observation_sha256="d" * 64,
        episode_semantic_sha256="e" * 64,
        started_at_utc="2026-08-07T00:00:00Z",
        completed_at_utc="2026-08-07T00:00:01Z",
    )


def _trace() -> ActionTrace:
    return ActionTrace.build(
        provenance=TraceProvenance(
            run_id="run-e1",
            task_id="alfworld_valid_unseen_all134_0000",
            episode_id="e1-t0000-s0000000017-a000",
            replicate_id=0,
            arm_id="R0_RAW_WITH_MENU_V1",
            code_commit="commit",
            config_sha256="a" * 64,
            provider="vllm",
            model_name="Qwen2.5-3B-Instruct-E1",
            model_version="revision",
            provider_request_id="provider",
            retry_count=0,
            timestamp_utc="2026-08-07T00:00:00Z",
        ),
        pipeline_variant=PipelineVariant.RAW_V1,
        model_call_index=0,
        environment_step_index=None,
        execution_status=ExecutionStatus.NOT_EXECUTED,
        public_task_goal="goal",
        observation="initial",
        prompt_text="prompt",
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
    )


def test_cell_lock_and_bundle_match_bidirectionally() -> None:
    bundle = build_attempt_bundle_bytes(
        episode_artifact=_episode(),
        traces=(_trace(),),
        public_transitions=(),
    )
    corrected = EpisodeArtifactV1.from_json(
        bundle.attempt_json
    )
    lock = build_scientific_cell_lock(
        episode_artifact=corrected,
        bundle=bundle,
        run_schedule_sha256="a" * 64,
    )

    validate_cell_lock_matches_bundle(
        lock=lock,
        episode_artifact=corrected,
        bundle=bundle,
    )

    assert lock.scheduled_cell_id == corrected.scheduled_cell_id
    assert lock.execution_attempt_id == corrected.execution_attempt_id
    assert lock.episode_semantic_sha256 == (
        bundle.episode_semantic_sha256
    )
    assert lock.attempt_bundle_sha256 == (
        bundle.attempt_bundle_sha256
    )

    with pytest.raises(CellLockMismatchError):
        validate_cell_lock_matches_bundle(
            lock=replace(
                lock,
                attempt_bundle_sha256="f" * 64,
            ),
            episode_artifact=corrected,
            bundle=bundle,
        )

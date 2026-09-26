from __future__ import annotations

from dataclasses import replace

import pytest

from pchsi.evaluation.action_trace import (
    ActionTrace,
    ExecutionStatus,
    PipelineVariant,
    TraceProvenance,
)
from pchsi.evaluation.episode_artifact import (
    build_attempt_bundle_bytes,
)
from pchsi.evaluation.schema_models import (
    BudgetSnapshotV1,
    EpisodeArtifactV1,
)

DIGEST = "a" * 64


def _trace(
    *,
    model_call_index: int,
    provider_request_id: str,
    timestamp_utc: str,
    episode_id: str,
) -> ActionTrace:
    provenance = TraceProvenance(
        run_id="run-e1",
        task_id="alfworld_valid_unseen_all134_0000",
        episode_id=episode_id,
        replicate_id=0,
        arm_id="R0_RAW_WITH_MENU_V1",
        code_commit="commit",
        config_sha256=DIGEST,
        provider="vllm",
        model_name="Qwen2.5-3B-Instruct-E1",
        model_version="revision",
        provider_request_id=provider_request_id,
        retry_count=0,
        timestamp_utc=timestamp_utc,
    )
    return ActionTrace.build(
        provenance=provenance,
        pipeline_variant=PipelineVariant.RAW_V1,
        model_call_index=model_call_index,
        environment_step_index=None,
        execution_status=ExecutionStatus.NOT_EXECUTED,
        public_task_goal="put the object away",
        observation="initial",
        prompt_text="RAW_POLICY_PROMPT_V1",
        admissible_commands=("look", "inventory"),
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


def _episode(
    *,
    attempt_ordinal: int = 0,
    operational: str = "PUBLISHED",
    started: str = "2026-08-07T00:00:00Z",
    completed: str = "2026-08-07T00:00:01Z",
) -> EpisodeArtifactV1:
    return EpisodeArtifactV1(
        schema_id="E1_EPISODE_ARTIFACT_V1",
        schema_version=1,
        run_id="run-e1",
        scheduled_cell_id="e1-t0000-s0000000017",
        execution_attempt_id=(
            "e1-t0000-s0000000017-"
            f"a{attempt_ordinal:03d}"
        ),
        attempt_ordinal=attempt_ordinal,
        task_index=0,
        task_id="alfworld_valid_unseen_all134_0000",
        task_type="pick_and_place_simple",
        gamefile_sha1="b" * 40,
        gamefile_sha256="c" * 64,
        seed=17,
        evaluator_commit="evaluator",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        raw_protocol_sha256=DIGEST,
        split_access_sha256=DIGEST,
        gamefile_identity_manifest_sha256=DIGEST,
        environment_runtime_manifest_sha256=DIGEST,
        policy_runtime_manifest_sha256=DIGEST,
        policy_request_schema_sha256=DIGEST,
        scientific_outcome_status=(
            "SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE"
        ),
        operational_finalization_status=operational,
        success=False,
        termination_reason=(
            "POLICY_ATTEMPT_BUDGET_EXHAUSTED"
        ),
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
        started_at_utc=started,
        completed_at_utc=completed,
    )


def test_bundle_bytes_are_deterministic_and_jsonl_ordered() -> None:
    trace = _trace(
        model_call_index=0,
        provider_request_id="provider-1",
        timestamp_utc="2026-08-07T00:00:00Z",
        episode_id="e1-t0000-s0000000017-a000",
    )
    one = build_attempt_bundle_bytes(
        episode_artifact=_episode(),
        traces=(trace,),
        public_transitions=(),
    )
    two = build_attempt_bundle_bytes(
        episode_artifact=_episode(),
        traces=(trace,),
        public_transitions=(),
    )

    assert one == two
    assert one.action_traces_jsonl == (
        trace.to_json().encode("utf-8") + b"\n"
    )
    assert one.public_transitions_jsonl == b""
    assert [name for name, _ in one.file_bytes()] == [
        "attempt.json",
        "action_traces.jsonl",
        "public_transitions.jsonl",
        "SHA256SUMS",
    ]

    second_trace = _trace(
        model_call_index=1,
        provider_request_id="provider-2",
        timestamp_utc="2026-08-07T00:00:01Z",
        episode_id="e1-t0000-s0000000017-a000",
    )
    with pytest.raises(ValueError, match="model_call_index"):
        build_attempt_bundle_bytes(
            episode_artifact=replace(
                _episode(),
                trace_count=2,
            ),
            traces=(second_trace, trace),
            public_transitions=(),
        )


def test_semantic_hash_ignores_operational_metadata() -> None:
    first_trace = _trace(
        model_call_index=0,
        provider_request_id="provider-A",
        timestamp_utc="2026-08-07T00:00:00Z",
        episode_id="e1-t0000-s0000000017-a000",
    )
    second_trace = _trace(
        model_call_index=0,
        provider_request_id="provider-B",
        timestamp_utc="2026-08-08T01:02:03Z",
        episode_id="e1-t0000-s0000000017-a009",
    )

    first = build_attempt_bundle_bytes(
        episode_artifact=_episode(
            attempt_ordinal=0,
            operational="PUBLISHED",
            started="2026-08-07T00:00:00Z",
            completed="2026-08-07T00:00:01Z",
        ),
        traces=(first_trace,),
        public_transitions=(),
    )
    second = build_attempt_bundle_bytes(
        episode_artifact=_episode(
            attempt_ordinal=9,
            operational="CLOSE_FAILED_RECORDED",
            started="2026-08-08T01:02:03Z",
            completed="2026-08-08T01:02:05Z",
        ),
        traces=(second_trace,),
        public_transitions=(),
    )

    assert (
        first.episode_semantic_sha256
        == second.episode_semantic_sha256
    )


def test_exact_bundle_hash_changes_with_exact_artifact_bytes() -> None:
    trace = _trace(
        model_call_index=0,
        provider_request_id="provider-A",
        timestamp_utc="2026-08-07T00:00:00Z",
        episode_id="e1-t0000-s0000000017-a000",
    )
    first = build_attempt_bundle_bytes(
        episode_artifact=_episode(),
        traces=(trace,),
        public_transitions=(),
    )
    second = build_attempt_bundle_bytes(
        episode_artifact=_episode(
            completed="2026-08-07T00:00:02Z"
        ),
        traces=(trace,),
        public_transitions=(),
    )

    assert (
        first.episode_semantic_sha256
        == second.episode_semantic_sha256
    )
    assert first.attempt_json != second.attempt_json
    assert (
        first.attempt_bundle_sha256
        != second.attempt_bundle_sha256
    )

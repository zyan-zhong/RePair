from __future__ import annotations

import base64
from pathlib import Path

from pchsi.evaluation.action_trace import (
    ActionTrace,
    ExecutionStatus,
    PipelineVariant,
    TraceProvenance,
    sha256_string_sequence,
)
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    canonical_json_text,
    sha256_bytes,
    sha256_text,
)
from pchsi.evaluation.episode_artifact import build_attempt_bundle_bytes
from pchsi.evaluation.policy_call_evidence import (
    PolicyCallEvidenceV1,
    allowlisted_response_headers,
)
from pchsi.evaluation.raw_policy_prompt import (
    sha256_executed_transitions,
)
from pchsi.evaluation.schema_models import (
    BudgetSnapshotV1,
    EpisodeArtifactV1,
)

DIGEST = "a" * 64


def policy_call() -> PolicyCallEvidenceV1:
    request = canonical_json_bytes({"model": "m", "request_id": "client"})
    semantic_json = canonical_json_text({"model": "m"})
    raw_text = "{}"
    response = canonical_json_bytes(
        {
            "id": "provider",
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
    return PolicyCallEvidenceV1(
        "POLICY_CALL_EVIDENCE_V1",
        1,
        0,
        0,
        "client",
        "provider",
        "hello",
        sha256_text("hello"),
        "<u>hello</u>",
        sha256_text("<u>hello</u>"),
        (1, 2),
        2,
        semantic_json,
        sha256_text(semantic_json),
        base64.b64encode(request).decode("ascii"),
        sha256_bytes(request),
        200,
        tuple(
            allowlisted_response_headers(
                {
                    "x-request-id": "provider",
                    "content-type": "application/json",
                }
            ).items()
        ),
        base64.b64encode(response).decode("ascii"),
        sha256_bytes(response),
        raw_text,
        sha256_text(raw_text),
        "stop",
        2,
        1,
        (1, 2),
        (3,),
        7,
        "goal",
        sha256_text("goal"),
        "obs",
        sha256_text("obs"),
        ("look",),
        sha256_string_sequence(("look",)),
        (),
        sha256_executed_transitions(()),
        None,
        (
            ("policy_attempt_count", 0),
            ("environment_step_count", 0),
            ("protocol_failure_count", 0),
            ("inadmissible_action_count", 0),
            ("consecutive_nonexecuted_attempt_count", 0),
        ),
    )


def action_trace() -> ActionTrace:
    provenance = TraceProvenance(
        run_id="run",
        task_id="alfworld_valid_unseen_all134_0000",
        episode_id="e1-t0000-s0000000017-a000",
        replicate_id=0,
        arm_id="R0",
        code_commit="code",
        config_sha256=DIGEST,
        provider="vllm",
        model_name="Qwen2.5-3B-Instruct-E1",
        model_version="revision",
        provider_request_id="provider",
        retry_count=0,
        timestamp_utc="2026-08-22T00:00:00Z",
        split_and_access_version="P1_COMPLETE_EVIDENCE_DEV_V1",
        split_name="train",
        access_mode="DEV_VISIBLE",
        policy_version="P4-R0-PI0",
        seed=17,
        memory_version="MEMORY_M0_V1",
        memory_state_sha256=DIGEST,
    )
    return ActionTrace.build(
        provenance=provenance,
        pipeline_variant=PipelineVariant.RAW_V1,
        model_call_index=0,
        environment_step_index=None,
        execution_status=ExecutionStatus.NOT_EXECUTED,
        public_task_goal="goal",
        observation="obs",
        prompt_text="hello",
        admissible_commands=("look",),
        raw_model_response="{}",
        literal_action="",
        parsed_phase=None,
        model_reason=None,
        parser_status="failed",
        parser_error="ENVELOPE_MISSING_ACTION",
        parser_metadata={
            "failure_code": "ENVELOPE_MISSING_ACTION",
            "failure_stage": "envelope",
            "status": "failed",
        },
        literal_action_exactly_admissible=False,
        literal_action_casefold_admissible=False,
        stages=(),
        final_executed_action=None,
        final_action_admissible=None,
        attempt_outcome="FORMAT_PROTOCOL_FAILURE",
        failure_stage="envelope",
        failure_code="ENVELOPE_MISSING_ACTION",
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
        environment_event_flags={},
        protocol_failure_count_before=0,
        inadmissible_action_count_before=0,
        consecutive_nonexecuted_attempt_count_before=0,
    )


def episode() -> EpisodeArtifactV1:
    return EpisodeArtifactV1(
        schema_id="E1_EPISODE_ARTIFACT_V1",
        schema_version=1,
        run_id="run",
        scheduled_cell_id="e1-t0000-s0000000017",
        execution_attempt_id="e1-t0000-s0000000017-a000",
        attempt_ordinal=0,
        task_index=0,
        task_id="alfworld_valid_unseen_all134_0000",
        task_type="pick_and_place_simple",
        gamefile_sha1="b" * 40,
        gamefile_sha256="c" * 64,
        seed=17,
        evaluator_commit="eval",
        design_merge_commit="design",
        runtime_core_commit="runtime",
        raw_protocol_sha256=DIGEST,
        split_access_sha256=DIGEST,
        gamefile_identity_manifest_sha256=DIGEST,
        environment_runtime_manifest_sha256=DIGEST,
        policy_runtime_manifest_sha256=DIGEST,
        policy_request_schema_sha256=DIGEST,
        scientific_outcome_status="SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE",
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
        initial_observation_sha256=sha256_text("obs"),
        final_observation_sha256=sha256_text("obs"),
        episode_semantic_sha256="e" * 64,
        started_at_utc="2026-08-22T00:00:00Z",
        completed_at_utc="2026-08-22T00:00:01Z",
    )


def write_bundle(root: Path) -> Path:
    bundle = build_attempt_bundle_bytes(
        episode_artifact=episode(),
        traces=(action_trace(),),
        policy_calls=(policy_call(),),
        public_transitions=(),
    )
    root.mkdir()
    for name, raw in bundle.file_bytes():
        (root / name).write_bytes(raw)
    return root

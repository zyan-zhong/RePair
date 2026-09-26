"""RED contract for P4 Harness-OFF SELECT execution identity V1.

These tests freeze the execution-identity requirements needed to compare:

- original model version pi0:
  base Qwen2.5-3B-Instruct, no project LoRA;

- trained model pi1:
  the same base Qwen plus one frozen Q2-BAD LoRA realization.

No test in this file authorizes SELECT execution.
"""

from __future__ import annotations

from dataclasses import MISSING, fields
import importlib
import json

import pytest

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
)
from pchsi.evaluation.episode_evaluator import (
    EpisodeExecutionConfig,
)
from pchsi.evaluation.action_trace import (
    TraceProvenance,
)
from pchsi.evaluation.policy_client import (
    PolicyClient,
)
from pchsi.evaluation.policy_execution_profile import (
    PolicyExecutionProfileV1,
    R0_EXECUTION_PROFILE_V1,
)
from pchsi.evaluation.policy_request import (
    E1PolicyRequestV1,
)
from pchsi.evaluation.policy_response import (
    PolicyResponseError,
    parse_policy_response,
)
from pchsi.evaluation.rendered_prompt import (
    RenderedPromptEvidence,
)
from pchsi.evaluation.schema_models import (
    EpisodeArtifactV1,
)


PI0_SERVED_MODEL = (
    "Qwen2.5-3B-Instruct-E1"
)

R1_17 = (
    "P4-R1-Q2-BAD-TRAIN17"
)

R1_31 = (
    "P4-R1-Q2-BAD-TRAIN31"
)

R1_47 = (
    "P4-R1-Q2-BAD-TRAIN47"
)

R1_LOGICAL_CONDITION = (
    "P4-R1-Q2-BAD"
)


def _response_body(
    *,
    model: str | None,
) -> bytes:
    payload = {
        "id": "chatcmpl-select-red",
        "choices": [
            {
                "message": {
                    "content":
                        '{"action":"look"}',
                },
                "finish_reason": "stop",
                "token_ids": [21],
            }
        ],
        "usage": {
            "prompt_tokens": 2,
            "completion_tokens": 1,
        },
        "prompt_token_ids": [11, 12],
    }

    if model is not None:
        payload["model"] = model

    return canonical_json_bytes(
        payload
    )


class _WireRequest:
    def __init__(
        self,
        model_name: str,
    ) -> None:
        self.model_name = (
            model_name
        )
        self.request_id = (
            "select-red-request"
        )

    def to_wire_dict(
        self,
    ) -> dict[str, object]:
        return {
            "model":
                self.model_name,
        }

    def to_wire_bytes(
        self,
    ) -> bytes:
        return canonical_json_bytes(
            self.to_wire_dict()
        )


class _Transport:
    def __init__(
        self,
        response_model: str,
    ) -> None:
        self.response_model = (
            response_model
        )

    def post_exact(
        self,
        *,
        path,
        body,
        headers,
    ):
        assert (
            path
            == "/v1/chat/completions"
        )

        return (
            200,
            {
                "x-request-id":
                    "provider-request",
            },
            _response_body(
                model=(
                    self.response_model
                )
            ),
        )


def _expected_prompt(
) -> RenderedPromptEvidence:
    return RenderedPromptEvidence(
        raw_policy_prompt_sha256=(
            "a" * 64
        ),
        chat_template_sha256=(
            "b" * 64
        ),
        rendered_prompt_text_sha256=(
            "c" * 64
        ),
        rendered_token_ids=(
            11,
            12,
        ),
        rendered_token_ids_sha256=(
            "d" * 64
        ),
        prompt_token_count=2,
        rendered_prompt_text=None,
    )


# ---------------------------------------------------------------------------
# 1. Frozen pi0 request behavior must remain byte-for-byte unchanged.
# ---------------------------------------------------------------------------

def test_pi0_default_request_wire_is_unchanged(
) -> None:
    request = E1PolicyRequestV1(
        prompt_text="test prompt",
        seed=17,
        request_id="req-pi0",
    )

    expected = {
        "model":
            PI0_SERVED_MODEL,
        "messages": [
            {
                "role": "user",
                "content":
                    "test prompt",
            }
        ],
        "temperature": 0.2,
        "top_p": 0.95,
        "max_tokens": 128,
        "seed": 17,
        "n": 1,
        "stream": False,
        "stop": None,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "logprobs": False,
        "top_logprobs": None,
        "best_of": None,
        "use_beam_search": False,
        "top_k": -1,
        "min_p": 0.0,
        "repetition_penalty": 1.0,
        "length_penalty": 1.0,
        "stop_token_ids": [],
        "include_stop_str_in_output":
            False,
        "ignore_eos": False,
        "min_tokens": 0,
        "skip_special_tokens": True,
        "spaces_between_special_tokens":
            True,
        "truncate_prompt_tokens": None,
        "prompt_logprobs": None,
        "allowed_token_ids": None,
        "bad_words": [],
        "echo": False,
        "add_generation_prompt": True,
        "continue_final_message":
            False,
        "add_special_tokens": False,
        "documents": None,
        "chat_template": None,
        "chat_template_kwargs": {},
        "structured_outputs": None,
        "priority": 0,
        "return_token_ids": True,
        "request_id": "req-pi0",
    }

    assert (
        request.to_wire_bytes()
        ==
        canonical_json_bytes(
            expected
        )
    )


# ---------------------------------------------------------------------------
# 2. A trained pi1 LoRA realization must be explicitly selectable.
# ---------------------------------------------------------------------------

def test_request_can_explicitly_select_r1_served_model(
) -> None:
    request = E1PolicyRequestV1(
        prompt_text="test prompt",
        seed=17,
        request_id="req-r1",
        served_model_name=R1_17,
    )

    assert (
        request.to_wire_dict()[
            "model"
        ]
        == R1_17
    )


# ---------------------------------------------------------------------------
# 3. Execution profile must carry the actual served-model identity.
# ---------------------------------------------------------------------------

def test_execution_profile_carries_served_model_identity(
) -> None:
    assert (
        "served_model_name"
        in
        PolicyExecutionProfileV1
        .__dataclass_fields__
    )

    assert (
        R0_EXECUTION_PROFILE_V1
        .served_model_name
        ==
        PI0_SERVED_MODEL
    )


# ---------------------------------------------------------------------------
# 4. vLLM response model identity must be retained.
# ---------------------------------------------------------------------------

def test_policy_response_captures_provider_model_name(
) -> None:
    generation = parse_policy_response(
        status_code=200,
        headers={
            "x-request-id":
                "provider-request",
        },
        body=_response_body(
            model=R1_17
        ),
        client_request_id=(
            "client-request"
        ),
        latency_ms=1,
    )

    assert (
        generation.provider_model_name
        == R1_17
    )


# ---------------------------------------------------------------------------
# 5. Missing response.model must fail closed.
# ---------------------------------------------------------------------------

def test_policy_response_rejects_missing_model_identity(
) -> None:
    with pytest.raises(
        PolicyResponseError,
        match="model",
    ):
        parse_policy_response(
            status_code=200,
            headers={},
            body=_response_body(
                model=None
            ),
            client_request_id=(
                "client-request"
            ),
            latency_ms=1,
        )


# ---------------------------------------------------------------------------
# 6. Request model != response model must fail before generation is accepted.
# ---------------------------------------------------------------------------

def test_policy_client_rejects_request_response_model_mismatch(
) -> None:
    client = PolicyClient(
        transport=_Transport(
            response_model=R1_31,
        ),
        clock_ns=iter(
            [
                0,
                1_000_000,
            ]
        ).__next__,
    )

    with pytest.raises(
        ValueError,
        match="model",
    ):
        client.generate_with_evidence(
            request=_WireRequest(
                R1_17
            ),
            expected_prompt=(
                _expected_prompt()
            ),
        )


# ---------------------------------------------------------------------------
# 7. Episode execution must distinguish P1 DEV from P4 SELECT explicitly.
# ---------------------------------------------------------------------------

def test_episode_config_has_explicit_evaluation_context(
) -> None:
    fields_ = (
        EpisodeExecutionConfig
        .__dataclass_fields__
    )

    assert (
        "evaluation_context"
        in fields_
    )

    assert (
        "select_execution_identity"
        in fields_
    )


# ---------------------------------------------------------------------------
# 8. Action-trace provenance must carry SELECT-specific identity.
# ---------------------------------------------------------------------------

def test_trace_provenance_has_select_identity_fields(
) -> None:
    fields_ = (
        TraceProvenance
        .__dataclass_fields__
    )

    required = {
        "evaluation_context",
        "logical_condition_id",
        "checkpoint_instance_id",
        "training_seed",
        "select_policy_runtime_manifest_sha256",
    }

    assert (
        required
        <= set(fields_)
    )


# ---------------------------------------------------------------------------
# 9. Episode artifact must preserve the same SELECT identity.
# ---------------------------------------------------------------------------

def test_episode_artifact_has_select_identity_fields(
) -> None:
    fields_ = (
        EpisodeArtifactV1
        .__dataclass_fields__
    )

    required = {
        "evaluation_context",
        "logical_condition_id",
        "checkpoint_instance_id",
        "training_seed",
        "select_policy_runtime_manifest_sha256",
    }

    assert (
        required
        <= set(fields_)
    )


# ---------------------------------------------------------------------------
# 10. SELECT must have an independent, fail-closed binding module.
# ---------------------------------------------------------------------------

def test_select_execution_identity_module_exists(
) -> None:
    module = importlib.import_module(
        "pchsi.evaluation."
        "select_execution_identity"
    )

    for name in (
        "SelectBoundEpisodeCellV1",
        "SelectExecutionIdentityV1",
        "bind_select_condition_cell",
        "validate_select_model_identity_chain",
    ):
        assert hasattr(
            module,
            name,
        ), name


# ---------------------------------------------------------------------------
# 11. Scientific group and concrete LoRA weight version are distinct fields.
# ---------------------------------------------------------------------------

def test_select_identity_separates_logical_condition_and_checkpoint(
) -> None:
    module = importlib.import_module(
        "pchsi.evaluation."
        "select_execution_identity"
    )

    cls = (
        module
        .SelectExecutionIdentityV1
    )

    names = {
        field.name
        for field in fields(
            cls
        )
    }

    required = {
        "evaluation_context",
        "logical_condition_id",
        "checkpoint_instance_id",
        "training_seed",
        "served_model_name",
        "adapter_bundle_sha256",
        "access_class",
        "policy_condition_id",
        "condition_cell_id",
        "task_access_manifest_sha256",
        "policy_condition_manifest_sha256",
        "condition_run_schedule_sha256",
        "select_policy_runtime_manifest_sha256",
    }

    assert required <= names


# ---------------------------------------------------------------------------
# 12. SELECT runtime identity is separate from frozen E1 pi0 runtime identity.
# ---------------------------------------------------------------------------

def test_select_runtime_manifest_types_exist(
) -> None:
    module = importlib.import_module(
        "pchsi.evaluation."
        "select_policy_runtime"
    )

    assert hasattr(
        module,
        "SelectServerRuntimeManifestV1",
    )

    assert hasattr(
        module,
        "SelectPolicyRuntimeManifestV1",
    )


# ---------------------------------------------------------------------------
# 13. SELECT policy runtime must not have a silent pi0 served-model fallback.
# ---------------------------------------------------------------------------

def test_select_runtime_requires_explicit_served_model_name(
) -> None:
    module = importlib.import_module(
        "pchsi.evaluation."
        "select_policy_runtime"
    )

    cls = (
        module
        .SelectPolicyRuntimeManifestV1
    )

    field_map = {
        field.name: field
        for field in fields(
            cls
        )
    }

    served = field_map[
        "served_model_name"
    ]

    assert (
        served.default
        is MISSING
    )

    assert (
        served.default_factory
        is MISSING
    )


# ---------------------------------------------------------------------------
# 14. SELECT result authority must come from a frozen master schedule set.
# ---------------------------------------------------------------------------

def test_select_result_audit_is_master_schedule_driven(
) -> None:
    module = importlib.import_module(
        "pchsi.evaluation."
        "select_result_audit"
    )

    assert hasattr(
        module,
        "derive_expected_select_cells_from_master_schedules",
    )

    assert hasattr(
        module,
        "validate_master_schedule_set",
    )


# ---------------------------------------------------------------------------
# 15. Any schedule→runtime→request→response→trace identity mismatch fails.
# ---------------------------------------------------------------------------

def test_select_model_identity_chain_rejects_trace_mismatch(
) -> None:
    module = importlib.import_module(
        "pchsi.evaluation."
        "select_execution_identity"
    )

    validator = (
        module
        .validate_select_model_identity_chain
    )

    with pytest.raises(
        ValueError,
        match="identity",
    ):
        validator(
            schedule_policy_condition_id=(
                R1_17
            ),
            bound_policy_condition_id=(
                R1_17
            ),
            manifest_policy_condition_id=(
                R1_17
            ),
            runtime_served_model_name=(
                R1_17
            ),
            profile_served_model_name=(
                R1_17
            ),
            request_model_name=(
                R1_17
            ),
            response_model_name=(
                R1_17
            ),
            trace_model_name=(
                R1_31
            ),
            artifact_policy_condition_id=(
                R1_17
            ),
        )


# ===========================================================================
# GREEN-B2 integration RED hardening
#
# The earlier tests prove that SELECT identity types exist.
# These tests prove that the actual evaluator/artifact path uses them.
# ===========================================================================


def _select_r1_identity_for_integration():
    from pchsi.evaluation.select_execution_identity import (
        P4_SELECT_EVALUATION_CONTEXT,
        SelectExecutionIdentityV1,
    )

    cell_id = (
        "p4-P4-R1-Q2-BAD-TRAIN17-"
        "t00002-s0000000017"
    )

    identity = SelectExecutionIdentityV1(
        evaluation_context=(
            P4_SELECT_EVALUATION_CONTEXT
        ),
        logical_condition_id=(
            "P4-R1-Q2-BAD"
        ),
        checkpoint_instance_id=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
        training_seed=17,
        served_model_name=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
        adapter_bundle_sha256=(
            "a" * 64
        ),
        access_class=(
            "SELECT_SUMMARY_ONLY"
        ),
        policy_condition_id=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
        condition_cell_id=(
            cell_id
        ),
        task_access_manifest_sha256=(
            "1" * 64
        ),
        policy_condition_manifest_sha256=(
            "2" * 64
        ),
        condition_run_schedule_sha256=(
            "3" * 64
        ),
        select_policy_runtime_manifest_sha256=(
            "4" * 64
        ),
    )

    return identity


def test_select_provenance_uses_real_pi1_identity_not_p1_or_pi0() -> None:
    """SELECT trace must describe the actual pi1 LoRA realization."""

    from types import SimpleNamespace

    from pchsi.evaluation.episode_evaluator import (
        _provenance,
    )
    from pchsi.evaluation.select_execution_identity import (
        build_select_execution_profile,
    )

    identity = (
        _select_r1_identity_for_integration()
    )

    profile = (
        build_select_execution_profile(
            identity
        )
    )

    config = SimpleNamespace(
        run_id="select-run",
        task=SimpleNamespace(
            task_id=(
                "alfworld_valid_unseen_all134_0002"
            ),
            split="valid_unseen",
        ),
        execution_attempt_id=(
            identity.condition_cell_id
            + "-a000"
        ),
        seed=17,
        evaluator_commit=(
            "e" * 40
        ),
        runtime_core_commit=(
            "f" * 40
        ),
        attempt_ordinal=0,

        raw_protocol_sha256=(
            "5" * 64
        ),
        split_access_sha256=(
            identity
            .task_access_manifest_sha256
        ),
        gamefile_identity_manifest_sha256=(
            "6" * 64
        ),
        environment_runtime_manifest_sha256=(
            "7" * 64
        ),
        policy_runtime_manifest_sha256=(
            identity
            .select_policy_runtime_manifest_sha256
        ),
        policy_request_schema_sha256=(
            "8" * 64
        ),
        run_schedule_sha256=(
            identity
            .condition_run_schedule_sha256
        ),

        task_access_manifest_sha256=(
            identity
            .task_access_manifest_sha256
        ),
        policy_condition_manifest_sha256=(
            identity
            .policy_condition_manifest_sha256
        ),
        condition_run_schedule_sha256=(
            identity
            .condition_run_schedule_sha256
        ),
        access_class=(
            identity.access_class
        ),
        policy_condition_id=(
            identity.policy_condition_id
        ),
        condition_cell_id=(
            identity.condition_cell_id
        ),

        evaluation_context=(
            identity.evaluation_context
        ),
        select_execution_identity=(
            identity
        ),
    )

    trace = _provenance(
        config=config,
        provider_request_id=(
            "provider-request"
        ),
        history=(),
        profile=profile,
    )

    assert (
        trace.arm_id
        == "P4-R1-Q2-BAD"
    )

    assert (
        trace.model_name
        == "P4-R1-Q2-BAD-TRAIN17"
    )

    assert (
        trace.split_and_access_version
        == "P4_SELECT_EVALUATION_LINEAGE_V1"
    )

    assert (
        trace.split_and_access_version
        != "P1_B_ACCESS_V1"
    )

    assert (
        trace.evaluation_context
        == "P4_HARNESS_OFF_SELECT"
    )

    assert (
        trace.logical_condition_id
        == "P4-R1-Q2-BAD"
    )

    assert (
        trace.checkpoint_instance_id
        == "P4-R1-Q2-BAD-TRAIN17"
    )

    assert (
        trace.training_seed
        == 17
    )

    assert (
        trace.select_policy_runtime_manifest_sha256
        == "4" * 64
    )


def test_select_episode_artifact_round_trips_complete_pi1_identity() -> None:
    """Final result artifact must retain the same SELECT model identity."""

    from pchsi.evaluation.schema_models import (
        BudgetSnapshotV1,
        EpisodeArtifactV1,
    )

    identity = (
        _select_r1_identity_for_integration()
    )

    artifact = EpisodeArtifactV1(
        schema_id=(
            "E1_EPISODE_ARTIFACT_V1"
        ),
        schema_version=1,

        run_id="select-run",
        scheduled_cell_id=(
            identity.condition_cell_id
        ),
        execution_attempt_id=(
            identity.condition_cell_id
            + "-a000"
        ),
        attempt_ordinal=0,

        task_index=2,
        task_id=(
            "alfworld_valid_unseen_all134_0002"
        ),
        task_type="pick_and_place_simple",

        gamefile_sha1=(
            "a" * 40
        ),
        gamefile_sha256=(
            "b" * 64
        ),

        seed=17,

        evaluator_commit=(
            "c" * 40
        ),
        design_merge_commit=(
            "d" * 40
        ),
        runtime_core_commit=(
            "e" * 40
        ),

        raw_protocol_sha256=(
            "1" * 64
        ),
        split_access_sha256=(
            identity
            .task_access_manifest_sha256
        ),
        gamefile_identity_manifest_sha256=(
            "2" * 64
        ),
        environment_runtime_manifest_sha256=(
            "3" * 64
        ),
        policy_runtime_manifest_sha256=(
            identity
            .select_policy_runtime_manifest_sha256
        ),
        policy_request_schema_sha256=(
            "5" * 64
        ),

        scientific_outcome_status=(
            "TASK_FAILURE"
        ),
        operational_finalization_status=(
            "PUBLISHED"
        ),

        success=False,
        termination_reason=(
            "ENVIRONMENT_TERMINATED"
        ),

        final_score=0,
        final_done=True,
        final_won=False,

        final_budget=(
            BudgetSnapshotV1(
                policy_attempt_count=1,
                environment_step_count=1,
                protocol_failure_count=0,
                inadmissible_action_count=0,
                consecutive_nonexecuted_attempt_count=0,
            )
        ),

        trace_count=1,
        public_transition_count=1,
        environment_call_trace_count=1,

        initial_observation_sha256=(
            "6" * 64
        ),
        final_observation_sha256=(
            "7" * 64
        ),
        episode_semantic_sha256=(
            "8" * 64
        ),

        started_at_utc=(
            "2026-08-10T00:00:00+00:00"
        ),
        completed_at_utc=(
            "2026-08-10T00:00:01+00:00"
        ),

        task_access_manifest_sha256=(
            identity
            .task_access_manifest_sha256
        ),
        policy_condition_manifest_sha256=(
            identity
            .policy_condition_manifest_sha256
        ),
        condition_run_schedule_sha256=(
            identity
            .condition_run_schedule_sha256
        ),

        access_class=(
            "SELECT_SUMMARY_ONLY"
        ),
        policy_condition_id=(
            identity.policy_condition_id
        ),
        condition_cell_id=(
            identity.condition_cell_id
        ),

        evaluation_context=(
            identity.evaluation_context
        ),
        logical_condition_id=(
            identity.logical_condition_id
        ),
        checkpoint_instance_id=(
            identity.checkpoint_instance_id
        ),
        training_seed=(
            identity.training_seed
        ),
        select_policy_runtime_manifest_sha256=(
            identity
            .select_policy_runtime_manifest_sha256
        ),
    )

    restored = (
        EpisodeArtifactV1.from_json(
            artifact.to_json()
        )
    )

    assert restored == artifact

    payload = restored.to_dict()

    assert (
        payload["access_class"]
        == "SELECT_SUMMARY_ONLY"
    )

    assert (
        payload["logical_condition_id"]
        == "P4-R1-Q2-BAD"
    )

    assert (
        payload["checkpoint_instance_id"]
        == "P4-R1-Q2-BAD-TRAIN17"
    )

    assert (
        payload["training_seed"]
        == 17
    )


def test_episode_execution_config_accepts_only_bound_select_identity() -> None:
    """Evaluator config must carry the exact frozen SELECT binding."""

    from pchsi.evaluation.condition_run_schedule import (
        condition_cell_id,
    )
    from pchsi.evaluation.episode_evaluator import (
        EpisodeExecutionConfig,
    )
    from pchsi.evaluation.run_schedule import (
        execution_attempt_id,
    )
    from pchsi.evaluation.select_execution_identity import (
        SelectBoundEpisodeCellV1,
    )
    from pchsi.evaluation.task_manifest import (
        FrozenTaskRecord,
    )
    from pchsi.evaluation.distillation_access import (
        DistillationAccessClass,
    )

    identity = (
        _select_r1_identity_for_integration()
    )

    expected_cell_id = (
        condition_cell_id(
            policy_condition_id=(
                identity.policy_condition_id
            ),
            manifest_index=2,
            seed=17,
        )
    )

    assert (
        identity.condition_cell_id
        == expected_cell_id
    )

    cell = (
        SelectBoundEpisodeCellV1(
            scheduled_cell_id=(
                expected_cell_id
            ),
            task_index=2,
            task_id=(
                "alfworld_valid_unseen_all134_0002"
            ),
            seed=17,
            policy_condition_id=(
                identity.policy_condition_id
            ),
            access_class=(
                DistillationAccessClass
                .SELECT_SUMMARY_ONLY
            ),
            execution_identity=(
                identity
            ),
        )
    )

    task = FrozenTaskRecord(
        index=2,
        task_id=(
            "alfworld_valid_unseen_all134_0002"
        ),
        split="valid_unseen",
        task_type="pick_and_place_simple",
        gamefile="/tmp/game.tw-pddl",
        gamefile_sha1=(
            "a" * 40
        ),
        root="/tmp/root",
        traj_file="/tmp/traj.json",
    )

    attempt_id = (
        execution_attempt_id(
            scheduled_cell_id=(
                expected_cell_id
            ),
            attempt_ordinal=0,
        )
    )

    config = EpisodeExecutionConfig(
        run_id="select-run",
        cell=cell,
        execution_attempt_id=(
            attempt_id
        ),
        attempt_ordinal=0,
        task=task,
        seed=17,

        evaluator_commit=(
            "b" * 40
        ),
        design_merge_commit=(
            "c" * 40
        ),
        runtime_core_commit=(
            "d" * 40
        ),

        raw_protocol_sha256=(
            "5" * 64
        ),
        split_access_sha256=(
            identity
            .task_access_manifest_sha256
        ),
        gamefile_identity_manifest_sha256=(
            "6" * 64
        ),
        environment_runtime_manifest_sha256=(
            "7" * 64
        ),
        policy_runtime_manifest_sha256=(
            identity
            .select_policy_runtime_manifest_sha256
        ),
        policy_request_schema_sha256=(
            "8" * 64
        ),
        run_schedule_sha256=(
            identity
            .condition_run_schedule_sha256
        ),
        gamefile_sha256=(
            "9" * 64
        ),

        task_access_manifest_sha256=(
            identity
            .task_access_manifest_sha256
        ),
        policy_condition_manifest_sha256=(
            identity
            .policy_condition_manifest_sha256
        ),
        condition_run_schedule_sha256=(
            identity
            .condition_run_schedule_sha256
        ),

        access_class=(
            identity.access_class
        ),
        policy_condition_id=(
            identity.policy_condition_id
        ),
        condition_cell_id=(
            identity.condition_cell_id
        ),

        evaluation_context=(
            identity.evaluation_context
        ),
        select_execution_identity=(
            identity
        ),
    )

    assert (
        config.evaluation_context
        == "P4_HARNESS_OFF_SELECT"
    )

    assert (
        config.select_execution_identity
        == identity
    )


# ===========================================================================
# Final hardening RED:
#
# 1. SELECT runtime manifests must be closed-schema,
#    round-trippable frozen artifacts.
#
# 2. Final SELECT audit must prove the actual model identity from
#    frozen schedule authority through exact request/response evidence,
#    trace provenance and final episode artifact.
# ===========================================================================


def _select_server_runtime_for_final_audit():
    from pchsi.evaluation.select_policy_runtime import (
        SelectServerRuntimeManifestV1,
        SelectStaticLoRARegistrationV1,
    )

    registrations = tuple(
        SelectStaticLoRARegistrationV1(
            logical_condition_id=(
                "P4-R1-Q2-BAD"
            ),
            checkpoint_instance_id=(
                "P4-R1-Q2-BAD-"
                f"TRAIN{seed}"
            ),
            training_seed=seed,
            served_model_name=(
                "P4-R1-Q2-BAD-"
                f"TRAIN{seed}"
            ),
            adapter_path=(
                "/tmp/"
                f"p4-r1-train{seed}"
            ),
            adapter_bundle_sha256=(
                digest
            ),
            adapter_rank=16,
        )
        for seed, digest in (
            (
                17,
                "a" * 64,
            ),
            (
                31,
                "b" * 64,
            ),
            (
                47,
                "c" * 64,
            ),
        )
    )

    return SelectServerRuntimeManifestV1(
        schema_id=(
            "SELECT_SERVER_RUNTIME_MANIFEST_V1"
        ),
        schema_version=1,
        manifest_id=(
            "SELECT_SERVER_RUNTIME_MANIFEST_V1"
        ),
        vllm_version="0.11.0",
        base_model_repository=(
            "Qwen/Qwen2.5-3B-Instruct"
        ),
        base_model_revision=(
            "aa8e72537993ba99e69dfaafa59ed015b17504d1"
        ),
        tokenizer_identity_manifest_sha256=(
            "d" * 64
        ),
        chat_template_sha256=(
            "e" * 64
        ),
        dtype="bfloat16",
        tensor_parallel_size=1,
        generation_config_mode="vllm",
        chat_template_content_format=(
            "string"
        ),
        enable_lora=True,
        max_lora_rank=16,
        max_loras=1,

        # Three frozen pi1 LoRA realizations
        # remain resident in the CPU LoRA cache.
        max_cpu_loras=3,

        lora_dtype="auto",
        runtime_dynamic_lora_updates=False,
        static_lora_registry=(
            registrations
        ),
    )


def _select_policy_runtime_for_final_audit():
    from pchsi.evaluation.canonical_evidence import (
        canonical_json_bytes,
        sha256_bytes,
    )
    from pchsi.evaluation.select_policy_runtime import (
        SelectPolicyRuntimeManifestV1,
    )

    server = (
        _select_server_runtime_for_final_audit()
    )

    server_sha = sha256_bytes(
        canonical_json_bytes(
            server.to_dict()
        )
    )

    runtime = (
        SelectPolicyRuntimeManifestV1(
            schema_id=(
                "SELECT_POLICY_RUNTIME_MANIFEST_V1"
            ),
            schema_version=1,
            manifest_id=(
                "SELECT_POLICY_RUNTIME_"
                "P4-R1-Q2-BAD-TRAIN17"
            ),
            server_runtime_manifest_sha256=(
                server_sha
            ),
            policy_condition_id=(
                "P4-R1-Q2-BAD-TRAIN17"
            ),
            logical_condition_id=(
                "P4-R1-Q2-BAD"
            ),
            checkpoint_instance_id=(
                "P4-R1-Q2-BAD-TRAIN17"
            ),
            training_seed=17,
            served_model_name=(
                "P4-R1-Q2-BAD-TRAIN17"
            ),
            adapter_path=(
                "/tmp/p4-r1-train17"
            ),
            adapter_bundle_sha256=(
                "a" * 64
            ),
            adapter_rank=16,
        )
    )

    return server, runtime


# ---------------------------------------------------------------------------
# 19. SELECT runtime manifests are closed-schema, round-trippable artifacts.
# ---------------------------------------------------------------------------

def test_select_runtime_manifests_have_closed_schema_round_trip(
) -> None:
    import json

    from pchsi.evaluation.canonical_evidence import (
        canonical_json_bytes,
    )
    from pchsi.evaluation.schema_contract import (
        load_schema,
    )
    from pchsi.evaluation.select_policy_runtime import (
        SelectPolicyRuntimeManifestV1,
        SelectServerRuntimeManifestV1,
    )

    server, runtime = (
        _select_policy_runtime_for_final_audit()
    )

    server_schema = load_schema(
        "SELECT_SERVER_RUNTIME_MANIFEST_V1"
    )

    policy_schema = load_schema(
        "SELECT_POLICY_RUNTIME_MANIFEST_V1"
    )

    assert (
        server_schema[
            "additionalProperties"
        ]
        is False
    )

    assert (
        policy_schema[
            "additionalProperties"
        ]
        is False
    )

    restored_server = (
        SelectServerRuntimeManifestV1
        .from_json(
            server.to_json()
        )
    )

    restored_runtime = (
        SelectPolicyRuntimeManifestV1
        .from_json(
            runtime.to_json()
        )
    )

    assert restored_server == server
    assert restored_runtime == runtime

    # Closed schema / parser:
    # an unknown field cannot silently enter
    # frozen SELECT runtime identity.
    payload = json.loads(
        server.to_json()
    )

    payload[
        "unexpected_field"
    ] = True

    with pytest.raises(
        ValueError,
    ):
        (
            SelectServerRuntimeManifestV1
            .from_json(
                canonical_json_bytes(
                    payload
                )
            )
        )


def _select_policy_condition_for_final_audit(
    *,
    runtime_sha256: str,
):
    from pchsi.evaluation.policy_condition import (
        CheckpointKind,
        PolicyConditionManifestV1,
        TrainingMethod,
    )

    return PolicyConditionManifestV1(
        schema_id=(
            "POLICY_CONDITION_MANIFEST_V1"
        ),
        schema_version=1,
        policy_condition_id=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
        base_model_repository=(
            "Qwen/Qwen2.5-3B-Instruct"
        ),
        base_model_revision=(
            "aa8e72537993ba99e69dfaafa59ed015b17504d1"
        ),
        checkpoint_kind=(
            CheckpointKind.LORA_ADAPTER
        ),
        checkpoint_path=(
            "/tmp/p4-r1-train17"
        ),
        checkpoint_sha256=(
            "a" * 64
        ),
        training_method=(
            TrainingMethod.SFT
        ),
        training_run_id=(
            "P4-R1-Q2-BAD-SEED17"
        ),
        training_config_sha256=(
            "b" * 64
        ),

        # In SELECT freeze V2 the policy condition
        # binds the SELECT policy-runtime identity,
        # not the old pi0-only E1 runtime manifest.
        policy_runtime_manifest_sha256=(
            runtime_sha256
        ),

        tokenizer_identity_manifest_sha256=(
            "d" * 64
        ),
        chat_template_sha256=(
            "e" * 64
        ),
        served_model_name=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
        policy_version=(
            "PI1_BAD"
        ),
        memory_version=(
            "MEMORY_M0_V1"
        ),
        raw_protocol_sha256=(
            "f" * 64
        ),
        runtime_core_commit=(
            "1" * 40
        ),
        evaluator_commit=(
            "2" * 40
        ),
    )


def _select_policy_call_for_final_audit(
    *,
    response_model_name: str,
):
    from pchsi.evaluation.budget import (
        BudgetState,
    )
    from pchsi.evaluation.canonical_evidence import (
        canonical_json_bytes,
        sha256_bytes,
        sha256_text,
    )
    from pchsi.evaluation.policy_call_evidence import (
        PolicyCallTransportEvidenceV1,
        allowlisted_response_headers,
        build_policy_call_evidence,
    )
    from pchsi.evaluation.policy_request import (
        E1PolicyRequestV1,
    )
    from pchsi.evaluation.policy_response import (
        PolicyGeneration,
    )
    from pchsi.evaluation.rendered_prompt import (
        RenderedPromptEvidence,
    )

    request = E1PolicyRequestV1(
        prompt_text="PROMPT",
        seed=17,
        request_id="select-audit-client",
        served_model_name=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
    )

    response_body = canonical_json_bytes(
        {
            "id":
                "chatcmpl-select-audit",
            "model":
                response_model_name,
            "choices": [
                {
                    "message": {
                        "content":
                            '{"action":"look"}',
                    },
                    "finish_reason":
                        "stop",
                    "token_ids": [
                        9,
                    ],
                }
            ],
            "usage": {
                "prompt_tokens":
                    2,
                "completion_tokens":
                    1,
            },
            "prompt_token_ids": [
                1,
                2,
            ],
        }
    )

    generation = PolicyGeneration(
        raw_response_text=(
            '{"action":"look"}'
        ),
        raw_response_body=(
            response_body
        ),
        provider_request_id=(
            "provider-select-audit"
        ),
        client_request_id=(
            request.request_id
        ),
        finish_reason="stop",
        prompt_tokens=2,
        completion_tokens=1,
        prompt_token_ids=(
            1,
            2,
        ),
        token_ids=(
            9,
        ),
        latency_ms=1,
        provider_model_name=(
            response_model_name
        ),
    )

    rendered = RenderedPromptEvidence(
        raw_policy_prompt_sha256=(
            sha256_text(
                "PROMPT"
            )
        ),
        chat_template_sha256=(
            "e" * 64
        ),
        rendered_prompt_text_sha256=(
            sha256_text(
                "rendered"
            )
        ),
        rendered_token_ids=(
            1,
            2,
        ),
        rendered_token_ids_sha256=(
            sha256_bytes(
                canonical_json_bytes(
                    [
                        1,
                        2,
                    ]
                )
            )
        ),
        prompt_token_count=2,
        rendered_prompt_text=(
            "rendered"
        ),
    )

    transport = (
        PolicyCallTransportEvidenceV1(
            request_wire_bytes=(
                request.to_wire_bytes()
            ),
            http_status=200,
            response_headers_allowlisted=tuple(
                allowlisted_response_headers(
                    {
                        "x-request-id":
                            "provider-select-audit",
                        "content-type":
                            "application/json",
                    }
                ).items()
            ),
            raw_response_body=(
                response_body
            ),
            latency_ms=1,
        )
    )

    return build_policy_call_evidence(
        model_call_index=0,
        public_task_goal=(
            "Put the object somewhere."
        ),
        observation=(
            "You are in a room."
        ),
        admissible_commands=(
            "look",
        ),
        executed_history=(),
        interface_feedback_before=None,
        budget_before=(
            BudgetState()
        ),
        request=request,
        expected_prompt=rendered,
        generation=generation,
        transport_evidence=(
            transport
        ),
    )


def _select_trace_provenance_for_final_audit():
    from pchsi.evaluation.action_trace import (
        TraceProvenance,
    )

    return TraceProvenance(
        run_id="select-run",
        task_id=(
            "alfworld_valid_unseen_all134_0002"
        ),
        episode_id=(
            "p4-P4-R1-Q2-BAD-TRAIN17-"
            "t00002-s0000000017-a000"
        ),
        replicate_id=0,
        arm_id=(
            "P4-R1-Q2-BAD"
        ),
        code_commit=(
            "2" * 40
        ),
        config_sha256=(
            "3" * 64
        ),
        provider="vllm",
        model_name=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
        model_version=(
            "4" * 64
        ),
        provider_request_id=(
            "provider-select-audit"
        ),
        retry_count=0,
        timestamp_utc=(
            "2026-08-10T00:00:00+00:00"
        ),
        split_and_access_version=(
            "P4_SELECT_EVALUATION_LINEAGE_V1"
        ),
        split_name="valid_unseen",
        access_mode=(
            "TASK_ACCESS_MANIFEST_V1"
        ),
        policy_version=(
            "PI1_BAD"
        ),
        seed=17,
        memory_version=(
            "MEMORY_M0_V1"
        ),
        memory_state_sha256=(
            "5" * 64
        ),
        task_access_manifest_sha256=(
            "6" * 64
        ),
        policy_condition_manifest_sha256=(
            "7" * 64
        ),
        condition_run_schedule_sha256=(
            "8" * 64
        ),
        access_class=(
            "SELECT_SUMMARY_ONLY"
        ),
        policy_condition_id=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
        condition_cell_id=(
            "p4-P4-R1-Q2-BAD-TRAIN17-"
            "t00002-s0000000017"
        ),
        evaluation_context=(
            "P4_HARNESS_OFF_SELECT"
        ),
        logical_condition_id=(
            "P4-R1-Q2-BAD"
        ),
        checkpoint_instance_id=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
        training_seed=17,
        select_policy_runtime_manifest_sha256=(
            "4" * 64
        ),
    )


def _select_episode_for_final_audit(
    *,
    policy_condition_sha256: str,
    runtime_sha256: str,
    schedule_sha256: str,
):
    from pchsi.evaluation.schema_models import (
        BudgetSnapshotV1,
        EpisodeArtifactV1,
    )

    cell_id = (
        "p4-P4-R1-Q2-BAD-TRAIN17-"
        "t00002-s0000000017"
    )

    return EpisodeArtifactV1(
        schema_id=(
            "E1_EPISODE_ARTIFACT_V1"
        ),
        schema_version=1,
        run_id="select-run",
        scheduled_cell_id=cell_id,
        execution_attempt_id=(
            cell_id
            + "-a000"
        ),
        attempt_ordinal=0,
        task_index=2,
        task_id=(
            "alfworld_valid_unseen_all134_0002"
        ),
        task_type=(
            "pick_and_place_simple"
        ),
        gamefile_sha1=(
            "a" * 40
        ),
        gamefile_sha256=(
            "b" * 64
        ),
        seed=17,
        evaluator_commit=(
            "2" * 40
        ),
        design_merge_commit=(
            "c" * 40
        ),
        runtime_core_commit=(
            "1" * 40
        ),
        raw_protocol_sha256=(
            "f" * 64
        ),
        split_access_sha256=(
            "6" * 64
        ),
        gamefile_identity_manifest_sha256=(
            "d" * 64
        ),
        environment_runtime_manifest_sha256=(
            "e" * 64
        ),
        policy_runtime_manifest_sha256=(
            runtime_sha256
        ),
        policy_request_schema_sha256=(
            "9" * 64
        ),
        scientific_outcome_status=(
            "TASK_FAILURE"
        ),
        operational_finalization_status=(
            "PUBLISHED"
        ),
        success=False,
        termination_reason=(
            "ENVIRONMENT_TERMINATED"
        ),
        final_score=0,
        final_done=True,
        final_won=False,
        final_budget=(
            BudgetSnapshotV1(
                policy_attempt_count=1,
                environment_step_count=1,
                protocol_failure_count=0,
                inadmissible_action_count=0,
                consecutive_nonexecuted_attempt_count=0,
            )
        ),
        trace_count=1,
        public_transition_count=1,
        environment_call_trace_count=1,
        initial_observation_sha256=(
            "1" * 64
        ),
        final_observation_sha256=(
            "2" * 64
        ),
        episode_semantic_sha256=(
            "3" * 64
        ),
        started_at_utc=(
            "2026-08-10T00:00:00+00:00"
        ),
        completed_at_utc=(
            "2026-08-10T00:00:01+00:00"
        ),
        task_access_manifest_sha256=(
            "6" * 64
        ),
        policy_condition_manifest_sha256=(
            policy_condition_sha256
        ),
        condition_run_schedule_sha256=(
            schedule_sha256
        ),
        access_class=(
            "SELECT_SUMMARY_ONLY"
        ),
        policy_condition_id=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
        condition_cell_id=(
            cell_id
        ),
        evaluation_context=(
            "P4_HARNESS_OFF_SELECT"
        ),
        logical_condition_id=(
            "P4-R1-Q2-BAD"
        ),
        checkpoint_instance_id=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
        training_seed=17,
        select_policy_runtime_manifest_sha256=(
            runtime_sha256
        ),
    )


def _select_final_audit_fixture(
    *,
    response_model_name: str,
):
    from pchsi.evaluation.canonical_evidence import (
        canonical_json_bytes,
        sha256_bytes,
    )
    from pchsi.evaluation.condition_run_schedule import (
        condition_cell_id,
    )
    from pchsi.evaluation.distillation_governance import (
        canonical_model_sha256,
    )
    from pchsi.evaluation.select_result_audit import (
        ExpectedSelectCellV1,
    )

    _server, runtime = (
        _select_policy_runtime_for_final_audit()
    )

    runtime_sha = sha256_bytes(
        canonical_json_bytes(
            runtime.to_dict()
        )
    )

    policy = (
        _select_policy_condition_for_final_audit(
            runtime_sha256=(
                runtime_sha
            ),
        )
    )

    policy_sha = (
        canonical_model_sha256(
            policy
        )
    )

    schedule_sha = (
        "8" * 64
    )

    cell_id = condition_cell_id(
        policy_condition_id=(
            policy.policy_condition_id
        ),
        manifest_index=2,
        seed=17,
    )

    expected = ExpectedSelectCellV1(
        schedule_name=(
            "r1_train17"
        ),
        condition_cell_id=(
            cell_id
        ),
        manifest_index=2,
        task_id=(
            "alfworld_valid_unseen_all134_0002"
        ),
        evaluation_seed=17,
        policy_condition_manifest_sha256=(
            policy_sha
        ),

        # The exact schedule carrying this cell
        # is also part of the frozen authority.
        condition_run_schedule_sha256=(
            schedule_sha
        ),
    )

    policy_call = (
        _select_policy_call_for_final_audit(
            response_model_name=(
                response_model_name
            ),
        )
    )

    trace = (
        _select_trace_provenance_for_final_audit()
    )

    # Replace synthetic provenance hashes with
    # the exact frozen identities for this fixture.
    from dataclasses import replace

    trace = replace(
        trace,
        model_version=(
            runtime_sha
        ),
        policy_condition_manifest_sha256=(
            policy_sha
        ),
        condition_run_schedule_sha256=(
            schedule_sha
        ),
        select_policy_runtime_manifest_sha256=(
            runtime_sha
        ),
    )

    episode = (
        _select_episode_for_final_audit(
            policy_condition_sha256=(
                policy_sha
            ),
            runtime_sha256=(
                runtime_sha
            ),
            schedule_sha256=(
                schedule_sha
            ),
        )
    )

    return (
        expected,
        policy,
        runtime,
        runtime_sha,
        policy_call,
        trace,
        episode,
    )


# ---------------------------------------------------------------------------
# 20. Final audit must consume exact request/response + trace + episode chain.
# ---------------------------------------------------------------------------

def test_select_result_audit_accepts_complete_model_identity_chain(
) -> None:
    from pchsi.evaluation.select_result_audit import (
        audit_select_cell_identity_chain,
    )

    (
        expected,
        policy,
        runtime,
        runtime_sha,
        policy_call,
        trace,
        episode,
    ) = _select_final_audit_fixture(
        response_model_name=(
            "P4-R1-Q2-BAD-TRAIN17"
        ),
    )

    audit_select_cell_identity_chain(
        expected_cell=expected,
        policy_condition=policy,
        policy_runtime=runtime,
        authorized_policy_runtime_sha256=(
            runtime_sha
        ),
        policy_calls=(
            policy_call,
        ),
        trace_provenances=(
            trace,
        ),
        episode_artifact=(
            episode
        ),
    )


# ---------------------------------------------------------------------------
# 21. A provider response naming another LoRA must fail final audit.
# ---------------------------------------------------------------------------

def test_select_result_audit_rejects_provider_model_mismatch(
) -> None:
    from pchsi.evaluation.select_result_audit import (
        audit_select_cell_identity_chain,
    )

    (
        expected,
        policy,
        runtime,
        runtime_sha,
        policy_call,
        trace,
        episode,
    ) = _select_final_audit_fixture(
        response_model_name=(
            "P4-R1-Q2-BAD-TRAIN31"
        ),
    )

    with pytest.raises(
        ValueError,
        match="model identity",
    ):
        audit_select_cell_identity_chain(
            expected_cell=expected,
            policy_condition=policy,
            policy_runtime=runtime,
            authorized_policy_runtime_sha256=(
                runtime_sha
            ),
            policy_calls=(
                policy_call,
            ),
            trace_provenances=(
                trace,
            ),
            episode_artifact=(
                episode
            ),
        )

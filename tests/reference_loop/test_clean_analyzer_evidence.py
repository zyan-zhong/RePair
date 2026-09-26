from __future__ import annotations

from pathlib import Path

import pytest

from pchsi.reference_loop.clean_analyzer_evidence import (
    build_clean_analyzer_evidence_pack,
    build_clean_current_trajectory_binding,
    build_pi0_i1_analyzer_policy_identity,
)
from pchsi.reference_loop.mechanical import extract_mechanical_episode_evidence
from pchsi.reference_loop.types import (
    BudgetCounters,
    NormalizedPolicyCall,
    NormalizedTrace,
    NormalizedTransition,
    ValidatedAttemptBundle,
)


def _bundle(root: Path) -> ValidatedAttemptBundle:
    before = BudgetCounters(0, 0, 0, 0, 0)
    after = BudgetCounters(1, 1, 0, 0, 0)
    call = NormalizedPolicyCall(
        model_call_index=0,
        environment_step_count_before=0,
        provider_request_id="req",
        public_task_goal="put a mug in cabinet",
        prompt_text="prompt",
        observation="start",
        admissible_commands=("go to shelf 1",),
        raw_response_text='{"phase":"SEARCH","reason":"inspect","action":"go to shelf 1"}',
        executed_history=(),
        budget_before=before,
    )
    trace = NormalizedTrace(
        model_call_index=0,
        environment_step_index=0,
        execution_status="executed",
        public_task_goal="put a mug in cabinet",
        observation="start",
        prompt_text="prompt",
        admissible_commands=("go to shelf 1",),
        raw_model_response=call.raw_response_text,
        literal_action="go to shelf 1",
        normalized_action="go to shelf 1",
        parser_status="success",
        parser_error=None,
        attempt_outcome="ACTION_EXECUTED",
        failure_stage=None,
        failure_code=None,
        submitted_environment_action="go to shelf 1",
        final_executed_action="go to shelf 1",
        resulting_observation="at shelf 1",
        episode_termination_reason="POLICY_ATTEMPT_BUDGET_EXHAUSTED",
        budget_before=before,
        budget_after=after,
        provenance={},
    )
    transition = NormalizedTransition(
        scheduled_cell_id="cell",
        execution_attempt_id="attempt",
        model_call_index=0,
        environment_step_index=0,
        submitted_action="go to shelf 1",
        pre_observation="start",
        pre_menu=("go to shelf 1",),
        resulting_observation="at shelf 1",
        resulting_menu=("look",),
        done=False,
        won=False,
        score=0,
    )
    return ValidatedAttemptBundle(
        bundle_root=root,
        episode={
            "task_id": "task-1",
            "task_type": "pick_and_place_simple",
            "gamefile_sha256": "a" * 64,
            "seed": 17,
            "success": False,
            "termination_reason": "POLICY_ATTEMPT_BUDGET_EXHAUSTED",
            "final_done": False,
            "final_won": False,
        },
        policy_calls=(call,),
        traces=(trace,),
        transitions=(transition,),
        source_file_sha256s=(
            ("attempt.json", "b" * 64),
            ("action_traces.jsonl", "c" * 64),
            ("policy_calls.jsonl", "d" * 64),
            ("public_transitions.jsonl", "e" * 64),
            ("SHA256SUMS", "f" * 64),
        ),
        episode_semantic_sha256="1" * 64,
        attempt_bundle_sha256="2" * 64,
        alignment_census={"status": "VALIDATED"},
    )


def _pi0_artifact() -> dict[str, object]:
    return {
        "schema_id": "PI0_CLEAN_MODEL_ARTIFACT_V1",
        "model_repository": "Qwen/Qwen2.5-3B-Instruct",
        "model_revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
        "pi0_artifact_sha256": "3" * 64,
        "project_lora_present": False,
        "project_adapter_present": False,
        "project_memory_present": False,
        "contaminated_trace_dependency_count": 0,
        "artifact_role": "PI0_CLEAN_PROJECT_UNADAPTED_POLICY",
    }


def _runtime() -> dict[str, object]:
    return {
        "schema_id": "PI0_CLEAN_RUNTIME_BINDING_V1",
        "pi0_artifact_sha256": "3" * 64,
        "runtime_binding_sha256": "4" * 64,
        "lora_modules": [],
        "project_adapter": None,
        "memory": "OFF",
        "harness": "OFF",
    }


def _cutoff(root: Path) -> dict[str, object]:
    return {
        "schema_id": "PI0_I1_TRAIN_UPDATE_EVIDENCE_CUTOFF_V1",
        "parent_policy_id": "PI0_CLEAN",
        "policy_interface_profile_id": "I1_EXECUTION_PROFILE_V1",
        "source_split": "ALFWORLD_TRAIN",
        "source_train_pool": "TRAIN_UPDATE",
        "source_campaign_root": str(root),
        "source_campaign_sha256": "5" * 64,
        "evidence_cutoff_sha256": "6" * 64,
        "evidence_cutoff_frozen": True,
        "benchmark_results_visible": False,
        "benchmark_feedback_authorized": False,
    }


def _readiness() -> dict[str, object]:
    return {
        "schema_id": "PI0_I1_ANALYZER_INPUT_READINESS_V1",
        "clean_inputs_pass": True,
        "benchmark_results_visible": False,
        "clean_access_grants": {"HIERARCHICAL_ANALYZER": "7" * 64},
    }


def _row() -> dict[str, object]:
    return {
        "scientific_cell_id": "clean-train-update-t0000-s0000000017",
        "execution_attempt_id": "attempt",
        "task_id": "task-1",
        "classification": "TASK_FAILURE",
        "source_campaign_sha256": "5" * 64,
        "policy_interface_profile_id": "I1_EXECUTION_PROFILE_V1",
        "attempt_bundle_sha256": "2" * 64,
        "episode_semantic_sha256": "1" * 64,
        "attempt_bundle_relpath": "attempt",
        "per_task_full_view_relpath": "reports/per_task/full/x.json",
        "per_task_full_view_sha256": "8" * 64,
    }


def test_clean_current_evidence_path_has_no_historical_lineage_dependency(tmp_path: Path) -> None:
    root = tmp_path / "campaign"
    bundle_root = root / "attempt"
    bundle_root.mkdir(parents=True)
    bundle = _bundle(bundle_root)
    cutoff = _cutoff(root)
    identity = build_pi0_i1_analyzer_policy_identity(
        pi0_artifact=_pi0_artifact(),
        runtime_binding=_runtime(),
        evidence_cutoff=cutoff,
    )
    binding = build_clean_current_trajectory_binding(
        bundle=bundle,
        evidence_row=_row(),
        evidence_cutoff=cutoff,
        analyzer_readiness=_readiness(),
        policy_identity=identity,
        source_campaign_root=root,
    )
    mechanical = extract_mechanical_episode_evidence(bundle)
    pack = build_clean_analyzer_evidence_pack(
        bundle=bundle,
        policy_identity=identity,
        trajectory_binding=binding,
        mechanical_evidence=mechanical,
    )

    assert identity["logical_policy_id"] == "PI0_CLEAN"
    assert identity["policy_interface_profile_id"] == "I1_EXECUTION_PROFILE_V1"
    assert binding["binding_mode"] == "CLEAN_CURRENT_ROUND_TRAIN_UPDATE_V1"
    assert binding["historical_adaptive_reference_count"] == 0
    assert pack["schema_id"] == "ANALYZER_EVIDENCE_PACK_V1"
    assert pack["pack_role"] == "COMMON_EVIDENCE_IDENTICAL_ACROSS_A0_A1_A2_A3"
    assert pack["policy_identity"]["logical_policy_id"] == "PI0_CLEAN"
    assert "historical_lineage_bridge_sha256" not in pack["trajectory_identity"]
    assert pack["memory_support_port"]["base_pack_exposes_memory"] is False
    assert pack["analyzer_output_authority"]["benefit_harm_authority"] is False
    assert pack["requires_environment_verification"] is True


def test_clean_current_binding_rejects_wrong_campaign(tmp_path: Path) -> None:
    root = tmp_path / "campaign"
    bundle_root = root / "attempt"
    bundle_root.mkdir(parents=True)
    bundle = _bundle(bundle_root)
    cutoff = _cutoff(root)
    identity = build_pi0_i1_analyzer_policy_identity(
        pi0_artifact=_pi0_artifact(),
        runtime_binding=_runtime(),
        evidence_cutoff=cutoff,
    )
    row = _row()
    row["source_campaign_sha256"] = "9" * 64
    with pytest.raises(ValueError, match="source campaign mismatch"):
        build_clean_current_trajectory_binding(
            bundle=bundle,
            evidence_row=row,
            evidence_cutoff=cutoff,
            analyzer_readiness=_readiness(),
            policy_identity=identity,
            source_campaign_root=root,
        )

from __future__ import annotations

from pathlib import Path

from pchsi.reference_loop.analyzer_evidence_pack import (
    build_analyzer_evidence_pack,
)
from pchsi.reference_loop.historical_rebinding import (
    build_historical_trajectory_rebinding_manifest,
)
from pchsi.reference_loop.types import (
    BudgetCounters,
    NormalizedPolicyCall,
    NormalizedTrace,
    NormalizedTransition,
    ValidatedAttemptBundle,
)


def _bundle() -> ValidatedAttemptBundle:
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
        raw_response_text='{"action":"go to shelf 1"}',
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
        raw_model_response='{"action":"go to shelf 1"}',
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
        episode_termination_reason=None,
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
        bundle_root=Path("/tmp/bundle"),
        episode={
            "task_id": "task-1",
            "task_type": "pick_and_place_simple",
            "gamefile_sha256": "a" * 64,
            "seed": 17,
            "logical_condition_id": None,
            "checkpoint_instance_id": None,
            "access_class": None,
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


def _identity():
    return {
        "schema_id": "PI1_REFERENCE_IDENTITY_V1",
        "logical_policy_id": "P4-R1-Q2-BAD",
        "checkpoint_instance_id": "P4-R1-Q2-BAD-TRAIN17",
        "identity_sha256": "3" * 64,
    }


def _access():
    return {
        "revalidation_sha256": "4" * 64,
        "rows": [
            {
                "task_id": "task-1",
                "gamefile_sha256": "a" * 64,
                "row_sha256": "5" * 64,
                "revalidation_disposition": "CONFIRMED_UNCHANGED",
                "strong_model_allowed": True,
                "allowed_artifact_granularity": (
                    "FULL_TRAJECTORY_DEV_VISIBLE"
                ),
            }
        ],
    }


def _lineage():
    row = {
        "attempt_bundle_sha256": "2" * 64,
        "episode_semantic_sha256": "1" * 64,
        "task_id": "task-1",
        "gamefile_sha256": "a" * 64,
        "logical_policy_id": "P4-R1-Q2-BAD",
        "checkpoint_instance_id": "P4-R1-Q2-BAD-TRAIN17",
        "task_access_row_sha256": "5" * 64,
        "row_sha256": "6" * 64,
    }
    return {
        "schema_id": "SOURCE_COLLECTION_PI1_LINEAGE_BRIDGE_V1",
        "bridge_sha256": "7" * 64,
        "rows": [row],
    }


def _mechanical():
    return {
        "schema_id": "MECHANICAL_EPISODE_EVIDENCE_V1",
        "source_attempt_bundle_sha256": "2" * 64,
        "authority": "DETERMINISTIC_FACTS_ONLY",
        "generic_episode_facts": {"policy_call_count": 1},
        "alfworld_event_facts": {"parser_version": "V1"},
        "evidence_sha256": "8" * 64,
    }


def test_historical_rebinding_uses_lineage_not_legacy_missing_fields() -> None:
    value = build_historical_trajectory_rebinding_manifest(
        bundle=_bundle(),
        pi1_identity=_identity(),
        task_access=_access(),
        lineage_bridge=_lineage(),
    )

    assert value["rebinding_mode"] == "HISTORICAL_LINEAGE_SIDECAR_V1"
    assert value["checkpoint_instance_id"] == "P4-R1-Q2-BAD-TRAIN17"
    assert value["analyzer_run_id"] is None
    assert value["candidate_repair_ids"] == []


def test_analyzer_evidence_pack_is_common_and_has_no_outcome_authority() -> None:
    bundle = _bundle()
    rebinding = build_historical_trajectory_rebinding_manifest(
        bundle=bundle,
        pi1_identity=_identity(),
        task_access=_access(),
        lineage_bridge=_lineage(),
    )
    pack = build_analyzer_evidence_pack(
        bundle=bundle,
        pi1_identity=_identity(),
        rebinding_manifest=rebinding,
        mechanical_evidence=_mechanical(),
        lineage_bridge=_lineage(),
    )

    assert pack["pack_role"] == "COMMON_EVIDENCE_IDENTICAL_ACROSS_A0_A1_A2_A3"
    assert pack["memory_support_port"]["base_pack_exposes_memory"] is False
    assert pack["analyzer_output_authority"]["benefit_harm_authority"] is False
    assert pack["requires_environment_verification"] is True
    assert pack["trajectory"][0]["observation_before"] == "start"

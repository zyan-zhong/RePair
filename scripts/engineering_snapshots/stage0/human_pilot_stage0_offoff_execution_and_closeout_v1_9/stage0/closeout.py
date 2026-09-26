from __future__ import annotations

from typing import Any

from .common import domain_sha256


def build_closeout(
    *,
    result_sha256: str,
    artifact_index_sha256: str,
    package_inventory_sha256: str,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_id": "PILOT_ENGINEERING_ROUND_CLOSEOUT_V1",
        "schema_version": 1,
        "round_id": "HUMAN_REFERENCE_ROUND_PI1_PI2_V1",
        "round_role": "PILOT_ENGINEERING_ROUND_V1",
        "round_status": "CLOSED",
        "paper_efficacy_evidence": False,
        "paper_performance_claim_authorized": False,
        "promotion_eligible": False,
        "promotion_decision": "NOT_APPLICABLE_ENGINEERING_PILOT",
        "contamination_note": (
            "117 public ALFWorld valid_unseen tasks were development-exposed "
            "before this retrospective 117/17 governance partition."
        ),
        "contaminated_valid_unseen_development_task_count": 117,
        "heldout_select_task_count": 17,
        "official_valid_unseen_task_count": 134,
        "result_sha256": result_sha256,
        "artifact_index_sha256": artifact_index_sha256,
        "package_inventory_sha256": package_inventory_sha256,
        "permitted_reuse": [
            "CODE",
            "SCHEMAS",
            "CONTRACTS",
            "TESTS",
            "INFRASTRUCTURE",
            "GENERIC_RUNTIME_PATTERNS",
        ],
        "forbidden_clean_experiment_inputs": [
            "CURRENT_PILOT_POLICY_ADAPTERS",
            "CURRENT_PILOT_TRAJECTORIES",
            "CURRENT_T2_TRAINING_ROWS",
            "CURRENT_FAILURE_MEMORY_CONTENT",
            "CURRENT_HUMAN_TASK_SPECIFIC_DECISIONS",
            "CURRENT_STRONG_TASK_SPECIFIC_TRACES",
            "CURRENT_RESEARCH_PLANNER_TASK_SPECIFIC_PLANS",
            "CURRENT_17_TASK_SELECT_OUTCOMES",
        ],
        "next_gate": (
            "GENERIC_ROUND_ORCHESTRATOR_AND_ROLE_HANDOFF_AUTOMATION"
        ),
        "closeout_sha256": "",
    }
    value["closeout_sha256"] = domain_sha256(
        value["schema_id"],
        value,
        sha_field="closeout_sha256",
    )
    return value


def build_stage1_handoff(*, closeout_sha256: str) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_id": "STAGE1_AUTOMATION_HANDOFF_V1",
        "schema_version": 1,
        "status": "READY_FOR_STAGE1_AUTOMATION_DESIGN",
        "stage0_closeout_sha256": closeout_sha256,
        "reuse_existing_components": [
            "EVIDENCE_PACKAGE",
            "HIERARCHICAL_ANALYZER",
            "PERSISTENT_FAILURE_EXPERIENCE",
            "RESEARCH_PLANNER_PRE_POST",
            "SAME_STATE_F0F1",
            "TRAINING_DATA_PLAN",
            "DETERMINISTIC_DATA_BUILDER",
            "SCHEMA_AWARE_RENDERER",
            "GENERIC_TRAINING_STAGE_V2_1",
            "MODEL_INIT_SMOKE",
            "TRAINING_RECEIPTS",
            "SELECT_EVALUATOR",
            "GENERIC_SELECT_POLICY_BINDING",
            "PROMOTION_ROLLBACK_CONTRACTS",
            "STRONG_TRACE_STORAGE",
        ],
        "minimal_new_components": [
            "GENERIC_ROUND_ORCHESTRATOR",
            "ROLE_AUTHORITY_SWITCH",
            "ROUND_LIFECYCLE_STATE_MACHINE",
            "CLEAN_DATA_ACCESS_GATE",
            "HUMAN_STRONG_LOCAL_TRACE_HANDOFF",
            "BENCHMARK_RESULT_SEALING",
            "CROSS_ROUND_RETENTION_POLICY",
            "AUTOMATIC_ROLLBACK_AND_NEXT_ROUND_CREATION",
        ],
        "clean_experiment_constraint": (
            "All future training, analysis, Memory, F0/F1, selection, and "
            "role supervision must use ALFWorld train-only evidence."
        ),
        "stage1_handoff_sha256": "",
    }
    value["stage1_handoff_sha256"] = domain_sha256(
        value["schema_id"],
        value,
        sha_field="stage1_handoff_sha256",
    )
    return value

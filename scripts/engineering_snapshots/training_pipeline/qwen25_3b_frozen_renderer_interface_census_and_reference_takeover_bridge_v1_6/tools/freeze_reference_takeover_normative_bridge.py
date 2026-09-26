#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from common import ContractError, finalize, write_new_json


def main() -> int:
    bridge = finalize(
        "REFERENCE_TO_TAKEOVER_NORMATIVE_BRIDGE_V1",
        "normative_bridge_sha256",
        {
            "schema_id": "REFERENCE_TO_TAKEOVER_NORMATIVE_BRIDGE_V1",
            "schema_version": 1,
            "continuity_principle": (
                "INHERIT_NORMS_AND_TEACHER_TRACES_RESET_FRESH_ROUND_ANSWERS"
            ),
            "human_reference_round_role": (
                "BOOTSTRAP_REFERENCE_CURRICULUM_AND_NORMATIVE_SPEC_BUILDER"
            ),
            "human_reference_teacher_artifact_identities": {
                "human_pre_record_sha256": os.environ[
                    "HUMAN_PRE_RECORD_SHA256"
                ],
                "strong_pre_shadow_record_sha256": os.environ[
                    "STRONG_PRE_RECORD_SHA256"
                ],
                "pre_field_adjudication_file_sha256": os.environ[
                    "PRE_FIELD_ADJUDICATION_FILE_SHA256"
                ],
                "f0f1_result_audit_sha256": os.environ[
                    "F0F1_RESULT_AUDIT_SHA256"
                ],
                "neutral_mechanism_audit_sha256": os.environ[
                    "NEUTRAL_MECHANISM_AUDIT_SHA256"
                ],
                "human_post_record_sha256": os.environ[
                    "HUMAN_POST_RECORD_SHA256"
                ],
                "strong_post_shadow_record_sha256": os.environ[
                    "STRONG_POST_RECORD_SHA256"
                ],
                "post_comparison_sha256": os.environ[
                    "POST_COMPARISON_SHA256"
                ],
                "post_adjudication_sha256": os.environ[
                    "POST_ADJUDICATION_SHA256"
                ],
                "strong_training_plan_sha256": os.environ[
                    "EXPECTED_STRONG_PLAN_SHA256"
                ],
                "semantic_materialization_sha256": os.environ[
                    "EXPECTED_V13_SEMANTIC_MATERIALIZATION_SHA256"
                ],
                "serialization_handoff_sha256": os.environ[
                    "EXPECTED_V14_SERIALIZATION_HANDOFF_SHA256"
                ],
            },
            "inherited_analysis_norms": [
                "PRE_POST_STRICT_SEPARATION",
                "ACTIVE_POLICY_AND_FAILURE_COHORT_EXPLICIT",
                "BOTTLENECK_HYPOTHESIS_EXPLICIT",
                "REPAIR_PORTFOLIO_AND_ABSTENTION_EXPLICIT",
                "SAME_STATE_F0F1_CAUSAL_VERIFICATION",
                "ENVIRONMENT_VERIFIER_SOLE_BENEFIT_HARM_NEUTRAL_UNCERTAIN_AUTHORITY",
                "BENEFIT_HARM_NEUTRAL_UNCERTAIN_ALL_HAVE_EXPLICIT_HANDLING",
                "NEUTRAL_TERMINAL_TRUTH_IMMUTABLE_BUT_TRAINING_ROUTE_MUST_RESOLVE",
                "UNCERTAIN_NOT_FORCED_BINARY",
                "FAILURE_EXPERIENCE_RETAINS_APPLICABILITY_AND_COUNTEREXAMPLE",
                "COST_RISK_BUDGET_STOP_AND_ROLLBACK_EXPLICIT",
            ],
            "inherited_training_norms": [
                "RESEARCH_PLANNER_POST_OWNS_DATA_SEMANTICS_MIXTURE_RECIPE_BUDGET",
                "DETERMINISTIC_DATA_BUILDER_NO_RELABEL_NO_SEMANTIC_INVENTION",
                "TRAINER_EXECUTES_FROZEN_RECIPE_ONLY",
                "PROMOTION_GATE_INDEPENDENT",
                "T0_T6_PERSISTENT_REGISTRY",
                "PREFIX_ONLY_POLICY_ACTION_SUPERVISION",
                "HINDSIGHT_ANALYSIS_SEPARATED_FROM_POLICY_ACTION_INPUT",
                "MEMORY_OFF_HARNESS_OFF_CAPABILITY_AUTHORITY",
                "NO_BEST_SEED_SELECTION",
                "SUCCESS_TRAJECTORY_OPTIMIZATION_INTERFACE_RETAINED_CURRENTLY_INACTIVE",
            ],
            "strong_takeover_inherits": [
                "ARTIFACT_SCHEMAS",
                "ANALYSIS_NORMS",
                "EVIDENCE_STANDARDS",
                "PRE_POST_DISCIPLINE",
                "OUTCOME_ROUTING_VOCABULARY",
                "T0_T6_TRAINING_REGISTRY",
                "DATA_BUILDER_TRAINER_PROMOTION_AUTHORITY_BOUNDARIES",
                "HUMAN_REFERENCE_TEACHER_TRACES_AS_BOOTSTRAP_CURRICULUM",
            ],
            "strong_takeover_fresh_round_resets": [
                "ACTIVE_PARENT_POLICY",
                "FRESH_FAILURE_COHORT",
                "BOTTLENECK",
                "PRINCIPAL_CHANGE",
                "REPAIR_PORTFOLIO",
                "EXPERIMENT_AND_BUDGET",
                "F0F1_OUTCOMES",
                "FINAL_TRAINING_ROUTES",
                "DATASET_MIXTURE",
                "TRAINING_RECIPE",
                "PROMOTION_DECISION",
            ],
            "strong_takeover_must_not_treat_as_fresh_answers": [
                "HUMAN_REFERENCE_BOTTLENECK",
                "HUMAN_REFERENCE_12_STATE_REPAIR_PORTFOLIO",
                "HUMAN_REFERENCE_NEUTRAL_LABELS",
                "HUMAN_REFERENCE_ROLLBACK_DECISION",
                "HUMAN_REFERENCE_T0_T2_MIXTURE",
            ],
            "strong_takeover_authority": {
                "fresh_round_required": True,
                "fresh_failure_cohort_required": True,
                "strong_research_planner_primary": True,
                "human_role": "AUDIT_DISAGREEMENT_SAFETY_ONLY",
                "human_reference_curriculum_visible": True,
                "human_reference_same_round_answers_binding": False,
                "same_artifact_contracts_required": True,
            },
            "local_autonomous_authority": {
                "fresh_round_required": True,
                "local_qwen_research_planner_primary": True,
                "teacher_curriculum_sources": [
                    "HUMAN_REFERENCE_ROUND",
                    "STRONG_PRIMARY_FRESH_ROUND",
                ],
                "same_artifact_contracts_required": True,
                "routine_human_decisions_zero": True,
                "routine_strong_calls_zero": True,
            },
            "current_readiness": {
                "human_reference_renderer_adapter_complete": False,
                "human_reference_training_complete": False,
                "human_reference_memory_off_harness_off_eval_complete": False,
                "human_reference_closeout_complete": False,
                "strong_takeover_execution_ready": False,
                "local_autonomous_execution_ready": False,
                "current_blocking_gate": (
                    "EXACT_SCHEMA_AWARE_RENDERER_ADAPTER_AND_PI2_HUMAN_CLOSEOUT"
                ),
            },
        },
    )

    root = Path(os.environ["BRIDGE_ROOT"])
    root.mkdir(parents=True, exist_ok=False)
    write_new_json(
        root / "REFERENCE_TO_TAKEOVER_NORMATIVE_BRIDGE_V1.json",
        bridge,
    )
    print("REFERENCE_TO_TAKEOVER_NORMATIVE_BRIDGE_FREEZE_PASS")
    print(
        "NORMATIVE_BRIDGE_SHA256="
        + bridge["normative_bridge_sha256"]
    )
    print("REFERENCE_NORM_CONTINUITY=true")
    print("FRESH_ROUND_ANSWERS_RESET=true")
    print("STRONG_TAKEOVER_EXECUTION_READY=false")
    print("LOCAL_AUTONOMOUS_EXECUTION_READY=false")
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        raise SystemExit("STOP=" + str(exc))

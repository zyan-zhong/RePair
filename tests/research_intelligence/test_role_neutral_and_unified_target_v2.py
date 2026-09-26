from __future__ import annotations

import hashlib

import pytest

from pchsi.research_intelligence.role_neutral import (
    AutonomyAttestationV1,
    ResearcherPreDecisionV1,
    ResearcherRoleModeV1,
    UnifiedQwenRoleTargetV1,
)


def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_role_neutral_pre_preserves_one_selected_bottleneck() -> None:
    pre = ResearcherPreDecisionV1(
        schema_version="RESEARCHER_PRE_DECISION_V1",
        round_id="pi1-to-pi2",
        parent_policy_id="pi1",
        researcher_role_mode=ResearcherRoleModeV1.HUMAN_REFERENCE,
        raw_artifact_sha256=h("human-pre"),
        evidence_cutoff_sha256=h("evidence"),
        candidate_bottleneck_ids=("b1", "b2", "b3"),
        selected_bottleneck_id="b2",
        selected_principal_change_id="change-1",
        rejected_direction_ids=("b1",),
        deferred_direction_ids=("b3",),
        repair_portfolio_sha256=h("repairs"),
        verification_budget_id="budget-1",
        training_plan_id="training-1",
        stop_rule_id="stop-1",
    )
    pre.validate()
    assert pre.to_dict()["researcher_role_mode"] == "HUMAN_REFERENCE"


def target(*, analyzer_checkpoint: str = "theta-k") -> UnifiedQwenRoleTargetV1:
    return UnifiedQwenRoleTargetV1(
        schema_version="UNIFIED_QWEN_ROLE_TARGET_V1",
        target_model_family="Qwen2.5-3B",
        target_checkpoint_id="theta-k",
        architecture_sha256=h("architecture"),
        tokenizer_sha256=h("tokenizer"),
        policy_checkpoint_id="theta-k",
        analyzer_checkpoint_id=analyzer_checkpoint,
        research_planner_checkpoint_id="theta-k",
        policy_visibility_contract_sha256=h("policy-view"),
        analyzer_visibility_contract_sha256=h("analyzer-view"),
        research_planner_visibility_contract_sha256=h("planner-view"),
        policy_role_prompt_sha256=h("policy-prompt"),
        analyzer_role_prompt_sha256=h("analyzer-prompt"),
        research_planner_role_prompt_sha256=h("planner-prompt"),
        target_requirement="MANDATORY_FINAL_SYSTEM_TARGET",
        immediate_reference_round_blocker=False,
    )


def test_final_system_requires_same_qwen_checkpoint_for_all_three_roles() -> None:
    target().validate()
    with pytest.raises(ValueError, match="share one checkpoint"):
        target(analyzer_checkpoint="theta-other").validate()


def test_autonomous_claim_requires_zero_human_and_external_routine_calls() -> None:
    attestation = AutonomyAttestationV1(
        schema_version="AUTONOMY_ATTESTATION_V1",
        round_id="fresh-pi2-pi3",
        policy_checkpoint_id="theta-3",
        analyzer_checkpoint_id="theta-3",
        research_planner_checkpoint_id="theta-3",
        per_round_human_scientific_decisions=1,
        routine_external_model_calls=0,
        independent_verifier=True,
        deterministic_promotion_gate=True,
        sealed_evaluation_details_hidden_from_planner=True,
        fresh_round=True,
    )
    with pytest.raises(ValueError, match="zero per-round human decisions"):
        attestation.validate_for_autonomous_claim()

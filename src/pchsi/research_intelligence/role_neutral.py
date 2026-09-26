"""Role-neutral Researcher artifacts and final unified-Qwen target contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class ResearcherRoleModeV1(str, Enum):
    HUMAN_REFERENCE = "HUMAN_REFERENCE"
    STRONG_API_SHADOW = "STRONG_API_SHADOW"
    STRONG_API_PRIMARY = "STRONG_API_PRIMARY"
    LOCAL_SHADOW = "LOCAL_SHADOW"
    LOCAL_PRIMARY = "LOCAL_PRIMARY"


class ResearcherArtifactStageV1(str, Enum):
    PRE_DECISION = "PRE_DECISION"
    POST_INTERPRETATION = "POST_INTERPRETATION"


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_sha256(value: str, name: str) -> None:
    _require_text(value, name)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{name} must be lowercase SHA-256")


def _unique(values: tuple[str, ...], name: str, *, allow_empty: bool = False) -> None:
    if not allow_empty and not values:
        raise ValueError(f"{name} must be non-empty")
    for value in values:
        _require_text(value, name)
    if len(set(values)) != len(values):
        raise ValueError(f"{name} contains duplicates")


@dataclass(frozen=True)
class ResearcherPreDecisionV1:
    schema_version: str
    round_id: str
    parent_policy_id: str
    researcher_role_mode: ResearcherRoleModeV1
    raw_artifact_sha256: str
    evidence_cutoff_sha256: str
    candidate_bottleneck_ids: tuple[str, ...]
    selected_bottleneck_id: str
    selected_principal_change_id: str
    rejected_direction_ids: tuple[str, ...]
    deferred_direction_ids: tuple[str, ...]
    repair_portfolio_sha256: str
    verification_budget_id: str
    training_plan_id: str
    stop_rule_id: str

    def validate(self) -> None:
        if self.schema_version != "RESEARCHER_PRE_DECISION_V1":
            raise ValueError("unexpected PRE schema version")
        for name in (
            "round_id",
            "parent_policy_id",
            "selected_bottleneck_id",
            "selected_principal_change_id",
            "verification_budget_id",
            "training_plan_id",
            "stop_rule_id",
        ):
            _require_text(getattr(self, name), name)
        _require_sha256(self.raw_artifact_sha256, "raw_artifact_sha256")
        _require_sha256(self.evidence_cutoff_sha256, "evidence_cutoff_sha256")
        _require_sha256(self.repair_portfolio_sha256, "repair_portfolio_sha256")
        _unique(self.candidate_bottleneck_ids, "candidate_bottleneck_ids")
        _unique(self.rejected_direction_ids, "rejected_direction_ids", allow_empty=True)
        _unique(self.deferred_direction_ids, "deferred_direction_ids", allow_empty=True)
        if self.selected_bottleneck_id not in self.candidate_bottleneck_ids:
            raise ValueError("selected bottleneck must be in candidate set")
        if set(self.rejected_direction_ids) & set(self.deferred_direction_ids):
            raise ValueError("a direction cannot be both rejected and deferred")
        if self.selected_bottleneck_id in set(self.rejected_direction_ids) | set(
            self.deferred_direction_ids
        ):
            raise ValueError("selected bottleneck cannot be rejected or deferred")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "round_id": self.round_id,
            "parent_policy_id": self.parent_policy_id,
            "researcher_role_mode": self.researcher_role_mode.value,
            "raw_artifact_sha256": self.raw_artifact_sha256,
            "evidence_cutoff_sha256": self.evidence_cutoff_sha256,
            "candidate_bottleneck_ids": list(self.candidate_bottleneck_ids),
            "selected_bottleneck_id": self.selected_bottleneck_id,
            "selected_principal_change_id": self.selected_principal_change_id,
            "rejected_direction_ids": list(self.rejected_direction_ids),
            "deferred_direction_ids": list(self.deferred_direction_ids),
            "repair_portfolio_sha256": self.repair_portfolio_sha256,
            "verification_budget_id": self.verification_budget_id,
            "training_plan_id": self.training_plan_id,
            "stop_rule_id": self.stop_rule_id,
        }


@dataclass(frozen=True)
class ResearcherPostInterpretationV1:
    schema_version: str
    round_id: str
    parent_policy_id: str
    candidate_policy_id: str | None
    researcher_role_mode: ResearcherRoleModeV1
    raw_artifact_sha256: str
    pre_decision_sha256: str
    round_evidence_package_sha256: str
    hypothesis_status: str
    unexpected_evidence_ids: tuple[str, ...]
    selected_lessons: tuple[str, ...]
    next_round_recommendation: str
    promotion_recommendation: str

    def validate(self) -> None:
        if self.schema_version != "RESEARCHER_POST_INTERPRETATION_V1":
            raise ValueError("unexpected POST schema version")
        for name in (
            "round_id",
            "parent_policy_id",
            "hypothesis_status",
            "next_round_recommendation",
            "promotion_recommendation",
        ):
            _require_text(getattr(self, name), name)
        if self.candidate_policy_id is not None:
            _require_text(self.candidate_policy_id, "candidate_policy_id")
        for name in (
            "raw_artifact_sha256",
            "pre_decision_sha256",
            "round_evidence_package_sha256",
        ):
            _require_sha256(getattr(self, name), name)
        _unique(self.unexpected_evidence_ids, "unexpected_evidence_ids", allow_empty=True)
        _unique(self.selected_lessons, "selected_lessons")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "round_id": self.round_id,
            "parent_policy_id": self.parent_policy_id,
            "candidate_policy_id": self.candidate_policy_id,
            "researcher_role_mode": self.researcher_role_mode.value,
            "raw_artifact_sha256": self.raw_artifact_sha256,
            "pre_decision_sha256": self.pre_decision_sha256,
            "round_evidence_package_sha256": self.round_evidence_package_sha256,
            "hypothesis_status": self.hypothesis_status,
            "unexpected_evidence_ids": list(self.unexpected_evidence_ids),
            "selected_lessons": list(self.selected_lessons),
            "next_round_recommendation": self.next_round_recommendation,
            "promotion_recommendation": self.promotion_recommendation,
        }


@dataclass(frozen=True)
class UnifiedQwenRoleTargetV1:
    schema_version: str
    target_model_family: str
    target_checkpoint_id: str
    architecture_sha256: str
    tokenizer_sha256: str
    policy_checkpoint_id: str
    analyzer_checkpoint_id: str
    research_planner_checkpoint_id: str
    policy_visibility_contract_sha256: str
    analyzer_visibility_contract_sha256: str
    research_planner_visibility_contract_sha256: str
    policy_role_prompt_sha256: str
    analyzer_role_prompt_sha256: str
    research_planner_role_prompt_sha256: str
    target_requirement: str
    immediate_reference_round_blocker: bool

    def validate(self) -> None:
        if self.schema_version != "UNIFIED_QWEN_ROLE_TARGET_V1":
            raise ValueError("unexpected unified-role target schema")
        if self.target_model_family != "Qwen2.5-3B":
            raise ValueError("final unified target must remain Qwen2.5-3B lineage")
        for name in (
            "target_checkpoint_id",
            "policy_checkpoint_id",
            "analyzer_checkpoint_id",
            "research_planner_checkpoint_id",
            "target_requirement",
        ):
            _require_text(getattr(self, name), name)
        checkpoints = {
            self.target_checkpoint_id,
            self.policy_checkpoint_id,
            self.analyzer_checkpoint_id,
            self.research_planner_checkpoint_id,
        }
        if len(checkpoints) != 1:
            raise ValueError("Policy, Analyzer, and Research Planner must share one checkpoint")
        for name in (
            "architecture_sha256",
            "tokenizer_sha256",
            "policy_visibility_contract_sha256",
            "analyzer_visibility_contract_sha256",
            "research_planner_visibility_contract_sha256",
            "policy_role_prompt_sha256",
            "analyzer_role_prompt_sha256",
            "research_planner_role_prompt_sha256",
        ):
            _require_sha256(getattr(self, name), name)
        if self.target_requirement != "MANDATORY_FINAL_SYSTEM_TARGET":
            raise ValueError("unified checkpoint must be a mandatory final target")
        if self.immediate_reference_round_blocker:
            raise ValueError(
                "unified checkpoint is mandatory eventually but cannot block the human reference round"
            )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "target_model_family": self.target_model_family,
            "target_checkpoint_id": self.target_checkpoint_id,
            "architecture_sha256": self.architecture_sha256,
            "tokenizer_sha256": self.tokenizer_sha256,
            "policy_checkpoint_id": self.policy_checkpoint_id,
            "analyzer_checkpoint_id": self.analyzer_checkpoint_id,
            "research_planner_checkpoint_id": self.research_planner_checkpoint_id,
            "policy_visibility_contract_sha256": self.policy_visibility_contract_sha256,
            "analyzer_visibility_contract_sha256": self.analyzer_visibility_contract_sha256,
            "research_planner_visibility_contract_sha256": self.research_planner_visibility_contract_sha256,
            "policy_role_prompt_sha256": self.policy_role_prompt_sha256,
            "analyzer_role_prompt_sha256": self.analyzer_role_prompt_sha256,
            "research_planner_role_prompt_sha256": self.research_planner_role_prompt_sha256,
            "target_requirement": self.target_requirement,
            "immediate_reference_round_blocker": self.immediate_reference_round_blocker,
        }


@dataclass(frozen=True)
class AutonomyAttestationV1:
    schema_version: str
    round_id: str
    policy_checkpoint_id: str
    analyzer_checkpoint_id: str
    research_planner_checkpoint_id: str
    per_round_human_scientific_decisions: int
    routine_external_model_calls: int
    independent_verifier: bool
    deterministic_promotion_gate: bool
    sealed_evaluation_details_hidden_from_planner: bool
    fresh_round: bool

    def validate_for_autonomous_claim(self) -> None:
        if self.schema_version != "AUTONOMY_ATTESTATION_V1":
            raise ValueError("unexpected autonomy attestation schema")
        _require_text(self.round_id, "round_id")
        checkpoints = {
            self.policy_checkpoint_id,
            self.analyzer_checkpoint_id,
            self.research_planner_checkpoint_id,
        }
        if len(checkpoints) != 1:
            raise ValueError("autonomous unified claim requires one shared checkpoint")
        if self.per_round_human_scientific_decisions != 0:
            raise ValueError("autonomous claim requires zero per-round human decisions")
        if self.routine_external_model_calls != 0:
            raise ValueError("autonomous claim requires zero routine external model calls")
        if not self.independent_verifier:
            raise ValueError("independent verifier is mandatory")
        if not self.deterministic_promotion_gate:
            raise ValueError("deterministic promotion gate is mandatory")
        if not self.sealed_evaluation_details_hidden_from_planner:
            raise ValueError("sealed evaluation details must be hidden from planner")
        if not self.fresh_round:
            raise ValueError("autonomous claim requires a fresh round")

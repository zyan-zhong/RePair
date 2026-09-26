"""Research Planner reference-round budget, decision and training-data policy.

The Human reference round is a supervised demonstration for later Strong-API
and Local Research Planner implementations. PRE and POST remain separate:
the PRE plans hypotheses, portfolio and budget before current outcomes; the
POST interprets the independent verifier manifest and freezes training-data
construction without changing the PRE rationale.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

from pchsi.reference_loop.canonical import domain_hash


def _require_sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


@dataclass(frozen=True, slots=True)
class VerificationBudgetPlanV1:
    total_branch_run_budget: int
    paired_repetitions_per_state: int
    branch_arms_per_repetition: int = 2
    infrastructure_reserve_branch_runs: int = 0
    registered_state_budget: int | None = None
    budget_plan_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "total_branch_run_budget",
            "paired_repetitions_per_state",
            "branch_arms_per_repetition",
            "infrastructure_reserve_branch_runs",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be non-negative integer")
        if self.paired_repetitions_per_state <= 0:
            raise ValueError("paired repetitions must be positive")
        if self.branch_arms_per_repetition != 2:
            raise ValueError("same-state F0/F1 requires exactly two arms")
        usable = (
            self.total_branch_run_budget
            - self.infrastructure_reserve_branch_runs
        )
        if usable < 0:
            raise ValueError("infrastructure reserve exceeds total budget")
        cost_per_state = (
            self.paired_repetitions_per_state
            * self.branch_arms_per_repetition
        )
        derived = usable // cost_per_state
        if self.registered_state_budget is None:
            object.__setattr__(
                self,
                "registered_state_budget",
                derived,
            )
        elif self.registered_state_budget != derived:
            raise ValueError(
                "registered state budget differs from deterministic derivation"
            )
        if usable % cost_per_state != 0:
            raise ValueError(
                "branch budget leaves an unregistered partial state"
            )
        expected = domain_hash(
            "VERIFICATION_BUDGET_PLAN_V1",
            self._without_sha(),
        )
        if self.budget_plan_sha256 is None:
            object.__setattr__(
                self,
                "budget_plan_sha256",
                expected,
            )
        elif self.budget_plan_sha256 != expected:
            raise ValueError("budget plan SHA mismatch")

    @property
    def branch_runs_per_state(self) -> int:
        return (
            self.paired_repetitions_per_state
            * self.branch_arms_per_repetition
        )

    def _without_sha(self) -> dict[str, object]:
        return {
            "schema_id": "VERIFICATION_BUDGET_PLAN_V1",
            "schema_version": 1,
            "total_branch_run_budget": self.total_branch_run_budget,
            "paired_repetitions_per_state": (
                self.paired_repetitions_per_state
            ),
            "branch_arms_per_repetition": (
                self.branch_arms_per_repetition
            ),
            "branch_runs_per_state": self.branch_runs_per_state,
            "infrastructure_reserve_branch_runs": (
                self.infrastructure_reserve_branch_runs
            ),
            "registered_state_budget": self.registered_state_budget,
            "derivation_rule": (
                "floor((total_branch_run_budget - "
                "infrastructure_reserve_branch_runs) / "
                "(paired_repetitions_per_state * "
                "branch_arms_per_repetition))"
            ),
            "outcome_adaptive_budget_change_allowed": False,
            "unfavorable_candidate_replacement_allowed": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._without_sha(),
            "budget_plan_sha256": self.budget_plan_sha256,
        }


def current_reference_budget_plan_v1() -> VerificationBudgetPlanV1:
    return VerificationBudgetPlanV1(
        total_branch_run_budget=120,
        paired_repetitions_per_state=5,
        branch_arms_per_repetition=2,
        infrastructure_reserve_branch_runs=0,
    )


def verified_training_data_policy_v1() -> dict[str, object]:
    """Pre-register label eligibility and ratio-decision timing.

    Exact mixture proportions are not invented before F0/F1 outcomes. The
    historical 50/50 correction-success-rehearsal recipe is retained as a
    secondary fixed-budget control, not treated as a universally optimal mix.
    """

    value = {
        "schema_id": "VERIFIED_TRAINING_DATA_POLICY_V1",
        "schema_version": 1,
        "training_arms": {
            "T0": {
                "description": "untrained parent policy",
                "eligible_sources": [],
            },
            "T1": {
                "description": "ordinary successful-trajectory SFT",
                "eligible_sources": ["PI1_SUCCESS_REHEARSAL"],
            },
            "T2": {
                "description": "all unverified Analyzer repairs",
                "eligible_sources": ["UNVERIFIED_ANALYZER_REPAIR"],
            },
            "T3": {
                "description": "environment/event-valid repair",
                "eligible_sources": ["ENVIRONMENT_REPLAY_VALID_REPAIR"],
            },
            "T4": {
                "description": "same-state verified Benefit-only SFT",
                "eligible_sources": ["VERIFIED_BENEFIT"],
            },
            "T4_MIX_50_50_CONTROL": {
                "description": (
                    "50% target-loss tokens from verified Benefit "
                    "corrections and 50% from π1 successful-trajectory "
                    "rehearsal; secondary fixed-budget recipe control"
                ),
                "eligible_sources": [
                    "VERIFIED_BENEFIT",
                    "PI1_SUCCESS_REHEARSAL",
                ],
                "target_loss_token_ratio": {
                    "VERIFIED_BENEFIT": 0.5,
                    "PI1_SUCCESS_REHEARSAL": 0.5,
                },
                "claim_boundary": (
                    "historical recipe control, not assumed optimal"
                ),
            },
            "T5": {
                "description": "Benefit-Harm preference training",
                "eligible_sources": [
                    "BENEFIT_F1_OVER_F0",
                    "HARM_F0_OVER_F1",
                ],
            },
            "T6": {
                "description": "audited RL, optional and post hoc only",
                "eligible_sources": ["VERIFIED_TRAINING_ARCHIVE"],
            },
        },
        "label_eligibility": {
            "Benefit": {
                "positive_sft": True,
                "preference_chosen": True,
                "memory_writeback": "HIGH_CONFIDENCE_EXPERIENCE",
            },
            "Harm": {
                "positive_sft": False,
                "preference_rejected": True,
                "memory_writeback": "COUNTEREXAMPLE_OR_DISABLED_ROUTE",
            },
            "NeutralSuccess": {
                "primary_training": False,
                "analysis_only_by_default": True,
            },
            "NeutralFailure": {
                "primary_training": False,
                "analysis_only_by_default": True,
            },
            "Uncertain": {
                "primary_training": False,
                "training_eligible": False,
            },
            "InfrastructureInvalid": {
                "primary_training": False,
                "scientific_label": False,
            },
        },
        "mixture_ratio_rule": {
            "exact_primary_ratio_frozen_now": False,
            "freeze_stage": (
                "AFTER_F0F1_MANIFEST_AND_TRAINING_ELIGIBILITY_AUDIT_"
                "BEFORE_ANY_POLICY_TRAINING_OUTCOME"
            ),
            "outcome_inputs_allowed": [
                "verified_label_census",
                "unique_source_task_count",
                "task_family_distribution",
                "dedup_group_distribution",
                "available_target_loss_tokens",
            ],
            "outcome_inputs_forbidden": [
                "trained_policy_SELECT_result",
                "sealed_test_result",
                "strong_model_benchmark_per_task_result",
            ],
            "unique_source_state_equal_weighting": True,
            "per_episode_and_per_task_caps_required": True,
            "task_family_distribution_report_required": True,
            "single_family_domination_forbidden": True,
            "same_total_training_tokens_across_comparable_arms": True,
        },
        "training_sequence": [
            "single-seed T0-T5 pilot under shared recipe",
            "freeze arm-selection rule before SELECT outcomes",
            "retain one or two scientifically informative arms",
            "run additional seeds for the selected best arm",
            "consider T6 only after SFT/preference evidence",
        ],
        "policy_sha256": "0" * 64,
    }
    value["policy_sha256"] = domain_hash(
        "VERIFIED_TRAINING_DATA_POLICY_V1",
        value,
        excluded_field="policy_sha256",
    )
    return value


def research_planner_reference_trace_template_v1(
    *,
    round_id: str,
    parent_policy_id: str,
    evidence_cutoff_sha256: str,
    canonical_candidate_pool_sha256: str,
    budget_plan: VerificationBudgetPlanV1,
) -> dict[str, object]:
    _require_sha(evidence_cutoff_sha256, "evidence_cutoff_sha256")
    _require_sha(
        canonical_candidate_pool_sha256,
        "canonical_candidate_pool_sha256",
    )
    value = {
        "schema_id": "RESEARCH_PLANNER_REFERENCE_TRACE_V1",
        "schema_version": 1,
        "round_id": round_id,
        "parent_policy_id": parent_policy_id,
        "evidence_cutoff_sha256": evidence_cutoff_sha256,
        "canonical_candidate_pool_sha256": (
            canonical_candidate_pool_sha256
        ),
        "pre_decision": {
            "principal_bottleneck": (
                "UNVERIFIED_SOURCE_CONDITIONED_REPAIR_QUALITY"
            ),
            "reasoning_steps": [
                "separate deterministic facts from hypotheses",
                "enumerate selected/rejected/deferred bottlenecks",
                "audit historical NO-GO and counterexamples",
                "compare candidate evidence and counterevidence",
                "estimate Benefit value, Harm risk and verification cost",
                "maximize non-duplicate task-family/mechanism coverage",
                "freeze one principal change and one portfolio",
                "freeze budget, endpoint and stop rule before outcomes",
            ],
            "budget_plan_sha256": budget_plan.budget_plan_sha256,
            "selected_candidate_ids": [],
            "selected_source_state_ids": [],
            "predicted_effect_classes": {},
            "human_approval": None,
        },
        "environment_feedback": {
            "f0f1_manifest_sha256": None,
            "label_census": None,
            "benefit_per_branch_run": None,
            "environment_calls_per_benefit": None,
            "task_family_coverage": None,
            "duplicate_mechanism_rate": None,
            "unexpected_harm_cases": [],
        },
        "post_decision": {
            "hypothesis_status": None,
            "pre_rationale_editable": False,
            "training_data_policy_sha256": (
                verified_training_data_policy_v1()["policy_sha256"]
            ),
            "training_mixture_manifest_sha256": None,
            "training_recommendation": None,
            "rejected_or_deferred_lessons": [],
            "next_round_implication": None,
            "research_memory_writeback_refs": [],
        },
        "localization_supervision": {
            "preserve_raw_input": True,
            "preserve_raw_human_decision": True,
            "preserve_strong_shadow_decision": True,
            "preserve_field_level_adjudication": True,
            "preserve_actual_environment_outcomes": True,
            "preserve_cost_and_budget_compliance": True,
            "human_reference_primary": True,
        },
        "trace_sha256": "0" * 64,
    }
    value["trace_sha256"] = domain_hash(
        "RESEARCH_PLANNER_REFERENCE_TRACE_V1",
        value,
        excluded_field="trace_sha256",
    )
    return value
# Round-adaptive extension. Historical V1 helpers above remain unchanged for
# exact reproduction of the original 12-state Human reference artifact.
def validate_research_planner_verification_plan_v2(
    value: Mapping[str, object],
) -> dict[str, object]:
    payload = dict(value)
    if payload.get("schema_id") != "RESEARCH_PLANNER_VERIFICATION_PLAN_V2":
        raise ValueError("Research Planner verification-plan schema mismatch")
    if payload.get("schema_version") != 2:
        raise ValueError("Research Planner verification-plan version mismatch")
    state_ids = payload.get("selected_source_state_ids")
    candidate_ids = payload.get("selected_candidate_ids")
    seeds = payload.get("paired_seeds")
    if not isinstance(state_ids, list) or not state_ids:
        raise ValueError("selected_source_state_ids must be non-empty array")
    if not isinstance(candidate_ids, list) or len(candidate_ids) != len(state_ids):
        raise ValueError("selected_candidate_ids must align with selected states")
    if len(set(state_ids)) != len(state_ids):
        raise ValueError("selected source states must be unique")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("selected candidates must be unique")
    for name, rows in (
        ("selected_source_state_ids", state_ids),
        ("selected_candidate_ids", candidate_ids),
    ):
        for row in rows:
            _require_sha(row, name)
    if not isinstance(seeds, list) or not seeds:
        raise ValueError("paired_seeds must be non-empty array")
    if any(type(seed) is not int or seed < 0 for seed in seeds):
        raise ValueError("paired_seeds must contain non-negative integers")
    if len(set(seeds)) != len(seeds):
        raise ValueError("paired_seeds must be unique")
    n_states = len(state_ids)
    repetitions = len(seeds)
    arms = payload.get("branch_arms_per_repetition")
    if arms != 2:
        raise ValueError("same-state F0/F1 requires exactly two arms")
    expected_pairs = n_states * repetitions
    expected_branches = expected_pairs * arms
    checks = {
        "registered_state_budget": n_states,
        "paired_repetitions_per_state": repetitions,
        "paired_experiment_count": expected_pairs,
        "total_branch_run_budget": expected_branches,
    }
    for field, expected in checks.items():
        if payload.get(field) != expected:
            raise ValueError(
                f"{field} differs from Planner-selected-state derivation"
            )
    if payload.get("state_budget_authority") != (
        "RESEARCH_PLANNER_PRE_SELECTED_UNIVERSE"
    ):
        raise ValueError("state-budget authority mismatch")
    if payload.get("outcome_adaptive_budget_change_allowed") is not False:
        raise ValueError("outcome-adaptive budget change must be disabled")
    if payload.get("outcome_adaptive_reselection_allowed") is not False:
        raise ValueError("outcome-adaptive reselection must be disabled")
    if payload.get("effect_authority") != (
        "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY"
    ):
        raise ValueError("effect authority mismatch")
    expected_sha = domain_hash(
        "RESEARCH_PLANNER_VERIFICATION_PLAN_V2",
        payload,
        excluded_field="verification_plan_sha256",
    )
    if payload.get("verification_plan_sha256") != expected_sha:
        raise ValueError("Research Planner verification-plan SHA mismatch")
    return payload


def build_research_planner_verification_plan_v2(
    *,
    round_id: str,
    parent_policy_id: str,
    evidence_cutoff_sha256: str,
    resource_budget_manifest_sha256: str,
    selected_source_state_ids: tuple[str, ...] | list[str],
    selected_candidate_ids: tuple[str, ...] | list[str],
    paired_seeds: tuple[int, ...] | list[int],
    stable_direction_min_pairs: int,
) -> dict[str, object]:
    _require_sha(evidence_cutoff_sha256, "evidence_cutoff_sha256")
    _require_sha(
        resource_budget_manifest_sha256,
        "resource_budget_manifest_sha256",
    )
    states = list(selected_source_state_ids)
    candidates = list(selected_candidate_ids)
    seeds = list(paired_seeds)
    if not isinstance(round_id, str) or not round_id:
        raise ValueError("round_id required")
    if not isinstance(parent_policy_id, str) or not parent_policy_id:
        raise ValueError("parent_policy_id required")
    if type(stable_direction_min_pairs) is not int or stable_direction_min_pairs <= 0:
        raise ValueError("stable_direction_min_pairs must be positive integer")
    if stable_direction_min_pairs > len(seeds):
        raise ValueError("stability threshold exceeds paired repetitions")
    n_states = len(states)
    repetitions = len(seeds)
    arms = 2
    value = {
        "schema_id": "RESEARCH_PLANNER_VERIFICATION_PLAN_V2",
        "schema_version": 2,
        "round_id": round_id,
        "parent_policy_id": parent_policy_id,
        "evidence_cutoff_sha256": evidence_cutoff_sha256,
        "resource_budget_manifest_sha256": resource_budget_manifest_sha256,
        "selected_source_state_ids": states,
        "selected_candidate_ids": candidates,
        "registered_state_budget": n_states,
        "paired_seeds": seeds,
        "paired_repetitions_per_state": repetitions,
        "branch_arms_per_repetition": arms,
        "paired_experiment_count": n_states * repetitions,
        "total_branch_run_budget": n_states * repetitions * arms,
        "stable_direction_min_pairs": stable_direction_min_pairs,
        "state_budget_authority": (
            "RESEARCH_PLANNER_PRE_SELECTED_UNIVERSE"
        ),
        "budget_derivation_rule": (
            "len(selected_source_state_ids) * "
            "paired_repetitions_per_state * branch_arms_per_repetition"
        ),
        "outcome_adaptive_budget_change_allowed": False,
        "outcome_adaptive_reselection_allowed": False,
        "effect_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
        "verification_plan_sha256": "0" * 64,
    }
    value["verification_plan_sha256"] = domain_hash(
        "RESEARCH_PLANNER_VERIFICATION_PLAN_V2",
        value,
        excluded_field="verification_plan_sha256",
    )
    return validate_research_planner_verification_plan_v2(value)

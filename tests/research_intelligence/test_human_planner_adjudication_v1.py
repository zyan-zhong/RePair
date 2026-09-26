from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from pchsi.research_intelligence.human_planner_adjudication import (
    build_strong_researcher_blind_pre_input_v1,
    compile_human_planner_artifacts_v1,
    validate_human_planner_adjudication_v1,
)


FAMILIES = (
    "pick_and_place_simple",
    "pick_heat_then_place_in_recep",
    "look_at_obj_in_light",
    "pick_clean_then_place_in_recep",
    "pick_two_obj_and_place",
    "pick_cool_then_place_in_recep",
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _candidate(
    *,
    state_index: int,
    condition: str,
    family: str,
) -> dict[str, object]:
    candidate_sha = _sha(
        f"candidate:{state_index}:{condition}"
    )
    memory_sha = (
        None
        if condition == "A2"
        else _sha(f"memory:{state_index}")
    )
    return {
        "condition_id": condition,
        "candidate_sha256": candidate_sha,
        "source_state_sha256": _sha(
            f"state:{state_index}"
        ),
        "task_family_values": [family],
        "group_manifest_sha256": _sha(
            f"group:{state_index}"
        ),
        "local_result_sha256": _sha(
            f"local:{state_index}"
        ),
        "source_proposal_sha256": _sha(
            f"proposal:{state_index}:{condition}"
        ),
        "formal_group_result_sha256": _sha(
            f"group-result:{state_index}:{condition}"
        ),
        "formal_x_crosscheck_sha256": _sha(
            f"x:{state_index}:{condition}"
        ),
        "formal_x_disposition": "ACCEPT",
        "formal_x_supporting_evidence_count": 1,
        "formal_x_crosscheck": {
            "supporting_evidence_sha256s": [
                _sha(f"evidence:{state_index}:{condition}")
            ],
            "contradiction_evidence_sha256s": [],
            "residual_case_ids": [],
        },
        "repair_kind": "EXACT_ACTION",
        "exact_action": f"go to location {state_index}",
        "option_actions": [],
        "termination_condition": None,
        "formal_group_mechanism_hypotheses": [
            {
                "hypothesis_id": (
                    f"hypothesis-{state_index}-{condition}"
                ),
                "statement": (
                    f"mechanism {state_index}"
                ),
                "uncertainty": (
                    "environment effect unknown"
                ),
                "evidence_sha256s": [
                    _sha(
                        f"evidence:{state_index}:{condition}"
                    )
                ],
            }
        ],
        "a3_analyzer_memory_pack_sha256": memory_sha,
        "a3_analyzer_memory_summary": (
            None
            if memory_sha is None
            else {
                "pack_sha256": memory_sha,
                "applicability": "bounded",
            }
        ),
    }


def _fixture():
    dossier_sha = _sha("dossier")
    x_authority_sha = _sha("x-authority")
    canonical_sha = _sha("canonical")
    selection_sha = _sha("selection")
    cutoff_sha = _sha("cutoff")
    round_evidence_sha = _sha("round-evidence")

    pairs: dict[str, dict[str, object]] = {}
    reviews: list[dict[str, object]] = []
    selected_states = []
    selected_candidates = []

    for state_index in range(30):
        family = FAMILIES[state_index // 5]
        state_sha = _sha(f"state:{state_index}")
        a2 = _candidate(
            state_index=state_index,
            condition="A2",
            family=family,
        )
        a3 = _candidate(
            state_index=state_index,
            condition="A3",
            family=family,
        )
        pairs[state_sha] = {"A2": a2, "A3": a3}

        selected = state_index % 5 < 2
        preferred_condition = (
            "A3" if state_index == 1 else "A2"
        )
        preferred = pairs[state_sha][preferred_condition]
        alternative_condition = (
            "A2" if preferred_condition == "A3" else "A3"
        )
        alternative = pairs[state_sha][alternative_condition]

        review = {
            "state_index": state_index,
            "source_state_sha256": state_sha,
            "task_family": family,
            "group_manifest_sha256": preferred[
                "group_manifest_sha256"
            ],
            "preferred_condition": preferred_condition,
            "preferred_candidate_sha256": preferred[
                "candidate_sha256"
            ],
            "preferred_repair_kind": preferred[
                "repair_kind"
            ],
            "preferred_exact_action": preferred[
                "exact_action"
            ],
            "preferred_option_actions": [],
            "preferred_x_disposition": "ACCEPT",
            "preferred_a3_memory_pack_sha256": preferred[
                "a3_analyzer_memory_pack_sha256"
            ],
            "alternative_condition": alternative_condition,
            "alternative_candidate_sha256": alternative[
                "candidate_sha256"
            ],
            "alternative_repair_kind": alternative[
                "repair_kind"
            ],
            "alternative_exact_action": alternative[
                "exact_action"
            ],
            "alternative_option_actions": [],
            "alternative_x_disposition": "ACCEPT",
            "alternative_a3_memory_pack_sha256": alternative[
                "a3_analyzer_memory_pack_sha256"
            ],
            "same_environment_intervention": True,
            "pair_adjudication_rationale": (
                "use minimal evidence lineage"
            ),
            "alternative_disposition": (
                "DEFERRED_DUPLICATE_INTERVENTION_LINEAGE"
            ),
            "state_portfolio_disposition": (
                "SELECTED"
                if selected
                else "DEFERRED_BUDGET"
            ),
            "selected_for_verification": selected,
            "expected_value_class": (
                "HIGH" if selected else "MEDIUM"
            ),
            "expected_harm_risk_class": "LOW",
            "evidence_support_class": "HIGH",
            "portfolio_marginal_value_class": (
                "HIGH" if selected else "LOW"
            ),
            "human_evidence_summary": (
                "registered mechanism evidence"
            ),
            "human_counterevidence_summary": (
                "effect remains unknown"
            ),
            "human_selection_rationale": (
                "selected for balanced unique-group coverage"
                if selected
                else "deferred under fixed budget"
            ),
            "formal_x_supporting_evidence_sha256s": [
                _sha(
                    f"evidence:{state_index}:"
                    f"{preferred_condition}"
                )
            ],
            "formal_x_contradiction_evidence_sha256s": [],
            "formal_x_residual_case_ids": [],
            "formal_x_crosscheck_sha256": preferred[
                "formal_x_crosscheck_sha256"
            ],
            "formal_group_result_sha256": preferred[
                "formal_group_result_sha256"
            ],
            "local_result_sha256": preferred[
                "local_result_sha256"
            ],
            "source_proposal_sha256": preferred[
                "source_proposal_sha256"
            ],
            "effect_label_authority": False,
        }
        reviews.append(review)
        if selected:
            selected_states.append(state_sha)
            selected_candidates.append(
                preferred["candidate_sha256"]
            )

    dossier = {
        "schema_id": (
            "EVIDENCE_RICH_A2_A3_PAIR_DOSSIER_V2"
        ),
        "schema_version": 2,
        "status": "READY_FOR_HUMAN_SCIENTIFIC_REVIEW",
        "dossier_sha256": dossier_sha,
        "formal_x_binding_authority_sha256": (
            x_authority_sha
        ),
        "canonical_pool_sha256": canonical_sha,
        "selection_authority_sha256": selection_sha,
        "formal_x_candidate_disposition_counts": {
            "ACCEPT": 60
        },
        "a2_analyzer_memory_binding_count": 0,
        "a3_analyzer_memory_binding_count": 30,
        "unique_a3_analyzer_memory_pack_count": 30,
        "state_pairs": pairs,
    }

    round_input = {
        "schema_id": (
            "RESEARCHER_ROUND_INPUT_PACKAGE_V1"
        ),
        "round_id": "round-k",
        "parent_policy_id": "pi1",
        "input_package_sha256": cutoff_sha,
        "round_evidence_package_sha256": (
            round_evidence_sha
        ),
        "current_policy_scorecard": {
            "rollout_census_sha256": _sha("rollout"),
        },
        "analyzer_evidence": {
            "formal_result_manifest_sha256": (
                _sha("formal")
            ),
        },
        "experiment_history": {
            "historical_f0f1_summary_sha256": None,
        },
        "resource_and_cost": {
            "resource_budget_manifest_sha256": (
                _sha("budget")
            ),
        },
    }
    shared = {
        "schema_id": (
            "RESEARCH_PLANNER_SHARED_PRE_INPUT_CANDIDATE_V2"
        ),
        "schema_version": 2,
        "status": "READY_FOR_HUMAN_SCIENTIFIC_REVIEW",
        "round_input_package": round_input,
        "researcher_memory_view": {
            "schema_id": "RESEARCHER_MEMORY_VIEW_V1",
            "view_sha256": _sha("memory-view"),
            "snapshot_sha256": _sha("snapshot"),
            "purpose": "ROUND_RESEARCH_PLANNING",
            "train_side_records": [],
            "heldout_aggregate_metrics": {},
        },
        "verification_budget_plan": {
            "registered_state_budget": 12,
            "paired_repetitions_per_state": 5,
            "branch_arms_per_repetition": 2,
            "total_branch_run_budget": 120,
            "outcome_adaptive_budget_change_allowed": False,
            "unfavorable_candidate_replacement_allowed": False,
        },
    }

    adjudication = {
        "schema_id": (
            "HUMAN_PLANNER_SCIENTIFIC_ADJUDICATION_V1"
        ),
        "schema_version": 1,
        "source_review_bundle_sha256": _sha("bundle"),
        "evidence_rich_dossier_sha256": dossier_sha,
        "formal_x_binding_authority_sha256": (
            x_authority_sha
        ),
        "canonical_pool_sha256": canonical_sha,
        "selection_authority_sha256": selection_sha,
        "round_id": "round-k",
        "parent_policy_id": "pi1",
        "evidence_cutoff_sha256": cutoff_sha,
        "round_evidence_package_sha256": (
            round_evidence_sha
        ),
        "principal_bottleneck_id": "B3",
        "principal_bottleneck_statement": (
            "repair effects remain unverified"
        ),
        "single_falsifiable_hypothesis": (
            "at least one stable Benefit and Benefits exceed Harms"
        ),
        "single_principal_change_id": "PC1",
        "single_principal_change": (
            "verify one bounded 12-state repair portfolio"
        ),
        "observed_facts": ["candidate coverage is complete"],
        "uncertainties": ["environment effects are unknown"],
        "candidate_bottlenecks": [
            {
                "candidate_id": "B1",
                "status": "DEFERRED",
                "observed_facts": ["broad policy weakness"],
                "uncertainties": ["not one intervention"],
                "disposition_reason": "defer",
            },
            {
                "candidate_id": "B2",
                "status": "REJECTED",
                "observed_facts": ["direct Memory not required"],
                "uncertainties": ["history still supports analysis"],
                "disposition_reason": "reject",
            },
            {
                "candidate_id": "B3",
                "status": "SELECTED",
                "observed_facts": ["effects unknown"],
                "uncertainties": ["labels unknown"],
                "disposition_reason": "select",
            },
            {
                "candidate_id": "B4",
                "status": "DEFERRED",
                "observed_facts": ["training not ready"],
                "uncertainties": ["mixture unknown"],
                "disposition_reason": "defer",
            },
        ],
        "selection_policy": {
            "registered_state_budget": 12,
            "paired_repetitions_per_state": 5,
            "branch_arms_per_repetition": 2,
            "total_branch_run_budget": 120,
            "select_exactly_two_states_per_task_family": True,
            "selected_groups_must_be_unique": True,
            "selected_repairs_must_be_exact_action": True,
            "selected_x_disposition_must_be_accept": True,
            "no_outcome_adaptive_replacement": True,
            "no_condition_balance_quota": True,
            "a3_history_is_support_not_effect_authority": True,
            "success_trajectory_optimization_active": False,
        },
        "ordinal_score_encoding": {
            "not_calibrated_probability": True,
            "expected_value": {
                "LOW": 0.25,
                "MEDIUM": 0.50,
                "HIGH": 0.75,
            },
            "expected_harm_risk": {
                "LOW": 0.20,
                "MEDIUM": 0.40,
                "HIGH": 0.70,
            },
            "evidence_support": {
                "LOW": 0.40,
                "MEDIUM": 0.65,
                "HIGH": 0.85,
            },
        },
        "state_reviews": reviews,
        "selected_source_state_sha256s": (
            selected_states
        ),
        "selected_candidate_sha256s": (
            selected_candidates
        ),
        "selected_condition_counts": {
            "A2": 11,
            "A3": 1,
        },
        "selected_task_family_counts": {
            family: 2 for family in FAMILIES
        },
        "selected_unique_group_count": 12,
        "support_criterion": (
            "at least one Benefit and Benefits exceed Harms"
        ),
        "refutation_criterion": (
            "zero Benefits or Harms at least Benefits"
        ),
        "stop_condition": (
            "complete all registered repetitions"
        ),
        "primary_endpoint": (
            "stable Benefit yield over 12 registered states"
        ),
        "secondary_diagnostics": [
            "Harm and Neutral counts",
            "cost per Benefit",
        ],
        "training_policy_at_pre": {
            "status": (
                "HOLD_PENDING_VERIFIED_F0F1_MANIFEST"
            ),
            "exact_training_mixture_frozen": False,
        },
        "human_approval": {
            "status": (
                "ASSISTANT_PREPARED_REQUIRES_USER_APPROVAL"
            ),
            "reviewer": None,
            "approval_timestamp": None,
            "approval_note": None,
        },
        "automatic_environment_effect_assignment": False,
        "human_pre_frozen": False,
        "strong_researcher_shadow_executed": False,
        "success_trajectory_optimization_active": False,
    }
    return adjudication, dossier, shared


def test_compiles_12_state_family_balanced_portfolio() -> None:
    adjudication, dossier, shared = _fixture()
    artifacts = compile_human_planner_artifacts_v1(
        adjudication=adjudication,
        dossier=dossier,
        shared_input=shared,
    )
    portfolio = artifacts["repair_portfolio"]
    selected = [
        row
        for row in portfolio["candidates"]
        if row["disposition"] == "SELECTED"
    ]
    assert len(selected) == 12
    assert len(
        {
            row["lineage"]["source_state_ids"][0]
            for row in selected
        }
    ) == 12
    assert portfolio["programs"][0][
        "estimated_verification_calls"
    ] == 12
    assert artifacts["build_report"][
        "selected_task_family_counts"
    ] == {family: 2 for family in FAMILIES}


def test_strong_blind_input_contains_all_pairs_and_no_human_decision(
) -> None:
    _, dossier, shared = _fixture()
    blind = build_strong_researcher_blind_pre_input_v1(
        dossier=dossier,
        shared_input=shared,
    )
    assert len(
        blind["registered_candidate_universe"]["pair_table"]
    ) == 30
    serialized = str(blind).lower()
    assert "human_planner_scientific_adjudication" not in serialized
    assert blind["visibility_boundary"][
        "human_selection_visible"
    ] is False
    assert blind["visibility_boundary"][
        "human_rationale_visible"
    ] is False
    assert blind["visibility_boundary"][
        "human_pre_visible"
    ] is False
    assert blind["visibility_boundary"][
        "current_f0f1_outcomes_visible"
    ] is False
    forbidden_keys = {
        "state_reviews",
        "selected_source_state_sha256s",
        "selected_candidate_sha256s",
        "human_selection_rationale",
        "human_expected_value",
        "human_harm_risk",
        "human_approval",
    }
    def walk_keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from walk_keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk_keys(child)
    assert not forbidden_keys.intersection(walk_keys(blind))


def test_rejects_selected_x_scope_downgrade() -> None:
    adjudication, dossier, shared = _fixture()
    first = adjudication["state_reviews"][0]
    first["preferred_x_disposition"] = "DOWNGRADE_SCOPE"
    preferred = dossier["state_pairs"][
        first["source_state_sha256"]
    ][first["preferred_condition"]]
    preferred["formal_x_disposition"] = "DOWNGRADE_SCOPE"
    with pytest.raises(ValueError, match="Formal X ACCEPT"):
        validate_human_planner_adjudication_v1(
            adjudication=adjudication,
            dossier=dossier,
            shared_input=shared,
        )


def test_rejects_duplicate_selected_group() -> None:
    adjudication, dossier, shared = _fixture()
    selected = [
        row
        for row in adjudication["state_reviews"]
        if row["selected_for_verification"]
    ]
    selected[1]["group_manifest_sha256"] = selected[0][
        "group_manifest_sha256"
    ]
    state = selected[1]["source_state_sha256"]
    condition = selected[1]["preferred_condition"]
    dossier["state_pairs"][state][condition][
        "group_manifest_sha256"
    ] = selected[0]["group_manifest_sha256"]
    with pytest.raises(ValueError, match="12 unique groups"):
        validate_human_planner_adjudication_v1(
            adjudication=adjudication,
            dossier=dossier,
            shared_input=shared,
        )


def test_rejects_task_family_imbalance() -> None:
    adjudication, dossier, shared = _fixture()
    selected = [
        row
        for row in adjudication["state_reviews"]
        if row["selected_for_verification"]
    ]
    selected[0]["task_family"] = FAMILIES[1]
    state = selected[0]["source_state_sha256"]
    condition = selected[0]["preferred_condition"]
    dossier["state_pairs"][state][condition][
        "task_family_values"
    ] = [FAMILIES[1]]
    adjudication["selected_task_family_counts"] = {
        family: 2 for family in FAMILIES
    }
    adjudication["selected_task_family_counts"][
        FAMILIES[0]
    ] = 1
    adjudication["selected_task_family_counts"][
        FAMILIES[1]
    ] = 3
    with pytest.raises(ValueError, match="two states per family"):
        validate_human_planner_adjudication_v1(
            adjudication=adjudication,
            dossier=dossier,
            shared_input=shared,
        )


def test_rejects_forbidden_future_outcomes() -> None:
    adjudication, dossier, shared = _fixture()
    shared["current_f0f1_outcomes"] = {"x": "Benefit"}
    with pytest.raises(ValueError, match="forbidden keys"):
        validate_human_planner_adjudication_v1(
            adjudication=adjudication,
            dossier=dossier,
            shared_input=shared,
        )


def test_exact_training_mixture_remains_unfrozen() -> None:
    adjudication, dossier, shared = _fixture()
    artifacts = compile_human_planner_artifacts_v1(
        adjudication=adjudication,
        dossier=dossier,
        shared_input=shared,
    )
    assert adjudication["training_policy_at_pre"][
        "exact_training_mixture_frozen"
    ] is False
    assert artifacts["reference_trace"]["pre_decision"][
        "exact_training_mixture_frozen"
    ] is False
    assert artifacts["build_report"][
        "success_trajectory_optimization_active"
    ] is False
def _retarget_fixture_to_dynamic_budget(adjudication, shared, selected_count):
    selected_rows = []
    for index, row in enumerate(adjudication["state_reviews"]):
        selected = index < selected_count
        row["selected_for_verification"] = selected
        row["state_portfolio_disposition"] = (
            "SELECTED" if selected else "DEFERRED_BUDGET"
        )
        row["human_selection_rationale"] = (
            "selected by Planner under current evidence and budget"
            if selected
            else "deferred by Planner under current evidence and budget"
        )
        if selected:
            selected_rows.append(row)

    repetitions = 5
    arms = 2
    total = selected_count * repetitions * arms
    shared["verification_budget_plan"].update({
        "registered_state_budget": selected_count,
        "paired_repetitions_per_state": repetitions,
        "branch_arms_per_repetition": arms,
        "total_branch_run_budget": total,
    })
    policy = adjudication["selection_policy"]
    policy.update({
        "registered_state_budget": selected_count,
        "paired_repetitions_per_state": repetitions,
        "branch_arms_per_repetition": arms,
        "total_branch_run_budget": total,
        "select_exactly_two_states_per_task_family": False,
        "state_budget_authority": (
            "RESEARCH_PLANNER_PRE_SELECTED_UNIVERSE"
        ),
    })
    adjudication["selected_source_state_sha256s"] = [
        row["source_state_sha256"] for row in selected_rows
    ]
    adjudication["selected_candidate_sha256s"] = [
        row["preferred_candidate_sha256"] for row in selected_rows
    ]
    adjudication["selected_condition_counts"] = dict(
        __import__("collections").Counter(
            row["preferred_condition"] for row in selected_rows
        )
    )
    adjudication["selected_task_family_counts"] = dict(
        __import__("collections").Counter(
            row["task_family"] for row in selected_rows
        )
    )
    adjudication["selected_unique_group_count"] = selected_count
    return selected_rows


@pytest.mark.parametrize("selected_count", [7, 13, 20])
def test_planner_selected_budget_drives_portfolio_pre_and_blind_contract(
    selected_count,
) -> None:
    adjudication, dossier, shared = _fixture()
    selected = _retarget_fixture_to_dynamic_budget(
        adjudication,
        shared,
        selected_count,
    )
    artifacts = compile_human_planner_artifacts_v1(
        adjudication=adjudication,
        dossier=dossier,
        shared_input=shared,
    )
    portfolio = artifacts["repair_portfolio"]
    assert portfolio["verification_call_budget"] == selected_count
    assert portfolio["programs"][0]["estimated_verification_calls"] == selected_count
    assert len(portfolio["programs"][0]["source_state_ids"]) == selected_count
    assert artifacts["human_pre_input"]["verification_budget"] == selected_count
    assert artifacts["human_pre_input"]["environment_budget"] == selected_count * 5 * 2
    contract = artifacts["strong_blind_input"]["required_output_contract"]
    assert contract["selected_state_budget"] == selected_count
    assert contract["branch_run_budget"] == selected_count * 5 * 2
    assert artifacts["build_report"]["selected_state_count"] == selected_count
    assert len(selected) == selected_count


def test_planner_budget_and_selected_state_count_mismatch_fails_closed() -> None:
    adjudication, dossier, shared = _fixture()
    _retarget_fixture_to_dynamic_budget(adjudication, shared, 13)
    shared["verification_budget_plan"]["registered_state_budget"] = 12
    shared["verification_budget_plan"]["total_branch_run_budget"] = 120
    with pytest.raises(ValueError, match="Planner-selected state budget"):
        validate_human_planner_adjudication_v1(
            adjudication=adjudication,
            dossier=dossier,
            shared_input=shared,
        )

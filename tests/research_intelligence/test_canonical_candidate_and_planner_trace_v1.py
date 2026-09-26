from __future__ import annotations

import hashlib
import json

import pytest

from pchsi.research_intelligence.canonical_candidate_pool import (
    build_canonical_candidate_pool_v1,
)
from pchsi.research_intelligence.research_planner_reference_trace import (
    VerificationBudgetPlanV1,
    current_reference_budget_plan_v1,
    research_planner_reference_trace_template_v1,
    verified_training_data_policy_v1,
)


def _sha(prefix: str, index: int) -> str:
    return hashlib.sha256(
        f"{prefix}:{index}".encode()
    ).hexdigest()


def _proposal(index: int) -> dict[str, object]:
    return {
        "schema_id": "ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1",
        "schema_version": 1,
        "group_manifest_sha256": _sha("group", index),
        "local_result_sha256": _sha("local", index),
        "error_instance_id": f"error-{index}",
        "source_state_sha256": _sha("state", index // 2),
        "menu_sha256": _sha("menu", index // 2),
        "exact_action": f"take object {index}",
        "option_actions": [],
        "termination_condition": None,
        "supporting_evidence_sha256s": [_sha("evidence", index)],
        "source_proposal_sha256": _sha("proposal", index),
    }


def _group(index: int) -> dict[str, object]:
    return {
        "schema_id": "ANALYZER_GROUP_MANIFEST_V1",
        "schema_version": 1,
        "group_id": f"group-{index}",
        "task_family": f"family-{index % 6}",
        "group_manifest_sha256": _sha("group", index),
    }


def _candidate(
    *,
    index: int,
    source_state_index: int,
    status: str = "EXECUTABLE_EXACT_ACTION",
) -> dict[str, object]:
    exact_action = (
        f"take object {index}"
        if status == "EXECUTABLE_EXACT_ACTION"
        else None
    )
    return {
        "schema_id": "ANALYZER_REPAIR_CANDIDATE_V1",
        "schema_version": 1,
        "candidate_kind": "FAILURE_REPAIR",
        "source_state_sha256": _sha("state", source_state_index),
        "menu_sha256": _sha("menu", source_state_index),
        "source_proposal_sha256": _sha("proposal", index),
        "candidate_status": status,
        "exact_action": exact_action,
        "option_actions": [],
        "termination_condition": None,
        "requires_environment_verification": True,
        "candidate_sha256": _sha("candidate", index),
        "live_menu_revalidation_required": True,
        "all_intervention_actions_count_against_environment_budget": True,
    }


def _pool() -> dict[str, object]:
    rows = []
    proposals = []
    groups = []
    crosschecks = []

    index = 0
    for state in range(30):
        for condition in (
            "A2_HIERARCHICAL_NO_HISTORY",
            "A3_HIERARCHICAL_WITH_HISTORY",
        ):
            candidate = _candidate(
                index=index,
                source_state_index=state,
            )
            proposal = _proposal(index)
            group = _group(index)
            rows.append(
                {
                    "condition_id": condition,
                    "unit_id": f"unit-{state}-{condition}",
                    "selected_candidate": candidate,
                    "candidate_sha256": candidate["candidate_sha256"],
                    "source_state_sha256": candidate[
                        "source_state_sha256"
                    ],
                }
            )
            proposals.append(proposal)
            groups.append(group)
            crosschecks.append(
                {
                    "schema_id": "ANALYZER_CROSSCHECK_RESULT_V1",
                    "schema_version": 1,
                    "target_artifact_sha256": proposal[
                        "source_proposal_sha256"
                    ],
                    "disposition": "ACCEPT",
                    "supporting_evidence_sha256s": [
                        _sha("cross-support", index)
                    ],
                    "contradiction_evidence_sha256s": [],
                    "residual_case_ids": [],
                    "current_evidence_sha256s": [],
                    "historical_evidence_sha256s": [],
                    "crosscheck_sha256": _sha("crosscheck", index),
                }
            )
            index += 1

    # Fourteen extra non-executable candidate objects reproduce the kind of
    # recursive overcount seen in the old candidate-like scanner.
    extra = []
    for offset in range(14):
        condition = (
            "A2_HIERARCHICAL_NO_HISTORY"
            if offset % 2 == 0
            else "A3_HIERARCHICAL_WITH_HISTORY"
        )
        extra_index = 1000 + offset
        candidate = _candidate(
            index=extra_index,
            source_state_index=offset % 7,
            status="ABSTAIN",
        )
        extra.append(
            {
                "condition_id": condition,
                "candidate": candidate,
                "summary": {
                    "candidate_id": candidate["candidate_sha256"],
                    "repair": "non-executable summary wrapper",
                },
            }
        )

    return {
        "schema_id": "FORMAL_ANALYZER_CANDIDATE_POOL_V1",
        "schema_version": 1,
        "state_condition_outcomes": rows,
        "proposals": proposals,
        "group_manifests": groups,
        "crosschecks": crosschecks,
        "extra_nonselected": extra,
        "summary": {
            "candidate_like_wrappers": [
                {
                    "condition": (
                        "A2" if i % 2 == 0 else "A3"
                    ),
                    "candidate_id": f"wrapper-{i}",
                    "repair": "summary only",
                }
                for i in range(74)
            ],
        },
    }


def test_canonical_extractor_ignores_wrappers_and_nonselected() -> None:
    pool = _pool()
    file_sha = hashlib.sha256(
        (
            json.dumps(pool, sort_keys=True)
            + "\n"
        ).encode()
    ).hexdigest()
    canonical = build_canonical_candidate_pool_v1(
        pool=pool,
        pool_file_sha256=file_sha,
    )
    assert len(canonical.selected_candidates) == 60
    assert len(canonical.nonselected_candidates) == 14
    assert len(canonical.state_pairs()) == 30
    assert {
        row.condition_id
        for row in canonical.selected_candidates
    } == {"A2", "A3"}
    assert canonical.schema_object_census[
        "ANALYZER_REPAIR_CANDIDATE_V1"
    ] == 74


def test_each_state_has_exact_a2_a3_pair() -> None:
    pool = _pool()
    canonical = build_canonical_candidate_pool_v1(
        pool=pool,
        pool_file_sha256="a" * 64,
    )
    for pair in canonical.state_pairs().values():
        assert set(pair) == {"A2", "A3"}


def test_budget_plan_derives_12_states_from_120_branches() -> None:
    budget = current_reference_budget_plan_v1()
    assert budget.registered_state_budget == 12
    assert budget.branch_runs_per_state == 10
    assert budget.total_branch_run_budget == 120


def test_budget_plan_rejects_partial_unregistered_state() -> None:
    with pytest.raises(ValueError, match="partial state"):
        VerificationBudgetPlanV1(
            total_branch_run_budget=121,
            paired_repetitions_per_state=5,
        )


def test_training_policy_does_not_invent_primary_ratio() -> None:
    policy = verified_training_data_policy_v1()
    assert (
        policy["mixture_ratio_rule"][
            "exact_primary_ratio_frozen_now"
        ]
        is False
    )
    assert policy["training_arms"][
        "T4_MIX_50_50_CONTROL"
    ]["target_loss_token_ratio"] == {
        "VERIFIED_BENEFIT": 0.5,
        "PI1_SUCCESS_REHEARSAL": 0.5,
    }
    assert policy["label_eligibility"]["Uncertain"][
        "training_eligible"
    ] is False
    assert policy["label_eligibility"]["Harm"][
        "positive_sft"
    ] is False


def test_reference_trace_separates_pre_and_post() -> None:
    budget = current_reference_budget_plan_v1()
    trace = research_planner_reference_trace_template_v1(
        round_id="round-k",
        parent_policy_id="pi-k",
        evidence_cutoff_sha256="b" * 64,
        canonical_candidate_pool_sha256="c" * 64,
        budget_plan=budget,
    )
    assert trace["pre_decision"]["selected_candidate_ids"] == []
    assert trace["environment_feedback"][
        "f0f1_manifest_sha256"
    ] is None
    assert trace["post_decision"]["pre_rationale_editable"] is False
    assert trace["localization_supervision"][
        "preserve_actual_environment_outcomes"
    ] is True



def test_executable_but_unselected_objects_do_not_change_registered_60() -> None:
    pool = _pool()

    # Reproduce the real failure mode: 14 additional repair objects are
    # executable, but they are not referenced by the final 60-row
    # state_condition_outcomes selection ledger.
    for wrapper in pool["extra_nonselected"]:
        candidate = wrapper["candidate"]
        candidate["candidate_status"] = "EXECUTABLE_EXACT_ACTION"
        candidate["exact_action"] = "inventory"
        candidate["option_actions"] = []

    file_sha = hashlib.sha256(
        (
            json.dumps(pool, sort_keys=True)
            + "\n"
        ).encode()
    ).hexdigest()

    canonical = build_canonical_candidate_pool_v1(
        pool=pool,
        pool_file_sha256=file_sha,
    )

    assert len(canonical.selected_candidates) == 60
    assert len(canonical.state_pairs()) == 30
    assert {
        row.condition_id
        for row in canonical.selected_candidates
    } == {"A2", "A3"}

    executable_audit = [
        row
        for row in canonical.nonselected_candidates
        if row.executable
    ]
    assert len(executable_audit) >= 14

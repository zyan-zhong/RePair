#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pchsi.research_intelligence.canonical_candidate_pool import (
    build_canonical_candidate_pool_v1,
)
from pchsi.research_intelligence.research_planner_reference_trace import (
    current_reference_budget_plan_v1,
    research_planner_reference_trace_template_v1,
    verified_training_data_policy_v1,
)
from pchsi.research_intelligence.round_research_inputs import (
    researcher_round_input_package_from_dict,
)
from pchsi.reference_loop.canonical import write_new_json


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--candidate-pool", required=True)
    p.add_argument("--round-input-package", required=True)
    p.add_argument("--result-manifest", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()

    candidate_path = Path(a.candidate_pool).resolve()
    input_path = Path(a.round_input_package).resolve()
    result_path = Path(a.result_manifest).resolve()
    out = Path(a.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)

    pool = build_canonical_candidate_pool_v1(
        pool=load(candidate_path),
        pool_file_sha256=sha(candidate_path),
    )
    round_input = researcher_round_input_package_from_dict(
        load(input_path)
    )
    result_manifest = load(result_path)

    expected = result_manifest["candidate_projection"]
    if expected["source_states"] != 30:
        raise SystemExit("STOP=RESULT_MANIFEST_SOURCE_STATE_COUNT")
    selected = expected["selected_candidates"]
    if selected != {"A2": 30, "A3": 30}:
        raise SystemExit("STOP=RESULT_MANIFEST_SELECTED_COUNTS")

    budget = current_reference_budget_plan_v1()
    training_policy = verified_training_data_policy_v1()
    trace = research_planner_reference_trace_template_v1(
        round_id=round_input.round_id,
        parent_policy_id=round_input.parent_policy_id,
        evidence_cutoff_sha256=round_input.input_package_sha256,
        canonical_candidate_pool_sha256=pool.canonical_pool_sha256,
        budget_plan=budget,
    )

    write_new_json(
        out / "CANONICAL_FORMAL_CANDIDATE_POOL_V1.json",
        pool.to_dict(),
    )
    write_new_json(
        out / "A2_A3_SOURCE_STATE_PAIR_TABLE_V1.json",
        {
            "schema_id": "A2_A3_SOURCE_STATE_PAIR_TABLE_V1",
            "schema_version": 1,
            "canonical_candidate_pool_sha256": (
                pool.canonical_pool_sha256
            ),
            "state_count": 30,
            "pairs": pool.state_pairs(),
        },
    )
    write_new_json(
        out / "VERIFICATION_BUDGET_PLAN_V1.json",
        budget.to_dict(),
    )
    write_new_json(
        out / "VERIFIED_TRAINING_DATA_POLICY_V1.json",
        training_policy,
    )
    write_new_json(
        out / "RESEARCH_PLANNER_REFERENCE_TRACE_V1_TEMPLATE.json",
        trace,
    )

    worksheet_rows = []
    for state, pair in pool.state_pairs().items():
        worksheet_rows.append(
            {
                "source_state_sha256": state,
                "A2": pair["A2"],
                "A3": pair["A3"],
                "human_selected_condition": None,
                "selection_status": "REQUIRES_HUMAN_REVIEW",
                "evidence_strength": None,
                "counterevidence_risk": None,
                "expected_value": None,
                "expected_harm_risk": None,
                "verification_cost": 10,
                "task_family_coverage_value": None,
                "mechanism_duplication_group": None,
                "historical_no_go_overlap": None,
                "selection_rationale": None,
            }
        )

    write_new_json(
        out / "HUMAN_REPAIR_PORTFOLIO_REVIEW_WORKSHEET_V2.json",
        {
            "schema_id": (
                "HUMAN_REPAIR_PORTFOLIO_REVIEW_WORKSHEET_V2"
            ),
            "schema_version": 2,
            "round_id": round_input.round_id,
            "parent_policy_id": round_input.parent_policy_id,
            "evidence_cutoff_sha256": (
                round_input.input_package_sha256
            ),
            "canonical_candidate_pool_sha256": (
                pool.canonical_pool_sha256
            ),
            "budget_plan_sha256": budget.budget_plan_sha256,
            "registered_state_budget": budget.registered_state_budget,
            "selection_rule": {
                "select_exactly_12_unique_source_states": True,
                "select_exactly_one_condition_per_selected_state": True,
                "do_not_use_current_f0f1_outcomes": True,
                "prioritize_evidence_grounding": True,
                "prioritize_counterevidence_awareness": True,
                "prioritize_task_family_and_mechanism_coverage": True,
                "penalize_duplicate_mechanisms": True,
                "penalize_historical_no_go_overlap": True,
                "record_expected_value_harm_and_cost": True,
                "tie_break": (
                    "higher evidence completeness, lower duplication, "
                    "broader coverage, then lexical candidate SHA"
                ),
            },
            "state_pair_rows": worksheet_rows,
            "selected_candidate_sha256s": [],
            "selected_source_state_sha256s": [],
            "selected_count": 0,
            "human_approval": None,
        },
    )

    summary = {
        "schema_id": "CANONICAL_POOL_AND_PLANNER_SCAFFOLD_REPORT_V1",
        "selected_candidate_count": len(pool.selected_candidates),
        "nonselected_candidate_count": len(pool.nonselected_candidates),
        "source_state_count": len(pool.state_pairs()),
        "condition_counts": {"A2": 30, "A3": 30},
        "canonical_candidate_pool_sha256": pool.canonical_pool_sha256,
        "budget_plan_sha256": budget.budget_plan_sha256,
        "registered_state_budget": budget.registered_state_budget,
        "branch_runs_per_state": budget.branch_runs_per_state,
        "total_branch_run_budget": budget.total_branch_run_budget,
        "training_ratio_frozen_now": False,
        "training_ratio_freeze_stage": training_policy[
            "mixture_ratio_rule"
        ]["freeze_stage"],
        "human_pre_frozen": False,
        "f0f1_executed": False,
        "training_executed": False,
        "benchmark_results_visible": False,
        "next_gate": (
            "HUMAN_REVIEW_CANONICAL_60_AND_SELECT_12"
        ),
    }
    write_new_json(
        out / "CANONICAL_POOL_AND_PLANNER_SCAFFOLD_REPORT_V1.json",
        summary,
    )

    print("CANONICAL_SELECTED_CANDIDATE_COUNT=60")
    print("CANONICAL_SOURCE_STATE_COUNT=30")
    print("CANONICAL_CONDITION_COUNTS={'A2': 30, 'A3': 30}")
    print(
        "CANONICAL_CANDIDATE_POOL_SHA256="
        + str(pool.canonical_pool_sha256)
    )
    print(
        "VERIFICATION_REGISTERED_STATE_BUDGET="
        + str(budget.registered_state_budget)
    )
    print(
        "VERIFICATION_TOTAL_BRANCH_RUN_BUDGET="
        + str(budget.total_branch_run_budget)
    )
    print("TRAINING_RATIO_FROZEN_NOW=false")
    print("NEXT_GATE=HUMAN_REVIEW_CANONICAL_60_AND_SELECT_12")


if __name__ == "__main__":
    main()

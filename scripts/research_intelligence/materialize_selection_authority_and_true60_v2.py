#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pchsi.research_intelligence.canonical_candidate_pool_v2 import (
    build_canonical_selected_pool_v2,
)
from pchsi.research_intelligence.research_planner_reference_trace import (
    current_reference_budget_plan_v1,
    research_planner_reference_trace_template_v1,
    verified_training_data_policy_v1,
)
from pchsi.research_intelligence.round_research_inputs import (
    researcher_round_input_package_from_dict,
)
from pchsi.research_intelligence.selected_candidate_authority import (
    discover_selected_candidate_authority_v1,
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

    pool_path = Path(a.candidate_pool).resolve()
    input_path = Path(a.round_input_package).resolve()
    result_path = Path(a.result_manifest).resolve()
    out = Path(a.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)

    pool_raw = load(pool_path)
    round_input = researcher_round_input_package_from_dict(
        load(input_path)
    )
    result = load(result_path)

    projection = result["candidate_projection"]
    selected_counts = projection.get(
        "selected_candidate_counts",
        projection.get("selected_candidates"),
    )
    if not isinstance(selected_counts, dict):
        raise SystemExit("STOP=RESULT_MANIFEST_SELECTED_COUNTS_MISSING")
    expected_counts = {
        "A2": int(selected_counts["A2"]),
        "A3": int(selected_counts["A3"]),
    }
    expected_total = int(
        projection.get(
            "state_condition_outcome_count",
            sum(expected_counts.values()),
        )
    )
    expected_states = int(
        projection.get(
            "source_state_count",
            projection.get("source_states"),
        )
    )

    authority, diagnostics = discover_selected_candidate_authority_v1(
        pool=pool_raw,
        expected_total=expected_total,
        expected_condition_counts=expected_counts,
        expected_source_state_count=expected_states,
    )

    canonical = build_canonical_selected_pool_v2(
        pool=pool_raw,
        pool_file_sha256=sha(pool_path),
        authority=authority,
    )

    if canonical["selected_candidate_count"] != expected_total:
        raise SystemExit("STOP=CANONICAL_SELECTED_COUNT")
    if canonical["selected_source_state_count"] != expected_states:
        raise SystemExit("STOP=CANONICAL_SOURCE_STATE_COUNT")

    budget = current_reference_budget_plan_v1()
    training_policy = verified_training_data_policy_v1()
    trace = research_planner_reference_trace_template_v1(
        round_id=round_input.round_id,
        parent_policy_id=round_input.parent_policy_id,
        evidence_cutoff_sha256=round_input.input_package_sha256,
        canonical_candidate_pool_sha256=canonical[
            "canonical_pool_sha256"
        ],
        budget_plan=budget,
    )

    write_new_json(
        out / "SELECTED_CANDIDATE_AUTHORITY_V1.json",
        authority.to_dict(),
    )
    write_new_json(
        out / "SELECTED_CANDIDATE_AUTHORITY_DISCOVERY_DIAGNOSTICS_V1.json",
        diagnostics,
    )
    write_new_json(
        out / "CANONICAL_FORMAL_CANDIDATE_POOL_V2.json",
        canonical,
    )
    write_new_json(
        out / "A2_A3_SOURCE_STATE_PAIR_TABLE_V2.json",
        {
            "schema_id": "A2_A3_SOURCE_STATE_PAIR_TABLE_V2",
            "schema_version": 2,
            "selection_authority_sha256": (
                authority.selection_authority_sha256
            ),
            "canonical_pool_sha256": canonical[
                "canonical_pool_sha256"
            ],
            "state_count": canonical["selected_source_state_count"],
            "pairs": canonical["state_pairs"],
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

    rows = []
    for state, pair in canonical["state_pairs"].items():
        rows.append(
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
                "verification_cost_branch_runs": (
                    budget.branch_runs_per_state
                ),
                "task_family_coverage_value": None,
                "mechanism_duplication_group": None,
                "historical_no_go_overlap": None,
                "selection_rationale": None,
            }
        )

    write_new_json(
        out / "HUMAN_REPAIR_PORTFOLIO_REVIEW_WORKSHEET_V3.json",
        {
            "schema_id": "HUMAN_REPAIR_PORTFOLIO_REVIEW_WORKSHEET_V3",
            "schema_version": 3,
            "round_id": round_input.round_id,
            "parent_policy_id": round_input.parent_policy_id,
            "evidence_cutoff_sha256": (
                round_input.input_package_sha256
            ),
            "selection_authority_sha256": (
                authority.selection_authority_sha256
            ),
            "canonical_candidate_pool_sha256": canonical[
                "canonical_pool_sha256"
            ],
            "registered_state_budget": budget.registered_state_budget,
            "paired_repetitions_per_state": (
                budget.paired_repetitions_per_state
            ),
            "branch_runs_per_state": budget.branch_runs_per_state,
            "total_branch_run_budget": budget.total_branch_run_budget,
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
            "state_pair_rows": rows,
            "selected_candidate_sha256s": [],
            "selected_source_state_sha256s": [],
            "selected_count": 0,
            "human_approval": None,
        },
    )

    audit = {
        "schema_id": "SELECTED60_EXTRA_CANDIDATE_AUDIT_V2",
        "selected_candidate_count": canonical[
            "selected_candidate_count"
        ],
        "selected_source_state_count": canonical[
            "selected_source_state_count"
        ],
        "extra_candidate_count": canonical["extra_candidate_count"],
        "extra_executable_candidate_count": canonical[
            "extra_executable_candidate_count"
        ],
        "extra_candidate_audit": canonical["extra_candidate_audit"],
        "registered_denominator_source": (
            "SELECTED_CANDIDATE_AUTHORITY_V1"
        ),
        "benefit_harm_visible": False,
        "environment_execution_performed": False,
    }
    write_new_json(
        out / "SELECTED60_EXTRA_CANDIDATE_AUDIT_V2.json",
        audit,
    )

    print(
        "SELECTION_AUTHORITY_SHA256="
        + str(authority.selection_authority_sha256)
    )
    print(
        "SELECTION_AUTHORITY_CONTAINER_COUNT="
        + str(len(authority.structural_container_paths))
    )
    print("CANONICAL_SELECTED_CANDIDATE_COUNT=60")
    print("CANONICAL_SOURCE_STATE_COUNT=30")
    print("CANONICAL_CONDITION_COUNTS={'A2': 30, 'A3': 30}")
    print(
        "EXTRA_CANDIDATE_COUNT="
        + str(canonical["extra_candidate_count"])
    )
    print(
        "EXTRA_EXECUTABLE_BUT_UNSELECTED_COUNT="
        + str(canonical["extra_executable_candidate_count"])
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
    print("NEXT_GATE=HUMAN_REVIEW_TRUE_60_AND_SELECT_12")


if __name__ == "__main__":
    main()

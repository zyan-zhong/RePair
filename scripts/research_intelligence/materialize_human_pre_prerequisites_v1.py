#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pchsi.research_intelligence.product_isolation import (
    assert_separate_roots,
)
from pchsi.research_intelligence.round_research_inputs import (
    build_human_evidence_binding_candidate_v1,
    build_researcher_round_input_package_v1,
)


def load(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            f"regular JSON file required: {path}"
        )
    value = json.loads(
        path.read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise ValueError(
            f"JSON object required: {path}"
        )
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def write(
    path: Path,
    value: object,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    if path.exists():
        raise FileExistsError(path)
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--memory-review",
        required=True,
    )
    p.add_argument(
        "--output-dir",
        required=True,
    )
    p.add_argument(
        "--parent-policy-id",
        required=True,
    )
    p.add_argument(
        "--human-scientific-root",
        required=True,
    )
    p.add_argument(
        "--benchmark-scientific-root",
        required=True,
    )
    a = p.parse_args()

    assert_separate_roots(
        Path(a.human_scientific_root),
        Path(a.benchmark_scientific_root),
    )

    review = load(
        Path(a.memory_review).resolve()
    )
    if review.get("status") != (
        "MECHANICALLY_VALID_"
        "EXISTING_ROUND_LEVEL_VIEW"
    ):
        raise SystemExit(
            "STOP=ROUND_LEVEL_MEMORY_REVIEW_NOT_READY"
        )

    round_path = Path(
        str(
            review[
                "round_evidence_bound_path"
            ]
        )
    ).resolve()
    memory_path = Path(
        str(
            review["memory_bound_path"]
        )
    ).resolve()

    round_evidence = load(round_path)
    memory = load(memory_path)

    package = (
        build_researcher_round_input_package_v1(
            round_evidence=round_evidence,
            round_evidence_file_sha256=sha(
                round_path
            ),
            researcher_memory=memory,
            researcher_memory_file_sha256=sha(
                memory_path
            ),
            parent_policy_id=(
                a.parent_policy_id
            ),
        )
    )
    package_dict = package.to_dict()
    evidence_binding = (
        build_human_evidence_binding_candidate_v1(
            package
        )
    )

    out = Path(a.output_dir).resolve()
    out.mkdir(
        parents=True,
        exist_ok=False,
    )

    bound_round = (
        out
        / "BOUND_ROUND_EVIDENCE_PACKAGE_V1.json"
    )
    bound_memory = (
        out
        / "BOUND_RESEARCHER_MEMORY_VIEW_V1.json"
    )
    bound_round.write_bytes(
        round_path.read_bytes()
    )
    bound_memory.write_bytes(
        memory_path.read_bytes()
    )

    write(
        out
        / "RESEARCHER_ROUND_INPUT_PACKAGE_V1.json",
        package_dict,
    )
    write(
        out
        / (
            "HUMAN_REFERENCE_"
            "EVIDENCE_BINDING_V1_CANDIDATE.json"
        ),
        evidence_binding,
    )

    worksheet = {
        "schema_id": (
            "HUMAN_RESEARCHER_PRE_"
            "WORKSHEET_V5_NONAUTHORITATIVE"
        ),
        "schema_version": 1,
        "not_freezable": True,
        "round_id": package.round_id,
        "policy_version": (
            package.parent_policy_id
        ),
        "evidence_cutoff": (
            package.input_package_sha256
        ),
        "round_evidence_package_sha256": (
            package.round_evidence_package_sha256
        ),
        "researcher_memory_view_sha256": (
            package.researcher_memory_view_sha256
        ),
        "mechanically_bound_inputs": {
            "current_policy_scorecard": (
                package.current_policy_scorecard
            ),
            "analyzer_evidence": (
                package.analyzer_evidence
            ),
            "historical_failure_experience": (
                package
                .historical_failure_experience
            ),
            "experiment_history": (
                package.experiment_history
            ),
            "resource_and_cost": (
                package.resource_and_cost
            ),
        },
        "human_decision_fields": {
            "observed_facts": [],
            "uncertainties": [],
            "candidate_bottlenecks": [],
            "selected_bottleneck_id": None,
            "selection_rationale": None,
            (
                "single_falsifiable_"
                "hypothesis"
            ): None,
            "single_principal_change": None,
            "baseline": None,
            "intervention": None,
            "fixed_variables": [],
            "sample_definition": None,
            "verification_budget": None,
            "model_logical_call_budget": None,
            "environment_budget": None,
            "gpu_budget_hours": None,
            "primary_endpoint": None,
            "secondary_diagnostics": [],
            "support_criterion": None,
            "refutation_criterion": None,
            "stop_condition": None,
        },
        "required_historical_evidence_checks": {
            (
                "pi0_to_pi1_"
                "long_horizon_no_go"
            ): (
                "BOUND_REFERENCE_PRESENT"
                if package.experiment_history[
                    (
                        "historical_go_nogo_"
                        "ledger_sha256"
                    )
                ]
                is not None
                else "MISSING_REFERENCE"
            ),
            (
                "failure_memory_q1_q3_"
                "negative_result"
            ): (
                "REQUIRES_HUMAN_CONTENT_AUDIT"
            ),
            (
                "three_direct_memory_"
                "exposure_cases"
            ): (
                "REQUIRES_HUMAN_CONTENT_AUDIT"
            ),
            "post_hoc_trajectory_dynamics": (
                "REQUIRES_HUMAN_CONTENT_AUDIT"
            ),
            (
                "cost_and_infrastructure_"
                "incidents"
            ): (
                "BOUND_RESOURCE_LEDGER_REFERENCE_PRESENT"
                if package.resource_and_cost[
                    (
                        "resource_budget_"
                        "manifest_sha256"
                    )
                ]
                is not None
                else "MISSING_REFERENCE"
            ),
        },
        "benchmark_artifact_count": 0,
        "benchmark_results_visible": False,
        (
            "current_round_future_"
            "outcomes_visible"
        ): False,
    }
    write(
        out
        / "HUMAN_RESEARCHER_PRE_WORKSHEET_V5.json",
        worksheet,
    )

    md = f"""# Human Researcher PRE — Prerequisite Review V5

This is not a frozen PRE decision.

## Exact common inputs

- round: `{package.round_id}`
- parent policy: `{package.parent_policy_id}`
- evidence cutoff / input package: `{package.input_package_sha256}`
- Round Evidence: `{package.round_evidence_package_sha256}`
- Researcher Memory view: `{package.researcher_memory_view_sha256}`
- Memory snapshot: `{package.historical_failure_experience['snapshot_sha256']}`
- train-side historical records: `{package.historical_failure_experience['train_side_record_count']}`

## Five automatically assembled lanes

1. Current policy scorecard:
   policy lineage, checkpoint/config, task-set, rollout census,
   mechanical failure census.
2. Analyzer evidence:
   Formal Analyzer result manifest and metric report.
3. Historical Failure Experience:
   the existing governed round-planning Researcher Memory view.
4. Experiment history:
   prior F0/F1, GO/NO-GO, prior Researcher decisions,
   training history, code/config changes.
5. Resource and cost:
   frozen resource budget manifest reference.

Human, Strong-API shadow and later Local shadow must consume these
same exact Round Evidence and Researcher Memory identities. Human PRE
content and its hash remain invisible to the shadow.

## Human decisions still required

- candidate bottleneck analysis;
- selected / rejected / deferred directions;
- one falsifiable hypothesis;
- one principal scientific change;
- exact verification/API/environment/GPU budgets;
- support/refutation/stop rules;
- training plan, which may remain HOLD before verified Benefits.

The Environment Verifier remains the only Benefit/Harm authority.
The Promotion Gate remains independent.
"""
    (
        out
        / (
            "HUMAN_RESEARCHER_PRE_"
            "PREREQUISITE_REVIEW_V5.md"
        )
    ).write_text(
        md,
        encoding="utf-8",
    )

    readiness = {
        "schema_id": (
            "HUMAN_PRE_PREREQUISITE_REPORT_V1"
        ),
        "status": (
            "READY_FOR_"
            "HUMAN_PRE_CONTENT_COMPLETION"
        ),
        "round_id": package.round_id,
        "parent_policy_id": (
            package.parent_policy_id
        ),
        "input_package_sha256": (
            package.input_package_sha256
        ),
        (
            "evidence_binding_"
            "candidate_sha256"
        ): (
            evidence_binding[
                "evidence_binding_sha256"
            ]
        ),
        "round_evidence_ready": True,
        (
            "round_level_"
            "researcher_memory_ready"
        ): True,
        "five_lane_dataflow_ready": True,
        (
            "same_input_for_"
            "human_strong_local"
        ): True,
        "human_pre_frozen": False,
        (
            "strong_researcher_"
            "shadow_executed"
        ): False,
        "f0f1_executed": False,
        "training_executed": False,
        "benchmark_results_visible": False,
        "next_gate": (
            "HUMAN_PRE_PREREQUISITE_"
            "CODE_AND_CONTENT_REVIEW"
        ),
    }
    write(
        out
        / "HUMAN_PRE_PREREQUISITE_REPORT_V1.json",
        readiness,
    )

    print(
        "RESEARCHER_ROUND_INPUT_PACKAGE_SHA256="
        + str(package.input_package_sha256)
    )
    print(
        "HUMAN_EVIDENCE_BINDING_CANDIDATE_SHA256="
        + str(
            evidence_binding[
                "evidence_binding_sha256"
            ]
        )
    )
    print(
        "HUMAN_PRE_PREREQUISITE_STATUS="
        "READY_FOR_HUMAN_PRE_CONTENT_COMPLETION"
    )
    print(
        "NEXT_GATE="
        "HUMAN_PRE_PREREQUISITE_"
        "CODE_AND_CONTENT_REVIEW"
    )


if __name__ == "__main__":
    main()

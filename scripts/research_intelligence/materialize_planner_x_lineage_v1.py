#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import json
import os
from typing import Any, Mapping

from pchsi.research_intelligence.formal_x_lineage import (
    bind_selected_candidates_to_formal_x_v1,
    build_formal_x_indexes_v1,
    canonical_json_bytes,
    load_json_object,
    sha256_bytes,
    sha256_file,
)
from pchsi.reference_loop.canonical import domain_hash


def write_new_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    data = canonical_json_bytes(value)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def compact_base_candidate(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "condition_id": row.get("condition_id"),
        "candidate_sha256": row.get("candidate_sha256"),
        "source_state_sha256": row.get("source_state_sha256"),
        "menu_sha256": row.get("menu_sha256"),
        "source_proposal_sha256": row.get("source_proposal_sha256"),
        "repair_kind": row.get("repair_kind"),
        "exact_action": row.get("exact_action"),
        "option_actions": row.get("option_actions", []),
        "termination_condition": row.get("termination_condition"),
        "task_family_values": row.get("task_family_values", []),
        "mechanism_values": row.get("mechanism_values", []),
        "diagnosis_values": row.get("diagnosis_values", []),
        "hypothesis_values": row.get("hypothesis_values", []),
        "evidence_sha256s": row.get("evidence_sha256s", []),
        "group_manifest_sha256": row.get("group_manifest_sha256"),
        "local_result_sha256": row.get("local_result_sha256"),
    }


def unique_json_rows(values: object, *, limit: int = 30) -> list[object]:
    if not isinstance(values, list):
        return []
    seen: set[str] = set()
    out: list[object] = []
    for value in values:
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if serialized in seen:
            continue
        seen.add(serialized)
        out.append(value)
        if len(out) >= limit:
            break
    return out


def candidate_review_row(
    *,
    base: Mapping[str, object],
    binding: Mapping[str, object],
) -> dict[str, object]:
    crosscheck = binding["crosscheck"]
    if not isinstance(crosscheck, dict):
        raise ValueError("crosscheck binding must be object")
    return {
        **compact_base_candidate(base),
        "formal_g_custom_id": binding["g_custom_id"],
        "formal_x_custom_id": binding["x_custom_id"],
        "formal_group_result_sha256": binding["group_result_sha256"],
        "formal_group_mechanism_hypotheses": unique_json_rows(
            binding.get("group_mechanism_hypotheses"), limit=12
        ),
        "formal_source_conditioned_proposals": unique_json_rows(
            binding.get("source_conditioned_proposals"), limit=8
        ),
        "formal_x_crosscheck": crosscheck,
        "formal_x_disposition": crosscheck["disposition"],
        "formal_x_supporting_evidence_count": len(
            crosscheck["supporting_evidence_sha256s"]
        ),
        "formal_x_contradiction_evidence_count": len(
            crosscheck["contradiction_evidence_sha256s"]
        ),
        "formal_x_residual_case_count": len(crosscheck["residual_case_ids"]),
        "formal_x_current_evidence_count": len(
            crosscheck["current_evidence_sha256s"]
        ),
        "formal_x_historical_evidence_count": len(
            crosscheck["historical_evidence_sha256s"]
        ),
        "formal_x_crosscheck_sha256": binding["crosscheck_sha256"],
        "a3_analyzer_memory_pack_sha256": binding[
            "a3_analyzer_memory_pack_sha256"
        ],
        "a3_analyzer_memory_summary": binding[
            "a3_analyzer_memory_summary"
        ],
        "human_expected_value": None,
        "human_harm_risk": None,
        "human_verification_priority": None,
        "human_historical_no_go_overlap": None,
        "human_evidence_summary": None,
        "human_counterevidence_summary": None,
        "human_selected": False,
        "human_selection_rationale": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-pool", required=True)
    parser.add_argument("--selection-authority", required=True)
    parser.add_argument("--base-dossier", required=True)
    parser.add_argument("--formal-state-root", required=True)
    parser.add_argument("--formal-archive-root", required=True)
    parser.add_argument("--round-input", required=True)
    parser.add_argument("--researcher-memory", required=True)
    parser.add_argument("--budget-plan", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    canonical_path = Path(args.canonical_pool).resolve()
    authority_path = Path(args.selection_authority).resolve()
    base_dossier_path = Path(args.base_dossier).resolve()
    formal_state_root = Path(args.formal_state_root).resolve()
    formal_archive_root = Path(args.formal_archive_root).resolve()
    round_input_path = Path(args.round_input).resolve()
    researcher_memory_path = Path(args.researcher_memory).resolve()
    budget_path = Path(args.budget_plan).resolve()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)

    canonical = load_json_object(canonical_path)
    selection_authority = load_json_object(authority_path)
    base_dossier = load_json_object(base_dossier_path)
    round_input = load_json_object(round_input_path)
    researcher_memory = load_json_object(researcher_memory_path)
    budget = load_json_object(budget_path)

    selected = canonical.get("selected_candidates")
    if not isinstance(selected, list) or len(selected) != 60:
        raise SystemExit("STOP=CANONICAL_SELECTED_CANDIDATE_COUNT_NOT_60")
    if selection_authority.get("expected_total") != 60:
        raise SystemExit("STOP=SELECTION_AUTHORITY_TOTAL_NOT_60")
    if int(budget.get("registered_state_budget", -1)) != 12:
        raise SystemExit("STOP=REGISTERED_STATE_BUDGET_NOT_12")

    indexes = build_formal_x_indexes_v1(formal_state_root)
    binding_result = bind_selected_candidates_to_formal_x_v1(
        selected_candidates=selected,
        indexes=indexes,
        allowed_artifact_roots=[formal_state_root, formal_archive_root],
    )
    binding_authority = binding_result["authority"]
    bound_artifacts = binding_result["bound_artifacts"]

    binding_map = {
        (
            row["condition_id"],
            row["candidate_sha256"],
            row["source_state_sha256"],
        ): row
        for row in binding_authority["candidate_bindings"]
    }

    base_pairs = base_dossier.get("state_pairs")
    if not isinstance(base_pairs, dict) or len(base_pairs) != 30:
        raise SystemExit("STOP=BASE_DOSSIER_STATE_PAIRS_NOT_30")

    enriched_pairs: dict[str, dict[str, dict[str, object]]] = {}
    for state_sha, pair in sorted(base_pairs.items()):
        if not isinstance(pair, dict) or set(pair) != {"A2", "A3"}:
            raise SystemExit("STOP=BASE_DOSSIER_PAIR_INCOMPLETE")
        enriched: dict[str, dict[str, object]] = {}
        for condition in ("A2", "A3"):
            base = pair[condition]
            if not isinstance(base, dict):
                raise SystemExit("STOP=BASE_DOSSIER_CANDIDATE_NOT_OBJECT")
            key = (
                condition,
                base.get("candidate_sha256"),
                base.get("source_state_sha256"),
            )
            binding = binding_map.get(key)
            if binding is None:
                raise SystemExit("STOP=MISSING_CANDIDATE_X_BINDING:" + repr(key))
            enriched[condition] = candidate_review_row(
                base=base,
                binding=binding,
            )
        enriched_pairs[state_sha] = enriched

    dispositions = Counter(
        candidate[condition]["formal_x_disposition"]
        for candidate in enriched_pairs.values()
        for condition in ("A2", "A3")
    )

    dossier = {
        "schema_id": "EVIDENCE_RICH_A2_A3_PAIR_DOSSIER_V2",
        "schema_version": 2,
        "status": "READY_FOR_HUMAN_SCIENTIFIC_REVIEW",
        "selection_authority_sha256": selection_authority.get(
            "selection_authority_sha256"
        ),
        "canonical_pool_sha256": canonical.get("canonical_pool_sha256"),
        "formal_x_binding_authority_sha256": binding_authority[
            "authority_sha256"
        ],
        "candidate_count": 60,
        "source_state_count": 30,
        "condition_counts": {"A2": 30, "A3": 30},
        "candidate_x_binding_count": 60,
        "unique_x_scientific_unit_count": binding_authority[
            "unique_x_scientific_unit_count"
        ],
        "candidate_x_disposition_counts": dict(sorted(dispositions.items())),
        "a2_analyzer_memory_binding_count": 0,
        "a3_analyzer_memory_binding_count": 30,
        "unique_a3_analyzer_memory_pack_count": binding_authority[
            "unique_a3_analyzer_memory_pack_count"
        ],
        "state_pairs": enriched_pairs,
        "automatic_scientific_selection_performed": False,
        "current_f0f1_outcomes_visible": False,
        "strong_model_benchmark_per_task_results_visible": False,
        "success_trajectory_optimization_active": False,
        "human_pre_freeze_allowed": False,
        "next_gate": "HUMAN_SCIENTIFIC_REVIEW_OF_30_ENRICHED_PAIRS",
        "dossier_sha256": "0" * 64,
    }
    dossier["dossier_sha256"] = domain_hash(
        "EVIDENCE_RICH_A2_A3_PAIR_DOSSIER_V2",
        dossier,
        excluded_field="dossier_sha256",
    )

    review = {
        "schema_id": "HUMAN_PLANNER_30_PAIR_REVIEW_TEMPLATE_V2",
        "schema_version": 2,
        "dossier_sha256": dossier["dossier_sha256"],
        "registered_state_budget": 12,
        "review_policy": {
            "review_all_30_pairs": True,
            "select_exactly_12_unique_source_states": True,
            "select_exactly_one_A2_or_A3_candidate_per_selected_state": True,
            "formal_x_reject_or_abstain_cannot_be_selected": True,
            "formal_x_downgrade_requires_human_scope_rationale": True,
            "A3_history_is_support_not_effect_authority": True,
            "do_not_use_current_f0f1_outcomes": True,
            "do_not_use_strong_benchmark_per_task_results": True,
            "success_trajectory_optimization_active": False,
        },
        "state_reviews": [
            {
                "source_state_sha256": state_sha,
                "A2_candidate_sha256": pair["A2"]["candidate_sha256"],
                "A2_x_disposition": pair["A2"]["formal_x_disposition"],
                "A3_candidate_sha256": pair["A3"]["candidate_sha256"],
                "A3_x_disposition": pair["A3"]["formal_x_disposition"],
                "A3_memory_pack_sha256": pair["A3"][
                    "a3_analyzer_memory_pack_sha256"
                ],
                "human_selected_condition": None,
                "human_selected_candidate_sha256": None,
                "human_expected_value": None,
                "human_harm_risk": None,
                "human_verification_priority": None,
                "human_historical_no_go_overlap": None,
                "human_evidence_summary": None,
                "human_counterevidence_summary": None,
                "human_selection_rationale": None,
                "human_disposition": "REQUIRES_REVIEW",
            }
            for state_sha, pair in sorted(enriched_pairs.items())
        ],
        "selected_source_state_sha256s": [],
        "selected_candidate_sha256s": [],
        "selected_count": 0,
        "human_approval": None,
    }

    shared_pre = {
        "schema_id": "RESEARCH_PLANNER_SHARED_PRE_INPUT_CANDIDATE_V2",
        "schema_version": 2,
        "status": "READY_FOR_HUMAN_REFERENCE_REVIEW_NOT_FROZEN",
        "round_input_package": round_input,
        "round_level_researcher_memory_view": researcher_memory,
        "selection_authority": selection_authority,
        "formal_x_binding_authority": binding_authority,
        "verification_budget_plan": budget,
        "evidence_rich_pair_dossier": dossier,
        "consumer_roles": [
            "HUMAN_REFERENCE",
            "STRONG_API_RESEARCHER_SHADOW",
            "LOCAL_RESEARCH_PLANNER_SHADOW",
            "LOCAL_RESEARCH_PLANNER_PRIMARY",
        ],
        "role_separation": {
            "round_level_researcher_memory": (
                "historical experiments, NO-GO, costs and round decisions"
            ),
            "A3_group_analyzer_memory": (
                "the exact frozen historical Failure Experience supplied to A3"
            ),
            "environment_effect_authority": "NOT_PRESENT_PRE_OUTCOME",
        },
        "human_pre_visible_to_shadow": False,
        "human_pre_hash_visible_to_shadow": False,
        "current_f0f1_outcomes_visible": False,
        "benchmark_per_task_results_visible": False,
        "automatic_scientific_selection_performed": False,
    }

    report = {
        "schema_id": "HUMAN_PLANNER_X_LINEAGE_BUILD_REPORT_V1",
        "status": "READY_FOR_HUMAN_SCIENTIFIC_REVIEW",
        "formal_state_scan_file_count": indexes.scan_file_count,
        "formal_state_scan_object_count": indexes.scan_object_count,
        "selected_candidate_count": 60,
        "source_state_count": 30,
        "candidate_x_binding_count": 60,
        "unique_x_scientific_unit_count": binding_authority[
            "unique_x_scientific_unit_count"
        ],
        "x_candidate_multiplicity_distribution": binding_authority[
            "x_candidate_multiplicity_distribution"
        ],
        "candidate_x_disposition_counts": binding_authority[
            "candidate_disposition_counts"
        ],
        "a2_memory_binding_count": 0,
        "a3_memory_binding_count": 30,
        "unique_a3_analyzer_memory_pack_count": binding_authority[
            "unique_a3_analyzer_memory_pack_count"
        ],
        "bound_artifact_count": len(bound_artifacts),
        "human_pre_freeze_allowed": False,
        "strong_shadow_execution_allowed": False,
        "f0f1_execution_allowed": False,
        "success_trajectory_optimization_active": False,
        "next_gate": "UPLOAD_X_LINEAGE_REVIEW_BUNDLE_FOR_HUMAN_SCIENTIFIC_REVIEW",
    }

    write_new_json(
        output / "FORMAL_X_CROSSCHECK_BINDING_AUTHORITY_V1.json",
        binding_authority,
    )
    write_new_json(
        output / "EVIDENCE_RICH_A2_A3_PAIR_DOSSIER_V2.json",
        dossier,
    )
    write_new_json(
        output / "HUMAN_PLANNER_30_PAIR_REVIEW_TEMPLATE_V2.json",
        review,
    )
    write_new_json(
        output / "RESEARCH_PLANNER_SHARED_PRE_INPUT_CANDIDATE_V2.json",
        shared_pre,
    )
    write_new_json(
        output / "HUMAN_PLANNER_X_LINEAGE_BUILD_REPORT_V1.json",
        report,
    )

    bound_root = output / "bound_artifacts"
    for artifact_sha, artifact in sorted(bound_artifacts.items()):
        write_new_json(bound_root / (artifact_sha + ".json"), artifact)

    lines = [
        "# Human Planner X-Lineage Review V1",
        "",
        "## Fixed facts",
        "",
        "- 60 selected candidate-level X bindings are complete.",
        f"- Unique group-condition X scientific units: {binding_authority['unique_x_scientific_unit_count']}.",
        f"- Candidate-level X dispositions: {dict(sorted(dispositions.items()))}.",
        "- A2 Analyzer Memory exposure: 0/30.",
        "- A3 exact frozen Analyzer Memory binding: 30/30.",
        "- Current F0/F1 outcomes are absent.",
        "- Human PRE is not frozen.",
        "- Success-trajectory optimization remains OFF.",
        "",
        "## Scientific boundary",
        "",
        "Formal X is group-condition-level. One X result may legitimately bind multiple source-conditioned candidates. The Human Researcher must review all 30 A2/A3 pairs and select exactly 12 unique states; no automatic scientific selection is performed here.",
    ]
    (output / "HUMAN_PLANNER_X_LINEAGE_REVIEW_V1.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print("FORMAL_X_CANDIDATE_BINDING_COUNT=60")
    print(
        "FORMAL_X_UNIQUE_SCIENTIFIC_UNIT_COUNT="
        + str(binding_authority["unique_x_scientific_unit_count"])
    )
    print(
        "FORMAL_X_CANDIDATE_DISPOSITION_COUNTS="
        + repr(binding_authority["candidate_disposition_counts"])
    )
    print("A2_ANALYZER_MEMORY_BINDING_COUNT=0")
    print("A3_ANALYZER_MEMORY_BINDING_COUNT=30")
    print(
        "UNIQUE_A3_ANALYZER_MEMORY_PACK_COUNT="
        + str(binding_authority["unique_a3_analyzer_memory_pack_count"])
    )
    print("EVIDENCE_RICH_PAIR_DOSSIER_V2_STATUS=READY_FOR_HUMAN_SCIENTIFIC_REVIEW")
    print("HUMAN_PRE_FREEZE_ALLOWED=false")
    print("SUCCESS_TRAJECTORY_OPTIMIZATION_ACTIVE=false")
    print("PLANNER_X_LINEAGE_MATERIALIZATION_PASS")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pchsi.cognitive_runtime.orchestrator import execute_one
from pchsi.reference_loop.canonical import domain_hash
from pchsi.research_intelligence.human_reference_round import (
    validate_evidence_binding,
)
from pchsi.research_intelligence.strong_researcher_evidence_hydration import (
    validate_hydrated_blind_input_v2,
)


STAGE_ID = "R-PRE-SHADOW-HYDRATED-V2"


def load(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"regular JSON file required: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--human-pre-freeze-receipt", required=True)
    parser.add_argument("--evidence-binding", required=True)
    parser.add_argument("--hydration-manifest", required=True)
    parser.add_argument("--blind-input-v2", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    receipt = load(Path(args.human_pre_freeze_receipt).resolve())
    binding = load(Path(args.evidence_binding).resolve())
    hydration = load(Path(args.hydration_manifest).resolve())
    blind = load(Path(args.blind_input_v2).resolve())

    validate_evidence_binding(binding)
    validate_hydrated_blind_input_v2(
        blind_input_v2=blind,
        hydration_manifest=hydration,
    )

    if hydration.get("hydration_ready") is not True:
        raise SystemExit("STOP=HYDRATION_NOT_READY")
    if hydration.get("resolved_required_slot_count") != 9:
        raise SystemExit("STOP=HYDRATION_NOT_NINE_OF_NINE")
    if hydration.get("unresolved_required_slot_ids") != []:
        raise SystemExit("STOP=HYDRATION_UNRESOLVED_NOT_EMPTY")

    if receipt.get("schema_id") != (
        "HUMAN_RESEARCHER_PRE_FREEZE_RECEIPT_V1"
    ):
        raise SystemExit("STOP=HUMAN_PRE_FREEZE_RECEIPT_SCHEMA")
    if receipt.get(
        "human_pre_content_hidden_from_strong_pre_shadow"
    ) is not True:
        raise SystemExit("STOP=HUMAN_PRE_NOT_HIDDEN")
    if receipt.get("evidence_binding_sha256") != binding[
        "evidence_binding_sha256"
    ]:
        raise SystemExit("STOP=EVIDENCE_BINDING_RECEIPT_MISMATCH")

    checks = {
        "round_id": binding["round_id"],
        "parent_policy_id": binding["parent_policy_id"],
        "evidence_cutoff_sha256": binding[
            "evidence_cutoff_sha256"
        ],
        "round_evidence_package_sha256": binding[
            "round_evidence_package_sha256"
        ],
    }
    for field, expected in checks.items():
        if blind.get(field) != expected:
            raise SystemExit(
                "STOP=BLIND_V2_BINDING_MISMATCH:" + field
            )

    visibility = blind.get("visibility_boundary")
    if not isinstance(visibility, dict):
        raise SystemExit("STOP=BLIND_VISIBILITY_BOUNDARY")
    for field in (
        "human_pre_visible",
        "human_pre_hash_visible",
        "human_selection_visible",
        "human_rationale_visible",
        "current_f0f1_outcomes_visible",
        "future_policy_evaluation_visible",
        "strong_model_benchmark_per_task_results_visible",
        "success_trajectory_optimization_active",
    ):
        if visibility.get(field) is not False:
            raise SystemExit(
                "STOP=BLIND_VISIBILITY_NOT_FALSE:" + field
            )

    forbidden_keys = {
        "human_adjudication_sha256",
        "human_pre_input_candidate_sha256",
        "selected_candidate_sha256s",
        "selected_source_state_sha256s",
        "selection_rationale",
        "principal_bottleneck_id",
        "principal_change_id",
    }
    observed_keys = set(_walk_keys(blind))
    leaked = sorted(forbidden_keys & observed_keys)
    if leaked:
        raise SystemExit(
            "STOP=HUMAN_DECISION_KEYS_LEAKED:" + repr(leaked)
        )

    serialized = json.dumps(
        blind,
        ensure_ascii=False,
        sort_keys=True,
    )
    human_pre_sha = receipt["human_pre_record_sha256"]
    if human_pre_sha in serialized:
        raise SystemExit("STOP=HUMAN_PRE_HASH_LEAKED")
    for forbidden in (
        "HUMAN_PLANNER_SCIENTIFIC_ADJUDICATION",
        "HUMAN_RESEARCHER_PRE_V1",
        "ASSISTANT_PREPARED_REQUIRES_USER_APPROVAL",
    ):
        if forbidden.lower() in serialized.lower():
            raise SystemExit(
                "STOP=HUMAN_DECISION_MARKER_LEAKED:" + forbidden
            )

    unit = {
        "round_id": blind["round_id"],
        "role": "TRAINING_RESEARCHER",
        "stage_id": STAGE_ID,
        "blind_input_sha256": blind["blind_input_sha256"],
        "evidence_hydration_manifest_sha256": hydration[
            "hydration_manifest_sha256"
        ],
    }
    unit["identity_sha256"] = domain_hash(
        "RESEARCHER_PRE_SHADOW_UNIT_V6",
        unit,
    )

    access = {
        "task_id": blind["round_id"],
        "gamefile_sha256": blind[
            "round_evidence_package_sha256"
        ],
        "access_class": "TRAIN_REFERENCE_ROUND",
        "dataset_split": "TRAIN_RESEARCH_INTELLIGENCE",
        "training_permitted": True,
        "select_evaluation_permitted": False,
        "confirmatory_permitted": False,
        "teacher_call_permitted": True,
    }

    projection = {
        "schema_id": "STRONG_RESEARCHER_BLIND_PRE_PROJECTION_V2",
        "blind_input_sha256": blind["blind_input_sha256"],
        "evidence_hydration_manifest_sha256": hydration[
            "hydration_manifest_sha256"
        ],
        "blind_input": blind,
        "human_pre_gate_satisfied": True,
        "human_pre_content_visible": False,
        "human_pre_hash_visible": False,
    }

    result = execute_one(
        output_root=Path(args.output_root),
        unit_identity=unit,
        stage_id=STAGE_ID,
        condition_id=None,
        round_id=str(blind["round_id"]),
        policy_version=str(blind["parent_policy_id"]),
        projection=projection,
        task_access=access,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

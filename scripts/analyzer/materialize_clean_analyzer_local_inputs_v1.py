#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from pchsi.cognitive_runtime.identity import build_scientific_unit_identity
from pchsi.cognitive_runtime.projections import local_projection
from pchsi.cognitive_runtime.schema_registry import validate_artifact
from pchsi.reference_loop.bundle_reader import validate_attempt_bundle
from pchsi.reference_loop.canonical import (
    domain_hash,
    sha256_file,
    strict_json_loads,
    write_new_json,
)
from pchsi.reference_loop.clean_analyzer_evidence import (
    build_clean_analyzer_evidence_pack,
    build_clean_current_trajectory_binding,
    build_pi0_i1_analyzer_policy_identity,
)
from pchsi.reference_loop.mechanical import extract_mechanical_episode_evidence
from pchsi.round_control.clean_analyzer_input_materialization import (
    build_actor_input_binding,
    build_clean_analyzer_task_access_record,
    build_local_u_reg_manifest,
    select_failure_only_u_reg,
    validate_round_analyzer_resource_budget,
)


def _object(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"regular input file required: {path}")
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _jsonl(path: Path) -> list[dict[str, object]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"regular JSONL input required: {path}")
    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise ValueError(f"newline-terminated nonempty JSONL required: {path}")
    rows: list[dict[str, object]] = []
    for index, line in enumerate(raw.splitlines(), 1):
        value = strict_json_loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"JSONL row {index} must be object")
        rows.append(value)
    return rows


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


_STAGE3F_SELECTION_FIELDS = frozenset(
    {
        "selection_score",
        "selection_rank",
        "family_cycle_index",
        "within_family_rank",
        "source_evidence_index_row_sha256",
        "gamefile_sha256",
        "source_unit_id",
    }
)


def _frozen_source_evidence_row(selected_row: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in selected_row.items()
        if key not in _STAGE3F_SELECTION_FIELDS
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage2c-root", required=True)
    parser.add_argument("--stage3c-root", required=True)
    parser.add_argument("--budget-authority", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    stage2c = Path(args.stage2c_root).resolve()
    stage3c = Path(args.stage3c_root).resolve()
    output = Path(args.output_root).resolve()
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=CLEAN_ANALYZER_INPUT_OUTPUT_ALREADY_EXISTS")
    output.mkdir(parents=True, exist_ok=False)

    budget = _object(Path(args.budget_authority).resolve())
    validate_round_analyzer_resource_budget(budget)
    cutoff = _object(stage3c / "PI0_I1_TRAIN_UPDATE_EVIDENCE_CUTOFF_V1.json")
    readiness = _object(stage3c / "PI0_I1_ANALYZER_INPUT_READINESS_V1.json")
    pi0 = _object(stage2c / "stage2c/PI0_CLEAN_MODEL_ARTIFACT_V1.json")
    runtime = _object(stage2c / "stage2c/PI0_CLEAN_RUNTIME_BINDING_V1.json")

    if cutoff.get("round_id") != budget.get("round_id"):
        raise SystemExit("STOP=ROUND_BUDGET_CUTOFF_MISMATCH")
    if cutoff.get("evidence_cutoff_frozen") is not True:
        raise SystemExit("STOP=EVIDENCE_CUTOFF_NOT_FROZEN")
    if cutoff.get("benchmark_results_visible") is not False:
        raise SystemExit("STOP=BENCHMARK_RESULTS_VISIBLE")
    if readiness.get("clean_inputs_pass") is not True:
        raise SystemExit("STOP=CLEAN_ANALYZER_INPUT_READINESS_NOT_PASS")

    train_root = Path(str(cutoff["source_campaign_root"])).resolve()
    if train_root.is_symlink() or not train_root.is_dir():
        raise SystemExit("STOP=TRAIN_CAMPAIGN_ROOT_INVALID")
    failure_path = stage3c / "PI0_I1_TRAIN_UPDATE_FAILURE_UNIVERSE_V1.jsonl"
    failure_rows = _jsonl(failure_path)
    selected = select_failure_only_u_reg(
        failure_rows=failure_rows,
        resource_budget=budget,
        source_campaign_sha256=str(cutoff["source_campaign_sha256"]),
    )

    validated: list[tuple[dict[str, object], object, dict[str, object]]] = []
    seen_gamefiles: set[str] = set()
    for row in selected:
        attempt_root = (train_root / str(row["attempt_bundle_relpath"])).resolve()
        bundle = validate_attempt_bundle(attempt_root)
        if bundle.task_id != row["task_id"]:
            raise SystemExit("STOP=SELECTED_TASK_ID_BUNDLE_MISMATCH")
        if bundle.attempt_bundle_sha256 != row["attempt_bundle_sha256"]:
            raise SystemExit("STOP=SELECTED_ATTEMPT_BUNDLE_SHA_MISMATCH")
        if bundle.episode_semantic_sha256 != row["episode_semantic_sha256"]:
            raise SystemExit("STOP=SELECTED_EPISODE_SEMANTIC_SHA_MISMATCH")
        if bundle.gamefile_sha256 in seen_gamefiles:
            raise SystemExit("STOP=SELECTED_GAMEFILE_IDENTITY_DUPLICATE")
        seen_gamefiles.add(bundle.gamefile_sha256)
        source_evidence_row = _frozen_source_evidence_row(dict(row))
        observed_source_row_sha = domain_hash(
            "PI0_I1_TRAIN_UPDATE_EVIDENCE_INDEX_ROW_V1",
            source_evidence_row,
        )
        if observed_source_row_sha != row.get(
            "source_evidence_index_row_sha256"
        ):
            raise SystemExit("STOP=SELECTED_SOURCE_EVIDENCE_ROW_SHA_MISMATCH")
        enriched = dict(row)
        enriched["gamefile_sha256"] = bundle.gamefile_sha256
        enriched["source_unit_id"] = domain_hash(
            "CLEAN_ANALYZER_SOURCE_UNIT_ID_V1",
            {
                "round_id": budget["round_id"],
                "source_campaign_sha256": cutoff["source_campaign_sha256"],
                "scientific_cell_id": row["scientific_cell_id"],
                "execution_attempt_id": row["execution_attempt_id"],
                "task_id": row["task_id"],
                "gamefile_sha256": bundle.gamefile_sha256,
            },
        )
        validated.append((enriched, bundle, source_evidence_row))

    u_reg = build_local_u_reg_manifest(
        round_id=str(budget["round_id"]),
        policy_version=str(budget["policy_version"]),
        evidence_cutoff_sha256=str(cutoff["evidence_cutoff_sha256"]),
        failure_universe_file_sha256=sha256_file(failure_path),
        source_campaign_sha256=str(cutoff["source_campaign_sha256"]),
        resource_budget=budget,
        selected_units=[row for row, _, _ in validated],
    )
    u_reg_path = output / "CLEAN_ANALYZER_LOCAL_U_REG_V1.json"
    write_new_json(u_reg_path, u_reg)

    policy_identity = build_pi0_i1_analyzer_policy_identity(
        pi0_artifact=pi0,
        runtime_binding=runtime,
        evidence_cutoff=cutoff,
    )
    write_new_json(output / "PI0_I1_ANALYZER_POLICY_IDENTITY_V1.json", policy_identity)

    registry_units: list[dict[str, object]] = []
    access_manifest_rows: list[dict[str, object]] = []
    materialized_rows: list[dict[str, object]] = []
    units_root = output / "units"

    for row, bundle, source_evidence_row in validated:
        source_unit_id = str(row["source_unit_id"])
        unit_root = units_root / source_unit_id
        unit_root.mkdir(parents=True, exist_ok=False)

        trajectory_binding = build_clean_current_trajectory_binding(
            bundle=bundle,
            evidence_row=source_evidence_row,
            evidence_cutoff=cutoff,
            analyzer_readiness=readiness,
            policy_identity=policy_identity,
            source_campaign_root=train_root,
        )
        mechanical = extract_mechanical_episode_evidence(bundle)
        pack = build_clean_analyzer_evidence_pack(
            bundle=bundle,
            policy_identity=policy_identity,
            trajectory_binding=trajectory_binding,
            mechanical_evidence=mechanical,
        )
        trajectory_path = unit_root / "trajectory_binding.json"
        mechanical_path = unit_root / "mechanical_evidence.json"
        pack_path = unit_root / "analyzer_evidence_pack.json"
        write_new_json(trajectory_path, trajectory_binding)
        write_new_json(mechanical_path, mechanical)
        write_new_json(pack_path, pack)

        source_manifest: dict[str, object] = {
            "schema_id": "CLEAN_ANALYZER_SOURCE_UNIT_MANIFEST_V1",
            "schema_version": 1,
            "round_id": budget["round_id"],
            "source_unit_id": source_unit_id,
            "selection_rank": row["selection_rank"],
            "scientific_cell_id": row["scientific_cell_id"],
            "execution_attempt_id": row["execution_attempt_id"],
            "task_id": row["task_id"],
            "task_type": row["task_type"],
            "gamefile_sha256": bundle.gamefile_sha256,
            "source_campaign_sha256": cutoff["source_campaign_sha256"],
            "evidence_cutoff_sha256": cutoff["evidence_cutoff_sha256"],
            "source_evidence_index_row_sha256": row[
                "source_evidence_index_row_sha256"
            ],
            "local_u_reg_sha256": u_reg["u_reg_sha256"],
            "attempt_bundle_sha256": bundle.attempt_bundle_sha256,
            "episode_semantic_sha256": bundle.episode_semantic_sha256,
            "trajectory_binding_sha256": trajectory_binding["binding_sha256"],
            "mechanical_evidence_sha256": mechanical["evidence_sha256"],
            "analyzer_evidence_pack_sha256": pack["evidence_pack_sha256"],
            "source_unit_manifest_sha256": "0" * 64,
        }
        if trajectory_binding["evidence_index_row_sha256"] != row[
            "source_evidence_index_row_sha256"
        ]:
            raise SystemExit("STOP=TRAJECTORY_SOURCE_EVIDENCE_ROW_SHA_MISMATCH")
        source_manifest["source_unit_manifest_sha256"] = domain_hash(
            "CLEAN_ANALYZER_SOURCE_UNIT_MANIFEST_V1",
            source_manifest,
            excluded_field="source_unit_manifest_sha256",
        )
        source_manifest_path = unit_root / "source_unit_manifest.json"
        write_new_json(source_manifest_path, source_manifest)

        identity = build_scientific_unit_identity(
            scientific_unit_type="EPISODE",
            scientific_unit_id=source_unit_id,
            source_unit_manifest_sha256=source_manifest[
                "source_unit_manifest_sha256"
            ],
            task_set_manifest_sha256=u_reg["u_reg_sha256"],
            task_id=row["task_id"],
            gamefile_sha256=bundle.gamefile_sha256,
            group_manifest_sha256=None,
            round_evidence_package_sha256=None,
        )
        identity_path = unit_root / "scientific_unit_identity.json"
        write_new_json(identity_path, identity)

        access = build_clean_analyzer_task_access_record(
            round_id=str(budget["round_id"]),
            source_unit_id=source_unit_id,
            task_id=str(row["task_id"]),
            gamefile_sha256=bundle.gamefile_sha256,
            source_campaign_sha256=str(cutoff["source_campaign_sha256"]),
            evidence_cutoff_sha256=str(cutoff["evidence_cutoff_sha256"]),
        )
        access_path = unit_root / "task_access_record.json"
        write_new_json(access_path, access)

        projection = local_projection(pack_path)
        projection_path = unit_root / "local_projection.json"
        write_new_json(projection_path, projection)

        access_manifest_rows.append(
            {
                "source_unit_id": source_unit_id,
                "task_access_record_path": _relative(access_path, output),
                "task_access_record_sha256": access["task_access_sha256"],
            }
        )
        for stage_id, condition_id in (("L-A0", "A0"), ("L-A1", "A1")):
            registry_units.append(
                {
                    "source_unit_id": source_unit_id,
                    "scientific_unit_identity_path": _relative(identity_path, output),
                    "stage_id": stage_id,
                    "condition_id": condition_id,
                    "input_projection_path": _relative(projection_path, output),
                    "task_access_record_path": _relative(access_path, output),
                    "expected_common_evidence_sha256": pack[
                        "evidence_pack_sha256"
                    ],
                    "expected_a1_local_result_sha256": None,
                    "expected_memory_pack_sha256": None,
                }
            )
        materialized_rows.append(
            {
                "source_unit_id": source_unit_id,
                "selection_rank": row["selection_rank"],
                "task_id": row["task_id"],
                "task_type": row["task_type"],
                "gamefile_sha256": bundle.gamefile_sha256,
                "scientific_unit_identity_sha256": identity["identity_sha256"],
                "analyzer_evidence_pack_sha256": pack["evidence_pack_sha256"],
                "source_evidence_index_row_sha256": row[
                    "source_evidence_index_row_sha256"
                ],
                "local_projection_file_sha256": sha256_file(projection_path),
                "task_access_sha256": access["task_access_sha256"],
            }
        )

    access_manifest: dict[str, object] = {
        "schema_id": "CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1",
        "schema_version": 1,
        "round_id": budget["round_id"],
        "source_campaign_sha256": cutoff["source_campaign_sha256"],
        "evidence_cutoff_sha256": cutoff["evidence_cutoff_sha256"],
        "row_count": len(access_manifest_rows),
        "rows": access_manifest_rows,
        "manifest_sha256": "0" * 64,
    }
    access_manifest["manifest_sha256"] = domain_hash(
        "CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1",
        access_manifest,
        excluded_field="manifest_sha256",
    )
    access_manifest_path = output / "CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1.json"
    write_new_json(access_manifest_path, access_manifest)

    registry: dict[str, object] = {
        "schema_id": "RUNTIME_INPUT_REGISTRY_V1",
        "schema_version": 1,
        "registry_role": "FORMAL_A0_A3",
        "round_id": budget["round_id"],
        "policy_version": budget["policy_version"],
        "task_access_manifest_sha256": sha256_file(access_manifest_path),
        "units": registry_units,
        "registry_sha256": "0" * 64,
    }
    registry["registry_sha256"] = domain_hash(
        "RUNTIME_INPUT_REGISTRY_V1",
        registry,
        excluded_field="registry_sha256",
    )
    validate_artifact("RUNTIME_INPUT_REGISTRY_V1", registry)
    registry_path = output / "CLEAN_ANALYZER_LOCAL_RUNTIME_INPUT_REGISTRY_V1.json"
    write_new_json(registry_path, registry)

    actor_binding = build_actor_input_binding(
        round_id=str(budget["round_id"]),
        runtime_registry_sha256=str(registry["registry_sha256"]),
        local_u_reg_sha256=str(u_reg["u_reg_sha256"]),
        human_primary_authorized=True,
        strong_shadow_authorized=True,
    )
    write_new_json(
        output / "CLEAN_ANALYZER_ACTOR_INPUT_BINDING_V1.json",
        actor_binding,
    )

    family_counts = Counter(str(row["task_type"]) for row, _, _ in validated)
    receipt: dict[str, object] = {
        "schema_id": "CLEAN_ANALYZER_LOCAL_INPUT_MATERIALIZATION_RECEIPT_V1",
        "schema_version": 1,
        "round_id": budget["round_id"],
        "policy_version": budget["policy_version"],
        "resource_budget_sha256": budget["budget_sha256"],
        "local_u_reg_sha256": u_reg["u_reg_sha256"],
        "runtime_registry_sha256": registry["registry_sha256"],
        "actor_input_binding_sha256": actor_binding["binding_sha256"],
        "source_state_count": len(validated),
        "a0_local_unit_count": len(validated),
        "a1_local_unit_count": len(validated),
        "total_local_unit_count": len(registry_units),
        "task_family_counts": dict(sorted(family_counts.items())),
        "human_selected_state_count": 0,
        "manual_source_state_count_input_allowed": False,
        "failure_success_ratio_input_allowed": False,
        "initial_memory_state": "EMPTY",
        "old_r0_reference_count": 0,
        "pilot_semantic_reference_count": 0,
        "benchmark_reference_count": 0,
        "model_execution_count": 0,
        "provider_call_count": 0,
        "environment_execution_count": 0,
        "training_execution_count": 0,
        "materialized_rows": materialized_rows,
        "receipt_sha256": "0" * 64,
    }
    receipt["receipt_sha256"] = domain_hash(
        "CLEAN_ANALYZER_LOCAL_INPUT_MATERIALIZATION_RECEIPT_V1",
        receipt,
        excluded_field="receipt_sha256",
    )
    write_new_json(
        output / "CLEAN_ANALYZER_LOCAL_INPUT_MATERIALIZATION_RECEIPT_V1.json",
        receipt,
    )

    print("CLEAN_ANALYZER_LOCAL_INPUT_MATERIALIZATION_PASS")
    print("SOURCE_STATE_COUNT=" + str(len(validated)))
    print("A0_LOCAL_UNIT_COUNT=" + str(len(validated)))
    print("A1_LOCAL_UNIT_COUNT=" + str(len(validated)))
    print("TOTAL_LOCAL_UNIT_COUNT=" + str(len(registry_units)))
    print("RUNTIME_REGISTRY_SHA256=" + str(registry["registry_sha256"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

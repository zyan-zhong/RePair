#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from pchsi.research_intelligence.final_two_slot_resolution import (
    build_final_two_slot_artifacts_v1,
)


def load(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"regular JSON file required: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def write_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    data = canonical_bytes(value)
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def markdown_report(artifacts: dict[str, object]) -> str:
    policy = artifacts["policy_resolution"]
    task = artifacts["task_set_resolution"]
    manifest = artifacts["hydration_manifest"]

    lines = [
        "# Strong Researcher Final Two-Slot Resolution V1",
        "",
        "This stage changes only the two remaining unreadable high-level "
        "Strong-Researcher evidence slots.",
        "",
        "## Resolution summary",
        "",
        f"- policy config: `{policy['status']}`",
        f"- task set: `{task['status']}`",
        f"- resolved required slots: "
        f"`{manifest['resolved_required_slot_count']}/"
        f"{manifest['required_bound_slot_count']}`",
        f"- hydration ready: `{str(manifest['hydration_ready']).lower()}`",
        "",
        "## Policy-config semantics",
        "",
        "The Round-Evidence field named `policy_config_sha256` is accepted "
        "only when the sealed policy-lineage artifact independently binds "
        "the same SHA as `policy_condition_manifest_sha256`, and a dedicated "
        "policy-condition manifest with the same condition identity is found.",
        "",
        "This is an explicit semantic alias; episode `attempt.json` records "
        "that merely reference the SHA are not authority.",
        "",
        "## Task-set rule",
        "",
        "Task-access manifests and `SCIENTIFIC_UNIT_IDENTITY_V1` references "
        "cannot substitute for the task-set manifest. A task set is resolved "
        "only by an exact readable file SHA or a dedicated task-set manifest "
        "that registers the exact bound identity.",
        "",
        "Deterministic reconstruction is not attempted unless the project's "
        "original task-set hash builder is located and separately reviewed.",
        "",
        "## Next gate",
        "",
        (
            "`USER_REVIEW_OF_FINAL_STRONG_BLIND_EVIDENCE`"
            if manifest["hydration_ready"]
            else "`QUERY_REQUIRED_FINAL_TWO_SLOT_EVIDENCE`"
        ),
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blind-input-v1", required=True)
    parser.add_argument("--reference-trace-v2", required=True)
    parser.add_argument("--base-hydration-manifest", required=True)
    parser.add_argument(
        "--policy-root",
        action="append",
        default=[],
        required=True,
    )
    parser.add_argument(
        "--task-set-root",
        action="append",
        default=[],
        required=True,
    )
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    blind = load(Path(args.blind_input_v1).resolve())
    trace = load(Path(args.reference_trace_v2).resolve())
    base = load(Path(args.base_hydration_manifest).resolve())

    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)

    artifacts = build_final_two_slot_artifacts_v1(
        blind_input_v1=blind,
        reference_trace_v2=trace,
        base_manifest=base,
        policy_roots=[
            Path(raw).resolve() for raw in args.policy_root
        ],
        task_set_roots=[
            Path(raw).resolve() for raw in args.task_set_root
        ],
    )

    write_new(
        output / "POLICY_CONFIG_SEMANTIC_ALIAS_RESOLUTION_V1.json",
        artifacts["policy_resolution"],
    )
    write_new(
        output / "TASK_SET_MANIFEST_RESOLUTION_V1.json",
        artifacts["task_set_resolution"],
    )
    write_new(
        output / "STRONG_RESEARCHER_EVIDENCE_HYDRATION_MANIFEST_V1.json",
        artifacts["hydration_manifest"],
    )

    if artifacts["blind_input_v2"] is not None:
        write_new(
            output / "STRONG_RESEARCHER_BLIND_PRE_INPUT_V2.json",
            artifacts["blind_input_v2"],
        )
        write_new(
            output / "RESEARCH_PLANNER_REFERENCE_TRACE_V3.json",
            artifacts["reference_trace_v3"],
        )

    report = {
        "schema_id": "STRONG_RESEARCHER_FINAL_TWO_SLOT_BUILD_REPORT_V1",
        "schema_version": 1,
        "policy_config_status": artifacts[
            "policy_resolution"
        ]["status"],
        "task_set_status": artifacts[
            "task_set_resolution"
        ]["status"],
        "required_bound_slot_count": artifacts[
            "hydration_manifest"
        ]["required_bound_slot_count"],
        "resolved_required_slot_count": artifacts[
            "hydration_manifest"
        ]["resolved_required_slot_count"],
        "unresolved_required_slot_ids": artifacts[
            "hydration_manifest"
        ]["unresolved_required_slot_ids"],
        "hydration_ready": artifacts[
            "hydration_manifest"
        ]["hydration_ready"],
        "hydration_manifest_sha256": artifacts[
            "hydration_manifest"
        ]["hydration_manifest_sha256"],
        "hydration_manifest_file_sha256": hashlib.sha256(
            canonical_bytes(artifacts["hydration_manifest"])
        ).hexdigest(),
        "blind_input_v2_sha256": (
            None
            if artifacts["blind_input_v2"] is None
            else artifacts["blind_input_v2"][
                "blind_input_sha256"
            ]
        ),
        "reference_trace_v3_sha256": (
            None
            if artifacts["reference_trace_v3"] is None
            else artifacts["reference_trace_v3"][
                "trace_sha256"
            ]
        ),
        "human_adjudication_changed": False,
        "human_pre_frozen": False,
        "strong_researcher_shadow_executed": False,
        "f0f1_executed": False,
        "training_executed": False,
        "success_trajectory_optimization_active": False,
        "next_gate": (
            "USER_REVIEW_OF_FINAL_STRONG_BLIND_EVIDENCE"
            if artifacts["hydration_manifest"][
                "hydration_ready"
            ]
            else "QUERY_REQUIRED_FINAL_TWO_SLOT_EVIDENCE"
        ),
    }
    write_new(
        output
        / "STRONG_RESEARCHER_FINAL_TWO_SLOT_BUILD_REPORT_V1.json",
        report,
    )
    (
        output / "STRONG_RESEARCHER_FINAL_TWO_SLOT_REVIEW_V1.md"
    ).write_text(
        markdown_report(artifacts),
        encoding="utf-8",
    )

    print(
        "FINAL_POLICY_CONFIG_STATUS="
        + report["policy_config_status"]
    )
    print(
        "FINAL_POLICY_CONFIG_TARGET_SHA256="
        + artifacts["policy_resolution"]["target_sha256"]
    )
    print(
        "FINAL_POLICY_CONFIG_CANDIDATE_OCCURRENCE_COUNT="
        + str(
            artifacts["policy_resolution"][
                "candidate_occurrence_count"
            ]
        )
    )
    print(
        "FINAL_TASK_SET_STATUS="
        + report["task_set_status"]
    )
    print(
        "FINAL_TASK_SET_TARGET_SHA256="
        + artifacts["task_set_resolution"]["target_sha256"]
    )
    print(
        "FINAL_TASK_SET_REFERENCE_OCCURRENCE_COUNT="
        + str(
            artifacts["task_set_resolution"][
                "reference_occurrence_count"
            ]
        )
    )
    print(
        "FINAL_TASK_SET_BUILDER_SOURCE_CANDIDATE_COUNT="
        + str(
            artifacts["task_set_resolution"][
                "builder_source_candidate_count"
            ]
        )
    )
    for row in artifacts["task_set_resolution"][
        "builder_source_candidates"
    ][:20]:
        print(
            "TASK_SET_BUILDER_CANDIDATE="
            + row["source_path"]
        )
    print(
        "FINAL_RESOLVED_REQUIRED_SLOT_COUNT="
        + str(report["resolved_required_slot_count"])
    )
    print(
        "FINAL_REQUIRED_BOUND_SLOT_COUNT="
        + str(report["required_bound_slot_count"])
    )
    print(
        "FINAL_UNRESOLVED_REQUIRED_SLOT_IDS="
        + repr(report["unresolved_required_slot_ids"])
    )
    print(
        "FINAL_HYDRATION_READY="
        + str(report["hydration_ready"]).lower()
    )
    print(
        "FINAL_HYDRATION_MANIFEST_SHA256="
        + report["hydration_manifest_sha256"]
    )
    print(
        "FINAL_HYDRATION_MANIFEST_FILE_SHA256="
        + report["hydration_manifest_file_sha256"]
    )
    if report["hydration_ready"]:
        print(
            "FINAL_STRONG_RESEARCHER_BLIND_INPUT_V2_SHA256="
            + report["blind_input_v2_sha256"]
        )
        print(
            "FINAL_RESEARCH_PLANNER_REFERENCE_TRACE_V3_SHA256="
            + report["reference_trace_v3_sha256"]
        )
    print("HUMAN_ADJUDICATION_CHANGED=false")
    print("HUMAN_PRE_FROZEN=false")
    print("STRONG_RESEARCHER_SHADOW_EXECUTED=false")
    print("SUCCESS_TRAJECTORY_OPTIMIZATION_ACTIVE=false")
    print("NEXT_GATE=" + report["next_gate"])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pchsi.research_intelligence.strong_researcher_evidence_hydration import (
    build_hydration_manifest_v1,
    build_reference_trace_v3,
    build_strong_blind_pre_input_v2,
    validate_hydrated_blind_input_v2,
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


def write_new_json(path: Path, value: object) -> None:
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


def safe_slot(slot_id: str) -> str:
    return "".join(
        ch if ch.isalnum() or ch in "._-" else "_"
        for ch in slot_id
    )


def markdown_report(
    manifest: dict[str, object],
) -> str:
    lines = [
        "# Strong Researcher Blind Evidence Hydration V1",
        "",
        "This review hydrates immutable Round-Evidence SHA references into "
        "model-readable, pre-outcome evidence views. It does not change the "
        "Human 12-state adjudication.",
        "",
        "## Summary",
        "",
        f"- required bound slots: `{manifest['required_bound_slot_count']}`",
        f"- resolved required slots: `{manifest['resolved_required_slot_count']}`",
        f"- hydration ready: `{str(manifest['hydration_ready']).lower()}`",
        "",
        "## Slot audit",
        "",
        "|lane|field|status|reference|selected source|",
        "|---|---|---|---|---|",
    ]
    for slot in manifest["slots"]:
        selected = slot.get("selected_match")
        source = (
            selected.get("source_path")
            if isinstance(selected, dict)
            else ""
        )
        reference = slot.get("reference_sha256")
        lines.append(
            "|"
            + str(slot["lane"])
            + "|"
            + str(slot["field"])
            + "|"
            + str(slot["status"])
            + "|`"
            + (str(reference)[:16] + "…" if reference else "null")
            + "`|"
            + str(source or "")
            .replace("|", "\\|")
            + "|"
        )

    lines.extend(
        [
            "",
            "## Scientific boundary",
            "",
            "- Human PRE / Human selection / Human rationale remain hidden.",
            "- Current F0/F1 outcomes remain absent.",
            "- Strong-model benchmark per-task results remain absent.",
            "- Null historical references remain explicitly absent; they are "
            "not backfilled from conversation memory.",
            "- The policy checkpoint remains an identity-only artifact; model "
            "weights are not injected into the Researcher prompt.",
            "- Success-trajectory optimization remains inactive.",
            "",
            "## Next gate",
            "",
            (
                "`USER_REVIEW_OF_STRONG_BLIND_EVIDENCE_HYDRATION`"
                if manifest["hydration_ready"]
                else "`QUERY_REQUIRED_EVIDENCE_HYDRATION`"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blind-input-v1", required=True)
    parser.add_argument("--reference-trace-v2", required=True)
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        required=True,
    )
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    blind_v1 = load(Path(args.blind_input_v1).resolve())
    trace_v2 = load(Path(args.reference_trace_v2).resolve())

    roots = [Path(raw).resolve() for raw in args.root]
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)

    manifest = build_hydration_manifest_v1(
        blind_input_v1=blind_v1,
        roots=roots,
    )
    write_new_json(
        output
        / "STRONG_RESEARCHER_EVIDENCE_HYDRATION_MANIFEST_V1.json",
        manifest,
    )

    bound_root = output / "bound_readable_evidence"
    for slot in manifest["slots"]:
        slot_dir = bound_root / safe_slot(str(slot["slot_id"]))
        slot_dir.mkdir(parents=True, exist_ok=True)
        write_new_json(
            slot_dir / "SLOT_AUDIT.json",
            slot,
        )
        if slot.get("readable_view") is not None:
            write_new_json(
                slot_dir / "READABLE_VIEW.json",
                slot["readable_view"],
            )

    blind_v2 = None
    trace_v3 = None
    if manifest["hydration_ready"]:
        blind_v2 = build_strong_blind_pre_input_v2(
            blind_input_v1=blind_v1,
            hydration_manifest=manifest,
        )
        validate_hydrated_blind_input_v2(
            blind_input_v2=blind_v2,
            hydration_manifest=manifest,
        )
        trace_v3 = build_reference_trace_v3(
            reference_trace_v2=trace_v2,
            hydration_manifest=manifest,
            blind_input_v2=blind_v2,
        )
        write_new_json(
            output / "STRONG_RESEARCHER_BLIND_PRE_INPUT_V2.json",
            blind_v2,
        )
        write_new_json(
            output / "RESEARCH_PLANNER_REFERENCE_TRACE_V3.json",
            trace_v3,
        )

    status = (
        "READY_FOR_USER_HYDRATION_REVIEW"
        if manifest["hydration_ready"]
        else "QUERY_REQUIRED_EVIDENCE_HYDRATION"
    )
    report = {
        "schema_id": (
            "STRONG_RESEARCHER_EVIDENCE_HYDRATION_BUILD_REPORT_V1"
        ),
        "schema_version": 1,
        "status": status,
        "source_blind_input_v1_sha256": blind_v1[
            "blind_input_sha256"
        ],
        "hydration_manifest_sha256": manifest[
            "hydration_manifest_sha256"
        ],
        "blind_input_v2_sha256": (
            None
            if blind_v2 is None
            else blind_v2["blind_input_sha256"]
        ),
        "reference_trace_v3_sha256": (
            None
            if trace_v3 is None
            else trace_v3["trace_sha256"]
        ),
        "required_bound_slot_count": manifest[
            "required_bound_slot_count"
        ],
        "resolved_required_slot_count": manifest[
            "resolved_required_slot_count"
        ],
        "unresolved_required_slot_ids": manifest[
            "unresolved_required_slot_ids"
        ],
        "human_adjudication_changed": False,
        "human_pre_frozen": False,
        "strong_researcher_shadow_executed": False,
        "f0f1_executed": False,
        "training_executed": False,
        "benchmark_per_task_results_visible": False,
        "success_trajectory_optimization_active": False,
        "next_gate": (
            "USER_REVIEW_OF_STRONG_BLIND_EVIDENCE_HYDRATION"
            if manifest["hydration_ready"]
            else "QUERY_REQUIRED_EVIDENCE_HYDRATION"
        ),
    }
    write_new_json(
        output
        / "STRONG_RESEARCHER_EVIDENCE_HYDRATION_BUILD_REPORT_V1.json",
        report,
    )
    (
        output
        / "STRONG_RESEARCHER_EVIDENCE_HYDRATION_REVIEW_V1.md"
    ).write_text(
        markdown_report(manifest),
        encoding="utf-8",
    )

    print(
        "HYDRATION_REQUIRED_BOUND_SLOT_COUNT="
        + str(manifest["required_bound_slot_count"])
    )
    print(
        "HYDRATION_RESOLVED_REQUIRED_SLOT_COUNT="
        + str(manifest["resolved_required_slot_count"])
    )
    print(
        "HYDRATION_UNRESOLVED_REQUIRED_SLOT_IDS="
        + repr(manifest["unresolved_required_slot_ids"])
    )
    print(
        "HYDRATION_SCAN_FILE_COUNT="
        + str(manifest["scan_statistics"]["scanned_file_count"])
    )
    print(
        "HYDRATION_PARSED_FILE_COUNT="
        + str(manifest["scan_statistics"]["parsed_file_count"])
    )
    print(
        "HYDRATION_READY="
        + str(manifest["hydration_ready"]).lower()
    )
    if blind_v2 is not None:
        print(
            "STRONG_RESEARCHER_BLIND_INPUT_V2_SHA256="
            + str(blind_v2["blind_input_sha256"])
        )
        print(
            "RESEARCH_PLANNER_REFERENCE_TRACE_V3_SHA256="
            + str(trace_v3["trace_sha256"])
        )
    print("HUMAN_ADJUDICATION_CHANGED=false")
    print("HUMAN_PRE_FROZEN=false")
    print("STRONG_RESEARCHER_SHADOW_EXECUTED=false")
    print("SUCCESS_TRAJECTORY_OPTIMIZATION_ACTIVE=false")
    print("NEXT_GATE=" + report["next_gate"])


if __name__ == "__main__":
    main()

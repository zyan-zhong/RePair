#!/usr/bin/env python3
"""Build a three-case human factual registration panel from source collection.

The selected failures are references into the complete collection ledger. This
program does not create scientific registration authority.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.source_collection import (
    NO_PERFORMANCE_ESTIMAND,
    SelectedFailurePanelV1,
    SelectedFailureReferenceV1,
    SourcePanelManifestV1,
    read_source_collection_ledger_v1,
)


def _load_attempt_materializer(repo_root: Path):
    path = (
        repo_root
        / "scripts/memory/materialize_sequence_failure_experience_v1.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_source_human_panel_attempt_loader",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load attempt materializer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_selected_panel(path: Path) -> SelectedFailurePanelV1:
    raw = path.read_bytes()
    payload = strict_json_loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("selected failure panel must be object")
    expected = {
        "schema_id",
        "schema_version",
        "panel_manifest_sha256",
        "collection_ledger_sha256",
        "selection_rule",
        "performance_estimand",
        "selected_failures",
        "selected_panel_sha256",
    }
    if set(payload) != expected:
        raise ValueError("selected failure panel fields mismatch")
    raw_refs = payload["selected_failures"]
    if not isinstance(raw_refs, list):
        raise TypeError("selected_failures must be array")
    panel = SelectedFailurePanelV1(
        schema_id=payload["schema_id"],
        schema_version=payload["schema_version"],
        panel_manifest_sha256=payload["panel_manifest_sha256"],
        collection_ledger_sha256=payload["collection_ledger_sha256"],
        selection_rule=payload["selection_rule"],
        performance_estimand=payload["performance_estimand"],
        selected_failures=tuple(
            SelectedFailureReferenceV1(
                panel_index=item["panel_index"],
                case_receipt_sha256=item["case_receipt_sha256"],
                execution_attempt_id=item["execution_attempt_id"],
                attempt_bundle_sha256=item["attempt_bundle_sha256"],
            )
            for item in raw_refs
        ),
        selected_panel_sha256=payload["selected_panel_sha256"],
    )
    if raw != panel.canonical_bytes():
        raise ValueError("selected failure panel is not canonical")
    return panel


def _excerpt(value: object, limit: int = 320) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).replace("\r", " ").replace("\n", " ").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _timeline(source):
    transitions = {
        item.model_call_index: item.to_dict()
        for item in source.public_transitions
    }
    policy_calls = {
        item.model_call_index: item.to_dict()
        for item in source.policy_calls
    }
    compact = []
    full = []
    for trace in source.traces:
        trace_payload = trace.to_dict()
        call = policy_calls[trace.model_call_index]
        transition = transitions.get(trace.model_call_index)

        compact.append(
            {
                "model_call_index": trace.model_call_index,
                "environment_step_index": trace.environment_step_index,
                "execution_status": trace.execution_status.value,
                "literal_action": _excerpt(trace.literal_action, 180),
                "submitted_environment_action": _excerpt(
                    trace.submitted_environment_action,
                    180,
                ),
                "parser_status": _excerpt(trace.parser_status),
                "parser_error": _excerpt(trace.parser_error),
                "attempt_outcome": _excerpt(trace.attempt_outcome),
                "failure_stage": _excerpt(trace.failure_stage),
                "failure_code": _excerpt(trace.failure_code),
                "feedback_before": _excerpt(
                    call.get("interface_feedback_before")
                ),
                "budget_before": json.dumps(
                    call.get("budget_before"),
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "observation": _excerpt(call.get("observation")),
                "resulting_observation": _excerpt(
                    None
                    if transition is None
                    else transition.get("resulting_observation")
                ),
                "score": (
                    None if transition is None else transition.get("score")
                ),
                "done": (
                    None if transition is None else transition.get("done")
                ),
                "won": (
                    None if transition is None else transition.get("won")
                ),
            }
        )
        full.append(
            {
                "model_call_index": trace.model_call_index,
                "action_trace": trace_payload,
                "policy_call": call,
                "public_transition": transition,
            }
        )

    return compact, full


def _write_jsonl(path: Path, rows) -> None:
    with path.open("wb") as handle:
        for row in rows:
            handle.write(canonical_json_bytes(row))


def _write_tsv(path: Path, rows) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _review_md(case_id: str, summary: dict[str, object], compact) -> str:
    lines = [
        f"# {case_id}",
        "",
        "## Authority boundary",
        "",
        "This case was selected only because it is one of the first three true",
        "failures in the pre-frozen complete TRAIN_MEMORY_SOURCE panel order.",
        "It is a source-evidence case, not a benchmark case.",
        "",
        f"- source panel index: `{summary['panel_index']}`",
        f"- task type: `{summary['task_type']}`",
        f"- source task: `{summary['source_task_id']}`",
        f"- attempt: `{summary['execution_attempt_id']}`",
        f"- attempt bundle SHA-256: `{summary['attempt_bundle_sha256']}`",
        f"- selected failure panel SHA-256: `{summary['selected_failure_panel_sha256']}`",
        f"- performance estimand: `{NO_PERFORMANCE_ESTIMAND}`",
        "",
        "## Human factual decision required",
        "",
        "Choose the factual source range:",
        "",
        "- `relevant_start_model_call_index`",
        "- `registered_failure_onset_model_call_index`",
        "- `final_model_call_index`",
        "- optional recovery start/final (both null or both integers)",
        "",
        "Also approve descriptive assembly text:",
        "",
        "- activation condition",
        "- release/termination condition",
        "- optional non-applicability condition",
        "- optional candidate mechanism",
        "- optional proposed recovery steps",
        "",
        "These descriptive fields are hypotheses/boundaries, not effect evidence.",
        "",
        "## Compact timeline",
        "",
        "| call | env step | execution | action | failure/feedback | observation → result |",
        "|---:|---:|---|---|---|---|",
    ]

    for row in compact:
        failure = " / ".join(
            str(value)
            for value in (
                row["failure_stage"],
                row["failure_code"],
                row["feedback_before"],
            )
            if value not in ("", None)
        )
        obs = (
            str(row["observation"])
            + " → "
            + str(row["resulting_observation"])
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["model_call_index"]),
                    str(row["environment_step_index"]),
                    str(row["execution_status"]),
                    str(
                        row["submitted_environment_action"]
                        or row["literal_action"]
                    ).replace("|", "\\|"),
                    failure.replace("|", "\\|"),
                    obs.replace("|", "\\|"),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "Full exact evidence is in `timeline_full.jsonl`.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--source-collection-root", required=True)
    parser.add_argument("--panel-manifest", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    collection_root = Path(args.source_collection_root).resolve()
    panel_manifest_path = Path(args.panel_manifest).resolve()
    output_root = Path(args.output_root).resolve()

    if output_root.exists():
        raise SystemExit("STOP=HUMAN_PANEL_OUTPUT_ALREADY_EXISTS")
    output_root.mkdir(parents=True)

    panel_raw = panel_manifest_path.read_bytes()
    panel = SourcePanelManifestV1.from_json(panel_raw)
    if panel_raw != panel.canonical_bytes():
        raise SystemExit("STOP=SOURCE_PANEL_NOT_CANONICAL")

    ledger_path = collection_root / "source_collection_ledger.jsonl"
    selected_path = collection_root / "selected_failure_panel.json"
    ledger = read_source_collection_ledger_v1(ledger_path)
    selected = _load_selected_panel(selected_path)

    if selected.panel_manifest_sha256 != panel.panel_manifest_sha256:
        raise SystemExit("STOP=SELECTED_PANEL_SOURCE_PANEL_MISMATCH")
    if (
        selected.collection_ledger_sha256
        != hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    ):
        raise SystemExit("STOP=SELECTED_PANEL_LEDGER_SHA_MISMATCH")

    loader = _load_attempt_materializer(repo_root)

    index_payload = {
        "schema_id": "FAILURE_MEMORY_HUMAN_REGISTRATION_PANEL_V2",
        "schema_version": 2,
        "source_panel_manifest_sha256": panel.panel_manifest_sha256,
        "source_collection_ledger_sha256": selected.collection_ledger_sha256,
        "selected_failure_panel_sha256": selected.selected_panel_sha256,
        "selection_rule": selected.selection_rule,
        "performance_estimand": NO_PERFORMANCE_ESTIMAND,
        "cases": [],
        "scientific_registration_authority_created": False,
    }

    for order, ref in enumerate(selected.selected_failures, start=1):
        receipt = ledger[ref.panel_index]
        entry = panel.entries[ref.panel_index]
        if receipt.receipt_sha256 != ref.case_receipt_sha256:
            raise SystemExit("STOP=SELECTED_FAILURE_RECEIPT_SHA_MISMATCH")
        if receipt.success is not False:
            raise SystemExit("STOP=SELECTED_FAILURE_REFERENCE_IS_NOT_FAILURE")

        attempt_dir = (
            collection_root
            / "evaluator_run"
            / "attempts"
            / ref.execution_attempt_id
        )
        source = loader.load_attempt_directory_v1(attempt_dir)
        if (
            source.attempt_bundle.attempt_bundle_sha256
            != ref.attempt_bundle_sha256
        ):
            raise SystemExit("STOP=HUMAN_PANEL_BUNDLE_SHA_MISMATCH")

        case_id = (
            f"FM-SOURCE-HR-C{order:02d}-"
            f"{ref.attempt_bundle_sha256[:12]}"
        )
        case_dir = output_root / "cases" / case_id
        case_dir.mkdir(parents=True)

        compact, full = _timeline(source)
        _write_tsv(case_dir / "timeline.tsv", compact)
        _write_jsonl(case_dir / "timeline_full.jsonl", full)

        case_summary = {
            "schema_id": "FAILURE_MEMORY_HUMAN_REGISTRATION_CASE_V2",
            "schema_version": 2,
            "case_id": case_id,
            "selected_failure_order": order - 1,
            "panel_index": ref.panel_index,
            "batch_index": entry.batch_index,
            "source_task_id": receipt.source_task_id,
            "task_type": entry.task_type,
            "task_gamefile_group_id": entry.task_gamefile_group_id,
            "task_access_record_line_index": (
                entry.task_access_record_line_index
            ),
            "task_access_record_sha256": entry.task_access_record_sha256,
            "dataset_relative_gamefile": entry.dataset_relative_gamefile,
            "absolute_gamefile": entry.absolute_gamefile,
            "gamefile_sha256": entry.gamefile_sha256,
            "execution_attempt_id": receipt.execution_attempt_id,
            "attempt_bundle_sha256": receipt.attempt_bundle_sha256,
            "termination_reason": receipt.termination_reason,
            "valid_model_call_index_min": 0,
            "valid_model_call_index_max": len(source.traces) - 1,
            "source_panel_manifest_sha256": panel.panel_manifest_sha256,
            "source_collection_ledger_sha256": selected.collection_ledger_sha256,
            "selected_failure_panel_sha256": selected.selected_panel_sha256,
            "case_receipt_sha256": receipt.receipt_sha256,
            "performance_estimand": NO_PERFORMANCE_ESTIMAND,
        }
        (case_dir / "case_summary.json").write_bytes(
            canonical_json_bytes(case_summary)
        )

        decision_template = {
            "schema_id": "FAILURE_MEMORY_HUMAN_REGISTRATION_DECISION_V2",
            "schema_version": 2,
            "case_id": case_id,
            "decision_status": "PENDING_HUMAN_APPROVAL",
            "source_panel_manifest_sha256": panel.panel_manifest_sha256,
            "source_collection_ledger_sha256": selected.collection_ledger_sha256,
            "selected_failure_panel_sha256": selected.selected_panel_sha256,
            "case_receipt_sha256": receipt.receipt_sha256,
            "attempt_bundle_sha256": receipt.attempt_bundle_sha256,
            "source_attempt_id": receipt.execution_attempt_id,
            "source_task_id": receipt.source_task_id,
            "source_round": "SOURCE_COLLECTION_V1",
            "source_condition": "P4-R1-Q2-BAD-TRAIN17",
            "relevant_start_model_call_index": None,
            "registered_failure_onset_model_call_index": None,
            "final_model_call_index": None,
            "registered_recovery_start_model_call_index": None,
            "registered_recovery_final_model_call_index": None,
            "activation_condition_text": "",
            "release_condition_text": "",
            "non_applicability_condition_text": "",
            "candidate_mechanism_text": "",
            "proposed_recovery_steps": [],
            "reviewer_notes": "",
        }
        (case_dir / "REGISTRATION_DECISION_TEMPLATE.json").write_bytes(
            canonical_json_bytes(decision_template)
        )
        (case_dir / "REVIEW.md").write_text(
            _review_md(case_id, case_summary, compact),
            encoding="utf-8",
        )

        index_payload["cases"].append(case_summary)

    (output_root / "PANEL_INDEX.json").write_bytes(
        canonical_json_bytes(index_payload)
    )

    checksum_lines = []
    for path in sorted(
        item
        for item in output_root.rglob("*")
        if item.is_file()
        and item.name != "SHA256SUMS.txt"
    ):
        checksum_lines.append(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
            + path.relative_to(output_root).as_posix()
        )
    (output_root / "SHA256SUMS.txt").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )

    zip_path = output_root.parent / (output_root.name + ".zip")
    if zip_path.exists():
        raise SystemExit("STOP=HUMAN_PANEL_ZIP_ALREADY_EXISTS")
    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(
            item for item in output_root.rglob("*") if item.is_file()
        ):
            archive.write(
                path,
                arcname=(
                    output_root.name
                    + "/"
                    + path.relative_to(output_root).as_posix()
                ),
            )

    print("HUMAN_REGISTRATION_PANEL_CASE_COUNT=3")
    print(
        "HUMAN_REGISTRATION_SELECTED_FAILURE_PANEL_SHA256="
        + selected.selected_panel_sha256
    )
    print("HUMAN_REGISTRATION_PANEL_ROOT=" + str(output_root))
    print("HUMAN_REGISTRATION_PANEL_ZIP=" + str(zip_path))
    print(
        "HUMAN_REGISTRATION_PANEL_ZIP_SHA256="
        + hashlib.sha256(zip_path.read_bytes()).hexdigest()
    )
    print("SCIENTIFIC_REGISTRATION_AUTHORITY_CREATED=false")
    print("NO_PERFORMANCE_ESTIMAND")
    print("HUMAN_REGISTRATION_PANEL_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

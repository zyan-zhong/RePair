#!/usr/bin/env python3
"""Execute the frozen train-side Failure Memory source panel.

Scientific boundary:
- this is source-evidence collection, not evaluation;
- all executed cases are preserved;
- outcomes are used only by the pre-frozen batch-complete stopping rule;
- no performance estimand is computed or emitted.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter
from pchsi.evaluation.artifact_publisher import ArtifactPublisher
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.evaluation.episode_evaluator import (
    EpisodeDependencies,
    EpisodeExecutionConfig,
    run_single_episode,
)
from pchsi.evaluation.policy_client import (
    HttpPolicyTransport,
    PolicyClient,
)
from pchsi.evaluation.policy_execution_profile import (
    PolicyExecutionProfileV1,
)
from pchsi.evaluation.rendered_prompt import (
    HuggingFaceTokenizerFactory,
    LocalTokenizerPromptRenderer,
)
from pchsi.evaluation.run_schedule import (
    ScheduledCell,
    execution_attempt_id,
    scheduled_cell_id,
)
from pchsi.evaluation.task_manifest import FrozenTaskRecord
from pchsi.memory.source_collection import (
    NO_PERFORMANCE_ESTIMAND,
    OUTCOME_USE,
    SOURCE_BATCH_SIZE,
    SOURCE_CASE_RECEIPT_V1,
    SOURCE_COLLECTION_CONTEXT_V1,
    SourceCollectionCaseReceiptV1,
    SourcePanelManifestV1,
    append_source_collection_receipt_v1,
    build_selected_failure_panel_v1,
    read_source_collection_ledger_v1,
    stopping_decision_after_complete_prefix_v1,
)


PROTECTED_TASK_ACCESS_SHA256 = (
    "260766366d72a9af7b0b4809d30a45bb"
    "56f42134dad66b29a4b61ff7ed4793ea"
)


def _load_materializer(repo_root: Path):
    path = repo_root / "scripts/memory/materialize_sequence_failure_experience_v1.py"
    spec = importlib.util.spec_from_file_location(
        "_source_collection_attempt_auditor",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load attempt auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_canonical_json(path: Path) -> tuple[dict[str, object], bytes]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"invalid canonical JSON path: {path}")
    raw = path.read_bytes()
    payload = strict_json_loads(raw)
    if not isinstance(payload, dict):
        raise TypeError(f"canonical JSON must be object: {path}")
    if raw != canonical_json_bytes(payload):
        raise ValueError(f"JSON bytes are not canonical: {path}")
    return payload, raw


def _sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _traj_file_for_gamefile(gamefile: Path) -> Path:
    for name in ("traj_data.json", "traj_data.jsonl"):
        candidate = gamefile.parent / name
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    # Keep a real stable absolute source file; do not invent a missing path.
    return gamefile


def _task_id(entry) -> str:
    return (
        "failure_memory_train_source_"
        + entry.task_gamefile_group_id[:24]
    )


def _audit_existing_prefix(
    *,
    manifest: SourcePanelManifestV1,
    receipts: tuple[SourceCollectionCaseReceiptV1, ...],
    run_root: Path,
    attempt_auditor,
) -> None:
    if len(receipts) > len(manifest.entries):
        raise ValueError("source ledger exceeds panel")

    for index, receipt in enumerate(receipts):
        entry = manifest.entries[index]
        if receipt.panel_manifest_sha256 != manifest.panel_manifest_sha256:
            raise ValueError("source receipt panel SHA mismatch")
        if receipt.panel_index != entry.panel_index:
            raise ValueError("source receipt panel index mismatch")
        if receipt.batch_index != entry.batch_index:
            raise ValueError("source receipt batch index mismatch")
        if (
            receipt.task_access_record_line_index
            != entry.task_access_record_line_index
        ):
            raise ValueError("source receipt task-access line mismatch")
        if (
            receipt.task_access_record_sha256
            != entry.task_access_record_sha256
        ):
            raise ValueError("source receipt task-access SHA mismatch")
        if receipt.task_gamefile_group_id != entry.task_gamefile_group_id:
            raise ValueError("source receipt task group mismatch")
        if receipt.performance_estimand != NO_PERFORMANCE_ESTIMAND:
            raise ValueError("source receipt performance boundary mismatch")
        if receipt.outcome_use != OUTCOME_USE:
            raise ValueError("source receipt outcome-use boundary mismatch")

        attempt_dir = run_root / "attempts" / receipt.execution_attempt_id
        loaded = attempt_auditor.load_attempt_directory_v1(attempt_dir)
        if (
            loaded.attempt_bundle.attempt_bundle_sha256
            != receipt.attempt_bundle_sha256
        ):
            raise ValueError("source receipt attempt-bundle SHA mismatch")
        if loaded.episode_artifact.task_id != receipt.source_task_id:
            raise ValueError("source receipt task ID mismatch")
        if loaded.episode_artifact.success is not receipt.success:
            raise ValueError("source receipt success mismatch")
        if (
            loaded.episode_artifact.termination_reason
            != receipt.termination_reason
        ):
            raise ValueError("source receipt termination mismatch")


def _write_atomic_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    temp = path.parent / f".{path.name}.{hashlib.sha256(data).hexdigest()}.tmp"
    if temp.exists() or temp.is_symlink():
        raise FileExistsError(str(temp))
    fd = os.open(
        temp,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("os.write made no progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temp, path)
    directory_fd = os.open(
        path.parent,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _write_collection_closure(
    *,
    output_root: Path,
    manifest: SourcePanelManifestV1,
    receipts: tuple[SourceCollectionCaseReceiptV1, ...],
    stopping_reason: str,
) -> None:
    ledger_path = output_root / "source_collection_ledger.jsonl"
    selected = build_selected_failure_panel_v1(
        panel_manifest_sha256=manifest.panel_manifest_sha256,
        collection_ledger_path=ledger_path,
    )
    selected_path = output_root / "selected_failure_panel.json"
    if not selected_path.exists():
        _write_atomic_once(selected_path, selected.canonical_bytes())

    # Outcome counts appear only as stopping-rule evidence; no rate/mean,
    # confidence interval, benchmark metric, or policy-selection value is
    # computed.
    stopping_failure_count = sum(
        1 for item in receipts if item.success is False
    )
    payload = {
        "schema_id": "FAILURE_MEMORY_SOURCE_COLLECTION_CLOSURE_V1",
        "schema_version": 1,
        "source_collection_context": SOURCE_COLLECTION_CONTEXT_V1,
        "panel_manifest_sha256": manifest.panel_manifest_sha256,
        "collection_ledger_sha256": sha256_file(ledger_path),
        "executed_case_count": len(receipts),
        "last_executed_panel_index": (
            None if not receipts else receipts[-1].panel_index
        ),
        "last_complete_batch_index": (
            None if not receipts else receipts[-1].batch_index
        ),
        "stopping_rule_id": manifest.stopping_rule_id,
        "stopping_reason": stopping_reason,
        "stopping_failure_count": stopping_failure_count,
        "stopping_failure_target": manifest.stopping_failure_target,
        "outcome_use": OUTCOME_USE,
        "performance_estimand": NO_PERFORMANCE_ESTIMAND,
        "benchmark_table_eligible": False,
        "pi1_performance_claim_eligible": False,
        "model_selection_eligible": False,
        "selected_failure_panel_sha256": selected.selected_panel_sha256,
        "selected_failure_indices": [
            item.panel_index for item in selected.selected_failures
        ],
        "all_executed_cases_preserved": True,
    }
    closure_path = output_root / "source_collection_closure.json"
    if not closure_path.exists():
        _write_atomic_once(
            closure_path,
            canonical_json_bytes(payload),
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-manifest", required=True)
    parser.add_argument("--runtime-binding", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--policy-base-url",
        default="http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120.0,
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]

    observed_head = subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        text=True,
    ).strip()

    panel_path = Path(args.panel_manifest)
    panel_raw = panel_path.read_bytes()
    manifest = SourcePanelManifestV1.from_json(panel_raw)
    if panel_raw != manifest.canonical_bytes():
        raise SystemExit("STOP=SOURCE_PANEL_MANIFEST_NOT_CANONICAL")
    if observed_head != manifest.source_collection_code_commit:
        raise SystemExit("STOP=SOURCE_COLLECTION_HEAD_AUTHORITY_MISMATCH")
    if (
        manifest.task_access_protected_manifest_sha256
        != PROTECTED_TASK_ACCESS_SHA256
    ):
        raise SystemExit("STOP=SOURCE_COLLECTION_ACCESS_AUTHORITY_MISMATCH")
    if manifest.performance_estimand != NO_PERFORMANCE_ESTIMAND:
        raise SystemExit("STOP=SOURCE_COLLECTION_PERFORMANCE_BOUNDARY_MISMATCH")

    runtime, runtime_raw = _load_canonical_json(Path(args.runtime_binding))
    if sha256_bytes(runtime_raw) != manifest.runtime_binding_sha256:
        raise SystemExit("STOP=SOURCE_COLLECTION_RUNTIME_BINDING_SHA_MISMATCH")
    if runtime["performance_estimand"] != NO_PERFORMANCE_ESTIMAND:
        raise SystemExit("STOP=RUNTIME_BINDING_PERFORMANCE_BOUNDARY_MISMATCH")

    policy_identity = manifest.policy_identity
    compare = {
        "logical_condition_id": runtime["logical_condition_id"],
        "checkpoint_instance_id": runtime["checkpoint_instance_id"],
        "training_seed": runtime["training_seed"],
        "served_model_name": runtime["served_model_name"],
        "adapter_bundle_sha256": runtime["adapter_bundle_sha256"],
        "policy_runtime_manifest_sha256": runtime[
            "policy_runtime_manifest_sha256"
        ],
        "server_runtime_manifest_sha256": runtime[
            "server_runtime_manifest_sha256"
        ],
        "raw_protocol_sha256": runtime["raw_protocol_sha256"],
        "policy_request_schema_sha256": runtime[
            "policy_request_schema_sha256"
        ],
        "memory_mode": "MEMORY_OFF_M0",
        "harness_mode": "HARNESS_OFF",
        "request_kind": "R0",
    }
    if policy_identity.to_dict() != compare:
        raise SystemExit("STOP=SOURCE_COLLECTION_POLICY_IDENTITY_MISMATCH")

    output_root = Path(args.output_root)
    if output_root.is_symlink():
        raise SystemExit("STOP=SOURCE_COLLECTION_OUTPUT_SYMLINK")
    output_root.mkdir(parents=True, exist_ok=True)
    if not output_root.is_dir():
        raise SystemExit("STOP=SOURCE_COLLECTION_OUTPUT_INVALID")

    evidence_root = output_root / "evaluator_run"
    evidence_root.mkdir(parents=True, exist_ok=True)
    ledger_path = output_root / "source_collection_ledger.jsonl"

    attempt_auditor = _load_materializer(repo_root)
    receipts = read_source_collection_ledger_v1(ledger_path)
    _audit_existing_prefix(
        manifest=manifest,
        receipts=receipts,
        run_root=evidence_root,
        attempt_auditor=attempt_auditor,
    )

    # A crash/disconnect may leave a scientifically valid contiguous prefix
    # inside a batch. Resume from the next frozen panel entry and finish that
    # same batch before inspecting outcomes. This preserves the batch-complete
    # stopping contract without re-running already published cases.
    prefix_inside_batch = (
        len(receipts) != len(manifest.entries)
        and len(receipts) % SOURCE_BATCH_SIZE != 0
    )

    initial_decision = (
        "CONTINUE"
        if prefix_inside_batch
        else stopping_decision_after_complete_prefix_v1(
            receipts,
            panel_size=len(manifest.entries),
        )
    )
    if initial_decision != "CONTINUE":
        _write_collection_closure(
            output_root=output_root,
            manifest=manifest,
            receipts=receipts,
            stopping_reason=initial_decision,
        )
        print("SOURCE_COLLECTION_ALREADY_COMPLETE=true")
        print("SOURCE_COLLECTION_STOPPING_REASON=" + initial_decision)
        print("NO_PERFORMANCE_ESTIMAND")
        return 0

    profile = PolicyExecutionProfileV1(
        profile_id="FAILURE_MEMORY_SOURCE_COLLECTION_R0_V1",
        arm_id=policy_identity.logical_condition_id,
        policy_version="PI1_BAD",
        request_kind="R0",
        requires_diagnostic_policy_call_evidence=True,
        requires_current_admissible_commands=False,
        served_model_name=policy_identity.served_model_name,
    )

    prompt_renderer = LocalTokenizerPromptRenderer(
        model_path=runtime["base_model_local_path"],
        revision=runtime["base_model_revision"],
        chat_template_sha256=runtime["chat_template_sha256"],
        tokenizer_factory=HuggingFaceTokenizerFactory(),
    )

    policy_client = PolicyClient(
        transport=HttpPolicyTransport(
            base_url=args.policy_base_url,
            timeout_seconds=args.timeout_seconds,
        )
    )
    publisher = ArtifactPublisher(run_root=evidence_root)

    run_id = (
        "failure-memory-source-collection-v1-"
        + manifest.panel_manifest_sha256[:16]
    )

    while True:
        receipts = read_source_collection_ledger_v1(ledger_path)
        start = len(receipts)
        if start >= len(manifest.entries):
            decision = "STOP_PANEL_EXHAUSTED"
            break

        current_batch = start // SOURCE_BATCH_SIZE
        batch_end = min(
            (current_batch + 1) * SOURCE_BATCH_SIZE,
            len(manifest.entries),
        )
        if current_batch != manifest.entries[start].batch_index:
            raise SystemExit("STOP=SOURCE_BATCH_IDENTITY_MISMATCH")

        print(
            "SOURCE_COLLECTION_BATCH_START="
            + str(manifest.entries[start].batch_index)
            + " panel_indices="
            + str(start)
            + ".."
            + str(batch_end - 1)
        )

        for panel_index in range(start, batch_end):
            entry = manifest.entries[panel_index]
            gamefile = Path(entry.absolute_gamefile)
            if gamefile.is_symlink() or not gamefile.is_file():
                raise SystemExit(
                    "STOP=SOURCE_COLLECTION_GAMEFILE_INVALID:"
                    + str(panel_index)
                )
            if sha256_file(gamefile) != entry.gamefile_sha256:
                raise SystemExit(
                    "STOP=SOURCE_COLLECTION_GAMEFILE_SHA_MISMATCH:"
                    + str(panel_index)
                )

            task_id = _task_id(entry)
            cell_id = scheduled_cell_id(
                task_index=panel_index,
                seed=17,
            )
            cell = ScheduledCell(
                scheduled_cell_id=cell_id,
                task_index=panel_index,
                task_id=task_id,
                seed=17,
            )
            attempt_id = execution_attempt_id(
                scheduled_cell_id=cell_id,
                attempt_ordinal=0,
            )

            task_root = gamefile.parent
            task = FrozenTaskRecord(
                index=panel_index,
                task_id=task_id,
                split="train",
                task_type=entry.task_type,
                gamefile=str(gamefile),
                gamefile_sha1=_sha1_file(gamefile),
                root=str(task_root),
                traj_file=str(_traj_file_for_gamefile(gamefile)),
            )

            environment = SpawnedAlfworldAdapter.start(
                exact_gamefile=gamefile,
                registration_id=(
                    "fm-source-"
                    + manifest.panel_manifest_sha256[:8]
                    + "-"
                    + f"{panel_index:04d}"
                ),
                runtime_manifest_sha256=runtime[
                    "environment_runtime_manifest_sha256"
                ],
            )

            config = EpisodeExecutionConfig(
                run_id=run_id,
                cell=cell,
                execution_attempt_id=attempt_id,
                attempt_ordinal=0,
                task=task,
                seed=17,
                evaluator_commit=observed_head,
                design_merge_commit=observed_head,
                runtime_core_commit=runtime["formal_runtime_core_commit"],
                raw_protocol_sha256=runtime["raw_protocol_sha256"],
                split_access_sha256=PROTECTED_TASK_ACCESS_SHA256,
                gamefile_identity_manifest_sha256=(
                    manifest.panel_manifest_sha256
                ),
                environment_runtime_manifest_sha256=runtime[
                    "environment_runtime_manifest_sha256"
                ],
                policy_runtime_manifest_sha256=runtime[
                    "policy_runtime_manifest_sha256"
                ],
                policy_request_schema_sha256=runtime[
                    "policy_request_schema_sha256"
                ],
                run_schedule_sha256=manifest.panel_manifest_sha256,
                gamefile_sha256=entry.gamefile_sha256,
            )

            result = run_single_episode(
                config=config,
                dependencies=EpisodeDependencies(
                    environment=environment,
                    policy_client=policy_client,
                    prompt_renderer=prompt_renderer,
                    artifact_publisher=publisher,
                    policy_execution_profile=profile,
                ),
            )

            if result.attempt_bundle is None:
                raise SystemExit(
                    "STOP=SOURCE_COLLECTION_NO_IMMUTABLE_BUNDLE:"
                    + str(panel_index)
                    + ":"
                    + result.termination_reason
                )
            if result.success is None:
                raise SystemExit(
                    "STOP=SOURCE_COLLECTION_NO_SCIENTIFIC_OUTCOME:"
                    + str(panel_index)
                )
            if result.operational_finalization_status.value != "PUBLISHED":
                raise SystemExit(
                    "STOP=SOURCE_COLLECTION_NOT_CLEANLY_PUBLISHED:"
                    + str(panel_index)
                    + ":"
                    + result.operational_finalization_status.value
                )

            published_attempt = evidence_root / "attempts" / attempt_id
            loaded = attempt_auditor.load_attempt_directory_v1(
                published_attempt
            )
            if (
                loaded.attempt_bundle.attempt_bundle_sha256
                != result.attempt_bundle.attempt_bundle_sha256
            ):
                raise SystemExit(
                    "STOP=SOURCE_COLLECTION_PUBLISHED_BUNDLE_MISMATCH:"
                    + str(panel_index)
                )

            existing = read_source_collection_ledger_v1(ledger_path)
            previous = None if not existing else existing[-1].receipt_sha256
            receipt = SourceCollectionCaseReceiptV1(
                schema_id=SOURCE_CASE_RECEIPT_V1,
                schema_version=1,
                panel_manifest_sha256=manifest.panel_manifest_sha256,
                panel_index=panel_index,
                batch_index=entry.batch_index,
                task_access_record_line_index=(
                    entry.task_access_record_line_index
                ),
                task_access_record_sha256=entry.task_access_record_sha256,
                task_gamefile_group_id=entry.task_gamefile_group_id,
                source_task_id=task_id,
                execution_attempt_id=attempt_id,
                attempt_bundle_sha256=(
                    result.attempt_bundle.attempt_bundle_sha256
                ),
                scientific_outcome_status=(
                    result.scientific_outcome_status.value
                ),
                success=bool(result.success),
                termination_reason=result.termination_reason,
                outcome_use=OUTCOME_USE,
                performance_estimand=NO_PERFORMANCE_ESTIMAND,
                previous_receipt_sha256=previous,
                receipt_sha256=None,
            )
            append_source_collection_receipt_v1(
                path=ledger_path,
                receipt=receipt,
            )

            print(
                "SOURCE_CASE_PUBLISHED"
                + " panel_index="
                + str(panel_index)
                + " task_type="
                + entry.task_type
                + " receipt_sha256="
                + receipt.receipt_sha256
                + " performance_estimand="
                + NO_PERFORMANCE_ESTIMAND
            )

        # Only now, after every case in the complete batch was preserved, may
        # outcomes be inspected for the pre-frozen stopping condition.
        receipts = read_source_collection_ledger_v1(ledger_path)
        decision = stopping_decision_after_complete_prefix_v1(
            receipts,
            panel_size=len(manifest.entries),
        )
        print(
            "SOURCE_COLLECTION_COMPLETE_BATCH_DECISION="
            + decision
            + " executed_case_count="
            + str(len(receipts))
            + " performance_estimand="
            + NO_PERFORMANCE_ESTIMAND
        )
        if decision != "CONTINUE":
            break

    receipts = read_source_collection_ledger_v1(ledger_path)
    _audit_existing_prefix(
        manifest=manifest,
        receipts=receipts,
        run_root=evidence_root,
        attempt_auditor=attempt_auditor,
    )
    _write_collection_closure(
        output_root=output_root,
        manifest=manifest,
        receipts=receipts,
        stopping_reason=decision,
    )

    print("SOURCE_COLLECTION_EXECUTED_CASE_COUNT=" + str(len(receipts)))
    print("SOURCE_COLLECTION_STOPPING_REASON=" + decision)
    print("SOURCE_COLLECTION_ALL_EXECUTED_CASES_PRESERVED=true")
    print("SOURCE_COLLECTION_SELECTED_FAILURE_PANEL_IS_REFERENCE_ONLY=true")
    print("SOURCE_COLLECTION_BENCHMARK_TABLE_ELIGIBLE=false")
    print("SOURCE_COLLECTION_PI1_PERFORMANCE_CLAIM_ELIGIBLE=false")
    print("SOURCE_COLLECTION_MODEL_SELECTION_ELIGIBLE=false")
    print("NO_PERFORMANCE_ESTIMAND")
    print("FAILURE_MEMORY_SOURCE_COLLECTION_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

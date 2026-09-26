#!/usr/bin/env python3
"""Extend frozen π1 train-side evidence for token-budget calibration only.

This runner never performs Memory-ON execution and never computes a performance
estimand. It reuses all already-executed source cases, continues the same frozen
2367-task panel in complete 12-case batches, and stops after a complete batch
once at least 30 total failures exist.
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
    SOURCE_BATCH_SIZE,
    SourcePanelManifestV1,
    read_source_collection_ledger_v1,
)
from pchsi.memory.token_budget_contract import (
    CALIBRATION_FAILURE_TARGET_V1,
)


CONTEXT = "FAILURE_MEMORY_TOKEN_BUDGET_CALIBRATION_SOURCE_V1"
OUTCOME_USE = "FAILURE_SELECTION_ONLY_NO_PERFORMANCE_ESTIMAND"


def _load_materializer(repo_root: Path):
    path = (
        repo_root
        / "scripts/memory/materialize_sequence_failure_experience_v1.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_token_budget_source_attempt_loader",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load attempt auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


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
    return gamefile


def _task_id(entry) -> str:
    return (
        "failure_memory_train_source_"
        + entry.task_gamefile_group_id[:24]
    )


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        count = os.write(fd, view)
        if count <= 0:
            raise OSError("os.write made no progress")
        view = view[count:]


def _append_line(path: Path, payload: dict[str, object]) -> None:
    data = canonical_json_bytes(payload)
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600,
    )
    try:
        _write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_extension(path: Path) -> tuple[dict[str, object], ...]:
    if not path.exists():
        return ()
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError("calibration extension ledger lacks terminal LF")
    rows = tuple(
        strict_json_loads(line)
        for line in raw.splitlines(keepends=True)
        if line.strip()
    )
    if any(not isinstance(item, dict) for item in rows):
        raise ValueError("calibration extension ledger row must be object")
    return rows


def _failure_refs(
    *,
    original_receipts,
    original_attempt_root: Path,
    extension_receipts,
    extension_attempt_root: Path,
) -> tuple[dict[str, object], ...]:
    refs = []

    for receipt in original_receipts:
        if receipt.success is False:
            refs.append(
                {
                    "panel_index": receipt.panel_index,
                    "execution_attempt_id": receipt.execution_attempt_id,
                    "attempt_bundle_sha256": receipt.attempt_bundle_sha256,
                    "attempt_directory": str(
                        original_attempt_root
                        / receipt.execution_attempt_id
                    ),
                    "source": "SEALED_SOURCE_COLLECTION_REUSE",
                }
            )

    for receipt in extension_receipts:
        if receipt["success"] is False:
            refs.append(
                {
                    "panel_index": receipt["panel_index"],
                    "execution_attempt_id": receipt[
                        "execution_attempt_id"
                    ],
                    "attempt_bundle_sha256": receipt[
                        "attempt_bundle_sha256"
                    ],
                    "attempt_directory": str(
                        extension_attempt_root
                        / receipt["execution_attempt_id"]
                    ),
                    "source": "TOKEN_BUDGET_CALIBRATION_EXTENSION",
                }
            )

    refs.sort(
        key=lambda item: (
            item["panel_index"],
            item["execution_attempt_id"],
        )
    )
    return tuple(refs)


def _write_failure_panel(
    *,
    output_root: Path,
    panel_manifest_sha256: str,
    refs: tuple[dict[str, object], ...],
) -> None:
    if len(refs) < CALIBRATION_FAILURE_TARGET_V1:
        raise ValueError("insufficient failures for calibration panel")

    selected = refs[:CALIBRATION_FAILURE_TARGET_V1]
    payload = {
        "schema_id": "FAILURE_MEMORY_TOKEN_BUDGET_FAILURE_PANEL_V1",
        "schema_version": 1,
        "selection_rule": (
            "FIRST_30_FAILURES_IN_PRE_FROZEN_TRAIN_MEMORY_SOURCE_PANEL_ORDER_V1"
        ),
        "source_panel_manifest_sha256": panel_manifest_sha256,
        "failure_count": CALIBRATION_FAILURE_TARGET_V1,
        "failures": list(selected),
        "performance_estimand": NO_PERFORMANCE_ESTIMAND,
        "memory_on_execution_used": False,
    }
    raw = canonical_json_bytes(payload)
    target = output_root / "calibration_failure_panel.json"
    if target.exists():
        observed = target.read_bytes()
        if observed != raw:
            raise ValueError("existing calibration failure panel mismatch")
        return
    target.write_bytes(raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--panel-manifest", required=True)
    parser.add_argument("--runtime-binding", required=True)
    parser.add_argument("--original-source-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--policy-base-url",
        default="http://127.0.0.1:18080",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120.0,
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    checked_out = subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        text=True,
    ).strip()

    panel_path = Path(args.panel_manifest)
    panel = SourcePanelManifestV1.from_json(
        panel_path.read_bytes()
    )
    runtime = _load_json(Path(args.runtime_binding))

    if panel.performance_estimand != NO_PERFORMANCE_ESTIMAND:
        raise SystemExit("STOP=CALIBRATION_SOURCE_PANEL_HAS_ESTIMAND")
    if runtime.get("performance_estimand") != NO_PERFORMANCE_ESTIMAND:
        raise SystemExit("STOP=CALIBRATION_RUNTIME_HAS_ESTIMAND")
    if runtime.get("memory_mode") != "MEMORY_OFF_M0":
        raise SystemExit("STOP=CALIBRATION_RUNTIME_MEMORY_NOT_OFF")
    if runtime.get("harness_mode") != "HARNESS_OFF":
        raise SystemExit("STOP=CALIBRATION_RUNTIME_HARNESS_NOT_OFF")

    original_root = Path(args.original_source_root).resolve()
    original_ledger_path = (
        original_root
        / "source_collection_ledger.jsonl"
    )
    original_receipts = read_source_collection_ledger_v1(
        original_ledger_path
    )
    if not original_receipts:
        raise SystemExit("STOP=ORIGINAL_SOURCE_LEDGER_EMPTY")

    # The sealed source collection must be a complete contiguous prefix.
    if tuple(
        receipt.panel_index
        for receipt in original_receipts
    ) != tuple(range(len(original_receipts))):
        raise SystemExit("STOP=ORIGINAL_SOURCE_LEDGER_NOT_CONTIGUOUS")

    attempt_loader = _load_materializer(repo_root)
    original_attempt_root = (
        original_root
        / "evaluator_run"
        / "attempts"
    )
    for receipt in original_receipts:
        loaded = attempt_loader.load_attempt_directory_v1(
            original_attempt_root
            / receipt.execution_attempt_id
        )
        if (
            loaded.attempt_bundle.attempt_bundle_sha256
            != receipt.attempt_bundle_sha256
        ):
            raise SystemExit(
                "STOP=ORIGINAL_SOURCE_ATTEMPT_BUNDLE_MISMATCH"
            )

    output_root = Path(args.output_root).resolve()
    if output_root.is_symlink():
        raise SystemExit("STOP=CALIBRATION_OUTPUT_ROOT_SYMLINK")
    output_root.mkdir(parents=True, exist_ok=True)

    extension_run_root = output_root / "evaluator_run"
    extension_run_root.mkdir(parents=True, exist_ok=True)
    extension_attempt_root = (
        extension_run_root
        / "attempts"
    )
    extension_ledger = (
        output_root
        / "calibration_extension_ledger.jsonl"
    )

    extension_receipts = _read_extension(extension_ledger)

    expected_panel_index = len(original_receipts)
    for row in extension_receipts:
        if row.get("panel_index") != expected_panel_index:
            raise SystemExit(
                "STOP=CALIBRATION_EXTENSION_LEDGER_NOT_CONTIGUOUS"
            )
        attempt_id = row["execution_attempt_id"]
        loaded = attempt_loader.load_attempt_directory_v1(
            extension_attempt_root / attempt_id
        )
        if (
            loaded.attempt_bundle.attempt_bundle_sha256
            != row["attempt_bundle_sha256"]
        ):
            raise SystemExit(
                "STOP=CALIBRATION_EXTENSION_BUNDLE_MISMATCH"
            )
        expected_panel_index += 1

    failure_refs = _failure_refs(
        original_receipts=original_receipts,
        original_attempt_root=original_attempt_root,
        extension_receipts=extension_receipts,
        extension_attempt_root=extension_attempt_root,
    )

    if len(failure_refs) >= CALIBRATION_FAILURE_TARGET_V1:
        _write_failure_panel(
            output_root=output_root,
            panel_manifest_sha256=panel.panel_manifest_sha256,
            refs=failure_refs,
        )
        print(
            "TOKEN_BUDGET_CALIBRATION_FAILURE_TARGET_ALREADY_REACHED="
            + str(len(failure_refs))
        )
        print("NO_PERFORMANCE_ESTIMAND")
        return 0

    policy_identity = panel.policy_identity
    profile = PolicyExecutionProfileV1(
        profile_id="FAILURE_MEMORY_TOKEN_BUDGET_CALIBRATION_R0_V1",
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
    publisher = ArtifactPublisher(
        run_root=extension_run_root
    )

    run_id = (
        "failure-memory-token-budget-calibration-v1-"
        + panel.panel_manifest_sha256[:16]
    )

    while True:
        extension_receipts = _read_extension(extension_ledger)
        start = len(original_receipts) + len(extension_receipts)

        failure_refs = _failure_refs(
            original_receipts=original_receipts,
            original_attempt_root=original_attempt_root,
            extension_receipts=extension_receipts,
            extension_attempt_root=extension_attempt_root,
        )

        if (
            len(failure_refs) >= CALIBRATION_FAILURE_TARGET_V1
            and start % SOURCE_BATCH_SIZE == 0
        ):
            break

        if start >= len(panel.entries):
            raise SystemExit(
                "STOP=CALIBRATION_SOURCE_PANEL_EXHAUSTED_BEFORE_30_FAILURES"
            )

        current_batch = start // SOURCE_BATCH_SIZE
        batch_end = min(
            (current_batch + 1) * SOURCE_BATCH_SIZE,
            len(panel.entries),
        )

        print(
            "TOKEN_BUDGET_CALIBRATION_BATCH_START="
            + str(current_batch)
            + " panel_indices="
            + str(start)
            + ".."
            + str(batch_end - 1)
        )

        for panel_index in range(start, batch_end):
            entry = panel.entries[panel_index]
            gamefile = Path(entry.absolute_gamefile)
            if gamefile.is_symlink() or not gamefile.is_file():
                raise SystemExit(
                    "STOP=CALIBRATION_GAMEFILE_INVALID:"
                    + str(panel_index)
                )
            if sha256_file(gamefile) != entry.gamefile_sha256:
                raise SystemExit(
                    "STOP=CALIBRATION_GAMEFILE_SHA_MISMATCH:"
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

            task = FrozenTaskRecord(
                index=panel_index,
                task_id=task_id,
                split="train",
                task_type=entry.task_type,
                gamefile=str(gamefile),
                gamefile_sha1=_sha1_file(gamefile),
                root=str(gamefile.parent),
                traj_file=str(
                    _traj_file_for_gamefile(gamefile)
                ),
            )

            environment = SpawnedAlfworldAdapter.start(
                exact_gamefile=gamefile,
                registration_id=(
                    "fm-token-budget-"
                    + panel.panel_manifest_sha256[:8]
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
                evaluator_commit=checked_out,
                design_merge_commit=checked_out,
                runtime_core_commit=runtime[
                    "formal_runtime_core_commit"
                ],
                raw_protocol_sha256=runtime[
                    "raw_protocol_sha256"
                ],
                split_access_sha256=(
                    panel.task_access_protected_manifest_sha256
                ),
                gamefile_identity_manifest_sha256=(
                    panel.panel_manifest_sha256
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
                run_schedule_sha256=panel.panel_manifest_sha256,
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
                    "STOP=CALIBRATION_NO_ATTEMPT_BUNDLE:"
                    + str(panel_index)
                )
            if result.success is None:
                raise SystemExit(
                    "STOP=CALIBRATION_NO_SCIENTIFIC_OUTCOME:"
                    + str(panel_index)
                )
            if (
                result.operational_finalization_status.value
                != "PUBLISHED"
            ):
                raise SystemExit(
                    "STOP=CALIBRATION_ATTEMPT_NOT_PUBLISHED:"
                    + str(panel_index)
                )

            loaded = attempt_loader.load_attempt_directory_v1(
                extension_attempt_root / attempt_id
            )
            if (
                loaded.attempt_bundle.attempt_bundle_sha256
                != result.attempt_bundle.attempt_bundle_sha256
            ):
                raise SystemExit(
                    "STOP=CALIBRATION_PUBLISHED_BUNDLE_MISMATCH:"
                    + str(panel_index)
                )

            receipt = {
                "schema_id": (
                    "FAILURE_MEMORY_TOKEN_BUDGET_CALIBRATION_CASE_V1"
                ),
                "schema_version": 1,
                "context": CONTEXT,
                "panel_manifest_sha256": panel.panel_manifest_sha256,
                "panel_index": panel_index,
                "batch_index": current_batch,
                "execution_attempt_id": attempt_id,
                "attempt_bundle_sha256": (
                    result.attempt_bundle.attempt_bundle_sha256
                ),
                "success": bool(result.success),
                "termination_reason": result.termination_reason,
                "outcome_use": OUTCOME_USE,
                "performance_estimand": NO_PERFORMANCE_ESTIMAND,
                "memory_mode": "MEMORY_OFF_M0",
                "harness_mode": "HARNESS_OFF",
            }
            _append_line(extension_ledger, receipt)

        # Only inspect failure count after the complete batch is published.
        extension_receipts = _read_extension(extension_ledger)
        failure_refs = _failure_refs(
            original_receipts=original_receipts,
            original_attempt_root=original_attempt_root,
            extension_receipts=extension_receipts,
            extension_attempt_root=extension_attempt_root,
        )

        print(
            "TOKEN_BUDGET_CALIBRATION_COMPLETE_BATCH"
            + " executed_extension_cases="
            + str(len(extension_receipts))
            + " stopping_failure_count="
            + str(len(failure_refs))
            + " performance_estimand="
            + NO_PERFORMANCE_ESTIMAND
        )

    _write_failure_panel(
        output_root=output_root,
        panel_manifest_sha256=panel.panel_manifest_sha256,
        refs=failure_refs,
    )

    closure = {
        "schema_id": "FAILURE_MEMORY_TOKEN_BUDGET_SOURCE_CLOSURE_V1",
        "schema_version": 1,
        "context": CONTEXT,
        "source_panel_manifest_sha256": panel.panel_manifest_sha256,
        "original_source_case_count": len(original_receipts),
        "extension_case_count": len(
            _read_extension(extension_ledger)
        ),
        "selected_failure_count": CALIBRATION_FAILURE_TARGET_V1,
        "selection_rule": (
            "FIRST_30_FAILURES_IN_PRE_FROZEN_TRAIN_MEMORY_SOURCE_PANEL_ORDER_V1"
        ),
        "outcome_use": OUTCOME_USE,
        "performance_estimand": NO_PERFORMANCE_ESTIMAND,
        "memory_on_execution_used": False,
        "benchmark_table_eligible": False,
        "policy_performance_claim_eligible": False,
        "model_selection_eligible": False,
    }
    (output_root / "calibration_source_closure.json").write_bytes(
        canonical_json_bytes(closure)
    )

    print("TOKEN_BUDGET_CALIBRATION_FAILURE_PANEL_COUNT=30")
    print("TOKEN_BUDGET_CALIBRATION_ALL_EXECUTED_CASES_PRESERVED=true")
    print("NO_PERFORMANCE_ESTIMAND")
    print("TOKEN_BUDGET_CALIBRATION_SOURCE_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

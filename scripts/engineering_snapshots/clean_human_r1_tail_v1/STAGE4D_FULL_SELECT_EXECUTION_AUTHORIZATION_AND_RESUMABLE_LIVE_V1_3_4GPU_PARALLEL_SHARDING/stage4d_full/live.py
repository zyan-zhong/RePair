from __future__ import annotations

import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import types as pytypes
from typing import Any

from .contract import (
    CONDITION_ORDER,
    EXPECTED_I1_REQUEST_SCHEMA_SHA256,
    EXPECTED_LEGACY_LIVE_RUNNER_SHA256,
    EXPECTED_PAIR_CELLS,
    EXPECTED_TOTAL_CELLS,
    LEGACY_LIVE_RUNNER_RELATIVE,
    LEGACY_PACKAGE_PARENT_RELATIVE,
    Stage4DFullError,
    canonical_json_bytes,
    load_json,
    require_sha,
    sha256_file,
)
from .parallel import PARALLEL_SHARD_COUNT, partition_ordinals, remaining_ordinals, shard_for_ordinal


def _load_adapted_legacy_live_runner(code_worktree: Path):
    legacy_parent = code_worktree / LEGACY_PACKAGE_PARENT_RELATIVE
    if str(legacy_parent) not in sys.path:
        sys.path.insert(0, str(legacy_parent))
    importlib.import_module("stage0")
    path = code_worktree / LEGACY_LIVE_RUNNER_RELATIVE
    require_sha(path, EXPECTED_LEGACY_LIVE_RUNNER_SHA256, "LEGACY_LIVE_RUNNER")
    source = path.read_text(encoding="utf-8")
    replacements = {
        '"human-stage0-"': '"stage4d-select-"',
        'run_id="human-pilot-stage0-" + label.lower()': 'run_id="stage4d-full-select-" + label.lower()',
    }
    for old, new in replacements.items():
        if source.count(old) != 1:
            raise Stage4DFullError(f"LEGACY_ADAPTER_REPLACEMENT_COUNT_CHANGED:{old}")
        source = source.replace(old, new, 1)
    name = "stage0.live_runner_stage4d_exact_adapter"
    module = pytypes.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = "stage0"
    sys.modules[name] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def _load_repo_types(code_worktree: Path) -> dict[str, Any]:
    if str(code_worktree / "src") not in sys.path:
        sys.path.insert(0, str(code_worktree / "src"))
    from pchsi.evaluation.canonical_evidence import canonical_json_bytes as repo_canonical_json_bytes, sha256_bytes
    from pchsi.evaluation.condition_run_schedule import ConditionRunScheduleV1
    from pchsi.evaluation.distillation_access import TaskAccessManifestV1
    from pchsi.evaluation.distillation_governance import canonical_model_sha256
    from pchsi.evaluation.policy_condition import PolicyConditionManifestV1
    from pchsi.evaluation.select_execution_identity import (
        build_select_i1_execution_profile,
        validate_select_execution_profile_binding,
    )
    from pchsi.evaluation.select_policy_runtime import SelectPolicyRuntimeManifestV1
    return locals()


def _prepare_live_context(*, execution_root: Path, binding_root: Path) -> dict[str, Any]:
    identity = load_json(execution_root / "EXECUTION_IDENTITY_V1.json")
    code_worktree = Path(identity["code_worktree"])
    inputs = load_json(binding_root / "BINDING_INPUTS.json")
    types = _load_repo_types(code_worktree)
    legacy = _load_adapted_legacy_live_runner(code_worktree)
    legacy.GENERIC_WORKTREE = code_worktree
    legacy.BASE_MODEL_PATH = Path(inputs["base_model_path"])
    task_access_path = binding_root / "CLEAN_SELECT_TASK_ACCESS_MANIFEST_V1.json"
    legacy.TASK_ACCESS_SHA256 = sha256_file(task_access_path)
    legacy_types = legacy._load_repo_types()

    def build_i1(identity_value):
        return types["build_select_i1_execution_profile"](
            identity_value,
            request_contract_sha256=EXPECTED_I1_REQUEST_SCHEMA_SHA256,
        )

    def validate_i1(*, identity, profile):
        return types["validate_select_execution_profile_binding"](
            identity=identity,
            profile=profile,
            expected_request_schema_sha256=EXPECTED_I1_REQUEST_SCHEMA_SHA256,
        )

    legacy_types["build_select_execution_profile"] = build_i1
    legacy_types["validate_select_execution_profile_binding"] = validate_i1

    task_access = types["TaskAccessManifestV1"].from_json(task_access_path.read_bytes())
    access_by_index = {row.manifest_index: row for row in task_access.records}
    attempt_auditor = legacy._load_attempt_auditor(code_worktree)

    bundles: dict[str, tuple[Any, ...]] = {}
    for label in CONDITION_ORDER:
        condition = types["PolicyConditionManifestV1"].from_dict(
            load_json(binding_root / f"{label}_POLICY_CONDITION_MANIFEST_V1.json")
        )
        runtime = types["SelectPolicyRuntimeManifestV1"].from_dict(
            load_json(binding_root / f"{label}_SELECT_POLICY_RUNTIME_MANIFEST_V1.json")
        )
        schedule = types["ConditionRunScheduleV1"].from_dict(
            load_json(binding_root / f"{label}_CONDITION_RUN_SCHEDULE_V1.json")
        )
        condition_sha = types["canonical_model_sha256"](condition)
        runtime_sha = types["sha256_bytes"](types["repo_canonical_json_bytes"](runtime.to_dict()))
        schedule_sha = types["canonical_model_sha256"](schedule)
        bundles[label] = (condition, runtime, schedule, condition_sha, runtime_sha, schedule_sha)

    t0_grid = [(c.manifest_index, c.task_id, c.seed) for c in bundles["T0"][2].cells]
    t2_grid = [(c.manifest_index, c.task_id, c.seed) for c in bundles["T2"][2].cells]
    if t0_grid != t2_grid or len(t0_grid) != EXPECTED_PAIR_CELLS:
        raise Stage4DFullError("LIVE_T0_T2_GRID_CHANGED")

    t0_condition = bundles["T0"][0]
    preflight = {
        "environment_runtime_manifest_sha256": sha256_file(binding_root / "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1.json"),
        "base_model_revision": inputs["base_model_revision"],
        "chat_template_sha256": t0_condition.chat_template_sha256,
        "evaluator_commit": t0_condition.evaluator_commit,
        "design_merge_commit": inputs["fixed_head"],
        "runtime_core_commit": t0_condition.runtime_core_commit,
        "raw_protocol_sha256": t0_condition.raw_protocol_sha256,
        "gamefile_identity_manifest_sha256": sha256_file(binding_root / "CLEAN_SELECT_GAMEFILE_IDENTITY_MANIFEST_V1.json"),
        "policy_request_schema_sha256": inputs["policy_request_schema_sha256"],
    }
    return {
        "code_worktree": code_worktree,
        "inputs": inputs,
        "types": types,
        "legacy": legacy,
        "legacy_types": legacy_types,
        "access_by_index": access_by_index,
        "attempt_auditor": attempt_auditor,
        "bundles": bundles,
        "preflight": preflight,
    }


def _validate_canonical_row(*, row: dict[str, Any], cell, label: str, ordinal: int) -> None:
    if row.get("condition_cell_id") != cell.condition_cell_id:
        raise Stage4DFullError(f"CANONICAL_RECEIPT_CELL_CHANGED:label={label}:ordinal={ordinal}")
    if row.get("manifest_index") != cell.manifest_index or row.get("task_id") != cell.task_id or row.get("seed") != cell.seed:
        raise Stage4DFullError(f"CANONICAL_RECEIPT_GRID_CHANGED:label={label}:ordinal={ordinal}")
    if row.get("memory_state") != "OFF" or row.get("harness_state") != "OFF":
        raise Stage4DFullError(f"CANONICAL_RECEIPT_OFF_OFF_CHANGED:label={label}:ordinal={ordinal}")


def _canonical_prefix(*, execution_root: Path, context: dict[str, Any]) -> int:
    legacy = context["legacy"]
    bundles = context["bundles"]
    run_root = execution_root / "execution"
    t0 = legacy.load_receipts(run_root / "t0/cell_receipts.jsonl")
    t2 = legacy.load_receipts(run_root / "t2/cell_receipts.jsonl")
    if len(t0) > EXPECTED_PAIR_CELLS or len(t2) > EXPECTED_PAIR_CELLS:
        raise Stage4DFullError("CANONICAL_PREFIX_EXCEEDS_AUTHORITY")
    common = min(len(t0), len(t2))
    for ordinal in range(common):
        _validate_canonical_row(row=t0[ordinal], cell=bundles["T0"][2].cells[ordinal], label="T0", ordinal=ordinal)
        _validate_canonical_row(row=t2[ordinal], cell=bundles["T2"][2].cells[ordinal], label="T2", ordinal=ordinal)
    if len(t0) == len(t2):
        return common
    # Canonical consolidation appends T0 then T2. A crash between those two
    # appends is recoverable, but no other asymmetric state is accepted.
    if len(t0) == len(t2) + 1:
        ordinal = len(t2)
        _validate_canonical_row(row=t0[ordinal], cell=bundles["T0"][2].cells[ordinal], label="T0", ordinal=ordinal)
        return common
    raise Stage4DFullError("CANONICAL_T0_T2_PREFIX_LENGTH_MISMATCH")


def canonical_completed_prefix(*, execution_root: Path, binding_root: Path) -> int:
    return _canonical_prefix(
        execution_root=execution_root,
        context=_prepare_live_context(execution_root=execution_root, binding_root=binding_root),
    )


def _shard_root(execution_root: Path, shard_id: int) -> Path:
    return execution_root / "parallel_v1" / f"shard_{shard_id}"


def execute_shard(
    *,
    execution_root: Path,
    binding_root: Path,
    base_url: str,
    shard_id: int,
    completed_prefix_count: int,
    stop_before_monotonic: float | None,
) -> dict[str, Any]:
    if shard_id not in range(PARALLEL_SHARD_COUNT):
        raise Stage4DFullError("PARALLEL_SHARD_ID_INVALID")
    context = _prepare_live_context(execution_root=execution_root, binding_root=binding_root)
    canonical_prefix = _canonical_prefix(execution_root=execution_root, context=context)
    if canonical_prefix != completed_prefix_count:
        raise Stage4DFullError(
            f"PARALLEL_CANONICAL_PREFIX_CHANGED:expected={completed_prefix_count}:observed={canonical_prefix}"
        )
    legacy = context["legacy"]
    bundles = context["bundles"]
    shard_root = _shard_root(execution_root, shard_id)
    run_root = shard_root / "execution"
    run_root.mkdir(parents=True, exist_ok=True)
    lock_path = shard_root / "shard_execution.lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Stage4DFullError(f"PARALLEL_SHARD_ALREADY_ACTIVE:{shard_id}") from exc
        assigned = partition_ordinals(
            remaining_ordinals(completed_prefix_count=completed_prefix_count, total_pairs=EXPECTED_PAIR_CELLS),
            shard_count=PARALLEL_SHARD_COUNT,
        )[shard_id]
        graceful_partial = False
        for ordinal in assigned:
            t0_cell = bundles["T0"][2].cells[ordinal]
            t2_cell = bundles["T2"][2].cells[ordinal]
            t0_existing = {row["condition_cell_id"] for row in legacy.load_receipts(run_root / "t0/cell_receipts.jsonl")}
            t2_existing = {row["condition_cell_id"] for row in legacy.load_receipts(run_root / "t2/cell_receipts.jsonl")}
            t0_done = t0_cell.condition_cell_id in t0_existing
            t2_done = t2_cell.condition_cell_id in t2_existing
            if stop_before_monotonic is not None and time.monotonic() >= stop_before_monotonic and t0_done == t2_done:
                graceful_partial = True
                break
            for label, cell in (("T0", t0_cell), ("T2", t2_cell)):
                condition, runtime, _schedule, condition_sha, runtime_sha, schedule_sha = bundles[label]
                access_record = context["access_by_index"].get(cell.manifest_index)
                if access_record is None:
                    raise Stage4DFullError("LIVE_TASK_ACCESS_RECORD_MISSING")
                receipt = legacy._recover_or_execute_cell(
                    label=label,
                    cell=cell,
                    task_access_record=access_record,
                    condition=condition,
                    runtime=runtime,
                    condition_sha=condition_sha,
                    runtime_sha=runtime_sha,
                    schedule_sha=schedule_sha,
                    preflight=context["preflight"],
                    base_url=base_url,
                    types=context["legacy_types"],
                    attempt_auditor=context["attempt_auditor"],
                    condition_root=run_root / label.lower(),
                )
                print(
                    "STAGE4D_PARALLEL_CELL_COMPLETE"
                    + " shard=" + str(shard_id)
                    + " condition=" + label
                    + " ordinal=" + str(ordinal)
                    + " task_id=" + receipt["task_id"]
                    + " seed=" + str(receipt["seed"])
                    + " success=" + str(receipt["success"]).lower()
                    + " receipt_sha256=" + receipt["receipt_sha256"],
                    flush=True,
                )
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)

    assigned = partition_ordinals(
        remaining_ordinals(completed_prefix_count=completed_prefix_count, total_pairs=EXPECTED_PAIR_CELLS),
        shard_count=PARALLEL_SHARD_COUNT,
    )[shard_id]
    t0_rows = legacy.load_receipts(run_root / "t0/cell_receipts.jsonl")
    t2_rows = legacy.load_receipts(run_root / "t2/cell_receipts.jsonl")
    assigned_t0_ids = {bundles["T0"][2].cells[o].condition_cell_id for o in assigned}
    assigned_t2_ids = {bundles["T2"][2].cells[o].condition_cell_id for o in assigned}
    t0_completed = sum(row["condition_cell_id"] in assigned_t0_ids for row in t0_rows)
    t2_completed = sum(row["condition_cell_id"] in assigned_t2_ids for row in t2_rows)
    complete = t0_completed == len(assigned) and t2_completed == len(assigned)
    return {
        "shard_id": shard_id,
        "assigned_pair_count": len(assigned),
        "t0_cell_count": t0_completed,
        "t2_cell_count": t2_completed,
        "total_condition_cell_count": t0_completed + t2_completed,
        "graceful_partial": graceful_partial,
        "complete": complete,
    }


def _tree_inventory(root: Path) -> dict[str, str]:
    if root.is_symlink() or not root.is_dir():
        raise Stage4DFullError(f"ATTEMPT_TREE_INVALID:{root}")
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise Stage4DFullError(f"ATTEMPT_TREE_SYMLINK_FORBIDDEN:{path}")
        if path.is_file():
            out[str(path.relative_to(root))] = sha256_file(path)
        elif not path.is_dir():
            raise Stage4DFullError(f"ATTEMPT_TREE_SPECIAL_FILE_FORBIDDEN:{path}")
    return out


def _copy_tree_no_clobber_exact(src: Path, dst: Path) -> None:
    source_inventory = _tree_inventory(src)
    if dst.exists():
        if _tree_inventory(dst) != source_inventory:
            raise Stage4DFullError(f"CANONICAL_ATTEMPT_TREE_CHANGED:{dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.parent / ("." + dst.name + ".stage4d_copy_tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(src, tmp, symlinks=False)
    if _tree_inventory(tmp) != source_inventory:
        shutil.rmtree(tmp)
        raise Stage4DFullError("CANONICAL_ATTEMPT_COPY_VERIFICATION_FAILED")
    try:
        os.rename(tmp, dst)
    except FileExistsError:
        shutil.rmtree(tmp)
        if _tree_inventory(dst) != source_inventory:
            raise Stage4DFullError(f"CANONICAL_ATTEMPT_TREE_RACE_CHANGED:{dst}")


def _copy_file_no_clobber_exact(src: Path, dst: Path, *, required: bool) -> None:
    if src.is_symlink():
        raise Stage4DFullError(f"ATTEMPT_METADATA_SYMLINK_FORBIDDEN:{src}")
    if not src.exists():
        if required:
            raise Stage4DFullError(f"ATTEMPT_METADATA_MISSING:{src}")
        return
    if not src.is_file():
        raise Stage4DFullError(f"ATTEMPT_METADATA_NOT_REGULAR:{src}")
    payload = src.read_bytes()
    if dst.exists():
        if dst.is_symlink() or not dst.is_file() or dst.read_bytes() != payload:
            raise Stage4DFullError(f"CANONICAL_ATTEMPT_METADATA_CHANGED:{dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write while consolidating attempt metadata")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _copy_publication_metadata(*, source_evaluator: Path, canonical_evaluator: Path, row: dict[str, Any]) -> None:
    attempt_id = row["execution_attempt_id"]
    cell_id = row["condition_cell_id"]
    _copy_file_no_clobber_exact(
        source_evaluator / "attempt_ledger" / f"{attempt_id}.started.json",
        canonical_evaluator / "attempt_ledger" / f"{attempt_id}.started.json",
        required=True,
    )
    _copy_file_no_clobber_exact(
        source_evaluator / "attempt_ledger" / f"{attempt_id}.terminal.json",
        canonical_evaluator / "attempt_ledger" / f"{attempt_id}.terminal.json",
        required=False,
    )
    _copy_file_no_clobber_exact(
        source_evaluator / "cell_locks" / f"{cell_id}.json",
        canonical_evaluator / "cell_locks" / f"{cell_id}.json",
        required=True,
    )


def _validate_shard_receipt(*, row: dict[str, Any], condition, cell, attempt_auditor, attempt_dir: Path) -> None:
    if row.get("condition_id") != condition.policy_condition_id:
        raise Stage4DFullError("SHARD_RECEIPT_CONDITION_CHANGED")
    if row.get("condition_cell_id") != cell.condition_cell_id:
        raise Stage4DFullError("SHARD_RECEIPT_CELL_CHANGED")
    if row.get("manifest_index") != cell.manifest_index or row.get("task_id") != cell.task_id or row.get("seed") != cell.seed:
        raise Stage4DFullError("SHARD_RECEIPT_GRID_IDENTITY_CHANGED")
    if row.get("memory_state") != "OFF" or row.get("harness_state") != "OFF":
        raise Stage4DFullError("SHARD_RECEIPT_OFF_OFF_CHANGED")
    loaded = attempt_auditor.load_attempt_directory_v1(attempt_dir)
    if loaded.attempt_bundle.attempt_bundle_sha256 != row.get("attempt_bundle_sha256"):
        raise Stage4DFullError("SHARD_ATTEMPT_BUNDLE_CHANGED")
    if loaded.episode_artifact.task_id != row.get("task_id"):
        raise Stage4DFullError("SHARD_ATTEMPT_TASK_CHANGED")
    if loaded.episode_artifact.success != row.get("success"):
        raise Stage4DFullError("SHARD_ATTEMPT_SUCCESS_CHANGED")
    if loaded.episode_artifact.termination_reason != row.get("termination_reason"):
        raise Stage4DFullError("SHARD_ATTEMPT_TERMINATION_CHANGED")


def consolidate_shards(*, execution_root: Path, binding_root: Path, completed_prefix_count: int) -> dict[str, Any]:
    context = _prepare_live_context(execution_root=execution_root, binding_root=binding_root)
    if _canonical_prefix(execution_root=execution_root, context=context) < completed_prefix_count:
        raise Stage4DFullError("CANONICAL_PREFIX_REGRESSED_BEFORE_CONSOLIDATION")
    legacy = context["legacy"]
    bundles = context["bundles"]
    canonical_root = execution_root / "execution"
    lock_path = execution_root / "full_select_execution.lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Stage4DFullError("FULL_SELECT_CONSOLIDATION_ALREADY_ACTIVE") from exc

        shard_maps: dict[tuple[int, str], dict[str, dict[str, Any]]] = {}
        for shard_id in range(PARALLEL_SHARD_COUNT):
            shard_execution = _shard_root(execution_root, shard_id) / "execution"
            for label in CONDITION_ORDER:
                rows = legacy.load_receipts(shard_execution / label.lower() / "cell_receipts.jsonl")
                by_cell = {row["condition_cell_id"]: row for row in rows}
                if len(by_cell) != len(rows):
                    raise Stage4DFullError("SHARD_RECEIPT_DUPLICATE_CELL")
                shard_maps[(shard_id, label)] = by_cell

        canonical_rows = {
            label: list(legacy.load_receipts(canonical_root / label.lower() / "cell_receipts.jsonl"))
            for label in CONDITION_ORDER
        }
        if not (
            len(canonical_rows["T0"]) == len(canonical_rows["T2"])
            or len(canonical_rows["T0"]) == len(canonical_rows["T2"]) + 1
        ):
            raise Stage4DFullError("CANONICAL_T0_T2_LENGTH_CHANGED_DURING_CONSOLIDATION")
        start_ordinal = min(len(canonical_rows["T0"]), len(canonical_rows["T2"]))

        for ordinal in range(start_ordinal, EXPECTED_PAIR_CELLS):
            shard_id = shard_for_ordinal(ordinal)
            for label in CONDITION_ORDER:
                condition = bundles[label][0]
                cell = bundles[label][2].cells[ordinal]
                row = shard_maps[(shard_id, label)].get(cell.condition_cell_id)
                if row is None:
                    raise Stage4DFullError(f"SHARD_RECEIPT_MISSING:shard={shard_id}:label={label}:ordinal={ordinal}")
                shard_condition_root = _shard_root(execution_root, shard_id) / "execution" / label.lower()
                source_attempt = shard_condition_root / "evaluator_run" / "attempts" / row["execution_attempt_id"]
                _validate_shard_receipt(
                    row=row,
                    condition=condition,
                    cell=cell,
                    attempt_auditor=context["attempt_auditor"],
                    attempt_dir=source_attempt,
                )
                canonical_condition_root = canonical_root / label.lower()
                source_evaluator = shard_condition_root / "evaluator_run"
                canonical_evaluator = canonical_condition_root / "evaluator_run"
                canonical_attempt = canonical_evaluator / "attempts" / row["execution_attempt_id"]
                _copy_tree_no_clobber_exact(source_attempt, canonical_attempt)
                _copy_publication_metadata(
                    source_evaluator=source_evaluator,
                    canonical_evaluator=canonical_evaluator,
                    row=row,
                )
                current = legacy.load_receipts(canonical_condition_root / "cell_receipts.jsonl")
                if len(current) == ordinal + 1:
                    existing = current[ordinal]
                    _validate_canonical_row(row=existing, cell=cell, label=label, ordinal=ordinal)
                    if any(existing.get(key) != row.get(key) for key in (
                        "condition_id", "condition_cell_id", "manifest_index", "task_id", "seed",
                        "execution_attempt_id", "attempt_bundle_sha256", "success", "termination_reason",
                        "memory_state", "harness_state",
                    )):
                        raise Stage4DFullError(f"CANONICAL_EXISTING_RECEIPT_SCIENCE_CHANGED:label={label}:ordinal={ordinal}")
                    continue
                if len(current) != ordinal:
                    raise Stage4DFullError(
                        f"CANONICAL_APPEND_ORDINAL_CHANGED:label={label}:expected={ordinal}:observed={len(current)}"
                    )
                previous = None if not current else current[-1]["receipt_sha256"]
                canonical_receipt = legacy.make_cell_receipt(
                    condition_id=row["condition_id"],
                    condition_cell_id=row["condition_cell_id"],
                    manifest_index=row["manifest_index"],
                    task_id=row["task_id"],
                    seed=row["seed"],
                    execution_attempt_id=row["execution_attempt_id"],
                    attempt_bundle_sha256=row["attempt_bundle_sha256"],
                    success=row["success"],
                    termination_reason=row["termination_reason"],
                    previous_receipt_sha256=previous,
                )
                legacy.append_receipt(canonical_condition_root / "cell_receipts.jsonl", canonical_receipt)
                print(
                    "STAGE4D_PARALLEL_CANONICALIZED"
                    + " shard=" + str(shard_id)
                    + " condition=" + label
                    + " ordinal=" + str(ordinal)
                    + " task_id=" + row["task_id"]
                    + " seed=" + str(row["seed"])
                    + " receipt_sha256=" + canonical_receipt["receipt_sha256"],
                    flush=True,
                )
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)

    t0_count = len(legacy.load_receipts(canonical_root / "t0/cell_receipts.jsonl"))
    t2_count = len(legacy.load_receipts(canonical_root / "t2/cell_receipts.jsonl"))
    total = t0_count + t2_count
    if t0_count > EXPECTED_PAIR_CELLS or t2_count > EXPECTED_PAIR_CELLS or total > EXPECTED_TOTAL_CELLS:
        raise Stage4DFullError("LIVE_RECEIPT_COUNT_EXCEEDED_AUTHORITY")
    return {
        "t0_cell_count": t0_count,
        "t2_cell_count": t2_count,
        "total_condition_cell_count": total,
        "complete": t0_count == EXPECTED_PAIR_CELLS and t2_count == EXPECTED_PAIR_CELLS,
    }

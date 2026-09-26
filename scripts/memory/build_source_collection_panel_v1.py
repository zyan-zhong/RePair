#!/usr/bin/env python3
"""Build the complete frozen Failure Memory source-collection panel.

This program is pure/read-only with respect to model/environment state. It
freezes the entire 2367-task TRAIN_MEMORY_SOURCE order before any model call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.source_collection import (
    COMPLETE_PANEL_ORDER_RULE,
    NO_PERFORMANCE_ESTIMAND,
    OUTCOME_USE,
    SOURCE_BATCH_SIZE,
    SOURCE_COLLECTION_CONTEXT_V1,
    SOURCE_PANEL_SCHEMA_V1,
    SOURCE_STOPPING_FAILURE_TARGET,
    STOPPING_RULE_ID,
    SourceCollectionPolicyIdentityV1,
    SourcePanelEntryV1,
    SourcePanelManifestV1,
    build_complete_source_panel_order_v1,
    source_panel_order_score_v1,
)


PROTECTED_TASK_ACCESS_SHA256 = (
    "260766366d72a9af7b0b4809d30a45bb"
    "56f42134dad66b29a4b61ff7ed4793ea"
)

ALLOWED_TASK_TYPES = frozenset(
    {
        "pick_and_place_simple",
        "look_at_obj_in_light",
        "pick_clean_then_place_in_recep",
        "pick_heat_then_place_in_recep",
        "pick_cool_then_place_in_recep",
        "pick_two_obj_and_place",
    }
)


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise ValueError("output parent invalid")
    fd = os.open(
        path,
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


def _load_runtime_binding(path: Path) -> tuple[dict[str, object], bytes]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("runtime binding path invalid")
    raw = path.read_bytes()
    payload = strict_json_loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("runtime binding must be object")
    expected = {
        "schema_id",
        "schema_version",
        "identity_source",
        "formal_attempt_count_checked",
        "logical_condition_id",
        "checkpoint_instance_id",
        "training_seed",
        "served_model_name",
        "adapter_path",
        "adapter_bundle_sha256",
        "adapter_rank",
        "policy_runtime_manifest_path",
        "policy_runtime_manifest_sha256",
        "server_runtime_manifest_path",
        "server_runtime_manifest_sha256",
        "environment_runtime_manifest_sha256",
        "formal_runtime_core_commit",
        "raw_protocol_sha256",
        "policy_request_schema_sha256",
        "base_model_repository",
        "base_model_revision",
        "base_model_local_path",
        "tokenizer_identity_manifest_sha256",
        "chat_template_sha256",
        "vllm_version",
        "dtype",
        "tensor_parallel_size",
        "generation_config_mode",
        "chat_template_content_format",
        "enable_lora",
        "max_lora_rank",
        "max_loras",
        "max_cpu_loras",
        "lora_dtype",
        "runtime_dynamic_lora_updates",
        "memory_mode",
        "harness_mode",
        "performance_estimand",
    }
    if set(payload) != expected:
        raise ValueError("runtime binding fields mismatch")
    if payload["schema_id"] != "FAILURE_MEMORY_SOURCE_COLLECTION_RUNTIME_BINDING_V1":
        raise ValueError("runtime binding schema mismatch")
    if payload["schema_version"] != 1:
        raise ValueError("runtime binding schema version mismatch")
    if payload["performance_estimand"] != NO_PERFORMANCE_ESTIMAND:
        raise ValueError("runtime binding must declare NO_PERFORMANCE_ESTIMAND")
    if raw != canonical_json_bytes(payload):
        raise ValueError("runtime binding bytes are not canonical")
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


def _find_traj_file(root: Path) -> Path:
    candidates = (
        root / "traj_data.json",
        root / "traj_data.jsonl",
    )
    for path in candidates:
        if path.is_file() and not path.is_symlink():
            return path
    # E1 FrozenTaskRecord only needs a stable nonempty absolute source path;
    # prefer the ALFWorld trajectory if available, otherwise bind the gamefile
    # itself rather than inventing a path.
    gamefile = root / "game.tw-pddl"
    if gamefile.is_file() and not gamefile.is_symlink():
        return gamefile
    raise ValueError(f"no stable source file in task root: {root}")


def _load_source_records(
    *,
    protected_manifest: Path,
    dataset_root: Path,
) -> tuple[SourcePanelEntryV1, ...]:
    if protected_manifest.is_symlink() or not protected_manifest.is_file():
        raise ValueError("protected task-access manifest invalid")
    raw = protected_manifest.read_bytes()
    if sha256_bytes(raw) != PROTECTED_TASK_ACCESS_SHA256:
        raise ValueError("protected task-access authority SHA mismatch")
    if not raw.endswith(b"\n"):
        raise ValueError("protected task-access manifest lacks terminal LF")

    if dataset_root.is_symlink() or not dataset_root.is_dir():
        raise ValueError("dataset root invalid")
    dataset_root = dataset_root.resolve()

    entries = []
    source_count = 0

    for line_index, line in enumerate(raw.splitlines(keepends=True)):
        if not line.endswith(b"\n"):
            raise ValueError("task-access record lacks terminal LF")
        payload = strict_json_loads(line)
        if not isinstance(payload, dict):
            raise ValueError("task-access record must be object")

        if payload.get("access_class") != "TRAIN_MEMORY_SOURCE":
            continue
        if payload.get("split") != "train":
            raise ValueError("TRAIN_MEMORY_SOURCE record is not train split")

        source_count += 1

        task_type = payload.get("task_type")
        relative = payload.get("dataset_relative_gamefile")
        game_sha = payload.get("gamefile_sha256")
        group_id = payload.get("task_gamefile_group_id")

        if task_type not in ALLOWED_TASK_TYPES:
            raise ValueError(f"unsupported source task type: {task_type!r}")
        if not isinstance(relative, str) or not relative:
            raise ValueError("dataset_relative_gamefile invalid")
        if not isinstance(game_sha, str):
            raise ValueError("gamefile_sha256 invalid")
        if not isinstance(group_id, str):
            raise ValueError("task_gamefile_group_id invalid")

        gamefile = (dataset_root / relative).resolve()
        try:
            gamefile.relative_to(dataset_root)
        except ValueError as exc:
            raise ValueError("source gamefile escapes dataset root") from exc
        if gamefile.is_symlink() or not gamefile.is_file():
            raise ValueError(f"source gamefile invalid: {gamefile}")
        if sha256_file(gamefile) != game_sha:
            raise ValueError(f"source gamefile SHA mismatch: {relative}")

        trial_id = gamefile.parent.name
        if not trial_id:
            raise ValueError("trial_id cannot be derived")

        # Placeholder indices are legal here because constructor only checks
        # consistency. build_complete_source_panel_order_v1() replaces them with
        # the final frozen panel indices before publication.
        placeholder_index = len(entries)
        entries.append(
            SourcePanelEntryV1(
                panel_index=placeholder_index,
                batch_index=placeholder_index // SOURCE_BATCH_SIZE,
                task_access_record_line_index=line_index,
                task_access_record_sha256=sha256_bytes(line),
                trial_id=trial_id,
                task_type=task_type,
                dataset_relative_gamefile=relative,
                absolute_gamefile=str(gamefile),
                gamefile_sha256=game_sha,
                task_gamefile_group_id=group_id,
                order_score=source_panel_order_score_v1(group_id),
            )
        )

    if source_count != 2367 or len(entries) != 2367:
        raise ValueError(
            f"TRAIN_MEMORY_SOURCE population mismatch: {len(entries)}"
        )
    return tuple(entries)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protected-task-access-manifest", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--runtime-binding", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--code-commit", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=SOURCE_PANEL_OUTPUT_ALREADY_EXISTS")
    if output.parent.is_symlink() or not output.parent.is_dir():
        raise SystemExit("STOP=SOURCE_PANEL_OUTPUT_PARENT_INVALID")

    code_commit = args.code_commit
    if (
        len(code_commit) != 40
        or any(ch not in "0123456789abcdef" for ch in code_commit)
    ):
        raise SystemExit("STOP=SOURCE_COLLECTION_CODE_COMMIT_INVALID")

    repo_root = Path(__file__).resolve().parents[2]
    observed_head = subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if observed_head != code_commit:
        raise SystemExit("STOP=SOURCE_COLLECTION_CODE_COMMIT_HEAD_MISMATCH")

    runtime, runtime_raw = _load_runtime_binding(Path(args.runtime_binding))
    runtime_sha = sha256_bytes(runtime_raw)

    policy_identity = SourceCollectionPolicyIdentityV1(
        logical_condition_id=runtime["logical_condition_id"],
        checkpoint_instance_id=runtime["checkpoint_instance_id"],
        training_seed=runtime["training_seed"],
        served_model_name=runtime["served_model_name"],
        adapter_bundle_sha256=runtime["adapter_bundle_sha256"],
        policy_runtime_manifest_sha256=runtime[
            "policy_runtime_manifest_sha256"
        ],
        server_runtime_manifest_sha256=runtime[
            "server_runtime_manifest_sha256"
        ],
        raw_protocol_sha256=runtime["raw_protocol_sha256"],
        policy_request_schema_sha256=runtime[
            "policy_request_schema_sha256"
        ],
    )

    raw_entries = _load_source_records(
        protected_manifest=Path(args.protected_task_access_manifest),
        dataset_root=Path(args.dataset_root),
    )
    ordered = build_complete_source_panel_order_v1(raw_entries)

    manifest = SourcePanelManifestV1(
        schema_id=SOURCE_PANEL_SCHEMA_V1,
        schema_version=1,
        source_collection_context=SOURCE_COLLECTION_CONTEXT_V1,
        source_collection_code_commit=code_commit,
        runtime_binding_sha256=runtime_sha,
        task_access_protected_manifest_sha256=PROTECTED_TASK_ACCESS_SHA256,
        complete_panel_order_rule=COMPLETE_PANEL_ORDER_RULE,
        batch_size=SOURCE_BATCH_SIZE,
        stopping_failure_target=SOURCE_STOPPING_FAILURE_TARGET,
        stopping_rule_id=STOPPING_RULE_ID,
        outcome_use=OUTCOME_USE,
        performance_estimand=NO_PERFORMANCE_ESTIMAND,
        policy_identity=policy_identity,
        entries=ordered,
        panel_manifest_sha256=None,
    )

    raw = manifest.canonical_bytes()
    _write_once(output, raw)

    # Auxiliary human-readable census is outcome-free and derived solely from
    # the pre-execution full manifest.
    counts: dict[str, int] = {}
    for item in ordered:
        counts[item.task_type] = counts.get(item.task_type, 0) + 1

    print("SOURCE_PANEL_ENTRY_COUNT=" + str(len(ordered)))
    print(
        "SOURCE_PANEL_TASK_TYPE_COUNTS="
        + json.dumps(counts, sort_keys=True, separators=(",", ":"))
    )
    print("SOURCE_PANEL_BATCH_SIZE=" + str(SOURCE_BATCH_SIZE))
    print(
        "SOURCE_PANEL_MAX_BATCH_INDEX="
        + str(ordered[-1].batch_index)
    )
    print("SOURCE_PANEL_MANIFEST_SHA256=" + manifest.panel_manifest_sha256)
    print("SOURCE_PANEL_PERFORMANCE_ESTIMAND=" + manifest.performance_estimand)
    print("SOURCE_PANEL_OUTCOME_USE=" + manifest.outcome_use)
    print("SOURCE_PANEL_MANIFEST_FROZEN_BEFORE_MODEL_EXECUTION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

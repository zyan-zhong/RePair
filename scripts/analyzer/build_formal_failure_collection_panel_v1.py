#!/usr/bin/env python3
"""Build the frozen Formal Analyzer fresh pi1 collection panel."""

from __future__ import annotations

import argparse
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
from pchsi.analyzer.formal_failure_collection import (
    COMPLETE_PANEL_ORDER_RULE,
    FORMAL_ACCESS_CLASS,
    FORMAL_BATCH_SIZE,
    FORMAL_COLLECTION_CONTEXT_V1,
    FORMAL_PANEL_SCHEMA_V1,
    FORMAL_STOPPING_FAILURE_TARGET,
    NO_PERFORMANCE_ESTIMAND,
    OUTCOME_USE,
    PROTECTED_TASK_ACCESS_SHA256,
    STOPPING_RULE_ID,
    FormalCollectionPolicyIdentityV1,
    FormalPanelEntryV1,
    FormalPanelManifestV1,
    build_complete_formal_panel_order_v1,
    formal_panel_order_score_v1,
)

ALLOWED_TASK_TYPES = frozenset({
    "pick_and_place_simple",
    "look_at_obj_in_light",
    "pick_clean_then_place_in_recep",
    "pick_heat_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_two_obj_and_place",
})


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise ValueError("output parent invalid")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
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
    if payload.get("schema_id") != "FAILURE_MEMORY_SOURCE_COLLECTION_RUNTIME_BINDING_V1":
        raise ValueError("runtime binding schema mismatch")
    if payload.get("schema_version") != 1:
        raise ValueError("runtime binding schema version mismatch")
    if payload.get("performance_estimand") != NO_PERFORMANCE_ESTIMAND:
        raise ValueError("runtime binding performance boundary mismatch")
    if raw != canonical_json_bytes(payload):
        raise ValueError("runtime binding bytes are not canonical")
    return payload, raw


def _load_exclusions(path: Path) -> tuple[set[str], str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("exclusion manifest invalid")
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict):
        raise TypeError("exclusion manifest must be object")
    if value.get("schema_id") != "FORMAL_ANALYZER_PRIOR_EXPOSURE_EXCLUSION_V1":
        raise ValueError("exclusion manifest schema mismatch")
    rows = value.get("gamefile_sha256s")
    if not isinstance(rows, list):
        raise TypeError("exclusion gamefiles must be array")
    if rows != sorted(set(rows)):
        raise ValueError("exclusion gamefiles must be sorted unique")
    return set(rows), sha256_bytes(raw)


def _load_records(
    *,
    protected_manifest: Path,
    dataset_root: Path,
    excluded_gamefiles: set[str],
) -> tuple[FormalPanelEntryV1, ...]:
    if protected_manifest.is_symlink() or not protected_manifest.is_file():
        raise ValueError("protected task-access manifest invalid")
    raw = protected_manifest.read_bytes()
    if sha256_bytes(raw) != PROTECTED_TASK_ACCESS_SHA256:
        raise ValueError("protected task-access SHA mismatch")
    if not raw.endswith(b"\n"):
        raise ValueError("protected task-access manifest lacks terminal LF")

    dataset_root = dataset_root.resolve()
    if dataset_root.is_symlink() or not dataset_root.is_dir():
        raise ValueError("dataset root invalid")

    entries = []
    retrieval_count = 0
    excluded_count = 0

    for line_index, line in enumerate(raw.splitlines(keepends=True)):
        if not line.endswith(b"\n"):
            raise ValueError("task-access record lacks terminal LF")
        payload = strict_json_loads(line)
        if not isinstance(payload, dict):
            raise ValueError("task-access row must be object")
        if payload.get("access_class") != FORMAL_ACCESS_CLASS:
            continue
        if payload.get("split") != "train":
            raise ValueError("TRAIN_RETRIEVAL_DEV row is not train")

        retrieval_count += 1
        game_sha = payload.get("gamefile_sha256")
        if game_sha in excluded_gamefiles:
            excluded_count += 1
            continue

        task_type = payload.get("task_type")
        relative = payload.get("dataset_relative_gamefile")
        group_id = payload.get("task_gamefile_group_id")
        if task_type not in ALLOWED_TASK_TYPES:
            raise ValueError(f"unsupported task type: {task_type!r}")
        if not isinstance(relative, str) or not relative:
            raise ValueError("dataset_relative_gamefile invalid")
        if not isinstance(game_sha, str) or not isinstance(group_id, str):
            raise ValueError("task/gamefile identity invalid")

        gamefile = (dataset_root / relative).resolve()
        try:
            gamefile.relative_to(dataset_root)
        except ValueError as exc:
            raise ValueError("gamefile escapes dataset root") from exc
        if gamefile.is_symlink() or not gamefile.is_file():
            raise ValueError(f"gamefile invalid: {gamefile}")
        if sha256_file(gamefile) != game_sha:
            raise ValueError(f"gamefile SHA mismatch: {relative}")

        trial_id = gamefile.parent.name
        placeholder = len(entries)
        entries.append(
            FormalPanelEntryV1(
                panel_index=placeholder,
                batch_index=placeholder // FORMAL_BATCH_SIZE,
                task_access_record_line_index=line_index,
                task_access_record_sha256=sha256_bytes(line),
                trial_id=trial_id,
                task_type=task_type,
                dataset_relative_gamefile=relative,
                absolute_gamefile=str(gamefile),
                gamefile_sha256=game_sha,
                task_gamefile_group_id=group_id,
                order_score=formal_panel_order_score_v1(group_id),
            )
        )

    if retrieval_count != 1186:
        raise ValueError(
            f"TRAIN_RETRIEVAL_DEV population mismatch: {retrieval_count}"
        )
    if len(entries) < FORMAL_STOPPING_FAILURE_TARGET:
        raise ValueError(
            f"eligible Formal collection panel too small: {len(entries)}"
        )
    print(f"FORMAL_RETRIEVAL_DEV_TOTAL={retrieval_count}")
    print(f"FORMAL_PRIOR_EXPOSURE_EXCLUDED={excluded_count}")
    print(f"FORMAL_ELIGIBLE_COLLECTION_PANEL={len(entries)}")
    return tuple(entries)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protected-task-access-manifest", required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--runtime-binding", required=True)
    parser.add_argument("--exclusion-manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--code-commit", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=FORMAL_PANEL_OUTPUT_ALREADY_EXISTS")
    if output.parent.is_symlink() or not output.parent.is_dir():
        raise SystemExit("STOP=FORMAL_PANEL_OUTPUT_PARENT_INVALID")

    code_commit = args.code_commit
    if (
        len(code_commit) != 40
        or any(ch not in "0123456789abcdef" for ch in code_commit)
    ):
        raise SystemExit("STOP=FORMAL_COLLECTION_CODE_COMMIT_INVALID")

    repo_root = Path(__file__).resolve().parents[2]
    observed_head = subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True
    ).strip()
    if observed_head != code_commit:
        raise SystemExit("STOP=FORMAL_COLLECTION_HEAD_MISMATCH")

    runtime, runtime_raw = _load_runtime_binding(Path(args.runtime_binding))
    excluded, exclusion_sha = _load_exclusions(Path(args.exclusion_manifest))

    policy_identity = FormalCollectionPolicyIdentityV1(
        logical_condition_id=runtime["logical_condition_id"],
        checkpoint_instance_id=runtime["checkpoint_instance_id"],
        training_seed=runtime["training_seed"],
        served_model_name=runtime["served_model_name"],
        adapter_bundle_sha256=runtime["adapter_bundle_sha256"],
        policy_runtime_manifest_sha256=runtime["policy_runtime_manifest_sha256"],
        server_runtime_manifest_sha256=runtime["server_runtime_manifest_sha256"],
        raw_protocol_sha256=runtime["raw_protocol_sha256"],
        policy_request_schema_sha256=runtime["policy_request_schema_sha256"],
    )

    raw_entries = _load_records(
        protected_manifest=Path(args.protected_task_access_manifest),
        dataset_root=Path(args.dataset_root),
        excluded_gamefiles=excluded,
    )
    ordered = build_complete_formal_panel_order_v1(raw_entries)

    manifest = FormalPanelManifestV1(
        schema_id=FORMAL_PANEL_SCHEMA_V1,
        schema_version=1,
        collection_context=FORMAL_COLLECTION_CONTEXT_V1,
        collection_code_commit=code_commit,
        runtime_binding_sha256=sha256_bytes(runtime_raw),
        task_access_protected_manifest_sha256=PROTECTED_TASK_ACCESS_SHA256,
        exclusion_manifest_sha256=exclusion_sha,
        complete_panel_order_rule=COMPLETE_PANEL_ORDER_RULE,
        batch_size=FORMAL_BATCH_SIZE,
        stopping_failure_target=FORMAL_STOPPING_FAILURE_TARGET,
        stopping_rule_id=STOPPING_RULE_ID,
        outcome_use=OUTCOME_USE,
        performance_estimand=NO_PERFORMANCE_ESTIMAND,
        policy_identity=policy_identity,
        eligible_entry_count=len(ordered),
        entries=ordered,
        panel_manifest_sha256=None,
    )
    _write_once(output, manifest.canonical_bytes())

    counts: dict[str, int] = {}
    for item in ordered:
        counts[item.task_type] = counts.get(item.task_type, 0) + 1

    print(f"FORMAL_PANEL_ENTRY_COUNT={len(ordered)}")
    print(
        "FORMAL_PANEL_TASK_TYPE_COUNTS="
        + json.dumps(counts, sort_keys=True, separators=(",", ":"))
    )
    print(f"FORMAL_PANEL_BATCH_SIZE={FORMAL_BATCH_SIZE}")
    print(f"FORMAL_PANEL_STOPPING_FAILURE_TARGET={FORMAL_STOPPING_FAILURE_TARGET}")
    print(f"FORMAL_PANEL_MANIFEST_SHA256={manifest.panel_manifest_sha256}")
    print("FORMAL_PANEL_FROZEN_BEFORE_ENVIRONMENT_OR_MODEL_EXECUTION=true")
    print("NO_PERFORMANCE_ESTIMAND")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

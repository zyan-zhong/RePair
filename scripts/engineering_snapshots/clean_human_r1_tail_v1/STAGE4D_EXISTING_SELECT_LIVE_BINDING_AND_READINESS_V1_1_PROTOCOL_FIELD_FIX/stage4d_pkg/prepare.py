from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from .common import (
    EXPECTED_ADAPTER_BUNDLE_SHA256,
    EXPECTED_ADAPTER_CONFIG_SHA256,
    EXPECTED_ADAPTER_MODEL_SHA256,
    EXPECTED_BASE_REPOSITORY,
    EXPECTED_BASE_REVISION,
    EXPECTED_CHAT_TEMPLATE_SHA256,
    EXPECTED_CONDITION_EPISODES,
    EXPECTED_FIXED_HEAD,
    EXPECTED_FIXED_TREE,
    EXPECTED_I1_REQUEST_SCHEMA_SHA256,
    EXPECTED_I1_SERIALIZATION_SCHEMA_SHA256,
    EXPECTED_PAIR_CELLS,
    EXPECTED_PROTOCOL_FILE_SHA256,
    EXPECTED_PROTOCOL_SHA256,
    EXPECTED_SEEDS,
    EXPECTED_TASK_COUNT,
    EXPECTED_TRAINING_PLAN_SHA256,
    EXPECTED_TRAINING_CONTRACT_FILE_SHA256,
    EXPECTED_TRAINING_RUN_ID,
    EXPECTED_TRAINING_SEED,
    EXPECTED_TRAIN_AUDIT_SHA256,
    EXPECTED_TRAIN_SELECT_SHA256,
    EXPECTED_TRAIN_UPDATE_SHA256,
    PI0_CONDITION_ID,
    PI0_SERVED_NAME,
    T2_CONDITION_ID,
    T2_SERVED_NAME,
    Stage4DError,
    canonical_json_bytes,
    load_json,
    load_jsonl,
    package_output_root,
    recursive_path_strings,
    require_file_sha,
    resolve_gamefile,
    sha256_bytes,
    sha256_file,
    verify_disjoint_pools,
    write_new_bytes,
    write_new_json,
)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def verify_frozen_protocol_grid(
    grid: dict[str, Any],
    *,
    expected_task_count: int = EXPECTED_TASK_COUNT,
    expected_seeds: tuple[int, ...] = EXPECTED_SEEDS,
    expected_pair_cells: int = EXPECTED_PAIR_CELLS,
    expected_condition_episodes: int = EXPECTED_CONDITION_EPISODES,
) -> None:
    if grid.get("task_count") != expected_task_count:
        raise Stage4DError("PROTOCOL_TASK_COUNT_CHANGED")
    if tuple(grid.get("replicate_seeds", [])) != expected_seeds:
        raise Stage4DError("PROTOCOL_SEEDS_CHANGED")
    if grid.get("paired_cells") != expected_pair_cells:
        raise Stage4DError("PROTOCOL_PAIR_CELL_COUNT_CHANGED")
    if grid.get("condition_episodes") != expected_condition_episodes:
        raise Stage4DError("PROTOCOL_EPISODE_COUNT_CHANGED")

    crosswalk = grid.get("index_crosswalk")
    if not isinstance(crosswalk, list) or len(crosswalk) != expected_task_count:
        raise Stage4DError("PROTOCOL_CROSSWALK_CHANGED")

    pairs = grid.get("pairs")
    if not isinstance(pairs, list) or len(pairs) != expected_pair_cells:
        raise Stage4DError("PROTOCOL_PAIR_PRODUCT_CHANGED")
    expected_pairs = [
        {
            "task_id": row.get("task_id"),
            "select_local_index": row.get("select_local_index"),
            "source_index": row.get("source_index"),
            "seed": seed,
        }
        for seed in expected_seeds
        for row in crosswalk
    ]
    if pairs != expected_pairs:
        raise Stage4DError("PROTOCOL_PAIR_PRODUCT_OR_ORDER_CHANGED")


def discover_stage4c(control_root: Path) -> tuple[Path, dict[str, Any]]:
    candidates: list[tuple[Path, dict[str, Any]]] = []
    root = control_root / "stage4c_existing_select_freeze_v1"
    for path in root.glob("*/NEXT_STAGE_BINDING.json"):
        value = load_json(path)
        if value.get("fixed_head") == EXPECTED_FIXED_HEAD:
            candidates.append((path.parent, value))
    if len(candidates) != 1:
        raise Stage4DError(
            f"STAGE4C_EXACT_BINDING_UNIQUE_REQUIRED:count={len(candidates)}"
        )
    return candidates[0]



def discover_candidate_handoff(
    control_root: Path,
    *,
    adapter_path: Path,
) -> tuple[Path, dict[str, Any]]:
    candidates: list[tuple[Path, dict[str, Any]]] = []
    root = control_root / "stage4a_clean_existing_trainer_v1"
    for path in root.glob("*/CANDIDATE_HANDOFF.json"):
        value = load_json(path)
        if (
            value.get("candidate_alias") == T2_SERVED_NAME
            and value.get("adapter_path") == str(adapter_path)
            and value.get("training_plan_sha256") == EXPECTED_TRAINING_PLAN_SHA256
        ):
            candidates.append((path, value))
    if len(candidates) != 1:
        raise Stage4DError(
            f"STAGE4A_CANDIDATE_HANDOFF_UNIQUE_REQUIRED:count={len(candidates)}"
        )
    return candidates[0]


def verify_existing_output_inventory(output_root: Path) -> None:
    inventory = output_root / "OUTPUT_FILES.sha256"
    if not inventory.is_file() or inventory.is_symlink():
        raise Stage4DError(f"EXISTING_STAGE4D_OUTPUT_INCOMPLETE:{output_root}")
    for line_number, line in enumerate(
        inventory.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            expected, name = line.split("  ", 1)
        except ValueError as exc:
            raise Stage4DError(
                f"EXISTING_STAGE4D_INVENTORY_INVALID:{line_number}"
            ) from exc
        path = output_root / name
        require_file_sha(path, expected, f"EXISTING_STAGE4D_OUTPUT_{name}")


def stage2_dataset_roots(stage2_root: Path) -> list[Path]:
    roots: set[Path] = set()
    for path in sorted((stage2_root / "stage2a").glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for raw in recursive_path_strings(value):
            marker = "/json_2.1.1"
            if marker not in raw:
                continue
            prefix = raw.split(marker, 1)[0] + marker
            candidate = Path(prefix)
            if candidate.is_dir():
                roots.add(candidate.resolve())
    if not roots:
        raise Stage4DError("STAGE2_DATASET_ROOT_NOT_DISCOVERED_FROM_FROZEN_ASSETS")
    return sorted(roots)


def load_repo_types(repo: Path) -> dict[str, Any]:
    src = repo / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from pchsi.evaluation.canonical_evidence import canonical_json_bytes as repo_canonical_json_bytes
    from pchsi.evaluation.condition_run_schedule import (
        ConditionRunPurpose,
        build_condition_run_schedule,
    )
    from pchsi.evaluation.distillation_access import (
        DistillationAccessClass,
        HistoricalAccessAuditRecordV1,
        HistoricalAccessAuditV1,
        HistoricalAccessFlag,
        TaskAccessManifestV1,
        TaskAccessRecordV1,
    )
    from pchsi.evaluation.distillation_governance import canonical_model_sha256
    from pchsi.evaluation.environment_runtime_manifest import (
        EnvironmentRuntimeInputs,
        EnvironmentRuntimeManifestV1,
        SourceIdentity,
        build_environment_runtime_manifest,
    )
    from pchsi.evaluation.policy_condition import (
        CheckpointKind,
        PolicyConditionManifestV1,
        TrainingMethod,
    )
    from pchsi.evaluation.rendered_prompt import (
        HuggingFaceTokenizerFactory,
        LocalTokenizerPromptRenderer,
    )
    from pchsi.evaluation.select_execution_identity import (
        select_i1_request_contract_sha256,
    )
    from pchsi.evaluation.select_policy_runtime import (
        SelectPolicyRuntimeManifestV1,
        SelectServerRuntimeManifestV1,
        SelectStaticLoRARegistrationV1,
    )

    return locals()


def tokenizer_identity(base_model_path: Path) -> dict[str, Any]:
    names = (
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "added_tokens.json",
        "vocab.json",
        "merges.txt",
    )
    files: dict[str, dict[str, Any]] = {}
    for name in names:
        path = base_model_path / name
        if path.is_file() and not path.is_symlink():
            files[name] = {
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
    if "tokenizer_config.json" not in files:
        raise Stage4DError("TOKENIZER_CONFIG_MISSING")
    if "tokenizer.json" not in files:
        raise Stage4DError("TOKENIZER_JSON_MISSING")
    return {
        "schema_id": "CLEAN_SELECT_TOKENIZER_IDENTITY_V1",
        "schema_version": 1,
        "base_model_repository": EXPECTED_BASE_REPOSITORY,
        "base_model_revision": EXPECTED_BASE_REVISION,
        "files": files,
    }


def build_environment(repo: Path, types: dict[str, Any]):
    import alfworld
    import textworld
    import textworld.gym
    import gym
    from alfworld.agents.environment.alfred_tw_env import (
        AlfredTWEnv,
        AlfredDemangler,
        AlfredInfos,
    )

    source_objects = (
        ("AlfredTWEnv", AlfredTWEnv),
        ("AlfredDemangler", AlfredDemangler),
        ("AlfredInfos", AlfredInfos),
        ("textworld.gym.register_games", textworld.gym.register_games),
    )
    sources = []
    for logical_name, obj in source_objects:
        raw_path = inspect.getsourcefile(obj)
        if not raw_path:
            raise Stage4DError(f"SOURCE_PATH_UNAVAILABLE:{logical_name}")
        path = Path(raw_path).resolve()
        if path.is_symlink() or not path.is_file():
            raise Stage4DError(f"SOURCE_FILE_INVALID:{logical_name}:{path}")
        sources.append(
            types["SourceIdentity"](
                logical_name=logical_name,
                source_path=str(path),
                sha256=sha256_file(path),
            )
        )

    inputs = types["EnvironmentRuntimeInputs"](
        python_version=sys.version.split()[0],
        python_executable_sha256=sha256_file(Path(sys.executable)),
        alfworld_version=importlib.metadata.version("alfworld"),
        textworld_version=importlib.metadata.version("textworld"),
        gym_version=importlib.metadata.version("gym"),
        source_identities=tuple(sources),
        wrapper_order=(
            "AlfredDemangler(shuffle=false)",
            "AlfredInfos",
        ),
        env_infos=(
            "won",
            "admissible_commands",
            "extra.gamefile",
        ),
        batch_size=1,
        asynchronous=False,
        auto_reset=False,
        max_episode_steps=31,
        process_start_method="spawn",
    )
    return types["EnvironmentRuntimeManifestV1"](
        schema_id="ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1",
        schema_version=1,
        manifest_id="ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1",
        python_version=inputs.python_version,
        python_executable_sha256=inputs.python_executable_sha256,
        alfworld_version=inputs.alfworld_version,
        textworld_version=inputs.textworld_version,
        gym_version=inputs.gym_version,
        source_identities=inputs.source_identities,
        wrapper_order=inputs.wrapper_order,
        env_infos=inputs.env_infos,
        batch_size=inputs.batch_size,
        asynchronous=inputs.asynchronous,
        auto_reset=inputs.auto_reset,
        max_episode_steps=inputs.max_episode_steps,
        process_start_method=inputs.process_start_method,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--badcase-root",
        default="/data/run01/scwb204/sdar_repro/badcase",
    )
    parser.add_argument(
        "--control-root",
        default="/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control",
    )
    parser.add_argument(
        "--scripts-root",
        default="/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts",
    )
    args = parser.parse_args(argv)

    badcase_root = Path(args.badcase_root).resolve()
    control_root = Path(args.control_root).resolve()
    scripts_root = Path(args.scripts_root).resolve()
    stage2_root = scripts_root / "stage2_clean_train_bootstrap_v1_output"

    stage4c_root, handoff = discover_stage4c(control_root)
    if handoff.get("fixed_tree") != EXPECTED_FIXED_TREE:
        raise Stage4DError("STAGE4C_FIXED_TREE_MISMATCH")
    if handoff.get("protocol_sha256") != EXPECTED_PROTOCOL_SHA256:
        raise Stage4DError("STAGE4C_PROTOCOL_IDENTITY_MISMATCH")
    if handoff.get("evaluation_execution_authorized") is not False:
        raise Stage4DError("STAGE4C_PREMATURE_EXECUTION_AUTHORITY")
    if handoff.get("next_gate") != "EXISTING_SELECT_LIVE_BINDING_AND_EXECUTION_AUTHORIZATION":
        raise Stage4DError("STAGE4C_NEXT_GATE_CHANGED")

    protocol_path = Path(handoff["protocol_path"])
    require_file_sha(protocol_path, EXPECTED_PROTOCOL_FILE_SHA256, "PROTOCOL")
    protocol = load_json(protocol_path)
    if protocol.get("protocol_sha256") != EXPECTED_PROTOCOL_SHA256:
        raise Stage4DError("PROTOCOL_SEMANTIC_IDENTITY_MISMATCH")
    if protocol.get("protocol_frozen") is not True:
        raise Stage4DError("PROTOCOL_NOT_FROZEN")
    if protocol.get("evaluation_execution_authorized") is not False:
        raise Stage4DError("PROTOCOL_PREMATURE_EXECUTION_AUTHORITY")

    grid = protocol.get("grid")
    if not isinstance(grid, dict):
        raise Stage4DError("PROTOCOL_GRID_MISSING")
    verify_frozen_protocol_grid(grid)
    crosswalk = grid["index_crosswalk"]

    code_worktree = Path(handoff["code_worktree"])
    if git(code_worktree, "rev-parse", "HEAD") != EXPECTED_FIXED_HEAD:
        raise Stage4DError("CODE_WORKTREE_HEAD_MISMATCH")
    if git(code_worktree, "rev-parse", "HEAD^{tree}") != EXPECTED_FIXED_TREE:
        raise Stage4DError("CODE_WORKTREE_TREE_MISMATCH")
    if git(code_worktree, "status", "--porcelain"):
        raise Stage4DError("CODE_WORKTREE_NOT_CLEAN")

    types = load_repo_types(code_worktree)
    if types["select_i1_request_contract_sha256"]() != EXPECTED_I1_REQUEST_SCHEMA_SHA256:
        raise Stage4DError("I1_REQUEST_SCHEMA_FACTORY_MISMATCH")

    pool_refs = handoff["pool_metadata_refs"]
    select_path = Path(pool_refs["TRAIN_SELECT"]["path"])
    update_path = Path(pool_refs["TRAIN_UPDATE"]["path"])
    audit_path = Path(pool_refs["TRAIN_AUDIT"]["path"])
    require_file_sha(select_path, EXPECTED_TRAIN_SELECT_SHA256, "TRAIN_SELECT")
    require_file_sha(update_path, EXPECTED_TRAIN_UPDATE_SHA256, "TRAIN_UPDATE")
    require_file_sha(audit_path, EXPECTED_TRAIN_AUDIT_SHA256, "TRAIN_AUDIT")
    select_rows = load_jsonl(select_path)
    update_rows = load_jsonl(update_path)
    audit_rows = load_jsonl(audit_path)
    if len(select_rows) != 355 or len(update_rows) != 2843 or len(audit_rows) != 355:
        raise Stage4DError("TRAIN_POOL_COUNT_MISMATCH")
    verify_disjoint_pools(select_rows, update_rows, audit_rows)
    select_by_id = {row["id"]: row for row in select_rows}

    dataset_roots = stage2_dataset_roots(stage2_root)
    source_evidence = (
        str(select_path),
        str(protocol_path),
        str(stage2_root / "stage2a"),
    )
    access_records = []
    audit_records = []
    gamefile_identity_rows = []
    for local_index, item in enumerate(crosswalk):
        if item.get("select_local_index") != local_index:
            raise Stage4DError("PROTOCOL_LOCAL_INDEX_NOT_CONTIGUOUS")
        task_id = item.get("task_id")
        row = select_by_id.get(task_id)
        if row is None:
            raise Stage4DError(f"PROTOCOL_TASK_NOT_IN_TRAIN_SELECT:{task_id}")
        if row.get("index") != item.get("source_index"):
            raise Stage4DError(f"PROTOCOL_SOURCE_INDEX_MISMATCH:{task_id}")
        if row.get("gamefile_sha256") != item.get("gamefile_sha256"):
            raise Stage4DError(f"PROTOCOL_GAMEFILE_SHA_MISMATCH:{task_id}")
        gamefile = resolve_gamefile(
            dataset_candidates=dataset_roots,
            gamefile_relpath=row["gamefile_relpath"],
            expected_sha1=row["gamefile_sha1"],
            expected_sha256=row["gamefile_sha256"],
        )
        flags = (types["HistoricalAccessFlag"].ACCESS_HISTORY_INCOMPLETE,)
        audit_records.append(
            types["HistoricalAccessAuditRecordV1"](
                task_id=task_id,
                gamefile=str(gamefile),
                dataset_split="train",
                first_known_access_date=None,
                access_flags=flags,
                evidence_sources=source_evidence,
            )
        )
        access_records.append(
            types["TaskAccessRecordV1"](
                manifest_index=local_index,
                task_id=task_id,
                dataset_split="train",
                task_type=row["task_type"],
                gamefile=str(gamefile),
                gamefile_sha1=row["gamefile_sha1"],
                gamefile_sha256=row["gamefile_sha256"],
                historical_access_flags=flags,
                access_class=types["DistillationAccessClass"].SELECT_SUMMARY_ONLY,
                teacher_call_permitted=False,
                training_permitted=False,
                select_evaluation_permitted=True,
                confirmatory_permitted=False,
                provenance_sources=source_evidence,
            )
        )
        gamefile_identity_rows.append({
            "manifest_index": local_index,
            "task_id": task_id,
            "gamefile": str(gamefile),
            "gamefile_sha1": row["gamefile_sha1"],
            "gamefile_sha256": row["gamefile_sha256"],
        })

    access_audit = types["HistoricalAccessAuditV1"](
        schema_id="DISTILLATION_HISTORICAL_ACCESS_AUDIT_V1",
        schema_version=1,
        audit_id="CLEAN_HUMAN_R1_TRAIN_SELECT_CONSERVATIVE_ACCESS_AUDIT_V1",
        dataset_version="json_2.1.1",
        record_count=len(audit_records),
        records=tuple(audit_records),
    )
    access_audit_sha = types["canonical_model_sha256"](access_audit)
    task_access = types["TaskAccessManifestV1"](
        schema_id="DISTILLATION_TASK_ACCESS_MANIFEST_V1",
        schema_version=1,
        manifest_id="CLEAN_HUMAN_R1_TRAIN_SELECT_TASK_ACCESS_V1",
        dataset_version="json_2.1.1",
        historical_access_audit_sha256=access_audit_sha,
        record_count=len(access_records),
        records=tuple(access_records),
    )
    task_access_sha = types["canonical_model_sha256"](task_access)

    model_binding = protocol["model_binding"]
    base_model_path = Path(model_binding["base"]["snapshot_path"])
    if base_model_path.is_symlink() or not base_model_path.is_dir():
        raise Stage4DError("BASE_MODEL_SNAPSHOT_INVALID")
    if model_binding["base"]["repository_id"] != EXPECTED_BASE_REPOSITORY:
        raise Stage4DError("BASE_MODEL_REPOSITORY_CHANGED")
    if model_binding["base"]["revision"] != EXPECTED_BASE_REVISION:
        raise Stage4DError("BASE_MODEL_REVISION_CHANGED")

    adapter_path = Path(model_binding["candidate_adapter_path"])
    if adapter_path.is_symlink() or not adapter_path.is_dir():
        raise Stage4DError("T2_ADAPTER_DIRECTORY_INVALID")
    if model_binding["candidate_adapter_bundle_sha256"] != EXPECTED_ADAPTER_BUNDLE_SHA256:
        raise Stage4DError("T2_ADAPTER_BUNDLE_IDENTITY_CHANGED")
    require_file_sha(adapter_path / "adapter_config.json", EXPECTED_ADAPTER_CONFIG_SHA256, "ADAPTER_CONFIG")
    require_file_sha(adapter_path / "adapter_model.safetensors", EXPECTED_ADAPTER_MODEL_SHA256, "ADAPTER_MODEL")

    candidate_handoff_path, candidate_handoff = discover_candidate_handoff(
        control_root,
        adapter_path=adapter_path,
    )
    run_manifest = candidate_handoff.get("run_manifest")
    if not isinstance(run_manifest, dict):
        raise Stage4DError("STAGE4A_CANDIDATE_RUN_MANIFEST_MISSING")
    if run_manifest.get("adapter_bundle_sha256") != EXPECTED_ADAPTER_BUNDLE_SHA256:
        raise Stage4DError("STAGE4A_CANDIDATE_ADAPTER_IDENTITY_CHANGED")
    if run_manifest.get("formal_training_seed") != EXPECTED_TRAINING_SEED:
        raise Stage4DError("STAGE4A_CANDIDATE_TRAINING_SEED_CHANGED")
    if run_manifest.get("training_contract_file_sha256") != EXPECTED_TRAINING_CONTRACT_FILE_SHA256:
        raise Stage4DError("STAGE4A_TRAINING_CONTRACT_IDENTITY_CHANGED")
    if run_manifest.get("research_planner_training_plan_domain_sha256") != EXPECTED_TRAINING_PLAN_SHA256:
        raise Stage4DError("STAGE4A_TRAINING_PLAN_IDENTITY_CHANGED")
    if run_manifest.get("diagnostic_only") is not True:
        raise Stage4DError("STAGE4A_CANDIDATE_DIAGNOSTIC_BOUNDARY_CHANGED")
    if run_manifest.get("promotion_eligible") is not False:
        raise Stage4DError("STAGE4A_CANDIDATE_PREMATURE_PROMOTION_ELIGIBILITY")
    if adapter_path.parent.name != EXPECTED_TRAINING_RUN_ID:
        raise Stage4DError("STAGE4A_CANDIDATE_TRAINING_RUN_ID_CHANGED")
    formal_run_manifest_path = Path(candidate_handoff["formal_run_manifest_path"])
    if formal_run_manifest_path.is_symlink() or not formal_run_manifest_path.is_file():
        raise Stage4DError("STAGE4A_FORMAL_RUN_MANIFEST_MISSING")
    if load_json(formal_run_manifest_path) != run_manifest:
        raise Stage4DError("STAGE4A_FORMAL_RUN_MANIFEST_CONTENT_MISMATCH")

    tokenizer = tokenizer_identity(base_model_path)
    tokenizer_sha = sha256_bytes(canonical_json_bytes(tokenizer))
    types["LocalTokenizerPromptRenderer"](
        model_path=str(base_model_path),
        revision=EXPECTED_BASE_REVISION,
        chat_template_sha256=EXPECTED_CHAT_TEMPLATE_SHA256,
        tokenizer_factory=types["HuggingFaceTokenizerFactory"](),
    )

    raw_prompt_source = code_worktree / "src/pchsi/evaluation/raw_policy_prompt.py"
    runtime_core_source = code_worktree / "src/pchsi/evaluation/runtime_core.py"
    parser_source = code_worktree / "src/pchsi/evaluation/raw_policy_parser.py"
    raw_protocol = {
        "schema_id": "CLEAN_SELECT_RAW_PROTOCOL_BINDING_V1",
        "schema_version": 1,
        "fixed_head": EXPECTED_FIXED_HEAD,
        "interface_profile_id": "I1_EXECUTION_PROFILE_V1",
        "select_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "i1_request_schema_sha256": EXPECTED_I1_REQUEST_SCHEMA_SHA256,
        "i1_serialization_schema_sha256": EXPECTED_I1_SERIALIZATION_SCHEMA_SHA256,
        "chat_template_sha256": EXPECTED_CHAT_TEMPLATE_SHA256,
        "raw_policy_prompt_source_sha256": sha256_file(raw_prompt_source),
        "runtime_core_source_sha256": sha256_file(runtime_core_source),
        "raw_policy_parser_source_sha256": sha256_file(parser_source),
        "max_policy_attempts": 60,
        "max_environment_steps": 30,
        "max_consecutive_nonexecuted_attempts": 3,
        "memory": "OFF",
        "harness": "OFF",
    }
    raw_protocol_sha = sha256_bytes(canonical_json_bytes(raw_protocol))

    static_registration = types["SelectStaticLoRARegistrationV1"](
        logical_condition_id=T2_CONDITION_ID,
        checkpoint_instance_id=T2_CONDITION_ID,
        training_seed=EXPECTED_TRAINING_SEED,
        served_model_name=T2_SERVED_NAME,
        adapter_path=str(adapter_path),
        adapter_bundle_sha256=EXPECTED_ADAPTER_BUNDLE_SHA256,
        adapter_rank=16,
    )
    server = types["SelectServerRuntimeManifestV1"](
        schema_id="SELECT_SERVER_RUNTIME_MANIFEST_V1",
        schema_version=1,
        manifest_id="CLEAN_HUMAN_R1_T0_T2_SELECT_SERVER_V1",
        vllm_version="0.11.0",
        base_model_repository=EXPECTED_BASE_REPOSITORY,
        base_model_revision=EXPECTED_BASE_REVISION,
        tokenizer_identity_manifest_sha256=tokenizer_sha,
        chat_template_sha256=EXPECTED_CHAT_TEMPLATE_SHA256,
        dtype="bfloat16",
        tensor_parallel_size=1,
        generation_config_mode="vllm",
        chat_template_content_format="string",
        enable_lora=True,
        max_lora_rank=16,
        max_loras=1,
        max_cpu_loras=1,
        lora_dtype="auto",
        runtime_dynamic_lora_updates=False,
        static_lora_registry=(static_registration,),
    )
    server_sha = sha256_bytes(types["repo_canonical_json_bytes"](server.to_dict()))

    t0_runtime = types["SelectPolicyRuntimeManifestV1"](
        schema_id="SELECT_POLICY_RUNTIME_MANIFEST_V1",
        schema_version=1,
        manifest_id="CLEAN_HUMAN_R1_T0_SELECT_RUNTIME_V1",
        server_runtime_manifest_sha256=server_sha,
        policy_condition_id=PI0_CONDITION_ID,
        logical_condition_id=PI0_CONDITION_ID,
        checkpoint_instance_id=PI0_CONDITION_ID,
        training_seed=None,
        served_model_name=PI0_SERVED_NAME,
        adapter_path=None,
        adapter_bundle_sha256=None,
        adapter_rank=None,
    )
    t2_runtime = types["SelectPolicyRuntimeManifestV1"](
        schema_id="SELECT_POLICY_RUNTIME_MANIFEST_V1",
        schema_version=1,
        manifest_id="CLEAN_HUMAN_R1_T2_SELECT_RUNTIME_V1",
        server_runtime_manifest_sha256=server_sha,
        policy_condition_id=T2_CONDITION_ID,
        logical_condition_id=T2_CONDITION_ID,
        checkpoint_instance_id=T2_CONDITION_ID,
        training_seed=EXPECTED_TRAINING_SEED,
        served_model_name=T2_SERVED_NAME,
        adapter_path=str(adapter_path),
        adapter_bundle_sha256=EXPECTED_ADAPTER_BUNDLE_SHA256,
        adapter_rank=16,
    )
    t0_runtime_sha = sha256_bytes(types["repo_canonical_json_bytes"](t0_runtime.to_dict()))
    t2_runtime_sha = sha256_bytes(types["repo_canonical_json_bytes"](t2_runtime.to_dict()))

    t0_condition = types["PolicyConditionManifestV1"](
        schema_id="POLICY_CONDITION_MANIFEST_V1",
        schema_version=1,
        policy_condition_id=PI0_CONDITION_ID,
        base_model_repository=EXPECTED_BASE_REPOSITORY,
        base_model_revision=EXPECTED_BASE_REVISION,
        checkpoint_kind=types["CheckpointKind"].BASE_MODEL,
        checkpoint_path=None,
        checkpoint_sha256=None,
        training_method=types["TrainingMethod"].NONE,
        training_run_id=None,
        training_config_sha256=None,
        policy_runtime_manifest_sha256=t0_runtime_sha,
        tokenizer_identity_manifest_sha256=tokenizer_sha,
        chat_template_sha256=EXPECTED_CHAT_TEMPLATE_SHA256,
        served_model_name=PI0_SERVED_NAME,
        policy_version="pi0",
        memory_version="MEMORY_M0_V1",
        raw_protocol_sha256=raw_protocol_sha,
        runtime_core_commit=EXPECTED_FIXED_HEAD,
        evaluator_commit=EXPECTED_FIXED_HEAD,
    )
    t2_condition = types["PolicyConditionManifestV1"](
        schema_id="POLICY_CONDITION_MANIFEST_V1",
        schema_version=1,
        policy_condition_id=T2_CONDITION_ID,
        base_model_repository=EXPECTED_BASE_REPOSITORY,
        base_model_revision=EXPECTED_BASE_REVISION,
        checkpoint_kind=types["CheckpointKind"].LORA_ADAPTER,
        checkpoint_path=str(adapter_path),
        checkpoint_sha256=EXPECTED_ADAPTER_BUNDLE_SHA256,
        training_method=types["TrainingMethod"].SFT,
        training_run_id=EXPECTED_TRAINING_RUN_ID,
        training_config_sha256=EXPECTED_TRAINING_CONTRACT_FILE_SHA256,
        policy_runtime_manifest_sha256=t2_runtime_sha,
        tokenizer_identity_manifest_sha256=tokenizer_sha,
        chat_template_sha256=EXPECTED_CHAT_TEMPLATE_SHA256,
        served_model_name=T2_SERVED_NAME,
        policy_version=T2_CONDITION_ID,
        memory_version="MEMORY_M0_V1",
        raw_protocol_sha256=raw_protocol_sha,
        runtime_core_commit=EXPECTED_FIXED_HEAD,
        evaluator_commit=EXPECTED_FIXED_HEAD,
    )
    t0_condition_sha = types["canonical_model_sha256"](t0_condition)
    t2_condition_sha = types["canonical_model_sha256"](t2_condition)

    t0_schedule = types["build_condition_run_schedule"](
        task_access_manifest=task_access,
        task_access_manifest_sha256=task_access_sha,
        policy_condition=t0_condition,
        policy_condition_manifest_sha256=t0_condition_sha,
        run_purpose=types["ConditionRunPurpose"].P4_HARNESS_OFF_SELECT,
        target_access_class=types["DistillationAccessClass"].SELECT_SUMMARY_ONLY,
        replicate_seeds=EXPECTED_SEEDS,
        output_namespace="stage4d_t0_select",
    )
    t2_schedule = types["build_condition_run_schedule"](
        task_access_manifest=task_access,
        task_access_manifest_sha256=task_access_sha,
        policy_condition=t2_condition,
        policy_condition_manifest_sha256=t2_condition_sha,
        run_purpose=types["ConditionRunPurpose"].P4_HARNESS_OFF_SELECT,
        target_access_class=types["DistillationAccessClass"].SELECT_SUMMARY_ONLY,
        replicate_seeds=EXPECTED_SEEDS,
        output_namespace="stage4d_t2_select",
    )
    if t0_schedule.cell_count != EXPECTED_PAIR_CELLS or t2_schedule.cell_count != EXPECTED_PAIR_CELLS:
        raise Stage4DError("CONDITION_SCHEDULE_CELL_COUNT_CHANGED")
    t0_grid = [(c.manifest_index, c.task_id, c.seed) for c in t0_schedule.cells]
    t2_grid = [(c.manifest_index, c.task_id, c.seed) for c in t2_schedule.cells]
    if t0_grid != t2_grid:
        raise Stage4DError("T0_T2_GRID_MISMATCH")
    t0_schedule_sha = types["canonical_model_sha256"](t0_schedule)
    t2_schedule_sha = types["canonical_model_sha256"](t2_schedule)

    environment = build_environment(code_worktree, types)
    environment_sha = types["canonical_model_sha256"](environment)
    gamefiles = {
        "schema_id": "CLEAN_SELECT_GAMEFILE_IDENTITY_MANIFEST_V1",
        "schema_version": 1,
        "dataset_version": "json_2.1.1",
        "record_count": len(gamefile_identity_rows),
        "records": gamefile_identity_rows,
    }
    gamefiles_sha = sha256_bytes(canonical_json_bytes(gamefiles))

    binding_inputs = {
        "schema_id": "STAGE4D_EXISTING_SELECT_LIVE_BINDING_INPUTS_V1",
        "schema_version": 1,
        "round_id": handoff["round_id"],
        "fixed_head": EXPECTED_FIXED_HEAD,
        "fixed_tree": EXPECTED_FIXED_TREE,
        "select_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "select_protocol_file_sha256": EXPECTED_PROTOCOL_FILE_SHA256,
        "train_select_sha256": EXPECTED_TRAIN_SELECT_SHA256,
        "train_update_sha256": EXPECTED_TRAIN_UPDATE_SHA256,
        "train_audit_sha256": EXPECTED_TRAIN_AUDIT_SHA256,
        "base_model_repository": EXPECTED_BASE_REPOSITORY,
        "base_model_revision": EXPECTED_BASE_REVISION,
        "base_model_path": str(base_model_path),
        "candidate_condition_id": T2_CONDITION_ID,
        "candidate_adapter_path": str(adapter_path),
        "candidate_adapter_bundle_sha256": EXPECTED_ADAPTER_BUNDLE_SHA256,
        "candidate_training_plan_sha256": EXPECTED_TRAINING_PLAN_SHA256,
        "candidate_training_contract_file_sha256": EXPECTED_TRAINING_CONTRACT_FILE_SHA256,
        "candidate_handoff_path": str(candidate_handoff_path),
        "interface_profile_id": "I1_EXECUTION_PROFILE_V1",
        "policy_request_schema_sha256": EXPECTED_I1_REQUEST_SCHEMA_SHA256,
        "serialization_schema_sha256": EXPECTED_I1_SERIALIZATION_SCHEMA_SHA256,
        "task_count": EXPECTED_TASK_COUNT,
        "replicate_seeds": list(EXPECTED_SEEDS),
        "paired_task_seed_cells": EXPECTED_PAIR_CELLS,
        "condition_episodes": EXPECTED_CONDITION_EPISODES,
        "historical_access_claim": "ACCESS_HISTORY_INCOMPLETE_CONSERVATIVE",
        "evaluation_execution_authorized": False,
        "promotion_eligible": False,
    }

    artifacts: dict[str, Any] = {
        "BINDING_INPUTS.json": binding_inputs,
        "CLEAN_SELECT_HISTORICAL_ACCESS_AUDIT_V1.json": access_audit.to_dict(),
        "CLEAN_SELECT_TASK_ACCESS_MANIFEST_V1.json": task_access.to_dict(),
        "CLEAN_SELECT_TOKENIZER_IDENTITY_V1.json": tokenizer,
        "CLEAN_SELECT_RAW_PROTOCOL_BINDING_V1.json": raw_protocol,
        "CLEAN_SELECT_GAMEFILE_IDENTITY_MANIFEST_V1.json": gamefiles,
        "SELECT_SERVER_RUNTIME_MANIFEST_V1.json": server.to_dict(),
        "T0_SELECT_POLICY_RUNTIME_MANIFEST_V1.json": t0_runtime.to_dict(),
        "T2_SELECT_POLICY_RUNTIME_MANIFEST_V1.json": t2_runtime.to_dict(),
        "T0_POLICY_CONDITION_MANIFEST_V1.json": t0_condition.to_dict(),
        "T2_POLICY_CONDITION_MANIFEST_V1.json": t2_condition.to_dict(),
        "T0_CONDITION_RUN_SCHEDULE_V1.json": t0_schedule.to_dict(),
        "T2_CONDITION_RUN_SCHEDULE_V1.json": t2_schedule.to_dict(),
        "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1.json": environment.to_dict(),
    }
    artifact_shas = {
        name: sha256_bytes(canonical_json_bytes(value))
        for name, value in artifacts.items()
    }
    binding_identity = {
        "schema_id": "STAGE4D_EXISTING_SELECT_LIVE_BINDING_IDENTITY_V1",
        "schema_version": 1,
        "upstream_fixed_head": EXPECTED_FIXED_HEAD,
        "select_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "artifacts": artifact_shas,
    }
    binding_sha = sha256_bytes(canonical_json_bytes(binding_identity))
    output_root = package_output_root(control_root, binding_sha)

    if output_root.exists():
        verify_existing_output_inventory(output_root)
        identity = load_json(output_root / "BINDING_IDENTITY.json")
        if sha256_bytes(canonical_json_bytes(identity)) != binding_sha:
            raise Stage4DError("EXISTING_STAGE4D_BINDING_IDENTITY_MISMATCH")
        print("STAGE4D_BINDING_ALREADY_EXISTS=true")
        print(f"STAGE4D_BINDING_ROOT={output_root}")
        print(f"STAGE4D_BINDING_SHA256={binding_sha}")
        print("EVALUATION_EXECUTION_AUTHORIZED=false")
        return 0

    output_root.mkdir(parents=True, exist_ok=False)
    for name, value in artifacts.items():
        write_new_json(output_root / name, value)
    write_new_json(output_root / "BINDING_IDENTITY.json", binding_identity)

    live_driver_binding = {
        "schema_id": "STAGE4D_LIVE_DRIVER_BINDING_CANDIDATE_V1",
        "schema_version": 1,
        "binding_root": str(output_root),
        "code_worktree": str(code_worktree),
        "fixed_head": EXPECTED_FIXED_HEAD,
        "existing_evaluator": handoff["existing_evaluator"],
        "existing_result_audit": handoff["existing_result_audit"],
        "select_identity_module": "pchsi.evaluation.select_execution_identity",
        "i1_profile_factory": "build_select_i1_execution_profile",
        "environment_adapter": "pchsi.evaluation.alfworld_adapter.SpawnedAlfworldAdapter",
        "server_mode": "STATIC_BASE_PLUS_SINGLE_LORA",
        "base_served_model_name": PI0_SERVED_NAME,
        "candidate_served_model_name": T2_SERVED_NAME,
        "dynamic_lora_updates": False,
        "scientific_episode_execution_in_this_stage": False,
        "evaluation_execution_authorized": False,
    }
    write_new_json(output_root / "LIVE_DRIVER_BINDING_CANDIDATE_V1.json", live_driver_binding)

    readiness = {
        "schema_id": "STAGE4D_STATIC_READINESS_V1",
        "schema_version": 1,
        "status": "STATIC_BINDING_COMPLETE_SERVER_SMOKE_REQUIRED",
        "binding_sha256": binding_sha,
        "binding_root": str(output_root),
        "typed_server_manifest": True,
        "typed_policy_runtime_manifests": 2,
        "typed_policy_condition_manifests": 2,
        "typed_condition_schedules": 2,
        "environment_runtime_manifest_bound": True,
        "task_count": EXPECTED_TASK_COUNT,
        "condition_cell_count_each": EXPECTED_PAIR_CELLS,
        "condition_episode_count": EXPECTED_CONDITION_EPISODES,
        "model_inference_executed": False,
        "alfworld_execution_count": 0,
        "evaluation_execution_authorized": False,
        "next_gate": "NONSCIENTIFIC_STATIC_SERVER_ROUTE_READINESS_SMOKE",
    }
    write_new_json(output_root / "STAGE4D_STATIC_READINESS_V1.json", readiness)

    lines = []
    for path in sorted(output_root.iterdir()):
        if path.name == "OUTPUT_FILES.sha256" or not path.is_file():
            continue
        lines.append(f"{sha256_file(path)}  {path.name}")
    write_new_bytes(
        output_root / "OUTPUT_FILES.sha256",
        ("\n".join(lines) + "\n").encode("utf-8"),
    )

    print("STAGE4D_STATIC_BINDING_PASS")
    print(f"STAGE4D_BINDING_ROOT={output_root}")
    print(f"STAGE4D_BINDING_SHA256={binding_sha}")
    print(f"TASK_ACCESS_MANIFEST_SHA256={task_access_sha}")
    print(f"SERVER_RUNTIME_MANIFEST_SHA256={server_sha}")
    print(f"T0_POLICY_RUNTIME_MANIFEST_SHA256={t0_runtime_sha}")
    print(f"T2_POLICY_RUNTIME_MANIFEST_SHA256={t2_runtime_sha}")
    print(f"T0_POLICY_CONDITION_MANIFEST_SHA256={t0_condition_sha}")
    print(f"T2_POLICY_CONDITION_MANIFEST_SHA256={t2_condition_sha}")
    print(f"T0_SCHEDULE_SHA256={t0_schedule_sha}")
    print(f"T2_SCHEDULE_SHA256={t2_schedule_sha}")
    print(f"ENVIRONMENT_RUNTIME_MANIFEST_SHA256={environment_sha}")
    print(f"GAMEFILE_IDENTITY_MANIFEST_SHA256={gamefiles_sha}")
    print("EVALUATION_EXECUTION_AUTHORIZED=false")
    print("NEXT_GATE=NONSCIENTIFIC_STATIC_SERVER_ROUTE_READINESS_SMOKE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

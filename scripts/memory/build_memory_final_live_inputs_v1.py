#!/usr/bin/env python3
"""Discover frozen assets and build all Memory FINAL live inputs pre-outcome.

This program does not call a model, execute ALFWorld, inspect task outcomes, or
modify Memory. It binds the already published Package-2 code to:
- the protected task-access authority;
- the exact pi1/Train17 runtime identity;
- the calibrated immutable Failure Memory snapshot;
- the registered Formal-A source states;
- outcome-blind Stage 1B/2/3 panels and decision rules.

Stage 1B: 3 registered source states x FM0/FM1/FM2/FM3 (12 cells).
Stage 2: 60 deterministic TRAIN_MEMORY_SOURCE tasks x S0/S1/S2/S3 (240 cells).
Stage 3: all 140 valid_seen + 134 valid_unseen x FM0/FM1/FM2/FM3
         (1096 cells; valid_seen is the registered primary split).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.scientific_decision import (
    FM0, FM1, FM2, FM3, ROUND_ACTIVE,
    STAGE_1B, STAGE_2, STAGE_3,
)
from pchsi.memory.token_budget_contract import (
    FailureMemoryTokenBudgetContractV1,
)

PROTECTED_TASK_ACCESS_SHA256 = (
    "260766366d72a9af7b0b4809d30a45bb"
    "56f42134dad66b29a4b61ff7ed4793ea"
)
ACTIVE_SNAPSHOT_SHA256 = (
    "8ebdf8feaa3f52874addcfc6541d1b29c"
    "bf5d124ea68fd0da0fc2ba037085189"
)
TOKEN_BUDGET_SHA256 = (
    "613166c9f092795cb03c892ee0046f0af"
    "5bf7fc13ba44f7fccb950027c329262"
)
EXPECTED_FAMILIES = (
    "look_at_obj_in_light",
    "pick_and_place_simple",
    "pick_clean_then_place_in_recep",
    "pick_heat_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_two_obj_and_place",
)


def _dsha(domain: str, value: dict[str, object], field: str) -> str:
    payload = dict(value)
    payload.pop(field, None)
    return hashlib.sha256(
        domain.encode("utf-8") + b"\0" + canonical_json_bytes(payload)
    ).hexdigest()


def _write_new(path: Path, value: object) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit("STOP=FINAL_INPUT_OUTPUT_EXISTS:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit("STOP=FINAL_INPUT_OUTPUT_EXISTS:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = b"".join(canonical_json_bytes(row) for row in rows)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _object(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
        raise ValueError("not canonical JSON object: " + str(path))
    return value


def _candidate_files(roots: tuple[Path, ...]) -> tuple[Path, ...]:
    result = []
    seen = set()
    prune = {
        ".git", "__pycache__", ".pytest_cache", "node_modules", "build",
        "conda_envs", "site-packages", "live_cells", "stage_authorities",
        "paper_evidence",
    }
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            dirnames[:] = [name for name in dirnames if name not in prune]
            # Limit accidental walks into large raw result trees.
            relative_depth = len(Path(dirpath).relative_to(root).parts)
            if relative_depth > 11:
                dirnames[:] = []
            for name in filenames:
                if not (
                    name.endswith(".json")
                    or name.endswith(".jsonl")
                    or name.endswith(".manifest")
                ):
                    continue
                path = Path(dirpath) / name
                try:
                    if path.is_symlink() or not path.is_file():
                        continue
                    if path.stat().st_size <= 0 or path.stat().st_size > 128 * 1024 * 1024:
                        continue
                    key = str(path.resolve())
                except OSError:
                    continue
                if key not in seen:
                    seen.add(key)
                    result.append(path.resolve())
    return tuple(sorted(result, key=str))


def _find_by_sha(
    files: tuple[Path, ...],
    expected: str,
    *,
    override_env: str | None = None,
) -> Path:
    if override_env and os.environ.get(override_env):
        path = Path(os.environ[override_env]).resolve()
        if path.is_symlink() or not path.is_file() or sha256_file(path) != expected:
            raise SystemExit("STOP=OVERRIDE_SHA_MISMATCH:" + override_env)
        return path
    matches = []
    for path in files:
        try:
            if sha256_file(path) == expected:
                matches.append(path)
        except OSError:
            continue
    if not matches:
        raise SystemExit("STOP=BOUND_SHA_NOT_FOUND:" + expected)
    # Multiple byte-identical copies are operationally harmless.
    return sorted(matches, key=lambda p: (len(str(p)), str(p)))[0]


def _resolve_token_budget_contract_v1(
    *,
    files: tuple[Path, ...],
    expected_contract_sha256: str,
    override_env: str | None,
) -> Path:
    def load_contract(path: Path) -> FailureMemoryTokenBudgetContractV1:
        if path.is_symlink() or not path.is_file():
            raise ValueError("token-budget contract path invalid")
        raw = path.read_bytes()
        return FailureMemoryTokenBudgetContractV1.from_json(raw)

    if override_env and os.environ.get(override_env):
        path = Path(os.environ[override_env]).resolve()
        try:
            contract = load_contract(path)
        except Exception as exc:
            raise SystemExit(
                "STOP=OVERRIDE_TOKEN_BUDGET_CONTRACT_INVALID:"
                + override_env
            ) from exc
        if contract.contract_sha256 != expected_contract_sha256:
            raise SystemExit(
                "STOP=OVERRIDE_TOKEN_BUDGET_CONTRACT_SHA_MISMATCH:"
                + override_env
            )
        return path

    matches: list[Path] = []
    raw_shas: set[str] = set()
    for path in files:
        try:
            contract = load_contract(path)
        except Exception:
            continue
        if contract.contract_sha256 == expected_contract_sha256:
            matches.append(path)
            raw_shas.add(sha256_file(path))

    if not matches:
        raise SystemExit(
            "STOP=TOKEN_BUDGET_CONTRACT_NOT_FOUND:"
            + expected_contract_sha256
        )
    if len(raw_shas) != 1:
        raise SystemExit("STOP=TOKEN_BUDGET_CONTRACT_CONTENT_CONFLICT")

    return sorted(
        matches,
        key=lambda p: (len(str(p)), str(p)),
    )[0]


def _find_schema(
    files: tuple[Path, ...],
    schema_id: str,
    *,
    override_env: str | None = None,
) -> Path:
    if override_env and os.environ.get(override_env):
        path = Path(os.environ[override_env]).resolve()
        if _object(path).get("schema_id") != schema_id:
            raise SystemExit("STOP=OVERRIDE_SCHEMA_MISMATCH:" + override_env)
        return path
    rows = []
    for path in files:
        try:
            value = _object(path)
        except Exception:
            continue
        if value.get("schema_id") == schema_id:
            rows.append((sha256_file(path), path))
    if not rows:
        raise SystemExit("STOP=SCHEMA_NOT_FOUND:" + schema_id)
    unique = {sha for sha, _ in rows}
    if len(unique) != 1:
        raise SystemExit("STOP=SCHEMA_CONTENT_CONFLICT:" + schema_id)
    return sorted((path for _, path in rows), key=lambda p: (len(str(p)), str(p)))[0]


def _find_source_runtime(
    files: tuple[Path, ...],
) -> Path:
    if os.environ.get("FAILURE_MEMORY_SOURCE_RUNTIME_BINDING"):
        path = Path(os.environ["FAILURE_MEMORY_SOURCE_RUNTIME_BINDING"]).resolve()
        value = _object(path)
        if value.get("schema_id") != "FAILURE_MEMORY_SOURCE_COLLECTION_RUNTIME_BINDING_V1":
            raise SystemExit("STOP=SOURCE_RUNTIME_OVERRIDE_SCHEMA")
        return path
    candidates = []
    for path in files:
        try:
            value = _object(path)
        except Exception:
            continue
        if (
            value.get("schema_id")
            == "FAILURE_MEMORY_SOURCE_COLLECTION_RUNTIME_BINDING_V1"
            and value.get("served_model_name") == "P4-R1-Q2-BAD-TRAIN17"
            and value.get("vllm_version") == "0.11.0"
            and Path(str(value.get("base_model_local_path", ""))).is_dir()
            and Path(str(value.get("adapter_path", ""))).is_dir()
        ):
            candidates.append(path)
    if not candidates:
        raise SystemExit("STOP=SOURCE_RUNTIME_BINDING_NOT_FOUND")
    core_fields = (
        "served_model_name",
        "policy_runtime_manifest_sha256",
        "adapter_bundle_sha256",
        "base_model_local_path",
        "adapter_path",
        "vllm_version",
        "chat_template_sha256",
        "environment_runtime_manifest_sha256",
    )
    signatures = {
        tuple(_object(path).get(field) for field in core_fields)
        for path in candidates
    }
    if len(signatures) != 1:
        raise SystemExit("STOP=SOURCE_RUNTIME_CORE_IDENTITY_CONFLICT")
    return sorted(candidates, key=lambda p: (len(str(p)), str(p)))[0]


def _find_a0_binding(files: tuple[Path, ...], manifest: dict[str, object]) -> Path:
    matches = []
    source_ids = {
        str(cell["source_state_id"])
        for cell in manifest["cells"]
    }
    for path in files:
        try:
            value = _object(path)
        except Exception:
            continue
        sources = value.get("sources")
        if not isinstance(sources, list):
            continue
        observed = {
            str(row.get("source_state_id"))
            for row in sources
            if isinstance(row, dict)
        }
        if observed == source_ids and all(
            isinstance(row, dict)
            and isinstance(row.get("replay_source_path"), str)
            and isinstance(row.get("representation_template_path"), str)
            for row in sources
        ):
            matches.append(path)
    if not matches:
        raise SystemExit("STOP=A0_INPUT_BINDING_NOT_FOUND")
    canonical = {sha256_file(path) for path in matches}
    if len(canonical) != 1:
        raise SystemExit("STOP=A0_INPUT_BINDING_CONFLICT")
    return sorted(matches, key=lambda p: (len(str(p)), str(p)))[0]


def _protected_records(path: Path) -> list[dict[str, object]]:
    rows = []
    for number, raw in enumerate(path.read_bytes().splitlines(keepends=True), 1):
        value = strict_json_loads(raw)
        if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
            raise SystemExit(f"STOP=PROTECTED_TASK_ACCESS_ROW:{number}")
        rows.append(value)
    counts = defaultdict(int)
    for row in rows:
        counts[str(row["access_class"])] += 1
    expected = {
        "TRAIN_MEMORY_SOURCE": 2367,
        "TRAIN_RETRIEVAL_DEV": 1186,
        "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 140,
        "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED": 134,
    }
    if dict(counts) != expected:
        raise SystemExit("STOP=PROTECTED_TASK_ACCESS_COUNTS:" + repr(dict(counts)))
    return rows


def _dataset_root(
    *,
    repo: Path,
    work: Path,
    protected: Path,
    roots: tuple[Path, ...],
    files: tuple[Path, ...],
) -> Path:
    if os.environ.get("FAILURE_MEMORY_DATASET_ROOT"):
        root = Path(os.environ["FAILURE_MEMORY_DATASET_ROOT"]).resolve()
    else:
        candidates = []
        for path in files:
            try:
                value = _object(path)
            except Exception:
                continue
            if value.get("schema_id") == "FAILURE_MEMORY_SOURCE_DATASET_ROOT_BINDING_V1":
                candidates.append(Path(str(value["dataset_root"])).resolve())
        candidates = sorted({str(path): path for path in candidates}.values(), key=str)
        if len(candidates) == 1:
            root = candidates[0]
        else:
            binding = work / "SOURCE_DATASET_ROOT_BINDING_V1.json"
            command = [
                sys.executable,
                str(repo / "scripts/memory/discover_source_dataset_root_v1.py"),
                "--protected-task-access-manifest", str(protected),
            ]
            for item in roots:
                command.extend(["--search-root", str(item)])
            command.extend(["--output", str(binding)])
            subprocess.run(command, check=True)
            root = Path(str(_object(binding)["dataset_root"])).resolve()
    if root.is_symlink() or not root.is_dir():
        raise SystemExit("STOP=FINAL_DATASET_ROOT_INVALID")
    return root


def _resolve_active_snapshot_manifest_v1(
    *,
    active_snapshot_dir: Path,
    expected_snapshot_sha256: str,
) -> Path:
    # MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V2 has a reserved semantic manifest
    # filename. Do not recursively search arbitrary JSON objects carrying
    # snapshot_sha256: snapshot_files.json legitimately carries the same
    # semantic SHA but is the file-census manifest.
    path = Path(active_snapshot_dir) / "snapshot.json"
    try:
        value = _object(path)
    except Exception as exc:
        raise SystemExit(
            "STOP=ACTIVE_SNAPSHOT_MANIFEST_INVALID:" + str(path)
        ) from exc
    if (
        value.get("schema_id") != "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V2"
        or value.get("schema_version") != 2
    ):
        raise SystemExit("STOP=ACTIVE_SNAPSHOT_MANIFEST_SCHEMA")
    if value.get("snapshot_sha256") != expected_snapshot_sha256:
        raise SystemExit("STOP=ACTIVE_SNAPSHOT_MANIFEST_SHA_MISMATCH")
    return path


def _task_entry(record: dict[str, object], dataset_root: Path, seed: int) -> dict[str, object]:
    gamefile = (dataset_root / str(record["dataset_relative_gamefile"])).resolve()
    try:
        gamefile.relative_to(dataset_root)
    except ValueError as exc:
        raise SystemExit("STOP=FINAL_GAMEFILE_ESCAPE") from exc
    if gamefile.is_symlink() or not gamefile.is_file():
        raise SystemExit("STOP=FINAL_GAMEFILE_MISSING:" + str(gamefile))
    if sha256_file(gamefile) != record["gamefile_sha256"]:
        raise SystemExit("STOP=FINAL_GAMEFILE_SHA:" + str(gamefile))
    return {
        "task_id": record["task_gamefile_group_id"],
        "task_family": record["task_type"],
        "split": record["access_class"],
        "start_mode": "TASK_RESET",
        "absolute_gamefile": str(gamefile),
        "gamefile_sha256": record["gamefile_sha256"],
        "dataset_relative_gamefile": record["dataset_relative_gamefile"],
        "continuation_seed": seed,
    }


def _self_hashed(
    schema_id: str,
    semantic_field: str,
    value: dict[str, object],
) -> dict[str, object]:
    result = {"schema_id": schema_id, "schema_version": 1, semantic_field: "0" * 64, **value}
    result[semantic_field] = _dsha(schema_id, result, semantic_field)
    return result


def _cell_id(stage: str, group: str, condition: str, round_index: int | None) -> str:
    return hashlib.sha256(
        b"FAILURE_MEMORY_FINAL_CELL_ID_V1\0"
        + canonical_json_bytes({
            "stage": stage,
            "comparison_group_id": group,
            "condition": condition,
            "round_index": round_index,
        })
    ).hexdigest()


def _schedule(stage: str, rows: list[dict[str, object]]) -> dict[str, object]:
    return _self_hashed(
        "FAILURE_MEMORY_FINAL_SCHEDULE_V1",
        "schedule_sha256",
        {
            "stage": stage,
            "cell_ids": [row["cell_id"] for row in rows],
            "execution_order": "CELL_MANIFEST_ORDER_V1",
            "continuation_seed_policy": "FIXED_17_FOR_TASK_RESET_A0_REGISTERED_FOR_SOURCE_STATE",
            "preoutcome_frozen": True,
        },
    )


def _run(command: list[str]) -> None:
    print("RUN=" + " ".join(command), flush=True)
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--fixed-head", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--execution-mode", choices=("local", "slurm"), default="local")
    parser.add_argument("--max-parallel", type=int, default=8)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    work = Path(args.work_root).resolve()
    if work.exists() or work.is_symlink():
        raise SystemExit("STOP=FINAL_INPUT_WORK_ROOT_EXISTS")
    work.mkdir(parents=True, mode=0o700)
    if subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() != args.fixed_head:
        raise SystemExit("STOP=FINAL_INPUT_FIXED_HEAD_MISMATCH")

    scripts_root = Path(os.environ.get(
        "PCHSI_SCRIPTS_ROOT",
        "/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts",
    )).resolve()
    roots = tuple(dict.fromkeys([
        repo,
        scripts_root,
        Path("/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts"),
        Path("/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts"),
    ]))
    files = _candidate_files(roots)

    protected = _find_by_sha(
        files,
        PROTECTED_TASK_ACCESS_SHA256,
        override_env="FAILURE_MEMORY_PROTECTED_TASK_ACCESS_MANIFEST",
    )
    records = _protected_records(protected)
    dataset_root = _dataset_root(
        repo=repo, work=work, protected=protected, roots=roots, files=files,
    )

    source_runtime_path = _find_source_runtime(files)
    source_runtime = _object(source_runtime_path)
    a0_runtime_path = _find_schema(
        files,
        "FORMAL_A0_RUNTIME_BINDING_V1",
        override_env="FAILURE_MEMORY_A0_RUNTIME_BINDING",
    )
    a0_manifest_path = _find_schema(
        files,
        "MEMORY_A0_SCIENTIFIC_MANIFEST_V1",
        override_env="FAILURE_MEMORY_A0_MANIFEST",
    )
    a0_manifest = _object(a0_manifest_path)
    a0_binding_path = (
        Path(os.environ["FAILURE_MEMORY_A0_INPUT_BINDING"]).resolve()
        if os.environ.get("FAILURE_MEMORY_A0_INPUT_BINDING")
        else _find_a0_binding(files, a0_manifest)
    )
    a0_binding = _object(a0_binding_path)

    dependency = _object(repo / "configs/memory/package_b_failure_memory_dependency_v1.json")
    if dependency["active_snapshot_sha256"] != ACTIVE_SNAPSHOT_SHA256:
        raise SystemExit("STOP=ACTIVE_SNAPSHOT_IDENTITY_CHANGED")
    active_snapshot_dir = Path(str(dependency["active_snapshot_external_directory"])).resolve()
    if active_snapshot_dir.is_symlink() or not active_snapshot_dir.is_dir():
        raise SystemExit("STOP=ACTIVE_SNAPSHOT_DIRECTORY_INVALID")

    snapshot_manifest_path = _resolve_active_snapshot_manifest_v1(
        active_snapshot_dir=active_snapshot_dir,
        expected_snapshot_sha256=ACTIVE_SNAPSHOT_SHA256,
    )

    snapshot_related_files = _candidate_files((
        active_snapshot_dir,
        active_snapshot_dir.parent,
        active_snapshot_dir.parent.parent,
    ))
    all_files = tuple(sorted(
        {str(path): path for path in (*files, *snapshot_related_files)}.values(),
        key=str,
    ))
    token_budget_path = _resolve_token_budget_contract_v1(
        files=all_files,
        expected_contract_sha256=TOKEN_BUDGET_SHA256,
        override_env="FAILURE_MEMORY_TOKEN_BUDGET_CONTRACT",
    )
    b_result_path = repo / "configs/memory/formal_b_minimal_q3_result_authority_v1.json"
    a0_result_path = repo / "configs/memory/formal_a0_result_authority_v1.json"
    program_path = repo / "configs/memory/failure_memory_scientific_program_freeze_v1.json"
    protocol_path = repo / "configs/memory/failure_memory_live_closure_contract_v2.json"
    stage0_path = _find_schema(
        files,
        "FAILURE_MEMORY_STAGE0_ROLE_RETRIEVAL_RESULT_V1",
        override_env="FAILURE_MEMORY_STAGE0_RESULT",
    )

    raw_evidence_root = work / "raw_cell_evidence"
    raw_evidence_root.mkdir()

    runtime_identity = _self_hashed(
        "FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1",
        "runtime_identity_sha256",
        {
            "source_runtime_binding_path": str(source_runtime_path),
            "source_runtime_binding_sha256": sha256_file(source_runtime_path),
            "a0_runtime_binding_path": str(a0_runtime_path),
            "a0_runtime_binding_sha256": sha256_file(a0_runtime_path),
            "active_snapshot_directory": str(active_snapshot_dir),
            "active_snapshot_sha256": ACTIVE_SNAPSHOT_SHA256,
            "token_budget_contract_path": str(token_budget_path),
            "token_budget_contract_sha256": TOKEN_BUDGET_SHA256,
            "formal_b_result_path": str(b_result_path),
            "formal_b_result_sha256": sha256_file(b_result_path),
            "raw_cell_evidence_root": str(raw_evidence_root),
            "vllm_version": source_runtime["vllm_version"],
            "served_model_name": source_runtime["served_model_name"],
            "preoutcome_frozen": True,
        },
    )
    runtime_identity_path = work / "FINAL_RUNTIME_IDENTITY_V1.json"
    _write_new(runtime_identity_path, runtime_identity)

    policy_identity = _self_hashed(
        "FAILURE_MEMORY_FINAL_POLICY_IDENTITY_V1",
        "policy_identity_sha256",
        {
            "logical_condition_id": source_runtime["logical_condition_id"],
            "checkpoint_instance_id": source_runtime["checkpoint_instance_id"],
            "training_seed": source_runtime["training_seed"],
            "served_model_name": source_runtime["served_model_name"],
            "adapter_bundle_sha256": source_runtime["adapter_bundle_sha256"],
            "policy_runtime_manifest_sha256": source_runtime[
                "policy_runtime_manifest_sha256"
            ],
            "memory_mode": "CELL_CONDITION_BOUND",
            "harness_mode": "HARNESS_OFF",
        },
    )
    policy_identity_path = work / "FINAL_POLICY_IDENTITY_V1.json"
    _write_new(policy_identity_path, policy_identity)

    environment_identity = _self_hashed(
        "FAILURE_MEMORY_FINAL_ENVIRONMENT_IDENTITY_V1",
        "environment_identity_sha256",
        {
            "environment_runtime_manifest_sha256": source_runtime[
                "environment_runtime_manifest_sha256"
            ],
            "dataset_root": str(dataset_root),
            "protected_task_access_manifest_sha256": PROTECTED_TASK_ACCESS_SHA256,
            "alfworld_batch_size": 1,
            "task_success_authority": "ALFWORLD_DONE_AND_WON",
        },
    )
    environment_identity_path = work / "FINAL_ENVIRONMENT_IDENTITY_V1.json"
    _write_new(environment_identity_path, environment_identity)

    # Stage 1B: exact registered source-state representation comparison.
    source_by_id = {str(row["source_state_id"]): row for row in a0_binding["sources"]}
    stage1_entries = []
    stage1_rows = []
    for source_state_id in sorted({
        str(cell["source_state_id"]) for cell in a0_manifest["cells"]
    }):
        source_row = source_by_id[source_state_id]
        stage1_entries.append({
            "task_id": source_state_id,
            "task_family": "registered_source_state",
            "split": "TRAIN_RETRIEVAL_DEV",
            "start_mode": "REGISTERED_SOURCE_STATE",
            "source_state_id": source_state_id,
            "source_task_id": next(
                cell["source_task_id"]
                for cell in a0_manifest["cells"]
                if cell["source_state_id"] == source_state_id
            ),
            "a0_manifest_path": str(a0_manifest_path),
            "a0_binding_path": str(a0_binding_path),
            "representation_template_path": source_row[
                "representation_template_path"
            ],
            "continuation_seed": next(
                int(cell["continuation_seed"])
                for cell in a0_manifest["cells"]
                if cell["source_state_id"] == source_state_id
            ),
        })
        for condition in (FM0, FM1, FM2, FM3):
            stage1_rows.append({
                "cell_id": _cell_id(STAGE_1B, source_state_id, condition, None),
                "comparison_group_id": source_state_id,
                "condition": condition,
                "round_index": None,
                "split": "TRAIN_RETRIEVAL_DEV",
                "task_id": source_state_id,
                "task_family": "registered_source_state",
                "snapshot_sha256": ACTIVE_SNAPSHOT_SHA256,
            })

    # Stage 2: 10 deterministic tasks per ALFWorld family.
    train_by_family = defaultdict(list)
    for row in records:
        if row["access_class"] == "TRAIN_MEMORY_SOURCE":
            train_by_family[str(row["task_type"])].append(row)
    if set(train_by_family) != set(EXPECTED_FAMILIES):
        raise SystemExit("STOP=TRAIN_FAMILY_POPULATION_MISMATCH")
    stage2_records = []
    for family in EXPECTED_FAMILIES:
        candidates = sorted(
            train_by_family[family],
            key=lambda row: str(row["task_gamefile_group_id"]),
        )
        if len(candidates) < 10:
            raise SystemExit("STOP=STAGE2_FAMILY_TOO_SMALL:" + family)
        stage2_records.extend(candidates[:10])
    stage2_entries = [_task_entry(row, dataset_root, 17) for row in stage2_records]

    snapshot_entries = []
    active_member_count = len(_object(snapshot_manifest_path)["members"])
    if active_member_count < 3:
        raise SystemExit("STOP=ACTIVE_SNAPSHOT_REQUIRES_THREE_MEMBERS")
    for round_index, limit in enumerate((0, 1, 2, 3)):
        if limit == 3 and active_member_count == 3:
            logical_sha = ACTIVE_SNAPSHOT_SHA256
        else:
            logical_sha = hashlib.sha256(
                b"FAILURE_MEMORY_LOGICAL_ROUND_SNAPSHOT_V1\0"
                + canonical_json_bytes({
                    "active_snapshot_sha256": ACTIVE_SNAPSHOT_SHA256,
                    "round_index": round_index,
                    "member_limit": limit,
                })
            ).hexdigest()
        snapshot_entries.append({
            "round_index": round_index,
            "member_limit": limit,
            "snapshot_sha256": logical_sha,
            "active_snapshot_sha256": ACTIVE_SNAPSHOT_SHA256,
            "writeback_policy": "NO_SAME_ROUND_READBACK",
        })
    snapshot_registry = _self_hashed(
        "FAILURE_MEMORY_FINAL_SNAPSHOT_REGISTRY_V1",
        "registry_sha256",
        {
            "active_snapshot_manifest_path": str(snapshot_manifest_path),
            "active_snapshot_sha256": ACTIVE_SNAPSHOT_SHA256,
            "entries": snapshot_entries,
            "rounds_contiguous": True,
        },
    )
    snapshot_registry_path = work / "FINAL_SNAPSHOT_REGISTRY_V1.json"
    _write_new(snapshot_registry_path, snapshot_registry)

    stage2_rows = []
    for entry in stage2_entries:
        group = str(entry["task_id"])
        for snap in snapshot_entries:
            round_index = int(snap["round_index"])
            stage2_rows.append({
                "cell_id": _cell_id(
                    STAGE_2, group, ROUND_ACTIVE, round_index
                ),
                "comparison_group_id": group,
                "condition": ROUND_ACTIVE,
                "round_index": round_index,
                "split": "TRAIN_MEMORY_SOURCE",
                "task_id": group,
                "task_family": entry["task_family"],
                "snapshot_sha256": snap["snapshot_sha256"],
            })

    # Stage 3: all protected valid_seen and valid_unseen identities.
    stage3_records = [
        row for row in records
        if row["access_class"] in {
            "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED",
            "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED",
        }
    ]
    stage3_entries = [_task_entry(row, dataset_root, 17) for row in stage3_records]
    stage3_rows = []
    split_map = {
        "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": "VALID_SEEN",
        "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED": "VALID_UNSEEN",
    }
    for entry in stage3_entries:
        group = str(entry["task_id"])
        for condition in (FM0, FM1, FM2, FM3):
            stage3_rows.append({
                "cell_id": _cell_id(STAGE_3, group, condition, None),
                "comparison_group_id": group,
                "condition": condition,
                "round_index": None,
                "split": split_map[str(entry["split"])],
                "task_id": group,
                "task_family": entry["task_family"],
                "snapshot_sha256": ACTIVE_SNAPSHOT_SHA256,
            })

    panels = {
        "stage1b": _self_hashed(
            "FAILURE_MEMORY_FINAL_PANEL_V1", "panel_sha256",
            {"stage": STAGE_1B, "entries": stage1_entries, "preoutcome_frozen": True},
        ),
        "stage2": _self_hashed(
            "FAILURE_MEMORY_FINAL_PANEL_V1", "panel_sha256",
            {"stage": STAGE_2, "entries": stage2_entries, "preoutcome_frozen": True},
        ),
        "stage3": _self_hashed(
            "FAILURE_MEMORY_FINAL_PANEL_V1", "panel_sha256",
            {"stage": STAGE_3, "entries": stage3_entries, "preoutcome_frozen": True},
        ),
    }
    rows_by_stage = {
        "stage1b": (STAGE_1B, stage1_rows),
        "stage2": (STAGE_2, stage2_rows),
        "stage3": (STAGE_3, stage3_rows),
    }

    stage_artifacts = {}
    executor = repo / "scripts/memory/run_memory_live_cell_executor_v1.py"
    for name, (stage, stage_rows) in rows_by_stage.items():
        root = work / name
        root.mkdir()
        panel_path = root / "PANEL_V1.json"
        cells_path = root / "CELLS_V1.jsonl"
        schedule_path = root / "SCHEDULE_V1.json"
        rule_path = root / "DECISION_RULE_V1.json"
        execution_path = root / "EXECUTION_MANIFEST_V2.json"
        _write_new(panel_path, panels[name])
        _write_jsonl(cells_path, stage_rows)
        _write_new(schedule_path, _schedule(stage, stage_rows))

        rule_command = [
            sys.executable,
            str(repo / "scripts/memory/freeze_memory_decision_rule_v1.py"),
            "--stage", stage,
            "--cell-manifest", str(cells_path),
            "--output", str(rule_path),
        ]
        if stage == STAGE_3:
            rule_command.extend(["--primary-split", "VALID_SEEN"])
        _run(rule_command)

        command = [
            sys.executable,
            str(repo / "scripts/memory/build_memory_live_execution_manifest_v2.py"),
            "--stage", stage,
            "--fixed-head", args.fixed_head,
            "--scientific-protocol", str(protocol_path),
            "--scientific-program", str(program_path),
            "--runtime-identity", str(runtime_identity_path),
            "--policy-identity", str(policy_identity_path),
            "--environment-identity", str(environment_identity_path),
            "--panel", str(panel_path),
            "--schedule", str(schedule_path),
            "--cell-manifest", str(cells_path),
            "--cell-executor", str(executor),
            "--decision-rule", str(rule_path),
            "--executor-code-approval",
            "CODE_APPROVED_FAILURE_MEMORY_LIVE_CELL_EXECUTOR_V1",
            "--output", str(execution_path),
        ]
        if stage == STAGE_2:
            command.extend(["--snapshot-registry", str(snapshot_registry_path)])
        else:
            command.extend(["--snapshot", str(snapshot_manifest_path)])
        _run(command)
        stage_artifacts[name] = execution_path

    program = _object(program_path)
    closure_manifest = work / "FAILURE_MEMORY_CLOSURE_EXECUTION_MANIFEST_V1.json"
    live_output_root = work / "live_cells"
    closure_output_root = work / "closure"
    _run([
        sys.executable,
        str(repo / "scripts/memory/build_memory_closure_manifest_v1.py"),
        "--fixed-head", args.fixed_head,
        "--scientific-program-sha256", str(program["program_sha256"]),
        "--stage0-result", str(stage0_path),
        "--a0-result", str(a0_result_path),
        "--b-result", str(b_result_path),
        "--stage1b-execution-manifest", str(stage_artifacts["stage1b"]),
        "--stage2-execution-manifest", str(stage_artifacts["stage2"]),
        "--stage3-execution-manifest", str(stage_artifacts["stage3"]),
        "--live-output-root", str(live_output_root),
        "--closure-output-root", str(closure_output_root),
        "--execution-mode", args.execution_mode,
        "--max-parallel", str(args.max_parallel),
        "--output", str(closure_manifest),
    ])

    asset_manifest = _self_hashed(
        "FAILURE_MEMORY_FINAL_INPUT_ASSET_MANIFEST_V1",
        "manifest_sha256",
        {
            "fixed_head": args.fixed_head,
            "protected_task_access_path": str(protected),
            "protected_task_access_sha256": PROTECTED_TASK_ACCESS_SHA256,
            "dataset_root": str(dataset_root),
            "source_runtime_binding_path": str(source_runtime_path),
            "a0_runtime_binding_path": str(a0_runtime_path),
            "a0_manifest_path": str(a0_manifest_path),
            "a0_input_binding_path": str(a0_binding_path),
            "active_snapshot_manifest_path": str(snapshot_manifest_path),
            "active_snapshot_sha256": ACTIVE_SNAPSHOT_SHA256,
            "token_budget_contract_path": str(token_budget_path),
            "stage1b_cell_count": len(stage1_rows),
            "stage2_cell_count": len(stage2_rows),
            "stage3_cell_count": len(stage3_rows),
            "closure_manifest_path": str(closure_manifest),
            "preoutcome_frozen": True,
        },
    )
    _write_new(work / "FINAL_INPUT_ASSET_MANIFEST_V1.json", asset_manifest)

    print("FAILURE_MEMORY_FINAL_LIVE_INPUTS_V1_PASS")
    print("STAGE1B_CELL_COUNT=" + str(len(stage1_rows)))
    print("STAGE2_CELL_COUNT=" + str(len(stage2_rows)))
    print("STAGE3_CELL_COUNT=" + str(len(stage3_rows)))
    print("CLOSURE_MANIFEST=" + str(closure_manifest))
    print("FINAL_INPUT_ROOT=" + str(work))


if __name__ == "__main__":
    main()

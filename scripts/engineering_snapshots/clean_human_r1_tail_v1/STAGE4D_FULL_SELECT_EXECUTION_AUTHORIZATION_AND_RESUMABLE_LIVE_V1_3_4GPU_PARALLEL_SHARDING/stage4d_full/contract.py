from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_FIXED_HEAD = "ede426ffb069bd887bd3caf847add8193c801d60"
EXPECTED_FIXED_TREE = "4460d1dd9b653258906ef0e625e5af7d7edbc338"
EXPECTED_PROTOCOL_SHA256 = "fcc798b70317d544dd205bb454c2e5017a7460473bd390a13af38b857ab0e1bf"
EXPECTED_BINDING_SHA256 = "4ab7942b2c66238cb3833bdb04eb7f7ca23b52d10c388575aaf1bd272dfc100d"
EXPECTED_READINESS_RECEIPT_SHA256 = "3958caccae90b3a7d990022e93539897c94dd7d04695948a962b593553bfee8a"
EXPECTED_TASK_COUNT = 355
EXPECTED_SEEDS = (17, 31, 47, 73, 101)
EXPECTED_PAIR_CELLS = 1775
EXPECTED_TOTAL_CELLS = 3550
PI0_SERVED_NAME = "Qwen2.5-3B-Instruct-E1"
T2_SERVED_NAME = "PI1_HUMAN_T2_DIAGNOSTIC_CANDIDATE"
EXPECTED_ADAPTER_SHA256 = "d1785b530043a1314d873bdfadd2c889bd1c073067d91a31a8429f52f6b60593"
EXPECTED_I1_REQUEST_SCHEMA_SHA256 = "f2dd1cc61bca16110be41c00245eee85f7ef1e6a36a73dd52789de0060a63f77"

EXPECTED_BINDING_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/"
    "stage4d_existing_select_live_binding_v1/"
    + EXPECTED_BINDING_SHA256
)
EXPECTED_READINESS_RECEIPT = (
    EXPECTED_BINDING_ROOT / "readiness/RUNTIME_READINESS_156385_V1.json"
)
EXECUTION_PARENT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/"
    "stage4d_existing_select_live_execution_v1"
)
LOG_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/logs/"
    "stage4d_existing_select_live_execution_v1"
)

READINESS_PACKAGE_ROOT = Path(
    "/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/"
    "STAGE4D_EXISTING_SELECT_LIVE_BINDING_AND_READINESS_V1_1_PROTOCOL_FIELD_FIX"
)
EXPECTED_READINESS_PY_SHA256 = "bab901718dd66d9708808e41ba2a160ca81bd4eb7d42f81f918d92273f7d7fd8"
EXPECTED_READINESS_COMMON_SHA256 = "aa47773ef40847c40cf7fbe2ec2819ba61266718d62a59b7c2543b40a1116156"

LEGACY_LIVE_RUNNER_RELATIVE = (
    "scripts/engineering_snapshots/stage0/"
    "human_pilot_stage0_offoff_execution_and_closeout_v1_9/"
    "stage0/live_runner.py"
)
LEGACY_PACKAGE_PARENT_RELATIVE = (
    "scripts/engineering_snapshots/stage0/"
    "human_pilot_stage0_offoff_execution_and_closeout_v1_9"
)
EXPECTED_LEGACY_LIVE_RUNNER_SHA256 = "fd0c395ef85d1800b6a9178ad5a27b8cc1c9bbda7317d14cc25a567afb9fedd6"
EXPECTED_EPISODE_EVALUATOR_SHA256 = "33c5a7828329e6b7634e588230206cf4f1a71ffea2a461a60f4ae16f9f054a52"
EXPECTED_SELECT_IDENTITY_SHA256 = "d63e7e7d5d5c10c4964f3c2a166effc83f1b3c6d43b5d4b7b44761dba449dc89"

EXPECTED_ARTIFACT_NAMES = (
    "CLEAN_SELECT_TASK_ACCESS_MANIFEST_V1.json",
    "SELECT_SERVER_RUNTIME_MANIFEST_V1.json",
    "T0_SELECT_POLICY_RUNTIME_MANIFEST_V1.json",
    "T2_SELECT_POLICY_RUNTIME_MANIFEST_V1.json",
    "T0_POLICY_CONDITION_MANIFEST_V1.json",
    "T2_POLICY_CONDITION_MANIFEST_V1.json",
    "T0_CONDITION_RUN_SCHEDULE_V1.json",
    "T2_CONDITION_RUN_SCHEDULE_V1.json",
    "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1.json",
    "CLEAN_SELECT_GAMEFILE_IDENTITY_MANIFEST_V1.json",
)

APPROVAL_TOKEN = "APPROVE_STAGE4D_FULL_SELECT_EXECUTION_V1"
RESUME_MODE = "PAIR_BOUNDARY_APPEND_ONLY"
CONDITION_ORDER = ("T0", "T2")


class Stage4DFullError(RuntimeError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_json_file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise Stage4DFullError(f"SEMANTIC_JSON_NOT_REGULAR:{path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Stage4DFullError(f"SEMANTIC_JSON_INVALID:{path}") from exc
    return sha256_bytes(canonical_json_bytes(value))


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise Stage4DFullError(f"JSON_NOT_REGULAR:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Stage4DFullError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def require_sha(path: Path, expected: str, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise Stage4DFullError(f"{label}_NOT_REGULAR:{path}")
    observed = sha256_file(path)
    if observed != expected:
        raise Stage4DFullError(
            f"{label}_SHA256_MISMATCH:expected={expected}:observed={observed}:path={path}"
        )


def write_new_json(path: Path, value: Any) -> None:
    payload = canonical_json_bytes(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(payload)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise OSError("short write")
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def write_or_reuse_exact(path: Path, value: Any) -> None:
    payload = canonical_json_bytes(value) + b"\n"
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise Stage4DFullError(f"EXISTING_OUTPUT_CHANGED:{path}")
        return
    write_new_json(path, value)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise Stage4DFullError("GIT_FAILED:" + result.stderr.strip())
    return result.stdout.strip()


def validate_readiness_receipt(value: dict[str, Any]) -> None:
    expected = {
        "schema_id": "STAGE4D_STATIC_SERVER_ROUTE_READINESS_V1",
        "schema_version": 1,
        "status": "PASS",
        "binding_root": str(EXPECTED_BINDING_ROOT),
        "model_probe_count": 2,
        "alfworld_environment_execution_count": 0,
        "scientific_select_cell_execution_count": 0,
        "scientific_outcome_generated": False,
        "evaluation_execution_authorized": False,
        "execution_authorization_ready": True,
        "next_gate": "EXPLICIT_FULL_SELECT_EXECUTION_AUTHORIZATION",
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise Stage4DFullError(f"READINESS_{key.upper()}_CHANGED")
    model_ids = value.get("model_ids")
    if not isinstance(model_ids, list) or not {
        PI0_SERVED_NAME,
        T2_SERVED_NAME,
    }.issubset(set(model_ids)):
        raise Stage4DFullError("READINESS_MODEL_IDS_CHANGED")


def verify_binding_inventory(binding_root: Path) -> None:
    inventory = binding_root / "OUTPUT_FILES.sha256"
    if inventory.is_symlink() or not inventory.is_file():
        raise Stage4DFullError("BINDING_INVENTORY_MISSING")
    for line_no, line in enumerate(inventory.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            expected, name = line.split("  ", 1)
        except ValueError as exc:
            raise Stage4DFullError(f"BINDING_INVENTORY_INVALID:{line_no}") from exc
        require_sha(binding_root / name, expected, "BINDING_FILE")
    identity = load_json(binding_root / "BINDING_IDENTITY.json")
    if sha256_bytes(canonical_json_bytes(identity)) != EXPECTED_BINDING_SHA256:
        raise Stage4DFullError("BINDING_IDENTITY_CHANGED")
    if identity.get("upstream_fixed_head") != EXPECTED_FIXED_HEAD:
        raise Stage4DFullError("BINDING_FIXED_HEAD_CHANGED")
    if identity.get("select_protocol_sha256") != EXPECTED_PROTOCOL_SHA256:
        raise Stage4DFullError("BINDING_PROTOCOL_CHANGED")
    artifact_semantic_hashes = identity.get("artifacts")
    if not isinstance(artifact_semantic_hashes, dict):
        raise Stage4DFullError("BINDING_ARTIFACT_HASH_MAP_INVALID")
    for name in EXPECTED_ARTIFACT_NAMES:
        expected = artifact_semantic_hashes.get(name)
        if not isinstance(expected, str) or len(expected) != 64:
            raise Stage4DFullError(f"BINDING_ARTIFACT_SEMANTIC_SHA_MISSING:{name}")
        observed = semantic_json_file_sha256(binding_root / name)
        if observed != expected:
            raise Stage4DFullError(
                f"BINDING_{name}_SEMANTIC_SHA256_MISMATCH:"
                f"expected={expected}:observed={observed}:path={binding_root / name}"
            )


def schedule_grid(value: dict[str, Any]) -> tuple[tuple[int, str, int], ...]:
    cells = value.get("cells")
    if not isinstance(cells, list) or len(cells) != EXPECTED_PAIR_CELLS:
        raise Stage4DFullError("SCHEDULE_CELL_COUNT_CHANGED")
    seeds = tuple(value.get("replicate_seeds", []))
    if seeds != EXPECTED_SEEDS or value.get("order") != "seed-major":
        raise Stage4DFullError("SCHEDULE_SEED_OR_ORDER_CHANGED")
    grid = tuple((row.get("manifest_index"), row.get("task_id"), row.get("seed")) for row in cells)
    if len(set(grid)) != EXPECTED_PAIR_CELLS:
        raise Stage4DFullError("SCHEDULE_GRID_DUPLICATED")
    return grid


def verify_scientific_grid(binding_root: Path) -> None:
    t0 = load_json(binding_root / "T0_CONDITION_RUN_SCHEDULE_V1.json")
    t2 = load_json(binding_root / "T2_CONDITION_RUN_SCHEDULE_V1.json")
    if schedule_grid(t0) != schedule_grid(t2):
        raise Stage4DFullError("T0_T2_GRID_CHANGED")
    access = load_json(binding_root / "CLEAN_SELECT_TASK_ACCESS_MANIFEST_V1.json")
    records = access.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_TASK_COUNT:
        raise Stage4DFullError("TASK_ACCESS_COUNT_CHANGED")
    if any(row.get("access_class") != "SELECT_SUMMARY_ONLY" for row in records):
        raise Stage4DFullError("TASK_ACCESS_CLASS_CHANGED")
    t0c = load_json(binding_root / "T0_POLICY_CONDITION_MANIFEST_V1.json")
    t2c = load_json(binding_root / "T2_POLICY_CONDITION_MANIFEST_V1.json")
    if t0c.get("memory_version") != "MEMORY_M0_V1" or t2c.get("memory_version") != "MEMORY_M0_V1":
        raise Stage4DFullError("MEMORY_NOT_OFF")
    if t2c.get("checkpoint_sha256") != EXPECTED_ADAPTER_SHA256:
        raise Stage4DFullError("T2_ADAPTER_CHANGED")
    inputs = load_json(binding_root / "BINDING_INPUTS.json")
    if inputs.get("interface_profile_id") != "I1_EXECUTION_PROFILE_V1":
        raise Stage4DFullError("I1_PROFILE_CHANGED")
    if inputs.get("policy_request_schema_sha256") != EXPECTED_I1_REQUEST_SCHEMA_SHA256:
        raise Stage4DFullError("I1_REQUEST_CONTRACT_CHANGED")


def verify_code_authority(binding_root: Path) -> Path:
    driver = load_json(binding_root / "LIVE_DRIVER_BINDING_CANDIDATE_V1.json")
    code_worktree = Path(driver.get("code_worktree", ""))
    if not code_worktree.is_dir():
        raise Stage4DFullError("CODE_WORKTREE_MISSING")
    if git(code_worktree, "rev-parse", "HEAD") != EXPECTED_FIXED_HEAD:
        raise Stage4DFullError("CODE_HEAD_CHANGED")
    if git(code_worktree, "rev-parse", "HEAD^{tree}") != EXPECTED_FIXED_TREE:
        raise Stage4DFullError("CODE_TREE_CHANGED")
    if git(code_worktree, "status", "--porcelain"):
        raise Stage4DFullError("CODE_WORKTREE_DIRTY")
    require_sha(code_worktree / LEGACY_LIVE_RUNNER_RELATIVE, EXPECTED_LEGACY_LIVE_RUNNER_SHA256, "LEGACY_LIVE_RUNNER")
    require_sha(code_worktree / "src/pchsi/evaluation/episode_evaluator.py", EXPECTED_EPISODE_EVALUATOR_SHA256, "EPISODE_EVALUATOR")
    require_sha(code_worktree / "src/pchsi/evaluation/select_execution_identity.py", EXPECTED_SELECT_IDENTITY_SHA256, "SELECT_IDENTITY")
    if driver.get("i1_profile_factory") != "build_select_i1_execution_profile":
        raise Stage4DFullError("I1_PROFILE_FACTORY_CHANGED")
    if driver.get("dynamic_lora_updates") is not False:
        raise Stage4DFullError("DYNAMIC_LORA_NOT_FORBIDDEN")
    return code_worktree


def authorization_payload(*, binding_root: Path, readiness_receipt_sha256: str) -> dict[str, Any]:
    return {
        "schema_id": "STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_V1",
        "schema_version": 1,
        "authorization_status": "APPROVED",
        "approval_token_id": APPROVAL_TOKEN,
        "binding_root": str(binding_root),
        "binding_sha256": EXPECTED_BINDING_SHA256,
        "readiness_receipt_path": str(EXPECTED_READINESS_RECEIPT),
        "readiness_receipt_sha256": readiness_receipt_sha256,
        "fixed_head": EXPECTED_FIXED_HEAD,
        "select_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "interface_profile_id": "I1_EXECUTION_PROFILE_V1",
        "memory_off": True,
        "harness_off": True,
        "server_mode": "STATIC_BASE_PLUS_SINGLE_LORA",
        "dynamic_lora_updates": False,
        "authorized_task_count": EXPECTED_TASK_COUNT,
        "authorized_replicate_seeds": list(EXPECTED_SEEDS),
        "authorized_paired_task_seed_cells": EXPECTED_PAIR_CELLS,
        "authorized_total_condition_cell_count": EXPECTED_TOTAL_CELLS,
        "condition_order_within_pair": list(CONDITION_ORDER),
        "resume_mode": RESUME_MODE,
        "evaluation_execution_authorized": True,
        "result_interpretation_authorized": False,
        "promotion_authorized": False,
        "repository_update_authorized": False,
        "next_gate_after_complete_execution": "STAGE4E_EXISTING_SELECT_RESULT_AUDIT",
    }


def authorization_sha(value: dict[str, Any]) -> str:
    return sha256_bytes(b"STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_V1\0" + canonical_json_bytes(value))


def execution_root(auth_sha: str) -> Path:
    return EXECUTION_PARENT / auth_sha

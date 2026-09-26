from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable


EXPECTED_FIXED_HEAD = "ede426ffb069bd887bd3caf847add8193c801d60"
EXPECTED_FIXED_TREE = "4460d1dd9b653258906ef0e625e5af7d7edbc338"
EXPECTED_PROTOCOL_SHA256 = "fcc798b70317d544dd205bb454c2e5017a7460473bd390a13af38b857ab0e1bf"
EXPECTED_PROTOCOL_FILE_SHA256 = "71890898f3c3ce66b860fcd634f98146c58eb346d3a89daec7537503c74289c1"
EXPECTED_TRAIN_SELECT_SHA256 = "b68f00cf164f0fa38df3506daf1a909a41f972b4b09a4610841a27c2de254400"
EXPECTED_TRAIN_UPDATE_SHA256 = "07221cbfa374e5ac100443079aee5940ca6227ffc42600c49c75d1d69de074cb"
EXPECTED_TRAIN_AUDIT_SHA256 = "101d1b728d0f6cfe48c79e287771d36c9712e086388dd82633eb25e6e23eb71e"
EXPECTED_ADAPTER_BUNDLE_SHA256 = "d1785b530043a1314d873bdfadd2c889bd1c073067d91a31a8429f52f6b60593"
EXPECTED_ADAPTER_CONFIG_SHA256 = "7db449cb82050e77c714ebc6ecb948f05dc3a0657843c0f3d2e1075f49b55459"
EXPECTED_ADAPTER_MODEL_SHA256 = "59c48b6451178647fd135600cb19bb898fed95c0ee9cc47dc881380020644432"
EXPECTED_BASE_REVISION = "aa8e72537993ba99e69dfaafa59ed015b17504d1"
EXPECTED_BASE_REPOSITORY = "Qwen/Qwen2.5-3B-Instruct"
EXPECTED_CHAT_TEMPLATE_SHA256 = "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f"
EXPECTED_I1_REQUEST_SCHEMA_SHA256 = "f2dd1cc61bca16110be41c00245eee85f7ef1e6a36a73dd52789de0060a63f77"
EXPECTED_I1_SERIALIZATION_SCHEMA_SHA256 = "ddca85be85528f1720614e9bfad1fd599f975737a43c51da130a402b312cce6a"
EXPECTED_TRAINING_PLAN_SHA256 = "ac04690c3cf665058b24b2c53af8ed9e35d2fdbb4a5771f771625772edfebb9e"
EXPECTED_TRAINING_CONTRACT_FILE_SHA256 = "fa0c49b9d86ab603969e3ccb852e2ec7ef0811483bfa31ae8815aba37d4df005"
EXPECTED_TRAINING_RUN_ID = "train_5223d537392ee5f54b5f"
EXPECTED_TRAINING_SEED = 17
EXPECTED_TASK_COUNT = 355
EXPECTED_SEEDS = (17, 31, 47, 73, 101)
EXPECTED_CONDITION_EPISODES = 3550
EXPECTED_PAIR_CELLS = 1775
PI0_CONDITION_ID = "P4-R0-PI0"
PI0_SERVED_NAME = "Qwen2.5-3B-Instruct-E1"
T2_CONDITION_ID = "PI1_HUMAN_T2_DIAGNOSTIC_CANDIDATE"
T2_SERVED_NAME = T2_CONDITION_ID


class Stage4DError(RuntimeError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Stage4DError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise Stage4DError(
                    f"JSONL_OBJECT_REQUIRED:{path}:{line_number}"
                )
            rows.append(value)
    return rows


def write_new_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_new_json(path: Path, value: Any) -> None:
    write_new_bytes(path, canonical_json_bytes(value) + b"\n")


def require_file_sha(path: Path, expected: str, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise Stage4DError(f"{label}_NOT_REGULAR_FILE:{path}")
    observed = sha256_file(path)
    if observed != expected:
        raise Stage4DError(
            f"{label}_SHA256_MISMATCH:expected={expected}:observed={observed}:path={path}"
        )


def unique_existing(paths: Iterable[Path], label: str) -> Path:
    existing = [path for path in paths if path.exists()]
    if len(existing) != 1:
        raise Stage4DError(
            f"{label}_UNIQUE_PATH_REQUIRED:count={len(existing)}:paths={existing}"
        )
    return existing[0]


def recursive_path_strings(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            result.extend(recursive_path_strings(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(recursive_path_strings(child))
    elif isinstance(value, str) and value.startswith("/"):
        result.append(value)
    return result


def resolve_gamefile(
    *,
    dataset_candidates: Iterable[Path],
    gamefile_relpath: str,
    expected_sha1: str,
    expected_sha256: str,
) -> Path:
    candidates: list[Path] = []
    rel = Path(gamefile_relpath)
    for root in dataset_candidates:
        for candidate in (root / rel, root / "train" / rel):
            if candidate in candidates:
                continue
            if candidate.is_symlink() or not candidate.is_file():
                continue
            if sha256_file(candidate) != expected_sha256:
                continue
            if sha1_file(candidate) != expected_sha1:
                continue
            candidates.append(candidate)
    if len(candidates) != 1:
        raise Stage4DError(
            "TRAIN_SELECT_GAMEFILE_RESOLUTION_FAILED:"
            f"rel={gamefile_relpath}:matches={[str(p) for p in candidates]}"
        )
    return candidates[0].resolve()


def verify_disjoint_pools(
    select_rows: list[dict[str, Any]],
    update_rows: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
) -> None:
    pools = {
        "TRAIN_SELECT": {row["id"] for row in select_rows},
        "TRAIN_UPDATE": {row["id"] for row in update_rows},
        "TRAIN_AUDIT": {row["id"] for row in audit_rows},
    }
    if len(pools["TRAIN_SELECT"]) != len(select_rows):
        raise Stage4DError("TRAIN_SELECT_DUPLICATE_TASK_ID")
    if len(pools["TRAIN_UPDATE"]) != len(update_rows):
        raise Stage4DError("TRAIN_UPDATE_DUPLICATE_TASK_ID")
    if len(pools["TRAIN_AUDIT"]) != len(audit_rows):
        raise Stage4DError("TRAIN_AUDIT_DUPLICATE_TASK_ID")
    names = tuple(pools)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlap = pools[left] & pools[right]
            if overlap:
                raise Stage4DError(
                    f"TRAIN_POOL_OVERLAP:{left}:{right}:count={len(overlap)}"
                )


def build_vllm_command(
    *,
    python_executable: str,
    base_model_path: str,
    adapter_path: str,
    host: str,
    port: int,
) -> list[str]:
    return [
        python_executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        base_model_path,
        "--served-model-name",
        PI0_SERVED_NAME,
        "--host",
        host,
        "--port",
        str(port),
        "--dtype",
        "bfloat16",
        "--tensor-parallel-size",
        "1",
        "--generation-config",
        "vllm",
        "--chat-template-content-format",
        "string",
        "--enable-lora",
        "--max-lora-rank",
        "16",
        "--max-loras",
        "1",
        "--max-cpu-loras",
        "1",
        "--lora-dtype",
        "auto",
        "--lora-modules",
        f"{T2_SERVED_NAME}={adapter_path}",
    ]


def package_output_root(control_root: Path, binding_sha256: str) -> Path:
    return (
        control_root
        / "stage4d_existing_select_live_binding_v1"
        / binding_sha256
    )

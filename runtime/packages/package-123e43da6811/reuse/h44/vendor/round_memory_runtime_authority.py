from __future__ import annotations

import functools
import hashlib
import inspect
import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

HEX64 = re.compile(r"^[0-9a-f]{64}$")
RUNTIME_SCHEMA = "FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1"


class RoundMemoryRuntimeAuthorityError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fsha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _sha(value: object, name: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise RoundMemoryRuntimeAuthorityError(
            "ROUND_MEMORY_RUNTIME_AUTHORITY_INVALID_SHA:" + name
        )
    return value


def _load_runtime(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file() or resolved.is_symlink():
        raise RoundMemoryRuntimeAuthorityError(
            "ROUND_MEMORY_RUNTIME_AUTHORITY_FILE_INVALID:" + str(resolved)
        )
    try:
        payload = json.loads(resolved.read_text("utf-8"))
    except Exception as exc:
        raise RoundMemoryRuntimeAuthorityError(
            "ROUND_MEMORY_RUNTIME_AUTHORITY_JSON_INVALID:" + str(resolved)
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema_id") != RUNTIME_SCHEMA:
        raise RoundMemoryRuntimeAuthorityError(
            "ROUND_MEMORY_RUNTIME_AUTHORITY_SCHEMA_INVALID:" + str(resolved)
        )
    active = _sha(payload.get("active_snapshot_sha256"), "active_snapshot_sha256")
    token = _sha(payload.get("token_budget_contract_sha256"), "token_budget_contract_sha256")
    snapshot_dir = payload.get("active_snapshot_directory")
    token_path = payload.get("token_budget_contract_path")
    if snapshot_dir is not None:
        if not isinstance(snapshot_dir, str) or not Path(snapshot_dir).is_absolute():
            raise RoundMemoryRuntimeAuthorityError("ROUND_MEMORY_RUNTIME_AUTHORITY_SNAPSHOT_PATH_INVALID")
    if token_path is not None:
        if not isinstance(token_path, str) or not Path(token_path).is_absolute():
            raise RoundMemoryRuntimeAuthorityError("ROUND_MEMORY_RUNTIME_AUTHORITY_TOKEN_PATH_INVALID")
    return {
        "path": str(resolved),
        "file_sha256": _fsha(resolved),
        "active_snapshot_sha256": active,
        "token_budget_contract_sha256": token,
        "active_snapshot_directory": snapshot_dir,
        "token_budget_contract_path": token_path,
        "schema_id": payload.get("schema_id"),
        "schema_version": payload.get("schema_version"),
    }


def discover_round_memory_runtime_authority(
    *,
    scripts_root: Path,
    explicit_path: Path | None,
) -> dict[str, Any]:
    scripts_root = scripts_root.resolve()
    if explicit_path is not None:
        row = _load_runtime(explicit_path)
        return {
            "schema_id": "ROUND_MEMORY_RUNTIME_AUTHORITY_CENSUS_V1",
            "schema_version": 1,
            "status": "RESOLVED_EXPLICIT_CURRENT_ROUND_MEMORY_RUNTIME_AUTHORITY",
            "authority_mode": "EXPLICIT_CURRENT_ROUND_MEMORY_RUNTIME_AUTHORITY",
            "authority_path": row["path"],
            "authority_file_sha256": row["file_sha256"],
            "authority_alias_paths": [row["path"]],
            "candidate_file_count": 1,
            "semantic_authority_count": 1,
            "active_snapshot_sha256": row["active_snapshot_sha256"],
            "token_budget_contract_sha256": row["token_budget_contract_sha256"],
            "hardcoded_runtime_identity_used": False,
            "scientific_candidate_selection_performed": False,
        }

    root = scripts_root / "failure_memory_v1_final_execution"
    candidates: list[dict[str, Any]] = []
    if root.is_dir():
        for path in sorted(root.glob("fixed_*/FINAL_RUNTIME_IDENTITY_V1.json")):
            try:
                candidates.append(_load_runtime(path))
            except RoundMemoryRuntimeAuthorityError:
                continue
    if not candidates:
        raise RoundMemoryRuntimeAuthorityError(
            "ROUND_MEMORY_RUNTIME_AUTHORITY_MATCH_COUNT_0"
        )

    by_semantics: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in candidates:
        key = (
            row["active_snapshot_sha256"],
            row["token_budget_contract_sha256"],
        )
        by_semantics.setdefault(key, []).append(row)
    if len(by_semantics) != 1:
        raise RoundMemoryRuntimeAuthorityError(
            "ROUND_MEMORY_RUNTIME_AUTHORITY_DISTINCT_SEMANTIC_COUNT_"
            + str(len(by_semantics))
        )
    (active, token), aliases = next(iter(by_semantics.items()))
    aliases = sorted(aliases, key=lambda row: row["path"])
    chosen = aliases[0]
    return {
        "schema_id": "ROUND_MEMORY_RUNTIME_AUTHORITY_CENSUS_V1",
        "schema_version": 1,
        "status": "RESOLVED_UNIQUE_MEMORY_RUNTIME_SEMANTICS",
        "authority_mode": "LEGACY_BOOTSTRAP_UNIQUE_MEMORY_RUNTIME_SEMANTICS",
        "authority_path": chosen["path"],
        "authority_file_sha256": chosen["file_sha256"],
        "authority_alias_paths": [row["path"] for row in aliases],
        "candidate_file_count": len(candidates),
        "semantic_authority_count": 1,
        "active_snapshot_sha256": active,
        "token_budget_contract_sha256": token,
        "hardcoded_runtime_identity_used": False,
        "scientific_candidate_selection_performed": False,
    }


def resolve_from_environment() -> dict[str, Any]:
    explicit_raw = os.environ.get("PCHSI_ROUND_MEMORY_RUNTIME_AUTHORITY")
    explicit = Path(explicit_raw) if explicit_raw else None
    return discover_round_memory_runtime_authority(
        scripts_root=Path(__file__).resolve().parent.parent,
        explicit_path=explicit,
    )


def make_round_execution_authority_guard(
    original: Callable[..., Any],
    *,
    on_resolution: Callable[[Mapping[str, Any]], None] | None = None,
):
    signature = inspect.signature(original)

    @functools.wraps(original)
    def guarded(*args: Any, **kwargs: Any):
        bound = signature.bind(*args, **kwargs)
        selected = bound.arguments.get("selected")
        if not isinstance(selected, Mapping):
            raise RoundMemoryRuntimeAuthorityError(
                "ROUND_MEMORY_RUNTIME_AUTHORITY_SELECTED_NOT_MAPPING"
            )
        selected_copy = dict(selected)
        materialization = selected_copy.get("materialization")
        if not isinstance(materialization, Mapping):
            raise RoundMemoryRuntimeAuthorityError(
                "ROUND_MEMORY_RUNTIME_AUTHORITY_MATERIALIZATION_NOT_MAPPING"
            )
        materialization_copy = dict(materialization)
        active = materialization_copy.get("active_snapshot_sha256")
        token = materialization_copy.get("token_budget_contract_sha256")
        if isinstance(active, str) and HEX64.fullmatch(active) and isinstance(token, str) and HEX64.fullmatch(token):
            census = {
                "schema_id": "ROUND_MEMORY_RUNTIME_AUTHORITY_GUARD_RECEIPT_V1",
                "schema_version": 1,
                "status": "EXPLICIT_ROUND_MEMORY_RUNTIME_AUTHORITY_ALREADY_BOUND",
                "authority_mode": "EXISTING_SELECTED_MATERIALIZATION",
                "source_state_sha256": materialization_copy.get("source_state_sha256"),
                "source_candidate_sha256": materialization_copy.get("source_candidate_sha256"),
                "active_snapshot_sha256": active,
                "token_budget_contract_sha256": token,
                "hardcoded_runtime_identity_used": False,
                "scientific_candidate_selection_performed": False,
            }
        else:
            census = resolve_from_environment()
            materialization_copy["active_snapshot_sha256"] = census["active_snapshot_sha256"]
            materialization_copy["token_budget_contract_sha256"] = census["token_budget_contract_sha256"]
            census = {
                **census,
                "source_state_sha256": materialization_copy.get("source_state_sha256"),
                "source_candidate_sha256": materialization_copy.get("source_candidate_sha256"),
            }
            selected_copy["materialization"] = materialization_copy
            bound.arguments["selected"] = selected_copy
        if on_resolution is not None:
            on_resolution(census)
        return original(*bound.args, **bound.kwargs)

    return guarded

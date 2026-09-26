from __future__ import annotations

from collections.abc import Mapping
import importlib.metadata
import os
from pathlib import Path

from pchsi.reference_loop.canonical import sha256_file, strict_json_loads


_REQUIRED_KEYS = {
    "schema_id",
    "candidate_roots",
    "required_relative_files",
    "expected_asset_sha256",
    "transport_module_relative_path",
    "transport_callable_name",
    "transport_required_kwonly_parameters",
    "transport_return_tuple",
    "transport_exception_contract",
    "expected_httpx_version",
    "endpoint",
    "direct_openai_sdk_fallback_allowed",
    "command_fallback_allowed",
}


def config_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "configs/cognitive_runtime/p2_asset_binding_v1.json"
    )


def binding_config() -> dict[str, object]:
    value = strict_json_loads(config_path().read_bytes())
    if not isinstance(value, dict):
        raise ValueError("P2 asset binding must be one JSON object")
    if set(value) != _REQUIRED_KEYS:
        raise ValueError(
            "P2 asset binding key set mismatch: "
            f"observed={sorted(value)} expected={sorted(_REQUIRED_KEYS)}"
        )
    if value["schema_id"] != "P2_ASSET_BINDING_V1":
        raise ValueError("P2 asset binding schema_id mismatch")
    if value["direct_openai_sdk_fallback_allowed"] is not False:
        raise ValueError("direct OpenAI SDK fallback must remain disabled")
    if value["command_fallback_allowed"] is not False:
        raise ValueError("P2 command/subprocess fallback must remain disabled")
    return value


def _matches_exact_binding(root: Path, cfg: Mapping[str, object]) -> bool:
    if not root.is_dir() or root.is_symlink():
        return False
    required = cfg.get("required_relative_files")
    expected = cfg.get("expected_asset_sha256")
    if not isinstance(required, list) or not isinstance(expected, Mapping):
        return False
    for relative in required:
        if not isinstance(relative, str):
            return False
        path = root / relative
        wanted = expected.get(relative)
        if (
            not path.is_file()
            or path.is_symlink()
            or not isinstance(wanted, str)
            or sha256_file(path) != wanted
        ):
            return False
    return True


def locate_p2_root() -> Path:
    cfg = binding_config()
    roots: list[str] = []
    override = os.environ.get("PCHSI_P2_RUNTIME_ROOT")
    if override:
        roots.append(override)
    configured = cfg["candidate_roots"]
    if not isinstance(configured, list):
        raise ValueError("candidate_roots must be an array")
    roots.extend(str(value) for value in configured)

    for raw in roots:
        root = Path(raw)
        if _matches_exact_binding(root, cfg):
            return root.resolve()
    raise ValueError(
        "exact frozen P2 runtime assets not found; "
        "no alternate provider client or command fallback is allowed"
    )


def verify_httpx_runtime() -> str:
    cfg = binding_config()
    observed = importlib.metadata.version("httpx")
    expected = cfg["expected_httpx_version"]
    if observed != expected:
        raise ValueError(
            f"httpx runtime mismatch: observed={observed} expected={expected}"
        )
    return observed


def audit_p2_assets() -> dict[str, object]:
    cfg = binding_config()
    root = locate_p2_root()
    expected = cfg["expected_asset_sha256"]
    rows = []
    for relative in cfg["required_relative_files"]:
        path = root / relative
        observed = sha256_file(path)
        rows.append(
            {
                "relative_path": relative,
                "sha256": observed,
                "expected_sha256": expected[relative],
                "size_bytes": path.stat().st_size,
                "exact_hash_match": observed == expected[relative],
            }
        )
    if not all(row["exact_hash_match"] for row in rows):
        raise ValueError("P2 exact asset identity audit failed")
    return {
        "schema_id": "P2_ASSET_IDENTITY_REPORT_V2",
        "p2_runtime_root_private": str(root),
        "asset_rows": rows,
        "transport_module_relative_path": cfg[
            "transport_module_relative_path"
        ],
        "transport_callable_name": cfg["transport_callable_name"],
        "transport_required_kwonly_parameters": cfg[
            "transport_required_kwonly_parameters"
        ],
        "transport_return_tuple": cfg["transport_return_tuple"],
        "transport_exception_contract": cfg[
            "transport_exception_contract"
        ],
        "httpx_version": verify_httpx_runtime(),
        "endpoint": cfg["endpoint"],
        "exact_asset_hashes_verified": True,
        "direct_openai_sdk_fallback_allowed": False,
        "command_fallback_allowed": False,
    }

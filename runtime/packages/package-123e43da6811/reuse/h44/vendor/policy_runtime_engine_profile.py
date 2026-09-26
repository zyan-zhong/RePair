from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse


def _canon(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _command_option(command: list[str], name: str) -> str | None:
    for idx, token in enumerate(command):
        if token == name:
            return command[idx + 1] if idx + 1 < len(command) else None
        prefix = name + "="
        if token.startswith(prefix):
            return token[len(prefix):]
    return None


def _command_flag(command: list[str], name: str) -> bool:
    return name in command


def _command_model_path(command: list[str]) -> str | None:
    explicit = _command_option(command, "--model")
    if explicit:
        return explicit
    for idx in range(len(command) - 2):
        if command[idx] == "vllm" and command[idx + 1] == "serve":
            value = command[idx + 2]
            return value if value and not value.startswith("-") else None
    return None


def _looks_like_vllm_command(command: object) -> list[str] | None:
    if not isinstance(command, list) or any(not isinstance(x, str) or not x for x in command):
        return None
    values = list(command)
    if any(token == "vllm.entrypoints.openai.api_server" for token in values):
        return values
    if any(values[i] == "vllm" and i + 1 < len(values) and values[i + 1] == "serve" for i in range(len(values))):
        return values
    return None


def _dict_nodes(value: object, inherited_version: object = None, pointer: str = "$"):
    if isinstance(value, dict):
        version = value.get("vllm_version", inherited_version)
        yield value, version, pointer
        for key, child in value.items():
            child_pointer = pointer + "/" + str(key).replace("~", "~0").replace("/", "~1")
            yield from _dict_nodes(child, version, child_pointer)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _dict_nodes(child, inherited_version, pointer + "/" + str(index))


def _command_fields(node: dict[str, object]):
    for field in ("command", "cmdline", "argv", "launch_command"):
        if field in node:
            yield field, node.get(field)


def _iter_json_paths(root: Path):
    if root.is_file():
        if root.suffix.lower() == ".json" and not root.is_symlink():
            yield root.resolve()
        return
    if not root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        base = Path(dirpath)
        dirnames[:] = sorted(name for name in dirnames if not (base / name).is_symlink())
        for name in sorted(filenames):
            if not name.lower().endswith(".json"):
                continue
            path = base / name
            if not path.is_symlink() and path.is_file():
                yield path.resolve()


def _raw_prefilter(raw: bytes, model_path: str) -> bool:
    lower = raw.lower()
    if b"vllm" not in lower:
        return False
    if model_path.encode("utf-8") not in raw:
        return False
    return any(key in lower for key in (b'"command"', b'"cmdline"', b'"argv"', b'"launch_command"'))


def _extract_profile(command: list[str]) -> dict[str, object] | None:
    dtype = _command_option(command, "--dtype")
    tp = _command_option(command, "--tensor-parallel-size") or _command_option(command, "-tp")
    generation = _command_option(command, "--generation-config")
    if not dtype or not tp or not generation:
        return None
    try:
        tp_int = int(tp)
    except ValueError:
        return None
    if tp_int <= 0:
        return None
    return {
        "dtype": dtype,
        "tensor_parallel_size": tp_int,
        "generation_config": generation,
        "chat_template_content_format": _command_option(command, "--chat-template-content-format"),
        "request_id_headers_enabled": _command_flag(command, "--enable-request-id-headers"),
    }


def discover_compatible_engine_profile(
    runtime: dict[str, object],
    search_roots: list[str | Path] | tuple[str | Path, ...],
    *,
    max_candidate_json_files: int = 4096,
    max_walked_json_files: int = 250000,
) -> dict[str, object]:
    if type(max_candidate_json_files) is not int or max_candidate_json_files <= 0:
        raise ValueError("max_candidate_json_files must be positive")
    if type(max_walked_json_files) is not int or max_walked_json_files <= 0:
        raise ValueError("max_walked_json_files must be positive")
    model_path = runtime.get("base_model_local_path")
    version = runtime.get("vllm_version")
    if not isinstance(model_path, str) or not model_path or not isinstance(version, str) or not version:
        raise ValueError("runtime model/vllm identity missing")

    roots: list[Path] = []
    for raw in search_roots:
        p = Path(raw).resolve()
        if p not in roots:
            roots.append(p)

    seen_paths: set[Path] = set()
    walked = parsed = skipped = parse_errors = 0
    rows: list[dict[str, object]] = []
    for root in roots:
        for path in _iter_json_paths(root):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            walked += 1
            if walked > max_walked_json_files:
                raise ValueError("engine-profile walked JSON file bound exceeded")
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if not _raw_prefilter(raw, model_path):
                skipped += 1
                continue
            parsed += 1
            if parsed > max_candidate_json_files:
                raise ValueError("engine-profile candidate JSON file bound exceeded")
            try:
                value = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                parse_errors += 1
                continue
            for node, inherited_version, pointer in _dict_nodes(value):
                if inherited_version != version:
                    continue
                for command_field, command_value in _command_fields(node):
                    command = _looks_like_vllm_command(command_value)
                    if command is None or _command_model_path(command) != model_path:
                        continue
                    profile = _extract_profile(command)
                    if profile is None:
                        continue
                    rows.append({
                        "path": str(path),
                        "file_sha256": hashlib.sha256(raw).hexdigest(),
                        "json_pointer": pointer,
                        "command_field": command_field,
                        "historical_served_model_name": _command_option(command, "--served-model-name"),
                        "historical_host": _command_option(command, "--host"),
                        "historical_port": _command_option(command, "--port"),
                        "profile": profile,
                    })

    # Collapse by semantically relevant engine-profile fields. Endpoint and served
    # alias are deliberately excluded; those are provided by the current runtime binding.
    required_fields = ("dtype", "tensor_parallel_size", "generation_config")
    optional_fields = ("chat_template_content_format", "request_id_headers_enabled")
    distinct_required = {
        tuple(row["profile"][f] for f in required_fields) for row in rows
    }
    report: dict[str, object] = {
        "schema_id": "POLICY_RUNTIME_COMPATIBLE_ENGINE_PROFILE_DISCOVERY_V1",
        "schema_version": 1,
        "status": None,
        "search_strategy": "CURRENT_RUNTIME_MODEL_AND_VLLM_IDENTITY_TO_HISTORICAL_ENGINE_PROFILE",
        "search_roots": [str(p) for p in roots],
        "base_model_local_path": model_path,
        "vllm_version": version,
        "json_file_count_seen": walked,
        "candidate_json_file_count_parsed": parsed,
        "non_candidate_json_file_count_skipped": skipped,
        "candidate_json_parse_error_count": parse_errors,
        "compatible_command_count": len(rows),
        "distinct_profile_count": len(distinct_required),
        "historical_endpoint_or_alias_reused": False,
        "operator_launch_knobs_synthesized": False,
        "scientific_candidate_reselection_performed": False,
        "evidence_rows": rows,
    }
    if not rows:
        report["status"] = "COMPATIBLE_POLICY_ENGINE_PROFILE_NOT_FOUND"
        return report
    if len(distinct_required) != 1:
        report["status"] = "FAIL_CLOSED_DISTINCT_COMPATIBLE_POLICY_ENGINE_PROFILES"
        return report

    required_values = dict(zip(required_fields, next(iter(distinct_required))))
    optional_values: dict[str, object] = {}
    for field in optional_fields:
        values = {row["profile"][field] for row in rows if row["profile"].get(field) not in (None, False)}
        if len(values) > 1:
            report["status"] = "FAIL_CLOSED_DISTINCT_COMPATIBLE_POLICY_ENGINE_PROFILES"
            report["conflicting_optional_field"] = field
            report["conflicting_optional_values"] = sorted(str(v) for v in values)
            return report
        optional_values[field] = next(iter(values)) if values else (False if field == "request_id_headers_enabled" else None)

    profile_material = {**required_values, **optional_values}
    report.update(profile_material)
    report["engine_profile_sha256"] = hashlib.sha256(
        b"POLICY_RUNTIME_COMPATIBLE_ENGINE_PROFILE_V1\0" + _canon(profile_material)
    ).hexdigest()
    report["status"] = "RESOLVED_UNIQUE_COMPATIBLE_POLICY_ENGINE_PROFILE"
    return report


def build_current_runtime_service_launch_contract(
    runtime: dict[str, object],
    profile: dict[str, object],
    *,
    python_executable: str,
) -> dict[str, object]:
    if profile.get("status") != "RESOLVED_UNIQUE_COMPATIBLE_POLICY_ENGINE_PROFILE":
        raise ValueError("compatible engine profile not resolved")
    parsed = urlparse(str(runtime.get("policy_base_url")))
    if parsed.scheme != "http" or not parsed.hostname or parsed.path not in ("", "/"):
        raise ValueError("current runtime launch contract requires plain HTTP host endpoint")
    port = parsed.port or 80
    model_path = runtime.get("base_model_local_path")
    served = runtime.get("served_model_name")
    context = runtime.get("context_window_tokens")
    if not isinstance(model_path, str) or not model_path or not isinstance(served, str) or not served:
        raise ValueError("runtime launch identity incomplete")
    if type(context) is not int or context <= 0:
        raise ValueError("runtime context window invalid")
    if not isinstance(python_executable, str) or not python_executable:
        raise ValueError("python_executable invalid")

    command = [
        python_executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_path,
        "--served-model-name", served,
        "--host", parsed.hostname,
        "--port", str(port),
        "--dtype", str(profile["dtype"]),
        "--tensor-parallel-size", str(profile["tensor_parallel_size"]),
        "--generation-config", str(profile["generation_config"]),
        "--max-model-len", str(context),
    ]
    chat = profile.get("chat_template_content_format")
    if isinstance(chat, str) and chat:
        command += ["--chat-template-content-format", chat]
    if profile.get("request_id_headers_enabled") is True:
        command.append("--enable-request-id-headers")

    payload: dict[str, object] = {
        "schema_id": "POLICY_RUNTIME_SERVICE_LAUNCH_CONTRACT_V1",
        "schema_version": 1,
        "status": "MATERIALIZED_CURRENT_RUNTIME_SERVICE_LAUNCH_CONTRACT",
        "policy_base_url": runtime.get("policy_base_url"),
        "served_model_name": served,
        "base_model_local_path": model_path,
        "context_window_tokens": context,
        "vllm_version": runtime.get("vllm_version"),
        "engine_profile_sha256": profile.get("engine_profile_sha256"),
        "engine_profile_status": profile.get("status"),
        "historical_endpoint_or_alias_reused": False,
        "operator_launch_knobs_synthesized": False,
        "scientific_candidate_reselection_performed": False,
        "launch_command": command,
        "launch_command_sha256": hashlib.sha256(_canon(command)).hexdigest(),
        "launch_contract_sha256": "0" * 64,
    }
    payload["launch_contract_sha256"] = hashlib.sha256(
        b"POLICY_RUNTIME_SERVICE_LAUNCH_CONTRACT_V1\0" + _canon({k: v for k, v in payload.items() if k != "launch_contract_sha256"})
    ).hexdigest()
    return payload


def normalize_profile(value: dict[str, object], *, runtime: dict[str, object]) -> dict[str, object]:
    """Validate one durable resolved engine-profile receipt against the current runtime.

    This is direct receipt reuse, not filesystem rediscovery.  Endpoint and served alias are
    deliberately not part of the historical engine-profile identity.
    """
    if not isinstance(value, dict):
        raise ValueError("engine profile receipt must be object")
    if value.get("schema_id") != "POLICY_RUNTIME_COMPATIBLE_ENGINE_PROFILE_DISCOVERY_V1":
        raise ValueError("engine profile receipt schema mismatch")
    if value.get("status") != "RESOLVED_UNIQUE_COMPATIBLE_POLICY_ENGINE_PROFILE":
        raise ValueError("engine profile receipt status mismatch")
    if value.get("base_model_local_path") != runtime.get("base_model_local_path"):
        raise ValueError("engine profile receipt model differs from current runtime")
    if value.get("vllm_version") != runtime.get("vllm_version"):
        raise ValueError("engine profile receipt vLLM differs from current runtime")
    dtype=value.get("dtype")
    tp=value.get("tensor_parallel_size")
    generation=value.get("generation_config")
    chat=value.get("chat_template_content_format")
    headers=value.get("request_id_headers_enabled")
    if not isinstance(dtype,str) or not dtype:
        raise ValueError("engine profile dtype invalid")
    if type(tp) is not int or tp <= 0:
        raise ValueError("engine profile tensor parallel size invalid")
    if not isinstance(generation,str) or not generation:
        raise ValueError("engine profile generation config invalid")
    if chat is not None and (not isinstance(chat,str) or not chat):
        raise ValueError("engine profile chat template content format invalid")
    if type(headers) is not bool:
        raise ValueError("engine profile request-id flag invalid")
    material={
        "dtype":dtype,
        "tensor_parallel_size":tp,
        "generation_config":generation,
        "chat_template_content_format":chat,
        "request_id_headers_enabled":headers,
    }
    expected=hashlib.sha256(
        b"POLICY_RUNTIME_COMPATIBLE_ENGINE_PROFILE_V1\0" + _canon(material)
    ).hexdigest()
    if value.get("engine_profile_sha256") != expected:
        raise ValueError("engine profile receipt hash mismatch")
    if value.get("distinct_profile_count") not in (None,1):
        raise ValueError("engine profile receipt is not unique")
    return dict(value)

from __future__ import annotations

import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import time
from urllib.parse import urlparse


def _canon(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required: " + str(path))
    return value


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha64(value: object, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(name + " must be lowercase SHA-256")
    return value


def _runtime_binding_identity_from_row(row: dict[str, object]) -> tuple[str, str, str | None]:
    path = row.get("runtime_binding_path")
    sha = row.get("runtime_binding_file_sha256")
    model = row.get("policy_model")
    if not isinstance(path, str) or not path:
        raise ValueError("branch binding runtime_binding_path missing")
    _sha64(sha, "runtime_binding_file_sha256")
    if model is not None and (not isinstance(model, str) or not model):
        raise ValueError("policy_model invalid")
    return path, str(sha), model if isinstance(model, str) else None


def derive_runtime_authority(integration_root: str | Path) -> dict[str, object]:
    root = Path(integration_root).resolve()
    bindings_root = root / "branch_bindings_v2"
    paths = sorted(p for p in bindings_root.glob("*.json") if p.is_file())
    if not paths:
        raise ValueError("no branch bindings found")
    identities = []
    for path in paths:
        identities.append(_runtime_binding_identity_from_row(_load_json(path)))
    distinct = sorted(set(identities))
    if len(distinct) != 1:
        raise ValueError("branch population does not share one runtime binding authority")
    runtime_path_text, runtime_sha, policy_model = distinct[0]
    runtime_path = Path(runtime_path_text)
    if runtime_path.is_symlink() or not runtime_path.is_file():
        raise ValueError("runtime binding path invalid")
    actual = _file_sha(runtime_path)
    if actual != runtime_sha:
        raise ValueError("runtime binding file SHA mismatch")
    runtime = _load_json(runtime_path)
    if runtime.get("schema_id") != "CLEAN_PI0_LIVE_RUNTIME_BINDING_V2" or runtime.get("schema_version") != 2:
        raise ValueError("runtime binding schema mismatch")
    served = runtime.get("served_model_name")
    if not isinstance(served, str) or not served:
        raise ValueError("served_model_name invalid")
    if policy_model is not None and policy_model != served:
        raise ValueError("branch policy model differs from runtime served model")
    base_url = runtime.get("policy_base_url")
    if not isinstance(base_url, str) or not base_url:
        raise ValueError("policy_base_url invalid")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.path not in {"", "/"}:
        raise ValueError("policy_base_url invalid")
    version = runtime.get("vllm_version")
    model_path = runtime.get("base_model_local_path")
    context = runtime.get("context_window_tokens")
    if not isinstance(version, str) or not version:
        raise ValueError("vllm_version invalid")
    if not isinstance(model_path, str) or not model_path:
        raise ValueError("base_model_local_path invalid")
    if type(context) is not int or context <= 0:
        raise ValueError("context_window_tokens invalid")
    return {
        "schema_id": "POLICY_RUNTIME_SERVICE_AUTHORITY_V1",
        "runtime_binding_path": str(runtime_path),
        "runtime_binding_file_sha256": runtime_sha,
        "policy_base_url": base_url,
        "served_model_name": served,
        "base_model_local_path": model_path,
        "context_window_tokens": context,
        "vllm_version": version,
        "runtime_binding": runtime,
        "branch_binding_count": len(paths),
        "scientific_candidate_reselection_performed": False,
    }


def _http_get(parsed, path: str, timeout_seconds: float) -> tuple[int, dict[str, str], bytes]:
    port = parsed.port
    cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    connection = cls(parsed.hostname, port=port, timeout=timeout_seconds)
    try:
        connection.request("GET", path, headers={"Accept": "application/json"})
        response = connection.getresponse()
        body = response.read()
        return int(response.status), {str(k): str(v) for k, v in response.getheaders()}, body
    finally:
        connection.close()


def probe_policy_runtime_service(runtime_or_authority: dict[str, object], *, timeout_seconds: float = 2.0) -> dict[str, object]:
    runtime = runtime_or_authority.get("runtime_binding") if isinstance(runtime_or_authority.get("runtime_binding"), dict) else runtime_or_authority
    base_url = runtime.get("policy_base_url")
    served = runtime.get("served_model_name")
    expected_version = runtime.get("vllm_version")
    if not isinstance(base_url, str) or not isinstance(served, str) or not isinstance(expected_version, str):
        raise ValueError("runtime service identity incomplete")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("policy_base_url invalid")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    report: dict[str, object] = {
        "schema_id": "POLICY_RUNTIME_SERVICE_READINESS_V1",
        "schema_version": 1,
        "policy_base_url": base_url,
        "host": parsed.hostname,
        "port": port,
        "expected_served_model_name": served,
        "expected_vllm_version": expected_version,
        "ready": False,
        "classification": None,
        "tcp_connect_ok": False,
        "health_status": None,
        "models_status": None,
        "version_status": None,
        "observed_model_ids": [],
        "observed_vllm_version": None,
        "transport_error_type": None,
        "transport_error_message": None,
        "scientific_model_calls": 0,
        "environment_calls": 0,
        "training_executions": 0,
    }
    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout_seconds):
            report["tcp_connect_ok"] = True
        hs, _, _ = _http_get(parsed, "/health", timeout_seconds)
        report["health_status"] = hs
        if hs != 200:
            report["classification"] = "HEALTH_ENDPOINT_NOT_READY"
            return report
        ms, _, mb = _http_get(parsed, "/v1/models", timeout_seconds)
        report["models_status"] = ms
        if ms != 200:
            report["classification"] = "MODEL_LIST_ENDPOINT_NOT_READY"
            return report
        try:
            models_payload = json.loads(mb)
            data = models_payload.get("data", []) if isinstance(models_payload, dict) else []
            ids = [row.get("id") for row in data if isinstance(row, dict) and isinstance(row.get("id"), str)]
        except Exception:
            report["classification"] = "MODEL_LIST_RESPONSE_INVALID"
            return report
        report["observed_model_ids"] = ids
        if served not in ids:
            report["classification"] = "SERVED_MODEL_IDENTITY_MISMATCH"
            return report
        vs, _, vb = _http_get(parsed, "/version", timeout_seconds)
        report["version_status"] = vs
        if vs != 200:
            report["classification"] = "VERSION_ENDPOINT_NOT_READY"
            return report
        try:
            version_payload = json.loads(vb)
            observed = version_payload.get("version") if isinstance(version_payload, dict) else None
        except Exception:
            observed = None
        report["observed_vllm_version"] = observed
        if observed != expected_version:
            report["classification"] = "VLLM_VERSION_MISMATCH"
            return report
        report["ready"] = True
        report["classification"] = "READY_EXACT_BOUND_POLICY_RUNTIME"
        return report
    except (OSError, http.client.HTTPException, TimeoutError) as exc:
        report["classification"] = "TCP_OR_HTTP_UNREACHABLE"
        report["transport_error_type"] = type(exc).__name__
        report["transport_error_message"] = str(exc)
        return report



def _command_option(command: list[str], name: str) -> str | None:
    for idx, token in enumerate(command):
        if token == name:
            if idx + 1 >= len(command):
                return None
            return command[idx + 1]
        prefix = name + "="
        if token.startswith(prefix):
            return token[len(prefix):]
    return None


def _command_model_path(command: list[str]) -> str | None:
    explicit = _command_option(command, "--model")
    if explicit:
        return explicit
    for idx in range(len(command) - 2):
        if command[idx] == "vllm" and command[idx + 1] == "serve":
            value = command[idx + 2]
            return value if value and not value.startswith("-") else None
    if len(command) >= 3 and command[0].endswith("vllm") and command[1] == "serve":
        value = command[2]
        return value if value and not value.startswith("-") else None
    return None


def _looks_like_vllm_server_command(command: list[str]) -> bool:
    if not command or any(not isinstance(token, str) or not token for token in command):
        return False
    if any(token == "vllm.entrypoints.openai.api_server" for token in command):
        return True
    return any(command[idx] == "vllm" and idx + 1 < len(command) and command[idx + 1] == "serve" for idx in range(len(command)))


def _matching_launch_command(command: object, *, runtime: dict[str, object], receipt_vllm_version: object) -> list[str] | None:
    if not isinstance(command, list) or any(not isinstance(token, str) or not token for token in command):
        return None
    values = list(command)
    if not _looks_like_vllm_server_command(values):
        return None
    if receipt_vllm_version != runtime.get("vllm_version"):
        return None
    if _command_model_path(values) != runtime.get("base_model_local_path"):
        return None
    if _command_option(values, "--served-model-name") != runtime.get("served_model_name"):
        return None
    parsed = urlparse(str(runtime.get("policy_base_url")))
    expected_host = parsed.hostname
    expected_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if _command_option(values, "--host") != expected_host:
        return None
    if _command_option(values, "--port") != str(expected_port):
        return None
    if _command_option(values, "--max-model-len") != str(runtime.get("context_window_tokens")):
        return None
    return values


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


def _iter_json_paths_streaming(root: Path):
    """Yield regular non-symlink JSON files without materializing the tree."""
    if root.is_file():
        if root.suffix.lower() == ".json" and not root.is_symlink():
            yield root.resolve()
        return
    if not root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        base = Path(dirpath)
        dirnames[:] = sorted(
            name for name in dirnames
            if not (base / name).is_symlink()
        )
        for name in sorted(filenames):
            if not name.lower().endswith(".json"):
                continue
            path = base / name
            if path.is_symlink() or not path.is_file():
                continue
            yield path.resolve()


def _raw_launch_authority_prefilter(raw: bytes) -> bool:
    """Cheap discovery accelerator; never an authority decision.

    Every accepted launch authority still passes full JSON parsing and exact
    runtime-identity matching below.  The prefilter merely prevents unrelated
    control-plane JSON from consuming the candidate-parse budget.
    """
    lower = raw.lower()
    if b"vllm" not in lower:
        return False
    command_keys = (
        b'"command"', b'"cmdline"', b'"argv"', b'"launch_command"'
    )
    return any(key in lower for key in command_keys)


def _command_fields(node: dict[str, object]):
    for field in ("command", "cmdline", "argv", "launch_command"):
        if field in node:
            yield field, node.get(field)


def discover_exact_policy_service_launch_authority(
    runtime_or_authority: dict[str, object],
    search_roots: list[str | Path] | tuple[str | Path, ...],
    *,
    max_json_files: int = 4096,
    max_walked_json_files: int = 250000,
) -> dict[str, object]:
    """Find a pre-existing exact vLLM launch receipt without synthesizing server knobs.

    Discovery is authority-first and streaming.  ``max_json_files`` bounds only
    launch-like JSON documents that survive a raw-byte prefilter; unrelated JSON
    does not exhaust that budget.  ``max_walked_json_files`` separately bounds
    filesystem traversal.  Neither bound is a scientific denominator.

    The runtime binding freezes scientific runtime identity and endpoint, but it
    does not freeze operational launch parameters such as dtype, tensor parallel
    size, or GPU-memory utilization.  Those values must therefore come from an
    existing launch receipt, never from operator-supplied defaults here.
    """
    if type(max_json_files) is not int or max_json_files <= 0:
        raise ValueError("max_json_files must be positive")
    if type(max_walked_json_files) is not int or max_walked_json_files <= 0:
        raise ValueError("max_walked_json_files must be positive")
    runtime = runtime_or_authority.get("runtime_binding") if isinstance(runtime_or_authority.get("runtime_binding"), dict) else runtime_or_authority
    if not isinstance(runtime, dict):
        raise TypeError("runtime authority must be mapping")
    roots = []
    for raw in search_roots:
        root = Path(raw).resolve()
        if root not in roots:
            roots.append(root)

    candidates: list[dict[str, object]] = []
    json_seen = 0
    candidate_json_parsed = 0
    skipped_non_candidate = 0
    parse_error_count = 0
    visited: set[Path] = set()

    for root in roots:
        for path in _iter_json_paths_streaming(root):
            if path in visited:
                continue
            visited.add(path)
            json_seen += 1
            if json_seen > max_walked_json_files:
                raise ValueError("launch authority walked JSON file bound exceeded")
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if not _raw_launch_authority_prefilter(raw):
                skipped_non_candidate += 1
                continue
            candidate_json_parsed += 1
            if candidate_json_parsed > max_json_files:
                raise ValueError("launch authority candidate JSON file bound exceeded")
            try:
                value = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                parse_error_count += 1
                continue
            for node, inherited_version, pointer in _dict_nodes(value):
                for command_field, command_value in _command_fields(node):
                    command = _matching_launch_command(
                        command_value,
                        runtime=runtime,
                        receipt_vllm_version=inherited_version,
                    )
                    if command is None:
                        continue
                    command_sha = hashlib.sha256(_canon(command)).hexdigest()
                    candidates.append({
                        "path": str(path),
                        "file_sha256": hashlib.sha256(raw).hexdigest(),
                        "json_pointer": pointer,
                        "command_field": command_field,
                        "launch_command": command,
                        "launch_command_sha256": command_sha,
                        "vllm_version": runtime.get("vllm_version"),
                    })

    # Exact duplicate references are aliases, not additional authority votes.
    deduped: list[dict[str, object]] = []
    seen_rows: set[tuple[str, str, str, str]] = set()
    for row in candidates:
        key = (
            str(row["path"]), str(row["json_pointer"]),
            str(row["command_field"]), str(row["launch_command_sha256"]),
        )
        if key in seen_rows:
            continue
        seen_rows.add(key)
        deduped.append(row)
    candidates = deduped

    groups: dict[str, list[dict[str, object]]] = {}
    for row in candidates:
        groups.setdefault(str(row["launch_command_sha256"]), []).append(row)
    report: dict[str, object] = {
        "schema_id": "EXACT_POLICY_SERVICE_LAUNCH_AUTHORITY_DISCOVERY_V2",
        "schema_version": 2,
        "status": None,
        "search_strategy": "STREAMING_RAW_PREFILTER_THEN_EXACT_IDENTITY",
        "search_roots": [str(p) for p in roots],
        "json_file_count_seen": json_seen,
        "candidate_json_file_count_parsed": candidate_json_parsed,
        "non_candidate_json_file_count_skipped": skipped_non_candidate,
        "candidate_json_parse_error_count": parse_error_count,
        # Backward-readable alias: this now means launch-like JSON parsed, not all JSON traversed.
        "json_file_count_scanned": candidate_json_parsed,
        "max_candidate_json_files": max_json_files,
        "max_walked_json_files": max_walked_json_files,
        "exact_match_count": len(candidates),
        "distinct_launch_command_count": len(groups),
        "candidate_paths": sorted({str(row["path"]) for row in candidates}),
        "authority_command_fields": sorted({str(row["command_field"]) for row in candidates}),
        "policy_base_url": runtime.get("policy_base_url"),
        "served_model_name": runtime.get("served_model_name"),
        "base_model_local_path": runtime.get("base_model_local_path"),
        "vllm_version": runtime.get("vllm_version"),
        "operator_launch_knobs_synthesized": False,
        "scientific_candidate_reselection_performed": False,
        "scientific_model_calls": 0,
        "environment_calls": 0,
        "training_executions": 0,
    }
    if not groups:
        report["status"] = "EXACT_POLICY_SERVICE_LAUNCH_AUTHORITY_NOT_FOUND"
        return report
    if len(groups) != 1:
        report["status"] = "FAIL_CLOSED_DISTINCT_EXACT_POLICY_SERVICE_LAUNCH_COMMANDS"
        report["launch_command_sha256s"] = sorted(groups)
        return report
    command_sha = next(iter(groups))
    aliases = sorted(
        groups[command_sha],
        key=lambda row: (
            str(row["path"]), str(row["json_pointer"]), str(row["command_field"]),
            str(row["file_sha256"]),
        ),
    )
    chosen = aliases[0]
    report.update({
        "status": "RESOLVED_UNIQUE_EXACT_POLICY_SERVICE_LAUNCH_AUTHORITY",
        "authority_path": chosen["path"],
        "authority_file_sha256": chosen["file_sha256"],
        "authority_json_pointer": chosen["json_pointer"],
        "authority_command_field": chosen["command_field"],
        "authority_alias_paths": sorted({str(row["path"]) for row in aliases}),
        "authority_aliases": [
            {
                "path": row["path"],
                "file_sha256": row["file_sha256"],
                "json_pointer": row["json_pointer"],
                "command_field": row["command_field"],
            }
            for row in aliases
        ],
        "launch_command": chosen["launch_command"],
        "launch_command_sha256": command_sha,
    })
    return report

def wait_for_policy_runtime_service(runtime: dict[str, object], *, timeout_seconds: float, poll_seconds: float = 2.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    last = probe_policy_runtime_service(runtime, timeout_seconds=min(2.0, max(0.2, poll_seconds)))
    while not last.get("ready") and time.monotonic() < deadline:
        time.sleep(poll_seconds)
        last = probe_policy_runtime_service(runtime, timeout_seconds=min(2.0, max(0.2, poll_seconds)))
    return last


def readiness_with_sha(report: dict[str, object]) -> dict[str, object]:
    payload = dict(report)
    payload["readiness_sha256"] = "0" * 64
    payload["readiness_sha256"] = hashlib.sha256(
        b"POLICY_RUNTIME_SERVICE_READINESS_V1\0" + _canon({k: v for k, v in payload.items() if k != "readiness_sha256"})
    ).hexdigest()
    return payload


def write_once(path: str | Path, value: object) -> None:
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _canon(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("os.write made no progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener

from .common import (
    PI0_SERVED_NAME,
    T2_SERVED_NAME,
    Stage4DError,
    build_vllm_command,
    load_json,
    sha256_file,
    write_new_json,
)

_DIRECT = build_opener(ProxyHandler({}))


def _urlopen(request: Request, timeout: float):
    parsed = urlparse(request.full_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise Stage4DError("READINESS_ONLY_PERMITS_LOOPBACK_HTTP")
    return _DIRECT.open(request, timeout=timeout)


def get_json(url: str, timeout: float) -> dict:
    with _urlopen(Request(url, method="GET"), timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise Stage4DError("READINESS_HTTP_JSON_OBJECT_REQUIRED")
    return value


def post_json(url: str, payload: dict, timeout: float) -> dict:
    request = Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _urlopen(request, timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise Stage4DError("READINESS_HTTP_JSON_OBJECT_REQUIRED")
    return value


def wait_ready(base_url: str, process: subprocess.Popen, timeout_seconds: float = 600.0) -> list[str]:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise Stage4DError(f"VLLM_EXITED_EARLY:{process.returncode}")
        try:
            with _urlopen(Request(base_url + "/health", method="GET"), 3.0) as response:
                if response.status != 200:
                    raise Stage4DError(f"VLLM_HEALTH_NON_200:{response.status}")
            models = get_json(base_url + "/v1/models", 5.0)
            model_ids = sorted(
                row.get("id")
                for row in models.get("data", [])
                if isinstance(row, dict) and isinstance(row.get("id"), str)
            )
            required = {PI0_SERVED_NAME, T2_SERVED_NAME}
            if not required.issubset(model_ids):
                raise Stage4DError(f"VLLM_MODELS_MISSING:{model_ids}")
            return model_ids
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, Stage4DError) as exc:
            last_error = repr(exc)
            time.sleep(2.0)
    raise Stage4DError("VLLM_READINESS_TIMEOUT:" + last_error)


def find_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding-root", required=True)
    args = parser.parse_args(argv)

    binding_root = Path(args.binding_root).resolve()
    if not binding_root.is_dir():
        raise Stage4DError("BINDING_ROOT_MISSING")
    inputs = load_json(binding_root / "BINDING_INPUTS.json")
    static = load_json(binding_root / "STAGE4D_STATIC_READINESS_V1.json")
    server = load_json(binding_root / "SELECT_SERVER_RUNTIME_MANIFEST_V1.json")
    if static.get("evaluation_execution_authorized") is not False:
        raise Stage4DError("STATIC_BINDING_PREMATURE_EXECUTION_AUTHORITY")
    if importlib.metadata.version("vllm") != "0.11.0":
        raise Stage4DError("VLLM_VERSION_CHANGED")
    registry = server.get("static_lora_registry")
    if not isinstance(registry, list) or len(registry) != 1:
        raise Stage4DError("STATIC_LORA_REGISTRY_NOT_SINGLE_CANDIDATE")
    if registry[0].get("served_model_name") != T2_SERVED_NAME:
        raise Stage4DError("STATIC_LORA_SERVED_NAME_CHANGED")

    base_model_path = Path(inputs["base_model_path"])
    adapter_path = Path(inputs["candidate_adapter_path"])
    if not base_model_path.is_dir() or base_model_path.is_symlink():
        raise Stage4DError("BASE_MODEL_PATH_INVALID")
    if not adapter_path.is_dir() or adapter_path.is_symlink():
        raise Stage4DError("ADAPTER_PATH_INVALID")

    readiness_root = binding_root / "readiness"
    readiness_root.mkdir(parents=True, exist_ok=True)
    job_id = os.environ.get("SLURM_JOB_ID", "local")
    receipt_path = readiness_root / f"RUNTIME_READINESS_{job_id}_V1.json"
    if receipt_path.exists():
        raise Stage4DError(f"READINESS_RECEIPT_ALREADY_EXISTS:{receipt_path}")

    port = find_port()
    base_url = f"http://127.0.0.1:{port}"
    command = build_vllm_command(
        python_executable=sys.executable,
        base_model_path=str(base_model_path),
        adapter_path=str(adapter_path),
        host="127.0.0.1",
        port=port,
    )
    command_path = readiness_root / f"vllm_{job_id}.command.json"
    write_new_json(command_path, command)
    stdout_path = readiness_root / f"vllm_{job_id}.out"
    stderr_path = readiness_root / f"vllm_{job_id}.err"

    with stdout_path.open("ab") as stdout, stderr_path.open("ab") as stderr:
        process = subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[1],
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
    try:
        model_ids = wait_ready(base_url, process)
        probes = []
        for model in (PI0_SERVED_NAME, T2_SERVED_NAME):
            response = post_json(
                base_url + "/v1/chat/completions",
                {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": "Engineering route check only. Reply READY.",
                        }
                    ],
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "max_tokens": 8,
                },
                180.0,
            )
            returned = response.get("model")
            if returned != model:
                raise Stage4DError(
                    f"VLLM_ROUTE_MODEL_IDENTITY_CHANGED:requested={model}:returned={returned}"
                )
            probes.append(
                {
                    "requested_model": model,
                    "returned_model": returned,
                    "choice_count": len(response.get("choices", [])),
                }
            )

        receipt = {
            "schema_id": "STAGE4D_STATIC_SERVER_ROUTE_READINESS_V1",
            "schema_version": 1,
            "status": "PASS",
            "slurm_job_id": str(job_id),
            "binding_root": str(binding_root),
            "base_url": base_url,
            "model_ids": model_ids,
            "probes": probes,
            "model_probe_count": 2,
            "alfworld_environment_execution_count": 0,
            "scientific_select_cell_execution_count": 0,
            "scientific_outcome_generated": False,
            "evaluation_execution_authorized": False,
            "execution_authorization_ready": True,
            "next_gate": "EXPLICIT_FULL_SELECT_EXECUTION_AUTHORIZATION",
        }
        write_new_json(receipt_path, receipt)
        print("STAGE4D_STATIC_SERVER_ROUTE_READINESS_PASS")
        print(f"READINESS_RECEIPT={receipt_path}")
        print(f"READINESS_RECEIPT_SHA256={sha256_file(receipt_path)}")
        print("MODEL_PROBE_COUNT=2")
        print("ALFWORLD_ENVIRONMENT_EXECUTION_COUNT=0")
        print("SCIENTIFIC_SELECT_CELL_EXECUTION_COUNT=0")
        print("EVALUATION_EXECUTION_AUTHORIZED=false")
        print("EXECUTION_AUTHORIZATION_READY=true")
        print("NEXT_GATE=EXPLICIT_FULL_SELECT_EXECUTION_AUTHORIZATION")
        return 0
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + 30.0
            while process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.5)
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        try:
            process.wait(timeout=30.0)
        except subprocess.TimeoutExpired:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

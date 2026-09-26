#!/usr/bin/env python3
"""Launch the exact frozen vLLM+LoRA runtime and run Memory closure locally.

The enclosing Slurm allocation owns the GPU. This program launches one vLLM
0.11.0 server, verifies health/model registration, executes Stage 1B -> 2 -> 3
through the Package-2 closure runner, and then shuts down the server.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.request import urlopen

from pchsi.evaluation.canonical_evidence import strict_json_loads


APPROVAL = "EXECUTION_APPROVED_FAILURE_MEMORY_LIVE_STAGES_V1"


def object_value(path: Path) -> dict[str, object]:
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise SystemExit("STOP=GPU_JOB_OBJECT_REQUIRED:" + str(path))
    return value


def wait_health(url: str, process: subprocess.Popen[bytes], timeout: int) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SystemExit(
                "STOP=VLLM_EXITED_BEFORE_HEALTH:" + str(process.returncode)
            )
        try:
            with urlopen(url + "/health", timeout=5) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = type(exc).__name__ + ":" + str(exc)
        time.sleep(2)
    raise SystemExit("STOP=VLLM_HEALTH_TIMEOUT:" + last_error)


def verify_model(url: str, served_model_name: str) -> None:
    with urlopen(url + "/v1/models", timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    names = {
        row.get("id")
        for row in payload.get("data", [])
        if isinstance(row, dict)
    }
    if served_model_name not in names:
        raise SystemExit(
            "STOP=FROZEN_LORA_MODEL_NOT_REGISTERED:"
            + served_model_name
            + ":"
            + repr(sorted(names, key=str))
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--closure-manifest", required=True)
    parser.add_argument("--log-root", required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    closure = object_value(Path(args.closure_manifest))
    stage1_manifest_path = Path(
        str(closure["inputs"]["stage1b_execution_manifest"]["path"])
    )
    stage1 = object_value(stage1_manifest_path)
    runtime_identity_path = Path(
        str(stage1["operational_paths"]["runtime_identity"])
    )
    runtime = object_value(runtime_identity_path)
    source_runtime = object_value(
        Path(str(runtime["source_runtime_binding_path"]))
    )

    observed_vllm = __import__("vllm").__version__
    if observed_vllm != source_runtime["vllm_version"]:
        raise SystemExit(
            "STOP=VLLM_VERSION_MISMATCH:"
            + observed_vllm
            + "!="
            + str(source_runtime["vllm_version"])
        )

    log_root = Path(args.log_root)
    log_root.mkdir(parents=True, exist_ok=True)
    stdout_path = log_root / "vllm.stdout.log"
    stderr_path = log_root / "vllm.stderr.log"
    base_url = f"http://127.0.0.1:{args.port}"

    command = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model", str(source_runtime["base_model_local_path"]),
        "--host", "127.0.0.1",
        "--port", str(args.port),
        "--dtype", str(source_runtime["dtype"]),
        "--tensor-parallel-size", str(source_runtime["tensor_parallel_size"]),
        "--generation-config", str(source_runtime["generation_config_mode"]),
        "--chat-template-content-format",
        str(source_runtime["chat_template_content_format"]),
        "--enable-lora",
        "--lora-modules",
        str(source_runtime["served_model_name"])
        + "="
        + str(source_runtime["adapter_path"]),
        "--max-lora-rank", str(source_runtime["max_lora_rank"]),
        "--max-loras", str(source_runtime["max_loras"]),
        "--max-cpu-loras", str(source_runtime["max_cpu_loras"]),
        "--lora-dtype", str(source_runtime["lora_dtype"]),
        "--gpu-memory-utilization",
        os.environ.get("FAILURE_MEMORY_GPU_MEMORY_UTILIZATION", "0.90"),
        "--max-num-seqs",
        os.environ.get("FAILURE_MEMORY_VLLM_MAX_NUM_SEQS", "16"),
        "--disable-log-requests",
    ]

    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(
            command,
            cwd=repo,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )

    try:
        wait_health(
            base_url,
            process,
            int(os.environ.get(
                "FAILURE_MEMORY_VLLM_STARTUP_TIMEOUT_SECONDS", "1800"
            )),
        )
        verify_model(base_url, str(source_runtime["served_model_name"]))
        env = dict(os.environ)
        env["FAILURE_MEMORY_LIVE_EXECUTION_APPROVAL"] = APPROVAL
        env["FAILURE_MEMORY_POLICY_BASE_URL"] = base_url
        subprocess.run(
            [
                sys.executable,
                str(repo / "scripts/memory/run_memory_final_parallel_closure_v1.py"),
                "--closure-manifest", str(Path(args.closure_manifest).resolve()),
            ],
            check=True,
            cwd=repo,
            env=env,
        )
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()

    closure_root = Path(str(closure["closure_output_root"]))
    marker = closure_root / "handoff_and_closure/FAILURE_MEMORY_MODULE_CLOSURE_V1.json"
    if not marker.is_file():
        raise SystemExit("STOP=MEMORY_CLOSURE_MARKER_MISSING_AFTER_GPU_JOB")
    print("FAILURE_MEMORY_FINAL_GPU_JOB_V1_PASS")
    print("CLOSURE_ROOT=" + str(closure_root))


if __name__ == "__main__":
    main()

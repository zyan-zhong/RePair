from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from .contract import EXPECTED_BINDING_ROOT, PI0_SERVED_NAME, T2_SERVED_NAME, READINESS_PACKAGE_ROOT, Stage4DFullError, load_json, write_or_reuse_exact
from .live import execute_shard
from .parallel import require_single_visible_device


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-root", required=True)
    parser.add_argument("--shard-id", required=True, type=int)
    parser.add_argument("--completed-prefix-count", required=True, type=int)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--worker-budget-seconds", required=True, type=float)
    args = parser.parse_args(argv)

    visible_gpu = require_single_visible_device(os.environ.get("CUDA_VISIBLE_DEVICES", ""))
    print(
        f"STAGE4D_PARALLEL_WORKER_GPU shard={args.shard_id} cuda_visible_devices={visible_gpu}",
        flush=True,
    )
    execution_root = Path(args.execution_root).resolve()
    auth = load_json(execution_root / "STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_V1.json")
    if auth.get("evaluation_execution_authorized") is not True:
        raise Stage4DFullError("FULL_SELECT_EXECUTION_NOT_AUTHORIZED")
    if Path(auth.get("binding_root", "")) != EXPECTED_BINDING_ROOT:
        raise Stage4DFullError("FULL_SELECT_BINDING_CHANGED")

    if str(READINESS_PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(READINESS_PACKAGE_ROOT))
    readiness = importlib.import_module("stage4d_pkg.readiness")
    inputs = load_json(EXPECTED_BINDING_ROOT / "BINDING_INPUTS.json")
    base_url = f"http://127.0.0.1:{args.port}"
    command = readiness.build_vllm_command(
        python_executable=sys.executable,
        base_model_path=inputs["base_model_path"],
        adapter_path=inputs["candidate_adapter_path"],
        host="127.0.0.1",
        port=args.port,
    )
    runtime_root = execution_root / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    job_id = os.environ.get("SLURM_JOB_ID", "local")
    suffix = f"{job_id}_shard{args.shard_id}"
    write_or_reuse_exact(runtime_root / f"vllm_{suffix}.command.json", command)
    with (runtime_root / f"vllm_{suffix}.out").open("ab") as out, (runtime_root / f"vllm_{suffix}.err").open("ab") as err:
        process = subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[1],
            stdout=out,
            stderr=err,
            start_new_session=True,
        )
    worker_start = time.monotonic()
    stop_before = worker_start + args.worker_budget_seconds
    try:
        model_ids = readiness.wait_ready(base_url, process, timeout_seconds=600.0)
        if not {PI0_SERVED_NAME, T2_SERVED_NAME}.issubset(set(model_ids)):
            raise Stage4DFullError("FULL_SELECT_SERVER_MODEL_SET_CHANGED")
        result = execute_shard(
            execution_root=execution_root,
            binding_root=EXPECTED_BINDING_ROOT,
            base_url=base_url,
            shard_id=args.shard_id,
            completed_prefix_count=args.completed_prefix_count,
            stop_before_monotonic=stop_before,
        )
        write_or_reuse_exact(
            execution_root / "parallel_v1" / f"shard_{args.shard_id}" / f"SHARD_STATUS_{job_id}_V1.json",
            {
                "schema_id": "STAGE4D_PARALLEL_SHARD_STATUS_V1",
                "schema_version": 1,
                "slurm_job_id": job_id,
                "shard_id": args.shard_id,
                "completed_prefix_count_at_start": args.completed_prefix_count,
                "assigned_pair_count": result["assigned_pair_count"],
                "t0_cell_count": result["t0_cell_count"],
                "t2_cell_count": result["t2_cell_count"],
                "total_condition_cell_count": result["total_condition_cell_count"],
                "complete": result["complete"],
                "graceful_partial": result["graceful_partial"],
                "result_interpretation_authorized": False,
                "promotion_authorized": False,
            },
        )
        print(f"STAGE4D_PARALLEL_SHARD_DONE shard={args.shard_id} complete={str(result['complete']).lower()} pairs={result['t0_cell_count']}/{result['assigned_pair_count']}", flush=True)
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

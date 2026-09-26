from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

from .contract import EXPECTED_BINDING_ROOT, EXPECTED_PAIR_CELLS, EXPECTED_TOTAL_CELLS, LOG_ROOT, Stage4DFullError, load_json, write_or_reuse_exact
from .live import canonical_completed_prefix, consolidate_shards
from .parallel import PARALLEL_SHARD_COUNT, allocate_free_ports

WORKER_BUDGET_SECONDS = 3 * 60 * 60 + 15 * 60


def _completion_payload(*, execution_root: Path, auth: dict, execution: dict) -> dict:
    return {
        "schema_id": "STAGE4D_FULL_SELECT_EXECUTION_COMPLETE_V1",
        "schema_version": 1,
        "authorization_sha256": execution_root.name,
        "binding_sha256": auth["binding_sha256"],
        "readiness_receipt_sha256": auth["readiness_receipt_sha256"],
        "t0_condition_cell_count": execution["t0_cell_count"],
        "t2_condition_cell_count": execution["t2_cell_count"],
        "paired_task_seed_cell_count": EXPECTED_PAIR_CELLS,
        "total_condition_cell_count": EXPECTED_TOTAL_CELLS,
        "scientific_execution_complete": True,
        "result_interpretation_authorized": False,
        "promotion_authorized": False,
        "next_gate": "STAGE4E_EXISTING_SELECT_RESULT_AUDIT",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-root", required=True)
    args = parser.parse_args(argv)
    execution_root = Path(args.execution_root).resolve()
    auth = load_json(execution_root / "STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_V1.json")
    if auth.get("evaluation_execution_authorized") is not True:
        raise Stage4DFullError("FULL_SELECT_EXECUTION_NOT_AUTHORIZED")
    if auth.get("result_interpretation_authorized") is not False or auth.get("promotion_authorized") is not False:
        raise Stage4DFullError("FULL_SELECT_AUTHORITY_SCOPE_CHANGED")
    if Path(auth.get("binding_root", "")) != EXPECTED_BINDING_ROOT:
        raise Stage4DFullError("FULL_SELECT_BINDING_CHANGED")

    completed_prefix = canonical_completed_prefix(
        execution_root=execution_root,
        binding_root=EXPECTED_BINDING_ROOT,
    )
    if completed_prefix == EXPECTED_PAIR_CELLS:
        execution = {
            "t0_cell_count": EXPECTED_PAIR_CELLS,
            "t2_cell_count": EXPECTED_PAIR_CELLS,
            "total_condition_cell_count": EXPECTED_TOTAL_CELLS,
            "complete": True,
        }
        write_or_reuse_exact(
            execution_root / "STAGE4D_FULL_SELECT_EXECUTION_COMPLETE_V1.json",
            _completion_payload(execution_root=execution_root, auth=auth, execution=execution),
        )
        print("STAGE4D_FULL_SELECT_EXECUTION_COMPLETE")
        print(f"T0_CELL_COUNT={EXPECTED_PAIR_CELLS}")
        print(f"T2_CELL_COUNT={EXPECTED_PAIR_CELLS}")
        print(f"TOTAL_CONDITION_CELL_COUNT={EXPECTED_TOTAL_CELLS}")
        print("RESULT_INTERPRETATION_AUTHORIZED=false")
        print("PROMOTION_AUTHORIZED=false")
        print("NEXT_GATE=STAGE4E_EXISTING_SELECT_RESULT_AUDIT")
        return 0

    ports = allocate_free_ports(PARALLEL_SHARD_COUNT)
    job_id = os.environ.get("SLURM_JOB_ID", "local")
    runtime_root = execution_root / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)

    workers: list[tuple[int, subprocess.Popen, object, object, Path, Path]] = []
    for shard_id, port in enumerate(ports):
        env = os.environ.copy()
        cache_root = Path(env["STAGE4D_RUNTIME_CACHE_ROOT"]) / f"shard_{shard_id}"
        env["VLLM_CACHE_ROOT"] = str(cache_root / "vllm")
        env["TORCHINDUCTOR_CACHE_DIR"] = str(cache_root / "torchinductor")
        env["TRITON_CACHE_DIR"] = str(cache_root / "triton")
        env["TMPDIR"] = f"/tmp/st4d-{env['SLURM_JOB_USER']}-{job_id}-shard{shard_id}"
        for path in (
            Path(env["VLLM_CACHE_ROOT"]),
            Path(env["TORCHINDUCTOR_CACHE_DIR"]),
            Path(env["TRITON_CACHE_DIR"]),
            Path(env["TMPDIR"]),
        ):
            path.mkdir(parents=True, exist_ok=True)
        out_path = runtime_root / f"worker_{job_id}_shard{shard_id}.out"
        err_path = runtime_root / f"worker_{job_id}_shard{shard_id}.err"
        out = out_path.open("ab")
        err = err_path.open("ab")
        command = [
            "srun",
            "--exclusive",
            "--gpus=1",
            sys.executable,
            "-m",
            "stage4d_full.shard_worker",
            "--execution-root",
            str(execution_root),
            "--shard-id",
            str(shard_id),
            "--completed-prefix-count",
            str(completed_prefix),
            "--port",
            str(port),
            "--worker-budget-seconds",
            str(WORKER_BUDGET_SECONDS),
        ]
        process = subprocess.Popen(
            command,
            env=env,
            stdout=out,
            stderr=err,
            cwd=Path(__file__).resolve().parents[1],
        )
        workers.append((shard_id, process, out, err, out_path, err_path))
        print(
            f"STAGE4D_PARALLEL_SHARD_STARTED shard={shard_id} port={port} srun_pid={process.pid}",
            flush=True,
        )

    failures: list[str] = []
    try:
        for shard_id, process, out, err, out_path, err_path in workers:
            rc = process.wait()
            out.flush()
            err.flush()
            print(f"STAGE4D_PARALLEL_SHARD_EXIT shard={shard_id} rc={rc}", flush=True)
            if rc != 0:
                failures.append(f"shard={shard_id}:rc={rc}:stdout={out_path}:stderr={err_path}")
    finally:
        for _shard_id, process, out, err, _out_path, _err_path in workers:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
            out.close()
            err.close()
    if failures:
        raise Stage4DFullError("PARALLEL_SHARD_FAILURE:" + ";".join(failures))

    statuses = []
    for shard_id in range(PARALLEL_SHARD_COUNT):
        status_path = execution_root / "parallel_v1" / f"shard_{shard_id}" / f"SHARD_STATUS_{job_id}_V1.json"
        status = load_json(status_path)
        if status.get("shard_id") != shard_id:
            raise Stage4DFullError("PARALLEL_SHARD_STATUS_ID_CHANGED")
        statuses.append(status)
    if not all(status.get("complete") is True for status in statuses):
        print("STAGE4D_FULL_SELECT_EXECUTION_GRACEFUL_PARTIAL")
        print(f"CANONICAL_PAIR_PREFIX={completed_prefix}/{EXPECTED_PAIR_CELLS}")
        for status in statuses:
            print(
                f"SHARD_PROGRESS shard={status['shard_id']} pairs={status['t0_cell_count']}/{status['assigned_pair_count']} complete={str(status['complete']).lower()}"
            )
        print("RESUBMIT_SAME_PACKAGE=true")
        print("RESULT_INTERPRETATION_AUTHORIZED=false")
        return 0

    execution = consolidate_shards(
        execution_root=execution_root,
        binding_root=EXPECTED_BINDING_ROOT,
        completed_prefix_count=completed_prefix,
    )
    if not execution["complete"]:
        raise Stage4DFullError("PARALLEL_CONSOLIDATION_NOT_COMPLETE")
    write_or_reuse_exact(
        execution_root / "STAGE4D_FULL_SELECT_EXECUTION_COMPLETE_V1.json",
        _completion_payload(execution_root=execution_root, auth=auth, execution=execution),
    )
    print("STAGE4D_FULL_SELECT_EXECUTION_COMPLETE")
    print(f"T0_CELL_COUNT={execution['t0_cell_count']}")
    print(f"T2_CELL_COUNT={execution['t2_cell_count']}")
    print(f"TOTAL_CONDITION_CELL_COUNT={execution['total_condition_cell_count']}")
    print("PARALLEL_SHARD_COUNT=4")
    print("RESULT_INTERPRETATION_AUTHORIZED=false")
    print("PROMOTION_AUTHORIZED=false")
    print("NEXT_GATE=STAGE4E_EXISTING_SELECT_RESULT_AUDIT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

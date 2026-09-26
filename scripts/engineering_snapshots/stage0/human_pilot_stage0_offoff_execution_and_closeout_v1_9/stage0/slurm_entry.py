from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from .common import Stage0Error, load_json_object, sha256_file, write_or_reuse_exact
from .constants import (
    FINAL_REVIEW_ZIP,
    PREFLIGHT_ROOT,
    STAGE0_ROOT,
    TWIN_REVIEW,
)
from .live_runner import execute_stage0
from .result_audit import finalize_stage0
from .runtime_server import (
    build_vllm_command,
    probe_registered_models,
    wait_for_server,
)
from .twin_contract import load_twin_review


def main() -> int:
    job_start_monotonic = time.monotonic()
    stop_before_monotonic = (
        job_start_monotonic
        + 30 * 60
    )
    package_root = Path(__file__).resolve().parents[1]
    if FINAL_REVIEW_ZIP.exists():
        raise Stage0Error(f"FINAL_REVIEW_ALREADY_EXISTS:{FINAL_REVIEW_ZIP}")
    preflight = load_json_object(
        PREFLIGHT_ROOT / "OFFLINE_PREFLIGHT_RECEIPT_V1.json"
    )
    twin = load_twin_review(TWIN_REVIEW)
    server_manifest = twin["values"][
        "bindings/SELECT_SERVER_RUNTIME_MANIFEST_V1.json"
    ]

    job_id = int(os.environ.get("SLURM_JOB_ID", "0") or "0")
    port = 18000 + (job_id % 1000)
    host = "127.0.0.1"
    base_url = f"http://{host}:{port}"
    runtime_root = STAGE0_ROOT / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    stdout_path = runtime_root / f"vllm_{job_id}.out"
    stderr_path = runtime_root / f"vllm_{job_id}.err"
    command = build_vllm_command(
        server_manifest=server_manifest,
        base_model_path=preflight["base_model_local_path"],
        host=host,
        port=port,
    )
    (runtime_root / f"vllm_{job_id}.command.json").write_text(
        json.dumps(command, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with stdout_path.open("ab") as stdout, stderr_path.open("ab") as stderr:
        process = subprocess.Popen(
            command,
            cwd=package_root,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
    try:
        readiness = wait_for_server(
            base_url=base_url,
            process=process,
            timeout_seconds=600.0,
        )
        probe = probe_registered_models(base_url=base_url)
        readiness_value = {
            "schema_id": "HUMAN_PILOT_STAGE0_RUNTIME_READINESS_V1",
            "schema_version": 1,
            "slurm_job_id": str(job_id),
            "base_url": base_url,
            "server_readiness": readiness,
            "model_probe": probe,
            "model_execution_count_before_offoff": probe[
                "model_probe_count"
            ],
            "environment_execution_count_before_offoff": 0,
        }
        runtime_readiness_path = (
            runtime_root
            / (
                "RUNTIME_READINESS_JOB_"
                + str(job_id)
                + "_V1.json"
            )
        )
        write_or_reuse_exact(
            runtime_readiness_path,
            readiness_value,
        )
        print(
            "RUNTIME_READINESS_PATH="
            + str(runtime_readiness_path)
        )

        execution = execute_stage0(
            base_url=base_url,
            stop_before_monotonic=(
                stop_before_monotonic
            ),
        )
        if execution["graceful_partial"]:
            print(
                "STAGE0_GRACEFUL_PARTIAL_COMPLETE"
            )
            print(
                "PARENT_CELL_COUNT="
                + str(
                    execution[
                        "parent_cell_count"
                    ]
                )
            )
            print(
                "CANDIDATE_CELL_COUNT="
                + str(
                    execution[
                        "candidate_cell_count"
                    ]
                )
            )
            print(
                "TOTAL_CONDITION_CELL_COUNT="
                + str(
                    execution[
                        "total_condition_cell_count"
                    ]
                )
            )
            print("RESUBMIT_SAME_PACKAGE=true")
            print("PAPER_EFFICACY_EVIDENCE=false")
            print("PROMOTION_ELIGIBLE=false")
            return 0

        complete = {
            "parent_cell_count": 85,
            "candidate_cell_count": 85,
            "total_condition_cell_count": 170,
            "graceful_partial": False,
        }
        if execution != complete:
            raise Stage0Error(
                f"STAGE0_EXECUTION_INCOMPLETE:{execution}"
            )

        inventory_sha = preflight["package_inventory_sha256"]
        final = finalize_stage0(package_inventory_sha256=inventory_sha)
        print("HUMAN_PILOT_STAGE0_OFFOFF_EXECUTION_PASS")
        print("PARENT_CELL_COUNT=85")
        print("CANDIDATE_CELL_COUNT=85")
        print("PAIRED_CELL_COUNT=85")
        print("TOTAL_CONDITION_CELL_COUNT=170")
        print("PAPER_EFFICACY_EVIDENCE=false")
        print("PROMOTION_ELIGIBLE=false")
        print("FINAL_REVIEW_ZIP=" + final["publication"]["path"])
        print("FINAL_REVIEW_ZIP_SHA256=" + final["publication"]["sha256"])
        print(
            "NEXT_GATE=GENERIC_ROUND_ORCHESTRATOR_AND_ROLE_HANDOFF_AUTOMATION"
        )
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
        process.wait(timeout=30.0)


if __name__ == "__main__":
    raise SystemExit(main())

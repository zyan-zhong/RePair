from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from safe_io import (
    load_json,
    safe_extract_zip,
    sha_file,
    write_new_bytes,
    write_new_json,
)
from submission_contract import (
    activation_identity,
    build_sbatch_argv,
    parse_sbatch_parsable,
)


def run(argv: list[str], *, stdout=None, stderr=None, check=False):
    return subprocess.run(
        argv,
        stdout=stdout if stdout is not None else subprocess.PIPE,
        stderr=stderr if stderr is not None else subprocess.PIPE,
        text=stdout is None and stderr is None,
        shell=False,
        check=check,
    )


def _query_jobs(job_name: str, comment: str) -> list[dict[str, str]]:
    cp = run(["squeue", "--noheader", "--format", "%i|%j|%k|%T"])
    if cp.returncode != 0:
        return []
    rows = []
    for raw in cp.stdout.splitlines():
        parts = raw.split("|", 3)
        if len(parts) != 4:
            continue
        job_id, name, observed_comment, state = (x.strip() for x in parts)
        if name == job_name and observed_comment == comment and job_id.isdigit():
            rows.append(
                {
                    "job_id": job_id,
                    "job_name": name,
                    "comment": observed_comment,
                    "state": state,
                }
            )
    return rows


def _release_job(job_id: str, state_root: Path) -> None:
    receipt = state_root / "SLURM_RELEASE_RECEIPT_V1.json"
    if receipt.is_file():
        return
    cp = run(["scontrol", "release", job_id])
    if cp.returncode != 0:
        raise SystemExit(
            "STOP=V1232_SCONTROL_RELEASE_FAILED:"
            + (cp.stderr or cp.stdout or "").strip()
        )
    write_new_json(
        receipt,
        {
            "schema_id": "PCHSI_V1232_SLURM_RELEASE_RECEIPT_V1",
            "schema_version": 1,
            "job_id": job_id,
            "release_performed": True,
            "human_release_decision": False,
        },
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1230-output-root", required=True)
    ap.add_argument("--lineage-root", required=True)
    args = ap.parse_args()

    package = Path(__file__).resolve().parent
    v1230 = Path(args.v1230_output_root).resolve()
    lineage = Path(args.lineage_root).resolve()

    authority = load_json(package / "V1232_INPUT_CAPSULE_AUTHORITY_V1.json")
    capsule = package / authority["capsule_filename"]
    if sha_file(capsule) != authority["capsule_sha256"]:
        raise SystemExit("STOP=V1232_CAPSULE_IDENTITY_CHANGED")

    # Validate/extract once to derive deterministic activation.
    scratch = package / ".v1232_submit_preflight"
    if scratch.exists():
        # Package-local scratch from an earlier invocation is not authority.
        # Do not delete it; use a process-local sibling instead.
        scratch = package / (".v1232_submit_preflight_" + str(os.getpid()))
    safe_extract_zip(capsule, scratch)
    try:
        execution_binding_path = (
            scratch / "ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_EXECUTION_BINDING_V1.json"
        )
        slurm_plan_path = (
            scratch / "ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_SLURM_RESOURCE_PLAN_V1.json"
        )
        allocation_path = (
            scratch / "ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_ALLOCATION_PREFLIGHT_V1.json"
        )
        execution_binding = load_json(execution_binding_path)
        slurm_plan = load_json(slurm_plan_path)
        allocation = load_json(allocation_path)

        implementation_head = execution_binding.get("implementation_head")
        if not isinstance(implementation_head, str) or not implementation_head:
            raise SystemExit("STOP=V1232_IMPLEMENTATION_HEAD_INVALID")

        activation = activation_identity(
            capsule_sha256=authority["capsule_sha256"],
            execution_binding_file_sha256=sha_file(execution_binding_path),
            slurm_plan_file_sha256=sha_file(slurm_plan_path),
            allocation_preflight_file_sha256=sha_file(allocation_path),
            implementation_head=implementation_head,
        )
    finally:
        # Scratch contains only a verified copy of the sealed package input.
        # Remove exactly this process-created directory.
        import shutil
        shutil.rmtree(scratch, ignore_errors=False)

    state_root = (
        lineage
        / "v1232_live_memory_aware_train_update_rollout"
        / activation
    )
    state_root.mkdir(parents=True, exist_ok=True, mode=0o700)

    terminal = state_root / "PCHSI_V1232_JOB_TERMINAL_V1.json"
    if terminal.is_file():
        obj = load_json(terminal)
        print("STATUS=" + str(obj.get("status")))
        print("V1232_STATE_ROOT=" + str(state_root))
        print("V1232_TERMINAL_ALREADY_EXISTS=true")
        return 0

    reservation = state_root / "PCHSI_V1232_SUBMISSION_RESERVATION_V1.json"
    if not reservation.exists():
        write_new_json(
            reservation,
            {
                "schema_id": "PCHSI_V1232_SUBMISSION_RESERVATION_V1",
                "schema_version": 1,
                "activation_id": activation,
                "capsule_sha256": authority["capsule_sha256"],
                "implementation_head": implementation_head,
                "slurm_plan_sha256": slurm_plan.get("plan_sha256"),
                "allocation_preflight_sha256": allocation.get("contract_sha256"),
                "same_round_fresh_rollout": True,
                "human_submission_decision_required": False,
            },
        )

    capsule_copy = state_root / capsule.name
    if not capsule_copy.exists():
        write_new_bytes(capsule_copy, capsule.read_bytes())
    elif sha_file(capsule_copy) != authority["capsule_sha256"]:
        raise SystemExit("STOP=V1232_STATE_CAPSULE_CHANGED")

    job_script = state_root / "run_v1232_batch.sh"
    service_python = (
        execution_binding
        .get("service_launch_contract", {})
        .get("launch_command", [None])[0]
    )
    if not isinstance(service_python, str) or not service_python:
        raise SystemExit("STOP=V1232_SERVICE_PYTHON_AUTHORITY_MISSING")

    if not job_script.exists():
        script = (
            "#!/usr/bin/env bash\n"
            "exec "
            + json.dumps(service_python)
            + " -B "
            + json.dumps(str(package / "live_rollout_job.py"))
            + " --state-root "
            + json.dumps(str(state_root))
            + " --v1230-output-root "
            + json.dumps(str(v1230))
            + " --capsule "
            + json.dumps(str(capsule_copy))
            + "\n"
        )
        write_new_bytes(job_script, script.encode("utf-8"), mode=0o700)

    stdout_path = state_root / "slurm-%j.out"
    stderr_path = state_root / "slurm-%j.err"
    sbatch_argv = build_sbatch_argv(
        slurm_plan=slurm_plan,
        script_path=job_script,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        activation_id=activation,
    )

    short = activation[:24]
    job_name = "pchsi-v1232-" + short
    comment = "pchsi-v1232:" + short

    submission_receipt = state_root / "PCHSI_V1232_SLURM_SUBMISSION_RECEIPT_V1.json"
    raw_stdout_path = state_root / "sbatch.parsable.stdout"
    raw_stderr_path = state_root / "sbatch.stderr"

    job_id = None
    if submission_receipt.is_file():
        rec = load_json(submission_receipt)
        value = rec.get("job_id")
        if isinstance(value, str) and value.isdigit():
            job_id = value
    elif raw_stdout_path.is_file() and raw_stdout_path.stat().st_size:
        job_id = parse_sbatch_parsable(
            raw_stdout_path.read_text(encoding="utf-8")
        )
        write_new_json(
            submission_receipt,
            {
                "schema_id": "PCHSI_V1232_SLURM_SUBMISSION_RECEIPT_V1",
                "schema_version": 1,
                "activation_id": activation,
                "job_id": job_id,
                "sbatch_argv": sbatch_argv,
                "submitted_held": True,
                "job_requeue_authorized": False,
                "human_submission_decision_required": False,
                "adopted_from_raw_stdout": True,
            },
        )
    else:
        matches = _query_jobs(job_name, comment)
        if len(matches) > 1:
            raise SystemExit("STOP=V1232_SLURM_DUPLICATE_JOB_MATCHES")
        if len(matches) == 1:
            job_id = matches[0]["job_id"]
            write_new_json(
                submission_receipt,
                {
                    "schema_id": "PCHSI_V1232_SLURM_SUBMISSION_RECEIPT_V1",
                    "schema_version": 1,
                    "activation_id": activation,
                    "job_id": job_id,
                    "sbatch_argv": sbatch_argv,
                    "submitted_held": True,
                    "job_requeue_authorized": False,
                    "human_submission_decision_required": False,
                    "adopted_from_squeue_comment": True,
                },
            )
        else:
            # First and only submission call. stdout file is opened O_EXCL before
            # invoking sbatch so a returned job id survives a later launcher fault.
            fd_out = os.open(
                raw_stdout_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            fd_err = os.open(
                raw_stderr_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            try:
                with os.fdopen(fd_out, "w", encoding="utf-8", closefd=True) as out_handle:
                    with os.fdopen(fd_err, "w", encoding="utf-8", closefd=True) as err_handle:
                        cp = subprocess.run(
                            sbatch_argv,
                            stdout=out_handle,
                            stderr=err_handle,
                            text=True,
                            shell=False,
                            check=False,
                        )
                        out_handle.flush()
                        os.fsync(out_handle.fileno())
                        err_handle.flush()
                        os.fsync(err_handle.fileno())
            finally:
                pass

            if cp.returncode != 0:
                write_new_json(
                    state_root / "PCHSI_V1232_SUBMISSION_FAILURE_V1.json",
                    {
                        "schema_id": "PCHSI_V1232_SUBMISSION_FAILURE_V1",
                        "schema_version": 1,
                        "activation_id": activation,
                        "sbatch_returncode": cp.returncode,
                        "automatic_resubmit_authorized": False,
                        "scientific_execution_started": False,
                    },
                )
                raise SystemExit("STOP=V1232_SBATCH_FAILED_NO_AUTOMATIC_RESUBMIT")

            job_id = parse_sbatch_parsable(
                raw_stdout_path.read_text(encoding="utf-8")
            )
            write_new_json(
                submission_receipt,
                {
                    "schema_id": "PCHSI_V1232_SLURM_SUBMISSION_RECEIPT_V1",
                    "schema_version": 1,
                    "activation_id": activation,
                    "job_id": job_id,
                    "sbatch_argv": sbatch_argv,
                    "submitted_held": True,
                    "job_requeue_authorized": False,
                    "human_submission_decision_required": False,
                    "adopted_from_raw_stdout": False,
                },
            )

    if job_id is None:
        raise AssertionError("job id unresolved")

    _release_job(job_id, state_root)

    print("STATUS=V1232_SLURM_FRESH_ROLLOUT_SUBMITTED_AND_RELEASED")
    print("V1232_STATE_ROOT=" + str(state_root))
    print("V1232_ACTIVATION_ID=" + activation)
    print("V1232_SLURM_JOB_ID=" + job_id)
    print("V1232_SLURM_PARTITION=" + str(slurm_plan["partition"]))
    print("V1232_SLURM_GPU_COUNT=" + str(slurm_plan["gpus"]))
    print("V1232_SLURM_PARTITION_AUTHORITY=" + str(slurm_plan["partition_authority"]))
    print("V1232_SLURM_GPU_COUNT_AUTHORITY=" + str(slurm_plan["gpu_count_authority"]))
    print("HUMAN_PID_SELECTION_REQUIRED=false")
    print("HUMAN_PARSER_SELECTION_REQUIRED=false")
    print("HUMAN_RETRY_DECISION_REQUIRED=false")
    print("REMOTE_MUTATION_PERFORMED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

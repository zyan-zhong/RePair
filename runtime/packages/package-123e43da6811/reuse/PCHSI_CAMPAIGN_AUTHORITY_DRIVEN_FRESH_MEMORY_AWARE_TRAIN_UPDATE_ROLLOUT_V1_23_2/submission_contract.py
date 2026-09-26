from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping
import hashlib
import json


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def activation_identity(
    *,
    capsule_sha256: str,
    execution_binding_file_sha256: str,
    slurm_plan_file_sha256: str,
    allocation_preflight_file_sha256: str,
    implementation_head: str,
) -> str:
    payload = {
        "capsule_sha256": capsule_sha256,
        "execution_binding_file_sha256": execution_binding_file_sha256,
        "slurm_plan_file_sha256": slurm_plan_file_sha256,
        "allocation_preflight_file_sha256": allocation_preflight_file_sha256,
        "implementation_head": implementation_head,
    }
    return hashlib.sha256(
        b"PCHSI_V1232_FRESH_ROLLOUT_ACTIVATION_V1\0"
        + canonical_bytes(payload)
    ).hexdigest()


def build_sbatch_argv(
    *,
    slurm_plan: Mapping[str, object],
    script_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    activation_id: str,
) -> list[str]:
    if slurm_plan.get("schema_id") != (
        "ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_SLURM_RESOURCE_PLAN_V1"
    ):
        raise ValueError("SLURM_PLAN_SCHEMA")
    resources = slurm_plan.get("submission_resource_argv")
    if (
        not isinstance(resources, list)
        or not resources
        or not all(isinstance(x, str) and x for x in resources)
    ):
        raise ValueError("SLURM_RESOURCE_ARGV")
    if slurm_plan.get("submission_command") != "sbatch":
        raise ValueError("SLURM_SUBMISSION_COMMAND")
    if slurm_plan.get("human_selection_required") is not False:
        raise ValueError("SLURM_HUMAN_SELECTION_FORBIDDEN")

    short = activation_id[:24]
    job_name = "pchsi-v1232-" + short
    comment = "pchsi-v1232:" + short

    return [
        "sbatch",
        "--parsable",
        "--hold",
        "--no-requeue",
        "--job-name",
        job_name,
        "--comment",
        comment,
        "--output",
        str(stdout_path),
        "--error",
        str(stderr_path),
        *resources,
        str(script_path),
    ]


def parse_sbatch_parsable(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise ValueError("SBATCH_JOB_ID_EMPTY")
    job = raw.split(";", 1)[0]
    if not job.isdigit():
        raise ValueError("SBATCH_JOB_ID_INVALID:" + raw)
    return job

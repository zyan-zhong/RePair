from __future__ import annotations
from collections.abc import Mapping
from pathlib import Path
import hashlib,json

def _canon(value:object)->bytes:
    return (json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()

def activation_id(
    *,capsule_sha256:str,sharding_authority_sha256:str,
    execution_binding_sha256:str,slurm_plan_sha256:str,
)->str:
    return hashlib.sha256(
      b"PCHSI_V1232K_CONTROL_PLANE_CLASSIFICATION_REPAIR_FRESH_ATTEMPT_ROLLOUT_V1\0"+
      _canon({
        "capsule_sha256":capsule_sha256,
        "sharding_authority_sha256":sharding_authority_sha256,
        "execution_binding_sha256":execution_binding_sha256,
        "slurm_plan_sha256":slurm_plan_sha256,
      })
    ).hexdigest()

def build_array_sbatch_argv(
    *,slurm_plan:Mapping[str,object], shard_count:int,
    max_concurrent_shards:int, walltime_minutes:int,
    script_path:Path, stdout_path:Path, stderr_path:Path,
    activation:str,
)->list[str]:
    if slurm_plan.get("schema_id")!="ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_SLURM_RESOURCE_PLAN_V1":
        raise ValueError("SLURM_PLAN_SCHEMA")
    resources=slurm_plan.get("submission_resource_argv")
    if not isinstance(resources,list) or not all(isinstance(x,str) and x for x in resources):
        raise ValueError("SLURM_RESOURCE_ARGV")
    for token in resources:
        for prefix in ("--cpus-per-task","--cpus-per-gpu","--mem","--mem-per-cpu","--mem-per-gpu"):
            if token==prefix or token.startswith(prefix+"="):
                raise ValueError("CPU_MEMORY_OVERRIDE_FORBIDDEN:"+token)
    if shard_count<=0 or max_concurrent_shards<=0 or max_concurrent_shards>shard_count:
        raise ValueError("SHARD_CONCURRENCY")
    if walltime_minutes<=0: raise ValueError("WALLTIME")
    short=activation[:24]
    return [
      "sbatch","--parsable","--hold","--no-requeue",
      "--array",f"0-{shard_count-1}%{max_concurrent_shards}",
      "--time",str(walltime_minutes),
      "--job-name","pchsi-v1232k-"+short,
      "--comment","pchsi-v1232k:"+short,
      "--output",str(stdout_path),
      "--error",str(stderr_path),
      *resources,str(script_path),
    ]

def parse_job_id(raw:str)->str:
    job=raw.strip().split(";",1)[0]
    if not job.isdigit(): raise ValueError("SBATCH_JOB_ID_INVALID:"+raw.strip())
    return job

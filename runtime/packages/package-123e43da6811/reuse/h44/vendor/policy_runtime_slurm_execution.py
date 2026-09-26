from __future__ import annotations
import hashlib, json, os, re
from pathlib import Path
from typing import Mapping


def _canon(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _sha64(value: object, name: str) -> str:
    if not isinstance(value,str) or len(value)!=64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(name+" must be lowercase SHA-256")
    return value


def load_cluster_policy(path: str | Path) -> dict[str, object]:
    p=Path(path)
    value=json.loads(p.read_text("utf-8"))
    if not isinstance(value,dict): raise ValueError("cluster policy must be object")
    if value.get("schema_id")!="POLICY_RUNTIME_SLURM_CLUSTER_EXECUTION_POLICY_V1" or value.get("schema_version")!=1:
        raise ValueError("cluster policy schema mismatch")
    if value.get("status")!="FROZEN_SITE_EXECUTION_POLICY": raise ValueError("cluster policy status mismatch")
    if value.get("gpu_count_rule")!="TENSOR_PARALLEL_SIZE": raise ValueError("unsupported GPU count authority")
    if value.get("same_allocation_service_and_f0f1_required") is not True: raise ValueError("service/F0F1 co-location required")
    if value.get("compile_node_gpu_execution_forbidden") is not True: raise ValueError("compile-node GPU execution must be forbidden")
    if value.get("execution_infrastructure_only") is not True: raise ValueError("cluster policy must be infrastructure-only")
    partition=value.get("inference_partition_default")
    if not isinstance(partition,str) or not re.fullmatch(r"[A-Za-z0-9_.-]+",partition): raise ValueError("cluster partition invalid")
    for name in ("nodes","ntasks"):
        if type(value.get(name)) is not int or value[name] <= 0: raise ValueError(name+" invalid")
    if value.get("submission_command")!="sbatch": raise ValueError("unsupported Slurm submission command")
    _sha64(value.get("canonical_ledger_source_sha256"),"canonical ledger source SHA")
    expected=hashlib.sha256(b"POLICY_RUNTIME_SLURM_CLUSTER_EXECUTION_POLICY_V1\0"+_canon({k:v for k,v in value.items() if k!="cluster_policy_sha256"})).hexdigest()
    if value.get("cluster_policy_sha256")!=expected: raise ValueError("cluster policy hash mismatch")
    return dict(value)


def validate_launch_contract(value: Mapping[str,object]) -> dict[str,object]:
    if value.get("schema_id") != "POLICY_RUNTIME_SERVICE_LAUNCH_CONTRACT_V1" or value.get("schema_version") != 1:
        raise ValueError("launch contract schema mismatch")
    if value.get("status") != "MATERIALIZED_CURRENT_RUNTIME_SERVICE_LAUNCH_CONTRACT":
        raise ValueError("launch contract status mismatch")
    if value.get("historical_endpoint_or_alias_reused") is not False or value.get("operator_launch_knobs_synthesized") is not False:
        raise ValueError("launch contract authority boundary violated")
    command=value.get("launch_command")
    if not isinstance(command,list) or any(not isinstance(x,str) or not x for x in command):
        raise ValueError("launch command invalid")
    if value.get("launch_command_sha256") != hashlib.sha256(_canon(command)).hexdigest():
        raise ValueError("launch command hash mismatch")
    expected=hashlib.sha256(b"POLICY_RUNTIME_SERVICE_LAUNCH_CONTRACT_V1\0"+_canon({k:v for k,v in value.items() if k!="launch_contract_sha256"})).hexdigest()
    if value.get("launch_contract_sha256") != expected:
        raise ValueError("launch contract hash mismatch")
    return dict(value)


def build_slurm_execution_contract(*, launch_contract: Mapping[str,object], engine_profile: Mapping[str,object], cluster_policy: Mapping[str,object], source_integration_root: str, retry_integration_root: str, repo: str, python_executable: str, package_root: str, launch_contract_path: str, execution_root: str, service_ready_timeout_seconds: float, branch_operational_timeout_seconds: int, termination_grace_seconds: int) -> dict[str,object]:
    validate_launch_contract(launch_contract)
    if cluster_policy.get("gpu_count_rule")!="TENSOR_PARALLEL_SIZE": raise ValueError("unsupported GPU count authority")
    tp=engine_profile.get("tensor_parallel_size")
    if type(tp) is not int or tp<=0: raise ValueError("tensor parallel size invalid")
    launch_engine=launch_contract.get("engine_profile_sha256")
    if launch_engine!=engine_profile.get("engine_profile_sha256"): raise ValueError("launch contract / engine profile mismatch")
    launch_tp=launch_contract.get("tensor_parallel_size")
    if launch_tp is not None and launch_tp != tp: raise ValueError("launch contract tensor parallel mismatch")
    for name,value in (("service_ready_timeout_seconds",service_ready_timeout_seconds),("branch_operational_timeout_seconds",branch_operational_timeout_seconds),("termination_grace_seconds",termination_grace_seconds)):
        if not isinstance(value,(int,float)) or value<=0: raise ValueError(name+" invalid")
    partition=cluster_policy.get("inference_partition_default")
    payload={
        "schema_id":"POLICY_RUNTIME_SLURM_F0F1_EXECUTION_CONTRACT_V1",
        "schema_version":1,
        "status":"MATERIALIZED_POLICY_RUNTIME_SLURM_F0F1_EXECUTION_CONTRACT",
        "launch_contract_sha256":launch_contract.get("launch_contract_sha256"),
        "engine_profile_sha256":engine_profile.get("engine_profile_sha256"),
        "cluster_policy_sha256":cluster_policy.get("cluster_policy_sha256"),
        "partition":partition,
        "nodes":cluster_policy.get("nodes"),
        "ntasks":cluster_policy.get("ntasks"),
        "gpus":tp,
        "tensor_parallel_size":tp,
        "gpu_count_authority":"ENGINE_PROFILE_TENSOR_PARALLEL_SIZE",
        "partition_authority":"FROZEN_SITE_EXECUTION_POLICY",
        "same_allocation_service_and_f0f1_required":True,
        "compile_node_gpu_execution_forbidden":True,
        "source_integration_root":str(Path(source_integration_root).resolve()),
        "retry_integration_root":str(Path(retry_integration_root).resolve()),
        "repo":str(Path(repo).resolve()),
        "python_executable":str(Path(python_executable).resolve()),
        "package_root":str(Path(package_root).resolve()),
        "launch_contract_path":str(Path(launch_contract_path).resolve()),
        "execution_root":str(Path(execution_root).resolve()),
        "service_ready_timeout_seconds":float(service_ready_timeout_seconds),
        "branch_operational_timeout_seconds":int(branch_operational_timeout_seconds),
        "termination_grace_seconds":int(termination_grace_seconds),
        "scientific_candidate_reselection_performed":False,
        "automatic_scientific_retry_authorized":False,
        "execution_contract_sha256":"0"*64,
    }
    for field in ("launch_contract_sha256","engine_profile_sha256","cluster_policy_sha256"):
        _sha64(payload[field],field)
    payload["execution_contract_sha256"]=hashlib.sha256(b"POLICY_RUNTIME_SLURM_F0F1_EXECUTION_CONTRACT_V1\0"+_canon({k:v for k,v in payload.items() if k!="execution_contract_sha256"})).hexdigest()
    return payload


def validate_execution_contract(value: Mapping[str,object]) -> dict[str,object]:
    if value.get("schema_id")!="POLICY_RUNTIME_SLURM_F0F1_EXECUTION_CONTRACT_V1" or value.get("schema_version")!=1:
        raise ValueError("execution contract schema mismatch")
    if value.get("status")!="MATERIALIZED_POLICY_RUNTIME_SLURM_F0F1_EXECUTION_CONTRACT": raise ValueError("execution contract status mismatch")
    if value.get("gpu_count_authority")!="ENGINE_PROFILE_TENSOR_PARALLEL_SIZE" or value.get("gpus")!=value.get("tensor_parallel_size"):
        raise ValueError("GPU count authority mismatch")
    expected=hashlib.sha256(b"POLICY_RUNTIME_SLURM_F0F1_EXECUTION_CONTRACT_V1\0"+_canon({k:v for k,v in value.items() if k!="execution_contract_sha256"})).hexdigest()
    if value.get("execution_contract_sha256")!=expected: raise ValueError("execution contract hash mismatch")
    return dict(value)


def render_batch_script(python_executable: str, package_root: str, execution_contract_path: str) -> str:
    for value in (python_executable,package_root,execution_contract_path):
        if not isinstance(value,str) or not value or "\n" in value or "\x00" in value: raise ValueError("batch path invalid")
    # Resource arguments are supplied by sbatch argv from the execution contract,
    # never embedded as static #SBATCH directives in this reusable template.
    return """#!/usr/bin/env bash\nPCHSI_PY=%s\nPCHSI_PKG=%s\nEXECUTION_CONTRACT=%s\n\"$PCHSI_PY\" -B \"$PCHSI_PKG/slurm_policy_runtime_f0f1_job.py\" --execution-contract \"$EXECUTION_CONTRACT\"\nJOB_RC=$?\nprintf 'POLICY_RUNTIME_SLURM_JOB_RC=%%s\\n' \"$JOB_RC\"\nexit \"$JOB_RC\"\n""" % (json.dumps(python_executable),json.dumps(package_root),json.dumps(execution_contract_path))


def build_sbatch_argv(contract: Mapping[str,object], batch_script: str, stdout_path: str, stderr_path: str) -> list[str]:
    validate_execution_contract(contract)
    job_name="pchsi-f0f1-"+str(contract["execution_contract_sha256"])[:12]
    return ["sbatch","--parsable","--partition",str(contract["partition"]),"--nodes",str(contract["nodes"]),"--ntasks",str(contract["ntasks"]),"--gpus",str(contract["gpus"]),"--job-name",job_name,"--output",stdout_path,"--error",stderr_path,batch_script]


def validate_slurm_environment(contract: Mapping[str,object], env: Mapping[str,str], *, cuda_device_count: int) -> dict[str,object]:
    job_id=env.get("SLURM_JOB_ID") or env.get("SLURM_JOBID")
    if not job_id: raise ValueError("SLURM job identity missing")
    if env.get("SLURM_JOB_PARTITION")!=contract.get("partition"): raise ValueError("Slurm partition differs from execution contract")
    if not env.get("SLURM_JOB_NODELIST"): raise ValueError("Slurm node list missing")
    expected=contract.get("gpus")
    if type(expected) is not int or expected<=0: raise ValueError("execution GPU count invalid")
    if type(cuda_device_count) is not int or cuda_device_count < expected: raise ValueError("CUDA visible device count below execution contract")
    return {
        "schema_id":"POLICY_RUNTIME_SLURM_ENVIRONMENT_ATTESTATION_V1",
        "schema_version":1,
        "validated":True,
        "execution_contract_sha256":contract.get("execution_contract_sha256"),
        "slurm_job_id":job_id,
        "slurm_job_partition":env.get("SLURM_JOB_PARTITION"),
        "slurm_job_nodelist":env.get("SLURM_JOB_NODELIST"),
        "slurm_gpus_on_node":env.get("SLURM_GPUS_ON_NODE"),
        "slurm_job_gpus":env.get("SLURM_JOB_GPUS"),
        "cuda_visible_devices":env.get("CUDA_VISIBLE_DEVICES"),
        "torch_cuda_device_count":cuda_device_count,
        "expected_gpu_count":expected,
        "tensor_parallel_size":contract.get("tensor_parallel_size"),
    }

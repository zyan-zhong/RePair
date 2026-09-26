"""Governed cognitive-role traces preserving external-model provenance."""

from __future__ import annotations
from collections.abc import Mapping
from pchsi.reference_loop.canonical import domain_hash
from .schema_contract import validate_payload_against_schema, verify_domain_hash


def build_cognitive_role_trace(
    task_access: Mapping[str,object],
    request: Mapping[str,object],
    adjudicated: Mapping[str,object],
    *,
    role: str,
    environment_outcome_sha256: str|None,
)->dict[str,object]:
    if task_access.get("teacher_call_permitted") is not True:
        raise ValueError("teacher_call_permitted=false")
    if role not in {"ANALYZER","TRAINING_RESEARCHER"}:
        raise ValueError("invalid role")
    if request.get("task_id") != task_access.get("task_id"):
        raise ValueError("request task_id does not match task-access record")
    if request.get("gamefile_sha256") != task_access.get("gamefile_sha256"):
        raise ValueError("request gamefile does not match task-access record")
    required_request=(
        "analysis_objective","round_id","policy_version","evidence_pack_sha256",
        "provider","model","model_version","prompt_sha256","request_id",
        "raw_request_sha256","raw_request_pointer","raw_response_sha256",
        "raw_response_pointer","prompt_template_id","output_schema_id",
        "output_schema_sha256","reasoning_config_sha256","parse_status",
        "input_tokens","output_tokens","latency_ms","cost_usd",
        "task_access_manifest_sha256",
    )
    missing=[x for x in required_request if x not in request]
    if missing:
        raise ValueError(f"request provenance missing fields: {missing}")
    out={
        "schema_id":"COGNITIVE_ROLE_TRACE_V1","schema_version":1,"role":role,
        "analysis_objective":request["analysis_objective"],
        "round_id":request["round_id"],"policy_version":request["policy_version"],
        "task_id":task_access["task_id"],
        "gamefile_sha256":task_access["gamefile_sha256"],
        "access_class":task_access["access_class"],
        "dataset_split":task_access["dataset_split"],
        "training_permitted":task_access["training_permitted"],
        "select_evaluation_permitted":task_access["select_evaluation_permitted"],
        "confirmatory_permitted":task_access["confirmatory_permitted"],
        "task_access_manifest_sha256":request["task_access_manifest_sha256"],
        "evidence_pack_sha256":request["evidence_pack_sha256"],
        "memory_pack_sha256":request.get("memory_pack_sha256"),
        "provider":request["provider"],"model":request["model"],
        "model_version":request["model_version"],
        "prompt_sha256":request["prompt_sha256"],
        "request_id":request["request_id"],
        "raw_request_sha256":request["raw_request_sha256"],
        "raw_request_pointer":request["raw_request_pointer"],
        "raw_response_sha256":request["raw_response_sha256"],
        "raw_response_pointer":request["raw_response_pointer"],
        "prompt_template_id":request["prompt_template_id"],
        "output_schema_id":request["output_schema_id"],
        "output_schema_sha256":request["output_schema_sha256"],
        "reasoning_config_sha256":request["reasoning_config_sha256"],
        "parse_status":request["parse_status"],
        "input_tokens":request["input_tokens"],"output_tokens":request["output_tokens"],
        "latency_ms":request["latency_ms"],"cost_usd":request["cost_usd"],
        "adjudicated_output_sha256":adjudicated["adjudicated_output_sha256"],
        "human_disposition":adjudicated["human_disposition"],
        "crosscheck_sha256":adjudicated.get("crosscheck_sha256"),
        "environment_outcome_sha256":environment_outcome_sha256,
        "trace_sha256":"0"*64,
    }
    out["trace_sha256"]=domain_hash(
        "COGNITIVE_ROLE_TRACE_V1",out,excluded_field="trace_sha256"
    )
    validate_payload_against_schema(
        schema_id="COGNITIVE_ROLE_TRACE_V1",payload=out
    )
    return out


def validate_cognitive_role_trace(trace: Mapping[str,object]) -> None:
    validate_payload_against_schema(
        schema_id="COGNITIVE_ROLE_TRACE_V1",payload=trace
    )
    verify_domain_hash(
        payload=trace,domain="COGNITIVE_ROLE_TRACE_V1",
        hash_field="trace_sha256",
    )

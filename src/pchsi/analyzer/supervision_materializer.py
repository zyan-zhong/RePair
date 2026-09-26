"""Leakage-aware Analyzer/Researcher supervision materialization."""

from __future__ import annotations
from collections.abc import Iterable,Mapping
from pchsi.reference_loop.canonical import domain_hash
from .role_trace import validate_cognitive_role_trace


def materialize_local_analyzer_supervision(
    traces: Iterable[Mapping[str,object]],
)->dict[str,object]:
    rows=[]
    seen=set()
    for trace in traces:
        validate_cognitive_role_trace(trace)
        if trace["role"]!="ANALYZER":
            continue
        key=(trace["task_id"],trace["gamefile_sha256"])
        if key in seen:
            raise ValueError("duplicate Analyzer supervision task/gamefile trace")
        seen.add(key)
        eligible=bool(trace["training_permitted"])
        reason=None if eligible else f"ACCESS_CLASS:{trace['access_class']}"
        rows.append({
            "trace_sha256":trace["trace_sha256"],
            "input_evidence_pack_sha256":trace["evidence_pack_sha256"],
            "target_adjudicated_output_sha256":trace["adjudicated_output_sha256"],
            "environment_outcome_sha256":trace["environment_outcome_sha256"],
            "training_eligible":eligible,
            "training_exclusion_reason":reason,
            "dataset_split":trace["dataset_split"],
            "task_id":trace["task_id"],
            "gamefile_sha256":trace["gamefile_sha256"],
        })
    out={
        "schema_id":"LOCAL_ANALYZER_SUPERVISION_DATASET_V1",
        "rows":rows,"dataset_sha256":"0"*64,
    }
    out["dataset_sha256"]=domain_hash(
        "LOCAL_ANALYZER_SUPERVISION_DATASET_V1",out,
        excluded_field="dataset_sha256",
    )
    return out


def materialize_local_researcher_supervision(
    traces: Iterable[Mapping[str,object]],
    pre_records: Mapping[str,object],
    post_records: Mapping[str,object],
    template_sha256: str,
)->dict[str,object]:
    if len(template_sha256)!=64:
        raise ValueError("Researcher supervision requires template SHA")
    rows=[]
    for trace in traces:
        validate_cognitive_role_trace(trace)
        if trace["role"]!="TRAINING_RESEARCHER":
            continue
        tid=trace["trace_sha256"]
        if tid not in pre_records or tid not in post_records:
            raise ValueError("Researcher supervision missing frozen pre/post record")
        rows.append({
            "trace_sha256":tid,
            "pre_record_sha256":pre_records[tid],
            "post_record_sha256":post_records[tid],
            "template_sha256":template_sha256,
            "training_eligible":bool(trace["training_permitted"]),
            "dataset_split":trace["dataset_split"],
        })
    out={
        "schema_id":"LOCAL_RESEARCHER_SUPERVISION_DATASET_V1",
        "rows":rows,"dataset_sha256":"0"*64,
    }
    out["dataset_sha256"]=domain_hash(
        "LOCAL_RESEARCHER_SUPERVISION_DATASET_V1",out,
        excluded_field="dataset_sha256",
    )
    return out

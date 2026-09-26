"""Post-Benefit D0-D4 decomposition with complete-condition semantics."""

from __future__ import annotations
from pchsi.reference_loop.canonical import domain_hash
from .schema_contract import validate_payload_against_schema

TASK14_LIVE_EXECUTION_ROLE="POST_BENEFIT_SECONDARY"
CONDITIONS=("D0_BASELINE","D1_FULL_REPAIR","D2_PREFIX","D3_MATCHED_PERTURBATION",
            "D4_HISTORY_ATTENUATED")
DEFINITIVE_NON_BENEFIT={"Harm","Neutral","Failure","NoBenefit"}


def register_decomposition(candidate_sha256):
    out={
        "schema_id":"REPAIR_EFFECT_DECOMPOSITION_TRACE_V1","schema_version":1,
        "registered_candidate_sha256":candidate_sha256,
        "execution_role":TASK14_LIVE_EXECUTION_ROLE,
        "conditions":list(CONDITIONS),"trace_sha256":"0"*64,
    }
    out["trace_sha256"]=domain_hash(
        "REPAIR_EFFECT_DECOMPOSITION_TRACE_V1",out,
        excluded_field="trace_sha256",
    )
    validate_payload_against_schema(
        schema_id="REPAIR_EFFECT_DECOMPOSITION_TRACE_V1",payload=out
    )
    return out


def interpret_decomposition(trace,labels):
    for required in ("D0","D1","D3","D4","prefix_results"):
        if required not in labels:
            raise ValueError(f"decomposition missing {required}")
    if labels["D1"]!="Benefit":
        raise ValueError("decomposition requires formal Benefit")
    if labels["D0"] not in DEFINITIVE_NON_BENEFIT:
        raise ValueError("D0 baseline must be definitively non-Benefit")
    prefix=list(labels["prefix_results"])
    if any(set(x)!={"prefix_length","effect_label"} for x in prefix):
        raise ValueError("prefix result schema invalid")
    lengths=[x["prefix_length"] for x in prefix]
    if lengths != list(range(1,len(lengths)+1)):
        raise ValueError("prefix results must cover contiguous tested prefixes")
    if any(x["effect_label"]=="Uncertain" for x in prefix) or labels["D3"]=="Uncertain" or labels["D4"]=="Uncertain":
        mechanism="UNRESOLVED_MULTI_CHANNEL_EFFECT"
    elif labels["D3"]=="Benefit":
        mechanism="NONSPECIFIC_PERTURBATION_EFFECT"
    elif labels["D4"] in DEFINITIVE_NON_BENEFIT:
        mechanism="HISTORY_CONTEXT_DEPENDENT"
    else:
        benefit_prefix=[x["prefix_length"] for x in prefix if x["effect_label"]=="Benefit"]
        if benefit_prefix:
            shortest=min(benefit_prefix)
            if any(
                x["prefix_length"]<shortest and x["effect_label"] not in DEFINITIVE_NON_BENEFIT
                for x in prefix
            ):
                mechanism="UNRESOLVED_MULTI_CHANNEL_EFFECT"
            elif shortest==1:
                mechanism="SPECIFIC_SINGLE_ACTION_EFFECT"
            else:
                mechanism="SHORTEST_TESTED_SUFFICIENT_PREFIX"
        else:
            mechanism="COMPOSITIONAL_OPTION_EFFECT"
    out={
        "schema_id":"REPAIR_EFFECT_DECOMPOSITION_RESULT_V1","schema_version":1,
        "trace_sha256":trace["trace_sha256"],"mechanism_label":mechanism,
        "formal_benefit_unchanged":True,"result_sha256":"0"*64,
    }
    out["result_sha256"]=domain_hash(
        "REPAIR_EFFECT_DECOMPOSITION_RESULT_V1",out,
        excluded_field="result_sha256",
    )
    validate_payload_against_schema(
        schema_id="REPAIR_EFFECT_DECOMPOSITION_RESULT_V1",payload=out
    )
    return out

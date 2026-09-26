"""Validated C-stage attribution and deterministic C/P aggregation."""

from __future__ import annotations
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from pchsi.reference_loop.canonical import domain_hash, strict_json_loads
from .schema_contract import validate_payload_against_schema, verify_domain_hash


def load_taxonomy(path: Path|None=None)->tuple[str,...]:
    p=path or Path(__file__).resolve().parents[3]/"configs/analyzer/analyzer_capability_taxonomy_v1.json"
    value=strict_json_loads(p.read_bytes())
    return tuple(value["components"])


def _validate_group_result(value:Mapping[str,object])->None:
    schema_id=value.get("schema_id")
    if schema_id not in {"ANALYZER_GROUP_RESULT_V1","ANALYZER_GROUP_RESULT_V2"}:
        raise ValueError("unsupported group result schema")
    validate_payload_against_schema(schema_id=str(schema_id),payload=value)
    verify_domain_hash(
        payload=value,domain=str(schema_id),hash_field="group_result_sha256"
    )


def _component_evidence_universe(
    group_result:Mapping[str,object],
)->set[str]:
    # Explicit C-stage evidence authorities only. Preserve the historical
    # coarse refs and add the mechanism-level evidence refs already
    # registered inside ANALYZER_GROUP_RESULT_V1/V2.
    known={
        str(group_result["group_manifest_sha256"]),
        str(group_result["group_result_sha256"]),
    }
    for value in group_result.get("source_conditioned_repair_sha256s",[]):
        if isinstance(value,str):
            known.add(value)
    mechanisms=group_result.get("mechanism_hypotheses",[])
    if isinstance(mechanisms,list):
        for item in mechanisms:
            if not isinstance(item,Mapping):
                continue
            refs=item.get("evidence_sha256s",[])
            if isinstance(refs,list):
                for ref in refs:
                    if isinstance(ref,str):
                        known.add(ref)
    return known


def finalize_component_attribution(
    value: Mapping[str,object],
    *,
    group_result: Mapping[str,object],
    taxonomy=None,
)->dict[str,object]:
    _validate_group_result(group_result)
    out=dict(value)
    if out["group_result_sha256"] != group_result["group_result_sha256"]:
        raise ValueError("component attribution group-result binding mismatch")
    allowed=set(taxonomy or load_taxonomy())
    if out["principal_component"] not in allowed:
        raise ValueError("unknown principal component")
    secondary=list(out["secondary_components"])
    if len(secondary)!=len(set(secondary)) or set(secondary)-allowed:
        raise ValueError("invalid secondary components")
    if out["principal_component"] in secondary:
        raise ValueError("principal repeated as secondary")
    evidence=set(out["evidence_sha256s"])
    known=_component_evidence_universe(group_result)
    if not evidence or not evidence <= known:
        raise ValueError("component attribution evidence is not bound to group result")
    out["attribution_sha256"]="0"*64
    out["attribution_sha256"]=domain_hash(
        "ANALYZER_COMPONENT_ATTRIBUTION_V1",out,excluded_field="attribution_sha256"
    )
    validate_payload_against_schema(
        schema_id="ANALYZER_COMPONENT_ATTRIBUTION_V1",payload=out
    )
    return out


def aggregate_capability_profile(
    attributions: Iterable[Mapping[str,object]],
    *,
    registered_group_results: Mapping[str,Mapping[str,object]],
)->dict[str,object]:
    universe=list(registered_group_results)
    if len(universe)!=len(set(universe)):
        raise ValueError("duplicate registered group")
    rows=list(attributions)
    seen=set(); principal=Counter(); secondary=Counter(); groups={}
    for attribution in rows:
        validate_payload_against_schema(
            schema_id="ANALYZER_COMPONENT_ATTRIBUTION_V1",payload=attribution
        )
        verify_domain_hash(
            payload=attribution,domain="ANALYZER_COMPONENT_ATTRIBUTION_V1",
            hash_field="attribution_sha256",
        )
        group=attribution["group_result_sha256"]
        if group in seen: raise ValueError("duplicate component attribution for group")
        seen.add(group)
        if group not in registered_group_results:
            raise ValueError("attribution outside registered universe")
        principal[attribution["principal_component"]]+=1
        groups.setdefault(attribution["principal_component"],[]).append(group)
        for comp in attribution["secondary_components"]: secondary[comp]+=1
    components=sorted(set(principal)|set(secondary))
    payload={
        "schema_id":"ANALYZER_CAPABILITY_PROFILE_V1","schema_version":1,
        "registered_group_count":len(universe),
        "attributed_group_count":len(seen),
        "zero_claim_group_count":len(universe)-len(seen),
        "component_rows":[{
            "component_id":c,"principal_count":principal[c],
            "secondary_count":secondary[c],
            "group_sha256s":sorted(groups.get(c,[])),
        } for c in components],
        "profile_sha256":"0"*64,
    }
    payload["profile_sha256"]=domain_hash(
        "ANALYZER_CAPABILITY_PROFILE_V1",payload,excluded_field="profile_sha256"
    )
    validate_payload_against_schema(
        schema_id="ANALYZER_CAPABILITY_PROFILE_V1",payload=payload
    )
    return payload


def build_policy_behavior_profile(profile: Mapping[str,object])->dict[str,object]:
    validate_payload_against_schema(
        schema_id="ANALYZER_CAPABILITY_PROFILE_V1",payload=profile
    )
    verify_domain_hash(
        payload=profile,domain="ANALYZER_CAPABILITY_PROFILE_V1",
        hash_field="profile_sha256",
    )
    candidates=[
        x["component_id"] for x in profile["component_rows"]
        if x["principal_count"]>0
    ]
    out={
        "schema_id":"ANALYZER_POLICY_BEHAVIOR_PROFILE_V1","schema_version":1,
        "capability_profile_sha256":profile["profile_sha256"],
        "candidate_bottleneck_components":candidates,
        "principal_bottleneck_selected":False,
        "training_method_selected":False,
        "policy_profile_sha256":"0"*64,
    }
    out["policy_profile_sha256"]=domain_hash(
        "ANALYZER_POLICY_BEHAVIOR_PROFILE_V1",out,
        excluded_field="policy_profile_sha256",
    )
    validate_payload_against_schema(
        schema_id="ANALYZER_POLICY_BEHAVIOR_PROFILE_V1",payload=out
    )
    return out

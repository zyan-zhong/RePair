"""Deterministic error-instance grouping and grouped-synthesis bindings."""

from __future__ import annotations
from collections.abc import Iterable, Mapping
from pchsi.reference_loop.canonical import domain_hash
from .schema_contract import validate_payload_against_schema


def _hash(domain: str, payload: Mapping[str, object], field: str) -> str:
    return domain_hash(domain,payload,excluded_field=field)


def build_group_manifests(local_results, mechanical_signatures):
    groups={}
    seen=set()
    for result in local_results:
        local_sha=str(result["local_result_sha256"])
        for error in result.get("error_instances",[]):
            eid=str(error["error_instance_id"])
            key=(local_sha,eid)
            if key in seen:
                raise ValueError("duplicate error membership")
            seen.add(key)
            sig=mechanical_signatures.get(key)
            if not isinstance(sig,Mapping):
                raise ValueError("missing mechanical grouping signature")
            primary={
                "task_family":sig.get("task_family"),
                "mechanical_signature_sha256":sig["mechanical_signature_sha256"],
                "progress_signature_sha256":sig["progress_signature_sha256"],
                "lifecycle_signature":error["resolution_status"],
                "terminal_footprint_class":error["terminal_footprint"],
            }
            gid=domain_hash("ANALYZER_ERROR_GROUP_V1",primary)
            membership={
                "schema_id":"ANALYZER_ERROR_INSTANCE_MEMBERSHIP_V1",
                "schema_version":1,
                "local_result_sha256":local_sha,
                "error_instance_id":eid,
                "task_id":result["task_id"],
                "gamefile_sha256":result["gamefile_sha256"],
                "task_family":sig.get("task_family"),
                "group_id":gid,
                "primary_group_key_sha256":gid,
                "inference_cluster_unit":"TASK_GAMEFILE",
                "membership_sha256":"0"*64,
            }
            membership["membership_sha256"]=_hash(
                "ANALYZER_ERROR_INSTANCE_MEMBERSHIP_V1",
                membership,"membership_sha256",
            )
            validate_payload_against_schema(
                schema_id="ANALYZER_ERROR_INSTANCE_MEMBERSHIP_V1",
                payload=membership,
            )
            row=groups.setdefault(gid,{
                "schema_id":"ANALYZER_GROUP_MANIFEST_V1","schema_version":1,
                "group_id":gid,**primary,"memberships":[],
            })
            row["memberships"].append(membership)
    out=[]
    for gid,row in sorted(groups.items()):
        members=sorted(row.pop("memberships"),key=lambda x:x["membership_sha256"])
        manifest={
            **row,
            "membership_sha256s":[x["membership_sha256"] for x in members],
            "source_local_result_sha256s":sorted({x["local_result_sha256"] for x in members}),
            "inference_cluster_unit":"TASK_GAMEFILE",
            "membership_records":members,
            "group_manifest_sha256":"0"*64,
        }
        manifest["group_manifest_sha256"]=_hash(
            "ANALYZER_GROUP_MANIFEST_V1",manifest,"group_manifest_sha256"
        )
        validate_payload_against_schema(
            schema_id="ANALYZER_GROUP_MANIFEST_V1",payload=manifest
        )
        out.append(manifest)
    return out


def build_group_synthesis_inputs(
    group_manifests: Iterable[Mapping[str,object]],
    *,
    source_bindings: Mapping[tuple[str,str],Mapping[str,object]],
) -> list[dict[str,object]]:
    """Bind each group member to exact source-state/menu identity before G-stage calls."""

    outputs=[]
    for manifest in group_manifests:
        validate_payload_against_schema(
            schema_id="ANALYZER_GROUP_MANIFEST_V1",payload=manifest
        )
        members=[]
        for membership in manifest["membership_records"]:
            key=(membership["local_result_sha256"],membership["error_instance_id"])
            binding=source_bindings.get(key)
            if not isinstance(binding,Mapping):
                raise ValueError("missing source-state/menu binding for group member")
            if binding.get("local_result_sha256") != key[0] or binding.get("error_instance_id") != key[1]:
                raise ValueError("source binding identity mismatch")
            call_index=binding.get("source_call_index")
            if type(call_index) is not int or call_index < 0:
                raise ValueError("source call index is invalid")
            members.append({
                "local_result_sha256":key[0],
                "error_instance_id":key[1],
                "source_state_sha256":binding["source_state_sha256"],
                "menu_sha256":binding["menu_sha256"],
                "source_call_index":call_index,
                "proposal_slot_limit":1,
            })
        payload={
            "schema_id":"ANALYZER_GROUP_SYNTHESIS_INPUT_V1",
            "schema_version":1,
            "group_manifest_sha256":manifest["group_manifest_sha256"],
            "member_rows":members,
            "base_memory_exposed":False,
            "group_synthesis_input_sha256":"0"*64,
        }
        payload["group_synthesis_input_sha256"]=_hash(
            "ANALYZER_GROUP_SYNTHESIS_INPUT_V1",
            payload,"group_synthesis_input_sha256",
        )
        validate_payload_against_schema(
            schema_id="ANALYZER_GROUP_SYNTHESIS_INPUT_V1",payload=payload
        )
        outputs.append(payload)
    return outputs


def finalize_source_conditioned_proposal(value: Mapping[str,object]) -> dict[str,object]:
    out=dict(value)
    exact=out.get("exact_action")
    option=out.get("option_actions")
    termination=out.get("termination_condition")
    if exact is not None:
        if not isinstance(exact,str) or not exact or option or termination is not None:
            raise ValueError("invalid exact-action source proposal")
    else:
        if not isinstance(option,list) or not 1 <= len(option) <= 4:
            raise ValueError("invalid short-option source proposal")
        if not isinstance(termination,str) or not termination:
            raise ValueError("short option requires termination condition")
    out["source_proposal_sha256"]="0"*64
    out["source_proposal_sha256"]=_hash(
        "ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1",
        out,"source_proposal_sha256",
    )
    validate_payload_against_schema(
        schema_id="ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1",payload=out
    )
    return out

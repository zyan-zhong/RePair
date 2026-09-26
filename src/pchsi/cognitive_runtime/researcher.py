from __future__ import annotations
from collections.abc import Mapping
from pchsi.reference_loop.canonical import domain_hash
from .schema_registry import validate_artifact


def finalize_human_pre(value: Mapping[str,object]) -> dict[str,object]:
    out={"schema_id":"HUMAN_RESEARCHER_PRE_V1","schema_version":1,**dict(value),
         "pre_record_sha256":"0"*64}
    selected=[x for x in out["candidate_bottlenecks"] if x["status"]=="SELECTED"]
    if len(selected)!=1 or selected[0]["candidate_id"]!=out["selected_bottleneck_id"]:
        raise ValueError("Human PRE must select exactly one bottleneck")
    out["pre_record_sha256"]=domain_hash("HUMAN_RESEARCHER_PRE_V1",out,
                                            excluded_field="pre_record_sha256")
    validate_artifact("HUMAN_RESEARCHER_PRE_V1",out); return out


def finalize_api_pre_shadow(value: Mapping[str,object]) -> dict[str,object]:
    out={"schema_id":"API_RESEARCHER_PRE_SHADOW_V1","schema_version":1,**dict(value),
         "shadow_record_sha256":"0"*64}
    out["shadow_record_sha256"]=domain_hash("API_RESEARCHER_PRE_SHADOW_V1",out,
                                               excluded_field="shadow_record_sha256")
    validate_artifact("API_RESEARCHER_PRE_SHADOW_V1",out); return out


def finalize_field_adjudication(value: Mapping[str,object]) -> dict[str,object]:
    out={"schema_id":"RESEARCHER_FIELD_ADJUDICATION_V1","schema_version":1,
         **dict(value),"adjudication_sha256":"0"*64}
    out["adjudication_sha256"]=domain_hash("RESEARCHER_FIELD_ADJUDICATION_V1",out,
                                              excluded_field="adjudication_sha256")
    validate_artifact("RESEARCHER_FIELD_ADJUDICATION_V1",out); return out


def finalize_api_post_shadow(value: Mapping[str,object]) -> dict[str,object]:
    out={"schema_id":"API_RESEARCHER_POST_SHADOW_V1","schema_version":1,**dict(value),
         "shadow_record_sha256":"0"*64}
    out["shadow_record_sha256"]=domain_hash("API_RESEARCHER_POST_SHADOW_V1",out,
                                               excluded_field="shadow_record_sha256")
    validate_artifact("API_RESEARCHER_POST_SHADOW_V1",out); return out

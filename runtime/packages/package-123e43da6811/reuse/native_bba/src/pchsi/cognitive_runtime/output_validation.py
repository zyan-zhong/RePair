from __future__ import annotations
from collections.abc import Mapping
from pchsi.reference_loop.canonical import domain_hash,strict_json_loads
from pchsi.analyzer.schema_contract import validate_payload_against_schema
from .researcher import finalize_api_pre_shadow,finalize_api_post_shadow
from .researcher_hydrated import finalize_strong_researcher_pre_shadow_v2
from .researcher_primary import finalize_strong_researcher_pre_primary_v1,finalize_api_post_primary_v1


def _object(text:str)->dict[str,object]:
 value=strict_json_loads(text)
 if not isinstance(value,dict): raise ValueError("model output must be one JSON object")
 return value


def _finalize_group_v2(
    value:dict[str,object],
    *,
    projection:Mapping[str,object],
)->dict[str,object]:
 from pchsi.cognitive_runtime.projections import (
  canonical_group_current_evidence_sha256s,
 )

 if value.get("group_manifest_sha256")!=projection.get("group_manifest_sha256"):
  raise ValueError("group result binding mismatch")

 group_id=projection.get("group_id")
 if not isinstance(group_id,str) or len(group_id)!=64:
  raise ValueError("G V3 projection missing deterministic group_id")

 canonical_current=canonical_group_current_evidence_sha256s(projection)
 if projection.get("current_evidence_sha256s")!=canonical_current:
  raise ValueError("G V3 current evidence universe mismatch")

 allowed=set(canonical_current)
 memory_sha=projection.get("memory_pack_sha256")
 if memory_sha is not None:
  if not isinstance(memory_sha,str) or len(memory_sha)!=64:
   raise ValueError("G V3 Memory identity invalid")
  allowed.add(memory_sha)

 hypotheses=value.get("mechanism_hypotheses")
 if not isinstance(hypotheses,list):
  raise ValueError("mechanism_hypotheses must be array")
 for hypothesis in hypotheses:
  if not isinstance(hypothesis,Mapping):
   raise ValueError("mechanism hypothesis must be object")
  refs=hypothesis.get("evidence_sha256s")
  if not isinstance(refs,list) or any(
   not isinstance(ref,str) or len(ref)!=64 for ref in refs
  ):
   raise ValueError("mechanism evidence refs invalid")
  if not set(refs)<=allowed:
   raise ValueError("mechanism evidence outside registered G evidence universe")
 contexts_raw=projection.get("source_contexts")
 if not isinstance(contexts_raw,list):
  raise ValueError("G V2 projection missing source contexts")
 contexts={}
 for row in contexts_raw:
  if not isinstance(row,Mapping):
   raise ValueError("source context row invalid")
  key=(row.get("local_result_sha256"),row.get("error_instance_id"))
  if key in contexts:
   raise ValueError("duplicate source context")
  contexts[key]=row
 proposals=value.get("source_conditioned_proposals")
 if not isinstance(proposals,list):
  raise ValueError("source_conditioned_proposals must be array")
 seen=set(); hashes=[]
 finalized=[]
 for raw in proposals:
  if not isinstance(raw,Mapping):
   raise ValueError("proposal must be object")
  p=dict(raw)
  support_refs=p.get("supporting_evidence_sha256s")
  if not isinstance(support_refs,list) or any(
   not isinstance(ref,str) or len(ref)!=64 for ref in support_refs
  ):
   raise ValueError("proposal supporting evidence refs invalid")
  if not set(support_refs)<=allowed:
   raise ValueError("proposal supporting evidence outside registered G evidence universe")
  key=(p.get("local_result_sha256"),p.get("error_instance_id"))
  if key not in contexts:
   raise ValueError("proposal outside registered group members")
  if key in seen:
   raise ValueError("more than one proposal for one group member")
  seen.add(key)
  context=contexts[key]
  for field in ("source_state_sha256","menu_sha256"):
   if p.get(field)!=context.get(field):
    raise ValueError(f"proposal source binding mismatch: {field}")
  if p.get("group_manifest_sha256")!=projection.get("group_manifest_sha256"):
   raise ValueError("proposal group-manifest binding mismatch")
  menu=context.get("admissible_commands")
  if not isinstance(menu,list) or not menu or any(not isinstance(x,str) for x in menu):
   raise ValueError("source context menu invalid")
  exact=p.get("exact_action"); options=p.get("option_actions"); term=p.get("termination_condition")
  if exact is not None:
   if not isinstance(exact,str) or exact not in menu:
    raise ValueError("proposal exact_action is not exact source-menu member")
   if options!=[] or term is not None:
    raise ValueError("exact proposal incompatible fields")
  else:
   if not isinstance(options,list) or not 1<=len(options)<=4:
    raise ValueError("short-option proposal requires 1-4 actions")
   if options[0] not in menu:
    raise ValueError("short-option first action is not exact source-menu member")
   if not isinstance(term,str) or not term:
    raise ValueError("short-option proposal requires termination condition")
  p["schema_id"]="ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1"
  p["schema_version"]=1
  p["source_proposal_sha256"]="0"*64
  p["source_proposal_sha256"]=domain_hash(
   "ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1",p,
   excluded_field="source_proposal_sha256",
  )
  validate_payload_against_schema(
   schema_id="ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1",payload=p
  )
  hashes.append(p["source_proposal_sha256"])
  finalized.append(p)
 out=dict(value)
 out["schema_id"]="ANALYZER_GROUP_RESULT_V2"; out["schema_version"]=2
 out["group_id"]=group_id
 out["source_conditioned_proposals"]=finalized
 out["source_conditioned_repair_sha256s"]=hashes
 out["group_result_sha256"]="0"*64
 out["group_result_sha256"]=domain_hash(
  "ANALYZER_GROUP_RESULT_V2",out,excluded_field="group_result_sha256"
 )
 validate_payload_against_schema(schema_id="ANALYZER_GROUP_RESULT_V2",payload=out)
 return out


def _finalize_crosscheck_v2(
    value:dict[str,object],
    *,
    projection:Mapping[str,object],
)->dict[str,object]:
 from pchsi.analyzer.crosscheck import finalize_crosscheck

 if value.get("target_artifact_sha256")!=projection.get("target_artifact_sha256"):
  raise ValueError("crosscheck target mismatch")

 stage=projection.get("target_stage_id")
 if stage not in {"G-A2","G-A3"}:
  raise ValueError("crosscheck target stage invalid")

 current=projection.get("current_evidence_manifest")
 historical=projection.get("historical_evidence_manifest")
 if not isinstance(current,Mapping):
  raise ValueError("crosscheck current evidence manifest missing")
 if not isinstance(historical,Mapping):
  raise ValueError("crosscheck historical evidence manifest missing")

 expected_current=domain_hash(
  "ANALYZER_X_CURRENT_EVIDENCE_MANIFEST_V1",
  current,
  excluded_field="current_evidence_manifest_sha256",
 )
 if current.get("current_evidence_manifest_sha256")!=expected_current:
  raise ValueError("crosscheck current evidence manifest hash mismatch")
 if projection.get("current_evidence_manifest_sha256")!=expected_current:
  raise ValueError("crosscheck current evidence projection hash mismatch")

 expected_historical=domain_hash(
  "ANALYZER_X_HISTORICAL_EVIDENCE_MANIFEST_V1",
  historical,
  excluded_field="historical_evidence_manifest_sha256",
 )
 if historical.get("historical_evidence_manifest_sha256")!=expected_historical:
  raise ValueError("crosscheck historical evidence manifest hash mismatch")
 if projection.get("historical_evidence_manifest_sha256")!=expected_historical:
  raise ValueError("crosscheck historical evidence projection hash mismatch")

 target=projection.get("target_artifact")
 if not isinstance(target,Mapping):
  raise ValueError("crosscheck target artifact missing")
 if target.get("group_manifest_sha256")!=current.get("group_manifest_sha256"):
  raise ValueError("crosscheck target/current group mismatch")

 memory_sha=projection.get("memory_pack_sha256")
 historical_memory=historical.get("memory_pack_sha256")

 if stage=="G-A2":
  if memory_sha is not None or "memory_pack" in projection:
   raise ValueError("crosscheck G-A2 must be Memory-blind")
  if historical_memory is not None:
   raise ValueError("crosscheck G-A2 historical manifest must be empty")

 if stage=="G-A3":
  if not isinstance(memory_sha,str) or len(memory_sha)!=64:
   raise ValueError("crosscheck G-A3 requires Memory identity")
  if historical_memory!=memory_sha:
   raise ValueError("crosscheck G-A3 historical Memory mismatch")
  memory=projection.get("memory_pack")
  if not isinstance(memory,Mapping):
   raise ValueError("crosscheck G-A3 requires Memory bytes")
  observed=next(
   (
    x for key,x in memory.items()
    if key in {"memory_pack_sha256","pack_sha256","snapshot_sha256"}
    and isinstance(x,str) and len(x)==64
   ),
   None,
  )
  if observed!=memory_sha:
   raise ValueError("crosscheck G-A3 Memory bytes identity mismatch")

 def sha_set(raw:object,label:str)->set[str]:
  if not isinstance(raw,list):
   raise ValueError(f"{label} must be array")
  values=[]
  for item in raw:
   if not isinstance(item,str) or len(item)!=64:
    raise ValueError(f"{label} contains invalid SHA")
   values.append(item)
  if len(values)!=len(set(values)):
   raise ValueError(f"{label} contains duplicate SHA")
  return set(values)

 allowed_current=sha_set(
  current.get("allowed_evidence_sha256s"),
  "current evidence allowlist",
 )
 allowed_historical=sha_set(
  historical.get("allowed_evidence_sha256s"),
  "historical evidence allowlist",
 )
 if stage=="G-A2" and allowed_historical:
  raise ValueError("crosscheck G-A2 historical allowlist must be empty")
 if stage=="G-A3" and allowed_historical!={memory_sha}:
  raise ValueError("crosscheck G-A3 historical allowlist mismatch")

 cited_current=sha_set(value.get("current_evidence_sha256s"),"current evidence refs")
 cited_historical=sha_set(
  value.get("historical_evidence_sha256s"),"historical evidence refs"
 )
 support=sha_set(value.get("supporting_evidence_sha256s"),"supporting refs")
 contradictions=sha_set(
  value.get("contradiction_evidence_sha256s"),"contradiction refs"
 )

 if not cited_current<=allowed_current:
  raise ValueError("crosscheck cites unregistered current evidence")
 if not cited_historical<=allowed_historical:
  raise ValueError("crosscheck cites unregistered historical evidence")

 union=allowed_current|allowed_historical
 if not support<=union:
  raise ValueError("crosscheck supporting evidence outside allowlists")
 if not contradictions<=union:
  raise ValueError("crosscheck contradiction evidence outside allowlists")

 if value.get("disposition")=="ACCEPT" and not cited_current:
  raise ValueError("crosscheck ACCEPT requires current evidence")

 return finalize_crosscheck(value)


_STAGE_OUTPUT_IDENTITY_V1: dict[str, tuple[str, int, str]] = {
    "L-A0": ("ANALYZER_LOCAL_RESULT_V2", 2, "local_result_sha256"),
    "L-A1": ("ANALYZER_LOCAL_RESULT_V2", 2, "local_result_sha256"),
    "G-A2": ("ANALYZER_GROUP_RESULT_V2", 2, "group_result_sha256"),
    "G-A3": ("ANALYZER_GROUP_RESULT_V2", 2, "group_result_sha256"),
    "C": ("ANALYZER_COMPONENT_ATTRIBUTION_V1", 1, "attribution_sha256"),
    "X": ("ANALYZER_CROSSCHECK_RESULT_V1", 1, "crosscheck_sha256"),
    "R-PRE-SHADOW": (
        "API_RESEARCHER_PRE_SHADOW_V1",
        1,
        "shadow_record_sha256",
    ),
    "R-POST-SHADOW": (
        "API_RESEARCHER_POST_SHADOW_V1",
        1,
        "shadow_record_sha256",
    ),
    "R-PRE-SHADOW-HYDRATED-V2": (
        "STRONG_RESEARCHER_PRE_SHADOW_V2",
        2,
        "shadow_record_sha256",
    ),
    "R-PRE-PRIMARY-V1": (
        "STRONG_RESEARCHER_PRE_PRIMARY_V1",
        1,
        "primary_record_sha256",
    ),
    "R-POST-PRIMARY-V1": (
        "API_RESEARCHER_POST_PRIMARY_V1",
        1,
        "primary_record_sha256",
    ),
}


def validated_artifact_identity(
    *,
    stage_id: str,
    artifact: Mapping[str, object],
) -> str:
    # Resolve the registered stage self-hash, never an arbitrary input SHA.
    spec = _STAGE_OUTPUT_IDENTITY_V1.get(stage_id)
    if spec is None:
        raise ValueError(f"unsupported validated artifact identity stage: {stage_id}")

    schema_id, schema_version, hash_field = spec
    if artifact.get("schema_id") != schema_id:
        raise ValueError("validated artifact identity schema mismatch")
    if artifact.get("schema_version") != schema_version:
        raise ValueError("validated artifact identity schema version mismatch")

    observed = artifact.get(hash_field)
    if not isinstance(observed, str) or len(observed) != 64:
        raise ValueError("validated artifact self-hash missing or invalid")

    expected = domain_hash(
        schema_id,
        artifact,
        excluded_field=hash_field,
    )
    if observed != expected:
        raise ValueError("validated artifact self-hash mismatch")
    return observed


def validate_stage_output(*,stage_id:str,text:str,raw_response_sha256:str,
                          projection:Mapping[str,object])->dict[str,object]:
 value=_object(text)
 if stage_id in {"L-A0","L-A1"}:
  from pchsi.analyzer.local_results import finalize_local_result,validate_local_result
  value["raw_response_sha256"]=raw_response_sha256
  value=finalize_local_result(value)
  return validate_local_result(value,evidence_pack=projection["evidence_pack"])
 if stage_id in {"G-A2","G-A3"}:
  return _finalize_group_v2(value,projection=projection)
 if stage_id=="C":
  from pchsi.analyzer.component_attribution import finalize_component_attribution
  return finalize_component_attribution(value,group_result=projection["group_result"])
 if stage_id=="X":
  return _finalize_crosscheck_v2(value,projection=projection)
 if stage_id=="R-PRE-SHADOW-HYDRATED-V2":
  return finalize_strong_researcher_pre_shadow_v2(
   value,projection=projection
  )
 if stage_id=="R-PRE-PRIMARY-V1":
  return finalize_strong_researcher_pre_primary_v1(
   value,projection=projection
  )
 if stage_id=="R-POST-PRIMARY-V1":
  return finalize_api_post_primary_v1(
   value,projection=projection
  )
 if stage_id=="R-PRE-SHADOW":
  value["round_evidence_package_sha256"]=projection["round_evidence_package_sha256"]
  return finalize_api_pre_shadow(value)
 if stage_id=="R-POST-SHADOW":
  value["environment_result_package_sha256"]=projection["environment_result_package_sha256"]
  value["human_pre_record_sha256"]=projection["human_pre_record_sha256"]
  return finalize_api_post_shadow(value)
 raise ValueError(f"unsupported semantic stage: {stage_id}")

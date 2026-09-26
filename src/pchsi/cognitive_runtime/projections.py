from __future__ import annotations
from pathlib import Path
from collections.abc import Mapping
from pchsi.reference_loop.canonical import strict_json_loads,sha256_file
from pchsi.analyzer.local_results import EvidencePackReferenceResolver


def load_object(path:Path)->dict[str,object]:
 value=strict_json_loads(path.read_bytes())
 if not isinstance(value,dict): raise ValueError(f"object required: {path}")
 return value


def _artifact_sha(value:dict[str,object],*fields:str)->str:
 for field in fields:
  x=value.get(field)
  if isinstance(x,str) and len(x)==64: return x
 raise ValueError(f"artifact has no recognized SHA field: {fields}")


def _catalog_ref(*,pack_sha:str,evidence_kind:str,local_selector:str,
                 authority:str)->dict[str,str]:
 return {
  "artifact_sha256":pack_sha,
  "evidence_kind":evidence_kind,
  "local_selector":local_selector,
  "authority":authority,
 }


def evidence_reference_catalog(pack:dict[str,object])->dict[str,object]:
 counterexamples=tuple(
  str(value)
  for value in pack.get("counterexample_inventory",[])
  if isinstance(value,str)
 )
 resolver=EvidencePackReferenceResolver.from_pack(
  pack,counterexamples=counterexamples
 )
 trajectory=[
  _catalog_ref(
   pack_sha=resolver.pack_sha,
   evidence_kind="TRAJECTORY_CALL",
   local_selector=f"trajectory:{index}",
   authority="DETERMINISTIC_FACT",
  )
  for index in sorted(resolver.trajectory_indices)
 ]
 mechanical=[
  _catalog_ref(
   pack_sha=resolver.pack_sha,
   evidence_kind="MECHANICAL_FACT",
   local_selector=selector,
   authority="DETERMINISTIC_FACT",
  )
  for selector in sorted(resolver.mechanical_selectors)
 ]
 counterexample_refs=[
  _catalog_ref(
   pack_sha=resolver.pack_sha,
   evidence_kind="COUNTEREXAMPLE",
   local_selector=selector,
   authority="SEMANTIC_HYPOTHESIS",
  )
  for selector in sorted(resolver.counterexample_selectors)
 ]
 return {
  "schema_id":"ANALYZER_EVIDENCE_REFERENCE_CATALOG_V1",
  "evidence_pack_sha256":resolver.pack_sha,
  "copy_policy":"EXACT_OBJECT_COPY_ONLY",
  "mechanical_selector_policy":"LEAF_ONLY_EXACT_CATALOG_MEMBER",
  "trajectory_calls":trajectory,
  "mechanical_facts":mechanical,
  "counterexamples":counterexample_refs,
 }


def local_repair_contract()->dict[str,object]:
 return {
  "schema_id":"ANALYZER_LOCAL_REPAIR_CONTRACT_V1",
  "EXACT_ACTION":{
   "exact_action":"REQUIRED_EXACT_ADMISSIBLE_COMMAND_STRING",
   "option_actions":"EMPTY_ARRAY",
   "termination_condition":"NULL",
   "trainable_rule":"NULL",
  },
  "SHORT_OPTION":{
   "exact_action":"NULL",
   "option_actions":"ARRAY_1_TO_4_FIRST_ACTION_ADMISSIBLE",
   "termination_condition":"REQUIRED_NONEMPTY_STRING",
   "trainable_rule":"NULL",
  },
  "TRAINABLE_RULE":{
   "exact_action":"NULL",
   "option_actions":"EMPTY_ARRAY",
   "termination_condition":"NULL",
   "trainable_rule":"REQUIRED_NONEMPTY_STRING",
  },
  "requires_environment_verification":True,
 }


def local_projection(evidence_pack_path:Path)->dict[str,object]:
 pack=load_object(evidence_pack_path)
 return {
  "evidence_pack_sha256":_artifact_sha(pack,"evidence_pack_sha256"),
  "evidence_pack":pack,
  "evidence_reference_catalog":evidence_reference_catalog(pack),
  "local_repair_contract":local_repair_contract(),
  "memory_pack_sha256":None,
 }


def group_projection(*,group_synthesis_input_path:Path,a1_local_result_path:Path,
                     memory_pack_path:Path|None)->dict[str,object]:
 group=load_object(group_synthesis_input_path); local=load_object(a1_local_result_path)
 memory=None if memory_pack_path is None else load_object(memory_pack_path)
 return {"group_manifest_sha256":_artifact_sha(group,"group_manifest_sha256"),
  "a1_local_result_sha256":_artifact_sha(local,"local_result_sha256"),
  "group_synthesis_input":group,
  "memory_pack_sha256":None if memory is None else _artifact_sha(memory,"memory_pack_sha256","pack_sha256","snapshot_sha256"),
  **({} if memory is None else {"memory_pack":memory})}


def group_projection_v2(
    *,
    group_synthesis_input_path:Path,
    a1_local_result_paths:list[Path],
    source_contexts_path:Path,
    memory_pack_path:Path|None,
)->dict[str,object]:
 group=load_object(group_synthesis_input_path)
 contexts_raw=strict_json_loads(source_contexts_path.read_bytes())
 if not isinstance(contexts_raw,list) or not contexts_raw:
  raise ValueError("source contexts must be non-empty array")
 locals_by_sha={}
 for path in a1_local_result_paths:
  local=load_object(path)
  sha=_artifact_sha(local,"local_result_sha256")
  if sha in locals_by_sha:
   raise ValueError("duplicate A1 local-result SHA")
  locals_by_sha[sha]=local
 members=group.get("member_rows")
 if not isinstance(members,list) or not members:
  raise ValueError("group synthesis input has no members")
 contexts={}
 for row in contexts_raw:
  if not isinstance(row,dict):
   raise ValueError("source context row must be object")
  key=(row.get("local_result_sha256"),row.get("error_instance_id"))
  if key in contexts:
   raise ValueError("duplicate source context")
  contexts[key]=row
 for member in members:
  if not isinstance(member,dict):
   raise ValueError("member row must be object")
  key=(member.get("local_result_sha256"),member.get("error_instance_id"))
  if key not in contexts:
   raise ValueError("group member missing source context")
  context=contexts[key]
  for field in ("source_state_sha256","menu_sha256","source_call_index"):
   if context.get(field)!=member.get(field):
    raise ValueError(f"group/source context mismatch: {field}")
  if member.get("local_result_sha256") not in locals_by_sha:
   raise ValueError("group member A1 bytes missing")
 memory=None if memory_pack_path is None else load_object(memory_pack_path)
 return {
  "group_manifest_sha256":_artifact_sha(group,"group_manifest_sha256"),
  "a1_local_result_sha256s":sorted(locals_by_sha),
  "a1_local_results":[locals_by_sha[x] for x in sorted(locals_by_sha)],
  "group_synthesis_input":group,
  "source_contexts":[contexts[
      (member["local_result_sha256"],member["error_instance_id"])
   ] for member in members],
  "memory_pack_sha256":None if memory is None else _artifact_sha(
      memory,"memory_pack_sha256","pack_sha256","snapshot_sha256"
  ),
  **({} if memory is None else {"memory_pack":memory}),
 }


def component_projection(group_result_path:Path)->dict[str,object]:
 group=load_object(group_result_path)
 return {"group_result_sha256":_artifact_sha(group,"group_result_sha256"),
         "group_result":group,"memory_pack_sha256":None}


def crosscheck_projection(*,target_path:Path,current_evidence_manifest_path:Path,
                          memory_pack_path:Path|None)->dict[str,object]:
 target=load_object(target_path); memory=None if memory_pack_path is None else load_object(memory_pack_path)
 return {"target_artifact_sha256":_artifact_sha(target,"local_result_sha256","group_result_sha256","attribution_sha256","profile_sha256","candidate_sha256"),
  "target_artifact":target,"current_evidence_manifest_sha256":sha256_file(current_evidence_manifest_path),
  "memory_pack_sha256":None if memory is None else _artifact_sha(memory,"memory_pack_sha256","pack_sha256","snapshot_sha256"),
  **({} if memory is None else {"memory_pack":memory})}

from pchsi.reference_loop.canonical import domain_hash

def _x_manifest_sha(
    *,
    domain: str,
    value: dict[str, object],
    field: str,
) -> str:
 out=dict(value)
 out[field]="0"*64
 return domain_hash(domain,out,excluded_field=field)


def crosscheck_projection_v2(
    *,
    target_path:Path,
    target_stage_id:str,
    group_manifest_path:Path,
    common_group_projection_path:Path,
    memory_pack_path:Path|None,
)->dict[str,object]:
 if target_stage_id not in {"G-A2","G-A3"}:
  raise ValueError("X target stage must be G-A2 or G-A3")

 target=load_object(target_path)
 group_manifest=load_object(group_manifest_path)
 common=load_object(common_group_projection_path)

 target_sha=_artifact_sha(target,"group_result_sha256")
 group_sha=_artifact_sha(group_manifest,"group_manifest_sha256")

 if target.get("group_manifest_sha256")!=group_sha:
  raise ValueError("X target/group-manifest mismatch")
 if common.get("group_manifest_sha256")!=group_sha:
  raise ValueError("X common projection/group-manifest mismatch")
 if common.get("memory_pack_sha256") is not None or "memory_pack" in common:
  raise ValueError("X common current-evidence projection must be Memory-blind")

 synthesis=common.get("group_synthesis_input")
 locals_raw=common.get("a1_local_results")
 contexts=common.get("source_contexts")
 if not isinstance(synthesis,dict):
  raise ValueError("X current evidence missing group synthesis input")
 if not isinstance(locals_raw,list) or not locals_raw:
  raise ValueError("X current evidence missing A1 local-result bytes")
 if not isinstance(contexts,list) or not contexts:
  raise ValueError("X current evidence missing source contexts")

 synthesis_sha=_artifact_sha(synthesis,"group_synthesis_input_sha256")
 local_shas=[]
 for row in locals_raw:
  if not isinstance(row,dict):
   raise ValueError("X A1 local result must be object")
  local_shas.append(_artifact_sha(row,"local_result_sha256"))

 source_state_shas=[]
 menu_shas=[]
 for row in contexts:
  if not isinstance(row,dict):
   raise ValueError("X source context must be object")
  state=row.get("source_state_sha256")
  menu=row.get("menu_sha256")
  if not isinstance(state,str) or len(state)!=64:
   raise ValueError("X source state identity invalid")
  if not isinstance(menu,str) or len(menu)!=64:
   raise ValueError("X source menu identity invalid")
  source_state_shas.append(state)
  menu_shas.append(menu)

 common_for_allowlist={
  "group_id":group_manifest.get("group_id"),
  "group_manifest_sha256":group_sha,
  "a1_local_results":locals_raw,
  "group_synthesis_input":synthesis,
  "source_contexts":contexts,
 }
 allowed_current=canonical_group_current_evidence_sha256s(
  common_for_allowlist
 )

 current_manifest={
  "schema_id":"ANALYZER_X_CURRENT_EVIDENCE_MANIFEST_V1",
  "schema_version":1,
  "group_manifest_sha256":group_sha,
  "group_manifest":group_manifest,
  "group_synthesis_input_sha256":synthesis_sha,
  "group_synthesis_input":synthesis,
  "a1_local_result_sha256s":sorted(local_shas),
  "a1_local_results":locals_raw,
  "source_state_sha256s":sorted(source_state_shas),
  "menu_sha256s":sorted(menu_shas),
  "source_contexts":contexts,
  "allowed_evidence_sha256s":allowed_current,
  "current_evidence_manifest_sha256":"0"*64,
 }
 current_manifest["current_evidence_manifest_sha256"]=_x_manifest_sha(
  domain="ANALYZER_X_CURRENT_EVIDENCE_MANIFEST_V1",
  value=current_manifest,
  field="current_evidence_manifest_sha256",
 )

 memory=None if memory_pack_path is None else load_object(memory_pack_path)
 memory_sha=None if memory is None else _artifact_sha(
  memory,"memory_pack_sha256","pack_sha256","snapshot_sha256"
 )

 if target_stage_id=="G-A2" and memory is not None:
  raise ValueError("X G-A2 target must remain Memory-blind")
 if target_stage_id=="G-A3" and memory is None:
  raise ValueError("X G-A3 target requires exact historical Memory pack")

 historical_manifest={
  "schema_id":"ANALYZER_X_HISTORICAL_EVIDENCE_MANIFEST_V1",
  "schema_version":1,
  "target_stage_id":target_stage_id,
  "memory_pack_sha256":memory_sha,
  "allowed_evidence_sha256s":[] if memory_sha is None else [memory_sha],
  "historical_evidence_manifest_sha256":"0"*64,
 }
 historical_manifest["historical_evidence_manifest_sha256"]=_x_manifest_sha(
  domain="ANALYZER_X_HISTORICAL_EVIDENCE_MANIFEST_V1",
  value=historical_manifest,
  field="historical_evidence_manifest_sha256",
 )

 return {
  "target_stage_id":target_stage_id,
  "target_artifact_sha256":target_sha,
  "target_artifact":target,
  "current_evidence_manifest_sha256":current_manifest[
   "current_evidence_manifest_sha256"
  ],
  "current_evidence_manifest":current_manifest,
  "historical_evidence_manifest_sha256":historical_manifest[
   "historical_evidence_manifest_sha256"
  ],
  "historical_evidence_manifest":historical_manifest,
  "memory_pack_sha256":memory_sha,
  **({} if memory is None else {"memory_pack":memory}),
 }

def _valid_sha256_text(value: object) -> bool:
 return (
  isinstance(value,str)
  and len(value)==64
  and all(ch in "0123456789abcdef" for ch in value)
 )


def _typed_evidence_artifact_sha256s(local_result: Mapping[str,object]) -> set[str]:
 """Collect exact typed evidence artifact identities visible in A1 bytes."""
 out=set()

 evidence_pack_sha=local_result.get("evidence_pack_sha256")
 if _valid_sha256_text(evidence_pack_sha):
  out.add(str(evidence_pack_sha))

 def add_refs(raw: object) -> None:
  if not isinstance(raw,list):
   return
  for ref in raw:
   if not isinstance(ref,Mapping):
    continue
   sha=ref.get("artifact_sha256")
   kind=ref.get("evidence_kind")
   authority=ref.get("authority")
   selector=ref.get("local_selector")
   if (
    _valid_sha256_text(sha)
    and isinstance(kind,str)
    and isinstance(authority,str)
    and isinstance(selector,str)
    and selector
   ):
    out.add(str(sha))

 errors=local_result.get("error_instances")
 if isinstance(errors,list):
  for error in errors:
   if not isinstance(error,Mapping):
    continue
   add_refs(error.get("supporting_evidence_refs"))
   add_refs(error.get("counterevidence_refs"))
   hyps=error.get("mechanism_hypotheses")
   if isinstance(hyps,list):
    for hyp in hyps:
     if isinstance(hyp,Mapping):
      add_refs(hyp.get("supporting_evidence_refs"))
      add_refs(hyp.get("counterevidence_refs"))

 repairs=local_result.get("local_repairs")
 if isinstance(repairs,list):
  for repair in repairs:
   if isinstance(repair,Mapping):
    add_refs(repair.get("supporting_evidence_refs"))

 return out


def canonical_group_current_evidence_sha256s(
    projection: Mapping[str,object],
) -> list[str]:
 """Single current-evidence citation universe shared by G and X."""
 group_id=projection.get("group_id")
 group_sha=projection.get("group_manifest_sha256")
 synthesis=projection.get("group_synthesis_input")
 locals_raw=projection.get("a1_local_results")
 contexts=projection.get("source_contexts")

 if not _valid_sha256_text(group_id):
  raise ValueError("group projection requires deterministic group_id")
 if not _valid_sha256_text(group_sha):
  raise ValueError("group projection requires group_manifest_sha256")
 if not isinstance(synthesis,Mapping):
  raise ValueError("group projection requires group synthesis input")
 if not isinstance(locals_raw,list) or not locals_raw:
  raise ValueError("group projection requires A1 local-result bytes")
 if not isinstance(contexts,list) or not contexts:
  raise ValueError("group projection requires source contexts")

 values={str(group_id),str(group_sha)}

 synthesis_sha=synthesis.get("group_synthesis_input_sha256")
 if not _valid_sha256_text(synthesis_sha):
  raise ValueError("group synthesis input identity invalid")
 values.add(str(synthesis_sha))

 for local in locals_raw:
  if not isinstance(local,Mapping):
   raise ValueError("A1 local result must be object")
  local_sha=local.get("local_result_sha256")
  if not _valid_sha256_text(local_sha):
   raise ValueError("A1 local result identity invalid")
  values.add(str(local_sha))
  values.update(_typed_evidence_artifact_sha256s(local))

 for context in contexts:
  if not isinstance(context,Mapping):
   raise ValueError("source context must be object")
  for field in ("source_state_sha256","menu_sha256"):
   value=context.get(field)
   if not _valid_sha256_text(value):
    raise ValueError(f"source context identity invalid: {field}")
   values.add(str(value))

 return sorted(values)


def group_projection_v3(
    *,
    group_manifest_path:Path,
    group_synthesis_input_path:Path,
    a1_local_result_paths:list[Path],
    source_contexts_path:Path,
    memory_pack_path:Path|None,
)->dict[str,object]:
 manifest=load_object(group_manifest_path)
 group=load_object(group_synthesis_input_path)

 group_id=_artifact_sha(manifest,"group_id")
 group_sha=_artifact_sha(manifest,"group_manifest_sha256")

 if group.get("group_manifest_sha256")!=group_sha:
  raise ValueError("group synthesis/manifest identity mismatch")

 base=group_projection_v2(
  group_synthesis_input_path=group_synthesis_input_path,
  a1_local_result_paths=a1_local_result_paths,
  source_contexts_path=source_contexts_path,
  memory_pack_path=memory_pack_path,
 )
 if base.get("group_manifest_sha256")!=group_sha:
  raise ValueError("group projection manifest identity mismatch")

 out={"group_id":group_id,**base}
 out["current_evidence_sha256s"]=canonical_group_current_evidence_sha256s(out)
 return out

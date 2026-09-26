from __future__ import annotations
from collections.abc import Iterable,Mapping
import hashlib,json
def _canonical(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def stable_memory_payload(view):
    if view.get("schema_id")!="RESEARCHER_MEMORY_VIEW_V1": raise ValueError("Researcher Memory schema mismatch")
    if view.get("purpose")!="ROUND_RESEARCH_PLANNING": raise ValueError("Researcher Memory purpose mismatch")
    if view.get("direct_environment_action_authority") is not False: raise ValueError("Researcher Memory action authority forbidden")
    if view.get("benefit_harm_authority") is not False: raise ValueError("Researcher Memory effect authority forbidden")
    records=view.get("train_side_records")
    if not isinstance(records,list): raise ValueError("train_side_records must be array")
    return {"snapshot_sha256":view.get("snapshot_sha256"),"purpose":view.get("purpose"),"train_side_records":records,"direct_environment_action_authority":False,"benefit_harm_authority":False,"may_propose_one_principal_system_change":view.get("may_propose_one_principal_system_change")}
def stable_memory_signature(view): return hashlib.sha256(_canonical(stable_memory_payload(view))).hexdigest()
def resolve_stable_memory_authority(views:Iterable[Mapping[str,object]],*,snapshot_sha256:str):
    candidates=[]; by_signature={}
    for raw in views:
        view=dict(raw)
        if view.get("schema_id")!="RESEARCHER_MEMORY_VIEW_V1" or view.get("snapshot_sha256")!=snapshot_sha256 or view.get("purpose")!="ROUND_RESEARCH_PLANNING": continue
        sig=stable_memory_signature(view); candidates.append(view); by_signature.setdefault(sig,[]).append(view)
    if not candidates: raise ValueError("NO_CURRENT_SNAPSHOT_RESEARCHER_MEMORY_VIEWS")
    if len(by_signature)!=1: raise ValueError("MULTIPLE_STABLE_MEMORY_AUTHORITIES:"+",".join(sorted(by_signature)))
    sig,rows=next(iter(by_signature.items())); stable=stable_memory_payload(rows[0])
    return {"candidate_view_count":len(candidates),"stable_signature_count":1,"stable_memory_signature_sha256":sig,"snapshot_sha256":snapshot_sha256,"train_side_records":stable["train_side_records"],"provenance_view_sha256s":sorted({str(row["view_sha256"]) for row in rows if isinstance(row.get("view_sha256"),str)})}
def build_current_round_evidence(*,round_id,parent_policy_id,analyzer_terminal_sha256,dynamic_pair_universe_sha256,dynamic_pair_count,round_start_memory_snapshot_sha256):
    return {"schema_id":"RESEARCHER_MEMORY_CURRENT_ROUND_EVIDENCE_V1","schema_version":1,"scientific_round_id":round_id,"parent_policy_id":parent_policy_id,"analyzer_terminal_sha256":analyzer_terminal_sha256,"dynamic_pair_universe_sha256":dynamic_pair_universe_sha256,"dynamic_pair_count":dynamic_pair_count,"round_start_memory_snapshot_sha256":round_start_memory_snapshot_sha256,"pre_outcome_only":True,"environment_effect_authority":False,"promotion_authority":False}

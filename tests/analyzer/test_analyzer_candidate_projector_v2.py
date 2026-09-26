from pchsi.analyzer.candidate_projector import project_candidate
from pchsi.analyzer.grouping import finalize_source_conditioned_proposal

def _state():
 return {"source_state_sha256":"a"*64,"menu_sha256":"b"*64,
         "admissible_commands":["look","go to fridge 1"]}

def _proposal():
 return finalize_source_conditioned_proposal({
  "schema_id":"ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1","schema_version":1,
  "group_manifest_sha256":"c"*64,"local_result_sha256":"d"*64,
  "error_instance_id":"e","source_state_sha256":"a"*64,"menu_sha256":"b"*64,
  "exact_action":"go to fridge 1","option_actions":[],"termination_condition":None,
  "supporting_evidence_sha256s":["f"*64],"source_proposal_sha256":"0"*64})

def test_projector_abstains_without_source_bytes_and_never_rewrites():
 assert project_candidate(None,_state(),candidate_kind="FAILURE_REPAIR")["candidate_status"]=="ABSTAIN"
 p=_proposal()
 out=project_candidate(p,_state(),candidate_kind="FAILURE_REPAIR")
 assert out["exact_action"]==p["exact_action"]
 bad=dict(p); bad["menu_sha256"]="0"*64
 from pchsi.reference_loop.canonical import domain_hash
 bad["source_proposal_sha256"]="0"*64
 bad["source_proposal_sha256"]=domain_hash(
   "ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1",bad,
   excluded_field="source_proposal_sha256")
 assert project_candidate(bad,_state(),candidate_kind="FAILURE_REPAIR")["candidate_status"]=="REJECTED_SOURCE_BINDING"

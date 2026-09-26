import pytest
from pchsi.analyzer.experiment_registry import validate_registry,build_execution_dedup_map

def _r():
 r={"conditions":["A0","A1","A2","A3"],"registered_unit_ids":["u"],
    "max_formal_candidate_count_per_unit":1,
    "common_repair_budget":{
      "max_candidate_count_per_unit":1,"max_option_actions":4,
      "analyzer_prose_in_policy_prompt":False,
      "all_intervention_actions_count_against_environment_budget":True},
    "unit_condition_rows":[
      {"unit_id":"u","condition_id":c,"candidate_count":0,"abstained":True}
      for c in ("A0","A1","A2","A3")]}
 for c in ("A0","A1","A2","A3"):
  r[c]={"registered_universe_sha256":"1"*64,
        "local_result_sha256s":[] if c=="A0" else ["2"*64],
        "common_evidence_pack_sha256s":["3"*64],
        "memory_pack_sha256":"4"*64 if c=="A3" else None}
 return r

def test_registry_enforces_a1_reuse_and_common_universe():
 assert validate_registry(_r())
 x=_r(); x["A3"]["local_result_sha256s"]=["c"*64]
 with pytest.raises(ValueError): validate_registry(x)

def test_identical_candidate_execution_is_deduplicated():
 rows=[{"source_state_sha256":"a"*64,"candidate_sha256":"b"*64,
        "termination_condition_sha256":"c"*64} for _ in range(2)]
 assert len(build_execution_dedup_map(rows))==1

from pchsi.cognitive_runtime.formal_registry import validate_formal_dag
from pchsi.reference_loop.canonical import domain_hash

def test_complete_u_reg_a0_a3_and_reuse():
 rows=[]
 for c in ("A0","A1","A2","A3"):
  rows.append({"source_unit_id":"u","condition_id":c,"common_evidence_pack_sha256":"a"*64,
   "a1_local_result_sha256":None if c=="A0" else "b"*64,
   "memory_pack_sha256":"c"*64 if c=="A3" else None,
   "candidate_budget":1,"abstain_permitted":True})
 v={"schema_id":"FORMAL_ANALYZER_DAG_REGISTRY_V1","schema_version":1,"round_id":"r",
  "registered_universe_sha256":"d"*64,"registered_unit_ids":["u"],"condition_rows":rows,
  "runtime_input_registry_sha256":"e"*64,"formal_dag_sha256":"0"*64}
 v["formal_dag_sha256"]=domain_hash("FORMAL_ANALYZER_DAG_REGISTRY_V1",v,excluded_field="formal_dag_sha256")
 validate_formal_dag(v)

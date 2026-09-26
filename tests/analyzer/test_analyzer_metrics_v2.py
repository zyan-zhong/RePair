from pchsi.analyzer.metrics import aggregate_repair_discovery_by_condition

def test_evry_keeps_abstention_and_uses_unique_registered_units():
 rows=[]
 for cond in ("A0","A1","A2","A3"):
  rows.extend([
   {"unit_id":"u1","condition_id":cond,"candidate_count":1,
    "formal_candidate_proposed":True,"effect_label":"Benefit",
    "protocol_complete":True,"formal_verifier_env_steps":3,
    "frozen_priority":1,"method_failure_reason":None,
    "infrastructure_unavailable":False},
   {"unit_id":"u2","condition_id":cond,"candidate_count":0,
    "formal_candidate_proposed":False,"effect_label":None,
    "protocol_complete":True,"formal_verifier_env_steps":0,
    "frozen_priority":2,"method_failure_reason":"ABSTAIN",
    "infrastructure_unavailable":False},
  ])
 report=aggregate_repair_discovery_by_condition(
     rows,registered_universe=["u1","u2"])
 assert report["conditions"]["A0"]["EVRY_reg"][
     "denominator"]==2
 assert report["conditions"]["A0"]["ProposalCoverage"][
     "numerator"]==1

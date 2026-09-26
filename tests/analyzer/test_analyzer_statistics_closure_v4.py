import pytest
import pchsi.analyzer.metrics as metrics

def _rows():
 rows=[]; outcomes={"A0":{"u1":"Neutral","u2":"Benefit","u3":"Neutral","u4":"Benefit"},"A1":{"u1":"Benefit","u2":"Benefit","u3":"Neutral","u4":"Neutral"},"A2":{"u1":"Benefit","u2":"Benefit","u3":"Benefit","u4":"Neutral"},"A3":{"u1":"Benefit","u2":"Benefit","u3":"Benefit","u4":"Benefit"}}
 for cond in ("A0","A1","A2","A3"):
  for i,unit in enumerate(("u1","u2","u3","u4"),1):
   rows.append({"unit_id":unit,"condition_id":cond,"candidate_count":1,"formal_candidate_proposed":True,"effect_label":outcomes[cond][unit],"protocol_complete":True,"formal_verifier_env_steps":1,"frozen_priority":i,"method_failure_reason":None,"infrastructure_unavailable":False,"infrastructure_reason":None})
 return rows

def test_paired_summary_includes_exact_mcnemar_rd_rr():
 out=metrics.paired_binary_summary(_rows(),condition_a="A0",condition_b="A1")
 assert out["paired_unit_count"]==4
 assert out["risk_difference_b_minus_a"]==0.0
 assert out["relative_risk_b_over_a"]==1.0
 assert out["mcnemar_exact_denominator"]==2
 assert out["mcnemar_exact_p"]==1.0

def test_holm_adjustment_is_monotone():
 out=metrics.holm_adjust({"a":0.01,"b":0.03,"c":0.20})
 assert out["a"]["holm_adjusted_p"]==pytest.approx(0.03)
 assert out["b"]["holm_adjusted_p"]==pytest.approx(0.06)
 assert out["c"]["holm_adjusted_p"]==pytest.approx(0.20)

def test_registered_secondary_report_freezes_three_contrasts():
 out=metrics.registered_secondary_contrast_report(_rows(),iterations=100,seed=7)
 assert list(out["contrasts"])==["A1_VS_A0","A2_VS_A1","A3_VS_A2"]
 assert out["adjustment"]=="HOLM"

def test_infrastructure_reason_is_mandatory():
 rows=_rows(); rows[0]["infrastructure_unavailable"]=True; rows[0]["protocol_complete"]=False
 with pytest.raises(ValueError,match="explicit reason"):
  metrics.aggregate_repair_discovery_by_condition(rows,registered_universe=["u1","u2","u3","u4"])

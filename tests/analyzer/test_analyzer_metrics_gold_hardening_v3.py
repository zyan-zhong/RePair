import pytest
import pchsi.analyzer.metrics as metrics
from pchsi.analyzer.gold_panel import select_gold_panels

def _rows():
    rows=[]
    for cond in ("A0","A1","A2","A3"):
        rows += [
            {"unit_id":"u1","condition_id":cond,"candidate_count":1,
             "formal_candidate_proposed":True,
             "effect_label":"Benefit" if cond in ("A2","A3") else "Neutral",
             "protocol_complete":True,"formal_verifier_env_steps":2,
             "frozen_priority":1,"method_failure_reason":None,
             "infrastructure_unavailable":False},
            {"unit_id":"u2","condition_id":cond,"candidate_count":0,
             "formal_candidate_proposed":False,"effect_label":None,
             "protocol_complete":True,"formal_verifier_env_steps":0,
             "frozen_priority":2,"method_failure_reason":"ABSTAIN",
             "infrastructure_unavailable":False},
        ]
    return rows

def test_metrics_are_condition_specific_and_complete():
    report=metrics.aggregate_repair_discovery_by_condition(
        _rows(),registered_universe=["u1","u2"]
    )
    assert report["conditions"]["A3"]["EVRY_reg"]["numerator"]==1
    assert report["conditions"]["A3"]["EVRY_reg"]["denominator"]==2
    assert report["conditions"]["A0"]["ProposalCoverage"]["denominator"]==2

def test_metric_rows_outside_u_reg_rejected():
    rows=_rows()
    rows.append({**rows[0],"unit_id":"outside"})
    with pytest.raises(ValueError,match="outside U_reg"):
        metrics.aggregate_repair_discovery_by_condition(rows,registered_universe=["u1","u2"])

def test_paired_summary_uses_same_units():
    out=metrics.paired_binary_summary(_rows(),condition_a="A1",condition_b="A3")
    assert out["paired_unit_count"]==2
    assert out["discordant_a0_b1"]==1

def test_gold_selection_balances_task_families():
    rows=[
        {"task_id":f"a{i}","gamefile_sha256":f"{i+1:064x}","outcome":"FAILURE",
         "task_family":"A","failure_burden":10-i,"frozen_order":i}
        for i in range(4)
    ]+[
        {"task_id":f"b{i}","gamefile_sha256":f"{i+20:064x}","outcome":"FAILURE",
         "task_family":"B","failure_burden":10-i,"frozen_order":10+i}
        for i in range(4)
    ]
    p=select_gold_panels(rows,failure_count=4,success_count=0)
    assert {x["task_family"] for x in p["failure"]}=={"A","B"}
    assert p["annotation_contract"]["blind_evaluator_required"] is True

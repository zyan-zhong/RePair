import json
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("driver", ROOT/"full_round_driver.py")
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def load(name):
    return json.loads((ROOT/"plans"/name).read_text())

def test_round1_tail_plan_is_fully_bound_and_valid():
    plan=load("ROUND1_ANALYZER_TAIL_BOUND_V1.json")
    gates=mod.validate_plan(plan)
    assert len(gates)==1
    assert gates[0]["binding_status"]=="BOUND"
    assert plan["expected_repo_head"]=="61c9b8798f0b0d1cfb046b5ca60d90b9d8d0da6a"
    assert plan["process_standard"]=="ONE_COMMAND_PI_K_TO_NEXT_ROUND_OR_TERMINAL_STOP_RECEIPT_DRIVEN"

def test_canonical_standard_has_full_cycle_and_fails_closed_until_bound():
    plan=load("CANONICAL_PI_K_TO_NEXT_ROUND_STANDARD_V1.json")
    gates=mod.validate_plan(plan)
    ids=[g["gate_id"] for g in gates]
    assert ids[0]=="POLICY_ROLLOUT_WITH_POLICY_MEMORY_VIEW"
    assert "RESEARCH_PLANNER_PRE" in ids
    assert "SAME_STATE_F0_F1" in ids
    assert "INDEPENDENT_ENVIRONMENT_VERIFICATION" in ids
    assert "RESEARCH_PLANNER_POST" in ids
    assert "MEMORY_ROUND_MAINTENANCE" in ids
    assert "POLICY_UPDATE_IF_AUTHORIZED" in ids
    assert "MEMORY_OFF_HARNESS_OFF_ACCEPTANCE" in ids
    assert "OUTER_LOOP_STOP_GOVERNANCE" in ids
    assert ids[-1]=="NEXT_ROUND_TRANSITION_IF_AUTHORIZED"
    stop_gate=next(g for g in gates if g["gate_id"]=="OUTER_LOOP_STOP_GOVERNANCE")
    next_gate=next(g for g in gates if g["gate_id"]=="NEXT_ROUND_TRANSITION_IF_AUTHORIZED")
    assert stop_gate["depends_on"]==["PROMOTE_OR_ROLLBACK"]
    assert next_gate["depends_on"]==["OUTER_LOOP_STOP_GOVERNANCE"]
    assert plan["process_standard"]=="ONE_COMMAND_PI_K_TO_NEXT_ROUND_OR_TERMINAL_STOP_RECEIPT_DRIVEN"
    assert all(g["binding_status"]=="UNBOUND" for g in gates)

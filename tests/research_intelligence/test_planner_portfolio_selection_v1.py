from pchsi.research_intelligence.planner_portfolio_selection import (
    build_select12_decision_aid_v1,
)

def _candidate(state, condition, family, group, negative=False):
    cross = [{
        "disposition": "REJECT" if negative else "ACCEPT",
        "supporting_evidence_sha256s": ["a"*64],
        "contradiction_evidence_sha256s": ["b"*64] if negative else [],
        "residual_case_ids": ["r"] if negative else [],
    }]
    return {
        "condition_id": condition,
        "candidate_sha256": (condition.lower()+state.replace("-",""))[:1]*64,
        "source_state_sha256": state,
        "repair_kind": "EXACT_ACTION",
        "option_actions": [],
        "supporting_evidence_sha256s": ["c"*64],
        "group_manifest": {"task_family": family, "group_id": group},
        "crosschecks": cross,
    }

def test_selects_12_from_30_pairs_without_outcomes():
    pairs={}
    for i in range(30):
        state=f"{i:064x}"
        pairs[state]={
            "A2":_candidate(state,"A2",f"family-{i%6}",f"group-{i}"),
            "A3":_candidate(state,"A3",f"family-{i%6}",f"group-{i}",negative=(i%7==0)),
        }
    out=build_select12_decision_aid_v1(
        canonical_pool={"state_pairs":pairs},
        researcher_memory={"x":"d"*64},
        registered_state_budget=12,
    )
    assert out["recommendation_count"]==12
    assert len({x["source_state_sha256"] for x in out["mechanical_recommendation"]})==12
    assert out["selection_method"]["uses_current_f0f1_outcomes"] is False
    assert out["success_trajectory_optimization_active"] is False

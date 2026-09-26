#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from pchsi.research_intelligence.planner_portfolio_selection import build_select12_decision_aid_v1

def load(p):
    v=json.loads(Path(p).read_text())
    assert isinstance(v,dict)
    return v

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--canonical-pool",required=True)
    ap.add_argument("--budget-plan",required=True)
    ap.add_argument("--memory",required=True)
    ap.add_argument("--output-dir",required=True)
    a=ap.parse_args()
    pool=load(a.canonical_pool)
    budget=load(a.budget_plan)
    memory=load(a.memory)
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=False)
    result=build_select12_decision_aid_v1(
        canonical_pool=pool,
        researcher_memory=memory,
        registered_state_budget=int(budget["registered_state_budget"]),
    )
    (out/"HUMAN_SELECT12_DECISION_AID_V1.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    )
    approval={
        "schema_id":"HUMAN_SELECT12_APPROVAL_V1",
        "decision_aid_sha256":None,
        "selected":result["mechanical_recommendation"],
        "status":"REQUIRES_HUMAN_REVIEW",
        "human_edits":[],
        "approval_rationale":None,
    }
    import hashlib
    approval["decision_aid_sha256"]=hashlib.sha256(
        (out/"HUMAN_SELECT12_DECISION_AID_V1.json").read_bytes()
    ).hexdigest()
    (out/"HUMAN_SELECT12_APPROVAL_TEMPLATE_V1.json").write_text(
        json.dumps(approval,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    )
    lines=["# Human Select-12 Review V1","",f"Recommended states: {len(result['mechanical_recommendation'])}","",
           "This is a mechanical decision aid only; Human Researcher approval is required.","",
           "|state|cond|candidate|","|---|---|---|"]
    for row in result["mechanical_recommendation"]:
        lines.append(f"|`{row['source_state_sha256'][:12]}`|{row['condition_id']}|`{row['candidate_sha256'][:12]}`|")
    (out/"HUMAN_SELECT12_REVIEW_V1.md").write_text("\n".join(lines)+"\n")
    print("HUMAN_SELECT12_RECOMMENDATION_COUNT=12")
    print("SUCCESS_TRAJECTORY_OPTIMIZATION_ACTIVE=false")
    print("NEXT_GATE=HUMAN_REVIEW_RECOMMENDED_12")
if __name__=="__main__": main()

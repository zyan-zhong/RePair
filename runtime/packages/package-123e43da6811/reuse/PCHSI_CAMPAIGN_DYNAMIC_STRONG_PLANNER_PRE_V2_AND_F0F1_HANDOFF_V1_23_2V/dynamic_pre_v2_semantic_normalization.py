from __future__ import annotations
from copy import deepcopy
from collections import Counter
from collections.abc import Mapping
ALLOWED_NORMALIZATION_PATHS=("selected_state_count","selected_source_state_sha256s","selected_candidate_sha256s","selected_condition_counts.A2","selected_condition_counts.A3","unused_state_budget","verification_plan.paired_repetitions_per_state","verification_plan.branch_arms_per_repetition","verification_plan.branch_runs_per_state","verification_plan.selected_state_budget_ceiling","verification_plan.selected_branch_run_budget","resource_plan.expected_environment_branch_runs")
_NORMALIZABLE_ERROR_FRAGMENTS=("selected-state count mismatch","unused-state budget mismatch","selected source-state list mismatch","selected candidate list mismatch","selected condition-count mismatch","verification-plan contract mismatch:","selected branch-run budget mismatch","resource plan mismatch")
def classify_validator_error(message):
    text=str(message); ok=any(x in text for x in _NORMALIZABLE_ERROR_FRAGMENTS)
    return {"normalization_candidate":ok,"message":text,"normalization_class":"DERIVED_SUMMARY_OR_FROZEN_PLAN_FIELD" if ok else None}
def _map(value,name):
    if not isinstance(value,Mapping): raise ValueError(f"{name} must be object")
    return dict(value)
def _selected_rows(value):
    reviews=value.get("state_reviews")
    if not isinstance(reviews,list): raise ValueError("state_reviews must be array")
    out=[]
    for raw in reviews:
        row=_map(raw,"state review")
        if row.get("selected_for_verification") is True:
            if row.get("state_portfolio_disposition")!="SELECTED": raise ValueError("selected state disposition mismatch")
            out.append(row)
        elif row.get("state_portfolio_disposition")=="SELECTED": raise ValueError("unselected state cannot be SELECTED")
    return out
def normalize_redundant_fields(value,contract):
    out=deepcopy(dict(value)); selected=_selected_rows(out)
    ceiling=contract.get("selected_state_budget_ceiling"); per_state=contract.get("branch_runs_per_state"); reps=contract.get("paired_repetitions_per_state"); arms=contract.get("branch_arms_per_repetition")
    if type(ceiling) is not int or ceiling<0: raise ValueError("dynamic contract selected-state ceiling invalid")
    if type(per_state) is not int or per_state<=0: raise ValueError("dynamic contract branch-runs/state invalid")
    if type(reps) is not int or reps<=0: raise ValueError("dynamic contract repetitions invalid")
    if type(arms) is not int or arms<=0: raise ValueError("dynamic contract branch arms invalid")
    count=len(selected); sources=[str(r["source_state_sha256"]) for r in selected]; candidates=[str(r["preferred_candidate_sha256"]) for r in selected]; counts=Counter(str(r["preferred_condition"]) for r in selected); branch_runs=count*per_state
    out["selected_state_count"]=count; out["selected_source_state_sha256s"]=sources; out["selected_candidate_sha256s"]=candidates; out["selected_condition_counts"]={"A2":counts["A2"],"A3":counts["A3"]}; out["unused_state_budget"]=ceiling-count
    plan=_map(out.get("verification_plan"),"verification_plan"); plan.update({"paired_repetitions_per_state":reps,"branch_arms_per_repetition":arms,"branch_runs_per_state":per_state,"selected_state_budget_ceiling":ceiling,"selected_branch_run_budget":branch_runs}); out["verification_plan"]=plan
    resource=_map(out.get("resource_plan"),"resource_plan"); resource["expected_environment_branch_runs"]=branch_runs; out["resource_plan"]=resource
    return out,list(ALLOWED_NORMALIZATION_PATHS)
def _walk_diff(before,after,prefix=""):
    if type(before) is not type(after): return [prefix or "<root>"]
    if isinstance(before,dict):
        diffs=[]
        for key in sorted(set(before)|set(after)):
            child=f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after: diffs.append(child)
            else: diffs.extend(_walk_diff(before[key],after[key],child))
        return diffs
    if isinstance(before,list): return [] if before==after else [prefix or "<root>"]
    return [] if before==after else [prefix or "<root>"]
def assert_only_allowed_changes(before,after):
    diffs=_walk_diff(dict(before),dict(after)); allowed=set(ALLOWED_NORMALIZATION_PATHS); bad=[x for x in diffs if x not in allowed]
    if bad: raise ValueError("NON_ALLOWLISTED_NORMALIZATION_CHANGE:"+",".join(bad))
    return diffs
def try_semantic_normalization(*,original_output,contract,original_validation_error,validator):
    cls=classify_validator_error(original_validation_error)
    if not cls["normalization_candidate"]: return {"status":"UNREPAIRABLE_SEMANTIC_INVALID","normalization_class":None,"changed_paths":[],"validated_artifact":None,"post_normalization_error":original_validation_error,"provider_call_count":0}
    normalized,_=normalize_redundant_fields(original_output,contract); changed=assert_only_allowed_changes(original_output,normalized)
    try: artifact=validator(normalized)
    except Exception as exc: return {"status":"NORMALIZATION_INSUFFICIENT","normalization_class":cls["normalization_class"],"changed_paths":changed,"validated_artifact":None,"post_normalization_error":f"{type(exc).__name__}:{exc}","provider_call_count":0}
    return {"status":"ACCEPTED_AFTER_DETERMINISTIC_NORMALIZATION","normalization_class":cls["normalization_class"],"changed_paths":changed,"validated_artifact":artifact,"post_normalization_error":None,"provider_call_count":0}

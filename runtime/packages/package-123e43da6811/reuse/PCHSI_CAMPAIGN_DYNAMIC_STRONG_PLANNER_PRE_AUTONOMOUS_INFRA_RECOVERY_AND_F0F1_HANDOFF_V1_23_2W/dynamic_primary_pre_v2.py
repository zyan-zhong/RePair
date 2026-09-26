"""Vendored exact Dynamic PRE V2 helper from durable staging authority."""
from __future__ import annotations
from collections import Counter
from collections.abc import Mapping, Sequence
import hashlib,json,re
_SHA_RE=re.compile(r"^[0-9a-f]{64}$")
def _sha(value): return isinstance(value,str) and _SHA_RE.fullmatch(value) is not None
def _map(value,name):
    if not isinstance(value,Mapping): raise ValueError(f"{name} must be object")
    return value
def _list(value,name):
    if not isinstance(value,list): raise ValueError(f"{name} must be array")
    return value
def _canonical_without_newline(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
def domain_hash(domain,value,excluded_field=None):
    body=dict(value)
    if excluded_field is not None: body.pop(excluded_field,None)
    return hashlib.sha256(domain.encode("utf-8")+b"\0"+_canonical_without_newline(body)).hexdigest()
def _complete_pair_rows(pair_rows):
    rows=[]; states=set()
    for raw in pair_rows:
        row=dict(raw)
        if row.get("pair_status")!="COMPLETE_A2_A3": raise ValueError("dynamic PRE requires complete pair rows only")
        state=row.get("source_state_sha256")
        if not _sha(state): raise ValueError("pair source-state identity invalid")
        if state in states: raise ValueError("duplicate pair source state")
        states.add(str(state))
        for condition in ("A2","A3"):
            candidate=_map(row.get(condition),condition)
            if candidate.get("source_state_sha256")!=state: raise ValueError("pair candidate source-state mismatch")
            if not _sha(candidate.get("candidate_sha256")): raise ValueError("pair candidate identity invalid")
        rows.append(row)
    if not rows: raise ValueError("dynamic PRE pair universe must be non-empty")
    return rows
def build_dynamic_pre_contract_v2(*,pair_rows,f0f1_protocol,dynamic_pair_universe_sha256):
    rows=_complete_pair_rows(pair_rows)
    if not _sha(dynamic_pair_universe_sha256): raise ValueError("dynamic pair-universe identity invalid")
    protocol=dict(f0f1_protocol)
    if protocol.get("schema_id")!="PLANNER_BOUND_F0F1_REPLICATION_PROTOCOL_V2": raise ValueError("F0/F1 protocol schema mismatch")
    if protocol.get("state_budget_authority")!="RESEARCH_PLANNER_PRE_SELECTED_UNIVERSE": raise ValueError("F0/F1 state-budget authority mismatch")
    if protocol.get("legacy_select12_authority_for_current_round") is not False: raise ValueError("legacy select12 authority forbidden")
    if protocol.get("outcome_adaptive_budget_change_allowed") is not False: raise ValueError("outcome-adaptive budget change forbidden")
    if protocol.get("outcome_adaptive_reselection_allowed") is not False: raise ValueError("outcome-adaptive reselection forbidden")
    if protocol.get("effect_authority")!="INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY": raise ValueError("effect authority mismatch")
    repetitions=protocol.get("paired_repetitions_per_state"); arms=protocol.get("branch_arms_per_repetition")
    if type(repetitions) is not int or repetitions<=0: raise ValueError("paired repetitions invalid")
    if type(arms) is not int or arms!=2: raise ValueError("F0/F1 branch-arm count invalid")
    pair_count=len(rows); per_state=repetitions*arms; ceiling=pair_count
    contract={"schema_id":"STRONG_RESEARCHER_PRE_PRIMARY_DYNAMIC_CONTRACT_V2","schema_version":2,"dynamic_pair_universe_sha256":dynamic_pair_universe_sha256,"pair_count":pair_count,"state_review_count_required":pair_count,"state_index_min":0,"state_index_max":pair_count-1,"selected_state_budget_ceiling":ceiling,"paired_repetitions_per_state":repetitions,"branch_arms_per_repetition":arms,"branch_runs_per_state":per_state,"max_derived_branch_runs":ceiling*per_state,"state_budget_authority":protocol["state_budget_authority"],"effect_authority":protocol["effect_authority"],"promotion_authority":"DETERMINISTIC_INDEPENDENT_GATE_ONLY","outcome_adaptive_budget_change_allowed":False,"outcome_adaptive_reselection_allowed":False,"legacy_exact_30_authority":False,"legacy_select12_authority":False,"contract_sha256":"0"*64}
    contract["contract_sha256"]=domain_hash("STRONG_RESEARCHER_PRE_PRIMARY_DYNAMIC_CONTRACT_V2",contract,excluded_field="contract_sha256")
    return contract
def derived_branch_runs(selected_state_count,contract):
    ceiling=contract.get("selected_state_budget_ceiling"); per_state=contract.get("branch_runs_per_state")
    if type(selected_state_count) is not int or selected_state_count<0: raise ValueError("selected_state_count invalid")
    if type(ceiling) is not int or not 0<=selected_state_count<=ceiling: raise ValueError("selected_state_count exceeds dynamic ceiling")
    if type(per_state) is not int or per_state<=0: raise ValueError("branch_runs_per_state invalid")
    return selected_state_count*per_state
def finalize_dynamic_primary_pre_v2(*,value,pair_rows,contract,blind_input_sha256,round_id):
    rows=_complete_pair_rows(pair_rows); out=dict(value)
    if out.get("schema_id")!="STRONG_RESEARCHER_PRE_PRIMARY_V2" or out.get("schema_version")!=2: raise ValueError("dynamic primary PRE schema mismatch")
    if out.get("round_id")!=round_id: raise ValueError("round mismatch")
    if out.get("blind_input_sha256")!=blind_input_sha256 or not _sha(blind_input_sha256): raise ValueError("blind-input identity mismatch")
    if out.get("automatic_environment_effect_assignment") is not False: raise ValueError("Strong cannot assign effects")
    if out.get("effect_authority")!="INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY": raise ValueError("effect authority mismatch")
    if out.get("promotion_authority")!="DETERMINISTIC_INDEPENDENT_GATE_ONLY": raise ValueError("promotion authority mismatch")
    reviews=_list(out.get("state_reviews"),"state_reviews"); required_count=int(contract["state_review_count_required"])
    if len(rows)!=required_count or len(reviews)!=required_count: raise ValueError("dynamic PRE review count mismatch")
    selected_rows=[]
    for index,(raw_review,pair) in enumerate(zip(reviews,rows,strict=True)):
        review=_map(raw_review,"state review")
        if review.get("state_index")!=index: raise ValueError("state-review index/order mismatch")
        if review.get("source_state_sha256")!=pair.get("source_state_sha256"): raise ValueError("state-review source binding mismatch")
        pref=review.get("preferred_condition"); alt=review.get("alternative_condition")
        if {pref,alt}!={"A2","A3"}: raise ValueError("A2/A3 comparison required")
        preferred=_map(pair[pref],"preferred candidate"); alternative=_map(pair[alt],"alternative candidate")
        if review.get("preferred_candidate_sha256")!=preferred.get("candidate_sha256"): raise ValueError("preferred candidate binding mismatch")
        if review.get("alternative_candidate_sha256")!=alternative.get("candidate_sha256"): raise ValueError("alternative candidate binding mismatch")
        selected=review.get("selected_for_verification")
        if type(selected) is not bool: raise ValueError("selected_for_verification must be bool")
        disposition=review.get("state_portfolio_disposition")
        if selected:
            if disposition!="SELECTED": raise ValueError("selected state disposition mismatch")
            selected_rows.append(review)
        elif disposition=="SELECTED": raise ValueError("unselected state cannot be SELECTED")
    ceiling=int(contract["selected_state_budget_ceiling"])
    if len(selected_rows)>ceiling: raise ValueError("selected-state ceiling exceeded")
    if out.get("selected_state_count")!=len(selected_rows): raise ValueError("selected-state count mismatch")
    if out.get("unused_state_budget")!=ceiling-len(selected_rows): raise ValueError("unused-state budget mismatch")
    sources=[str(row["source_state_sha256"]) for row in selected_rows]; candidates=[str(row["preferred_candidate_sha256"]) for row in selected_rows]
    if out.get("selected_source_state_sha256s")!=sources: raise ValueError("selected source-state list mismatch")
    if out.get("selected_candidate_sha256s")!=candidates: raise ValueError("selected candidate list mismatch")
    if len(sources)!=len(set(sources)) or len(candidates)!=len(set(candidates)): raise ValueError("selected identities not unique")
    counts=Counter(str(row["preferred_condition"]) for row in selected_rows); observed_counts=_map(out.get("selected_condition_counts"),"selected condition counts")
    if observed_counts.get("A2")!=counts["A2"] or observed_counts.get("A3")!=counts["A3"]: raise ValueError("selected condition-count mismatch")
    plan=_map(out.get("verification_plan"),"verification_plan")
    for field in ("paired_repetitions_per_state","branch_arms_per_repetition","branch_runs_per_state","selected_state_budget_ceiling"):
        if plan.get(field)!=contract.get(field): raise ValueError(f"verification-plan contract mismatch: {field}")
    if plan.get("outcome_adaptive_budget_change_allowed") is not False: raise ValueError("outcome-adaptive budget change forbidden")
    if plan.get("unfavorable_candidate_replacement_allowed") is not False: raise ValueError("candidate replacement forbidden")
    branch_runs=derived_branch_runs(len(selected_rows),contract)
    if plan.get("selected_branch_run_budget")!=branch_runs: raise ValueError("selected branch-run budget mismatch")
    resource=_map(out.get("resource_plan"),"resource_plan")
    if resource.get("expected_environment_branch_runs")!=branch_runs: raise ValueError("resource plan mismatch")
    memory=_map(out.get("memory_usage_summary"),"memory_usage_summary")
    if memory.get("memory_effect_authority") is not False: raise ValueError("Memory effect authority forbidden")
    training=_map(out.get("training_policy_at_pre"),"training_policy_at_pre")
    if training.get("status")!="HOLD_PENDING_VERIFIED_F0F1_MANIFEST": raise ValueError("PRE training must remain HOLD")
    if training.get("exact_training_mixture_frozen") is not False: raise ValueError("PRE cannot freeze exact training mixture")
    bottlenecks=_list(out.get("candidate_bottlenecks"),"candidate_bottlenecks"); selected_bottlenecks=[row for row in bottlenecks if isinstance(row,Mapping) and row.get("status")=="SELECTED"]
    if len(selected_bottlenecks)!=1: raise ValueError("exactly one principal bottleneck required")
    if selected_bottlenecks[0].get("candidate_id")!=out.get("selected_bottleneck_id"): raise ValueError("selected bottleneck identity mismatch")
    out["primary_record_sha256"]="0"*64; out["primary_record_sha256"]=domain_hash("STRONG_RESEARCHER_PRE_PRIMARY_V2",out,excluded_field="primary_record_sha256")
    return out

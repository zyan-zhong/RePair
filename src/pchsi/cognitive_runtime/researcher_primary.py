
from __future__ import annotations
from collections import Counter
from collections.abc import Mapping
import re
from pchsi.reference_loop.canonical import domain_hash
from pchsi.cognitive_runtime.schema_registry import validate_artifact

_SHA_RE=re.compile(r"^[0-9a-f]{64}$")
def _sha(v): return isinstance(v,str) and _SHA_RE.fullmatch(v) is not None
def _map(v,n):
    if not isinstance(v,Mapping): raise ValueError(f"{n} must be object")
    return v
def _list(v,n):
    if not isinstance(v,list): raise ValueError(f"{n} must be array")
    return v
def _sha_universe(value):
    out=set()
    def walk(v):
        if isinstance(v,Mapping):
            for x in v.values(): walk(x)
        elif isinstance(v,list):
            for x in v: walk(x)
        elif _sha(v): out.add(str(v))
    walk(value); return out

def finalize_strong_researcher_pre_primary_v1(value:Mapping[str,object],*,projection:Mapping[str,object])->dict[str,object]:
    forbidden={"human_pre_gate_satisfied","human_pre_content_visible","human_pre_hash_visible","human_pre_record_sha256"}
    if forbidden & set(projection): raise ValueError("primary PRE must not depend on Human PRE")
    blind=_map(projection.get("blind_input"),"blind_input")
    if blind.get("schema_id")!="STRONG_RESEARCHER_BLIND_PRE_INPUT_V2": raise ValueError("blind input schema mismatch")
    blind_sha=blind.get("blind_input_sha256"); hyd=blind.get("evidence_hydration_manifest_sha256")
    if not _sha(blind_sha) or not _sha(hyd): raise ValueError("blind identities invalid")
    if projection.get("blind_input_sha256")!=blind_sha or projection.get("evidence_hydration_manifest_sha256")!=hyd:
        raise ValueError("projection identity mismatch")
    out=dict(value)
    if out.get("schema_id")!="STRONG_RESEARCHER_PRE_PRIMARY_V1" or out.get("schema_version")!=1:
        raise ValueError("primary PRE schema mismatch")
    if out.get("round_id")!=blind.get("round_id"): raise ValueError("round mismatch")
    if out.get("blind_input_sha256")!=blind_sha or out.get("evidence_hydration_manifest_sha256")!=hyd:
        raise ValueError("output identity mismatch")
    if out.get("automatic_environment_effect_assignment") is not False: raise ValueError("Strong cannot assign effects")
    if out.get("effect_authority")!="INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY": raise ValueError("effect authority mismatch")
    if out.get("promotion_authority")!="DETERMINISTIC_INDEPENDENT_GATE_ONLY": raise ValueError("promotion authority mismatch")
    bottlenecks=_list(out.get("candidate_bottlenecks"),"candidate_bottlenecks")
    selected=[x for x in bottlenecks if isinstance(x,Mapping) and x.get("status")=="SELECTED"]
    if len(selected)!=1 or selected[0].get("candidate_id")!=out.get("selected_bottleneck_id"):
        raise ValueError("exactly one bottleneck required")
    allowed=_sha_universe(blind)
    for raw in bottlenecks:
        row=_map(raw,"bottleneck")
        for field in ("evidence_sha256s","counterevidence_sha256s"):
            refs=_list(row.get(field),field)
            if any(not _sha(x) for x in refs) or not set(refs)<=allowed: raise ValueError(f"{field} invalid")
    universe=_map(blind.get("registered_candidate_universe"),"candidate_universe")
    pairs=_list(universe.get("pair_table"),"pair_table")
    reviews=_list(out.get("state_reviews"),"state_reviews")
    if len(pairs)!=30 or len(reviews)!=30: raise ValueError("exact 30-pair review required")
    selected_rows=[]
    for i,(rr,rp) in enumerate(zip(reviews,pairs,strict=True)):
        r=_map(rr,"review"); p=_map(rp,"pair")
        if r.get("state_index")!=i or r.get("source_state_sha256")!=p.get("source_state_sha256"): raise ValueError("review order/binding mismatch")
        a2=_map(p.get("A2"),"A2"); a3=_map(p.get("A3"),"A3")
        pref=r.get("preferred_condition"); alt=r.get("alternative_condition")
        if {pref,alt}!={"A2","A3"}: raise ValueError("A2/A3 comparison required")
        preferred=a2 if pref=="A2" else a3; alternative=a2 if alt=="A2" else a3
        if r.get("preferred_candidate_sha256")!=preferred.get("candidate_sha256") or r.get("alternative_candidate_sha256")!=alternative.get("candidate_sha256"):
            raise ValueError("candidate binding mismatch")
        if r.get("preferred_x_disposition")!=preferred.get("formal_x_disposition") or r.get("alternative_x_disposition")!=alternative.get("formal_x_disposition"):
            raise ValueError("Formal-X binding mismatch")
        if r.get("selected_for_verification") is True:
            if r.get("state_portfolio_disposition")!="SELECTED": raise ValueError("selected disposition mismatch")
            selected_rows.append(r)
        elif r.get("state_portfolio_disposition")=="SELECTED": raise ValueError("unselected cannot be SELECTED")
    ceiling=_map(blind.get("required_output_contract"),"required_output_contract").get("selected_state_budget")
    if ceiling!=12 or len(selected_rows)>12: raise ValueError("12-state ceiling mismatch")
    if out.get("selected_state_count")!=len(selected_rows) or out.get("unused_state_budget")!=12-len(selected_rows):
        raise ValueError("selected-state counts mismatch")
    sources=[str(r["source_state_sha256"]) for r in selected_rows]
    candidates=[str(r["preferred_candidate_sha256"]) for r in selected_rows]
    if out.get("selected_source_state_sha256s")!=sources or out.get("selected_candidate_sha256s")!=candidates:
        raise ValueError("selected identity lists mismatch")
    if len(sources)!=len(set(sources)) or len(candidates)!=len(set(candidates)): raise ValueError("selected identities not unique")
    counts=Counter(str(r["preferred_condition"]) for r in selected_rows)
    observed=_map(out.get("selected_condition_counts"),"selected_condition_counts")
    if observed.get("A2")!=counts["A2"] or observed.get("A3")!=counts["A3"]: raise ValueError("condition counts mismatch")
    frozen=_map(blind.get("verification_budget_plan"),"verification_budget_plan")
    plan=_map(out.get("verification_plan"),"verification_plan")
    for field in ("paired_repetitions_per_state","branch_arms_per_repetition","branch_runs_per_state"):
        if plan.get(field)!=frozen.get(field): raise ValueError(f"budget mismatch {field}")
    if plan.get("total_branch_run_budget_ceiling")!=frozen.get("total_branch_run_budget"): raise ValueError("total budget mismatch")
    if plan.get("outcome_adaptive_budget_change_allowed") is not False or plan.get("unfavorable_candidate_replacement_allowed") is not False:
        raise ValueError("post-outcome budget/candidate adaptation forbidden")
    branch_runs=len(selected_rows)*int(frozen.get("branch_runs_per_state"))
    if plan.get("selected_branch_run_budget")!=branch_runs or branch_runs>int(frozen.get("total_branch_run_budget")):
        raise ValueError("branch budget mismatch")
    if _map(out.get("resource_plan"),"resource_plan").get("expected_environment_branch_runs")!=branch_runs:
        raise ValueError("resource plan mismatch")
    if _map(out.get("memory_usage_summary"),"memory_usage_summary").get("memory_effect_authority") is not False:
        raise ValueError("Memory effect authority forbidden")
    training=_map(out.get("training_policy_at_pre"),"training_policy_at_pre")
    if training.get("status")!="HOLD_PENDING_VERIFIED_F0F1_MANIFEST" or training.get("exact_training_mixture_frozen") is not False:
        raise ValueError("PRE training must remain HOLD")
    out["primary_record_sha256"]="0"*64
    out["primary_record_sha256"]=domain_hash("STRONG_RESEARCHER_PRE_PRIMARY_V1",out,excluded_field="primary_record_sha256")
    validate_artifact("STRONG_RESEARCHER_PRE_PRIMARY_V1",out)
    return out

def finalize_api_post_primary_v1(value:Mapping[str,object],*,projection:Mapping[str,object])->dict[str,object]:
    forbidden={"human_pre_record_sha256","human_post_record_sha256"}
    if forbidden&set(projection) or forbidden&set(value): raise ValueError("primary POST must not depend on Human records")
    env=projection.get("environment_result_package_sha256"); pre=projection.get("primary_pre_record_sha256")
    if not _sha(env) or not _sha(pre): raise ValueError("primary POST identities invalid")
    out=dict(value); out["environment_result_package_sha256"]=env; out["primary_pre_record_sha256"]=pre
    if out.get("schema_id")!="API_RESEARCHER_POST_PRIMARY_V1" or out.get("schema_version")!=1: raise ValueError("primary POST schema mismatch")
    if projection.get("round_id") is not None and out.get("round_id")!=projection.get("round_id"): raise ValueError("round mismatch")
    out["primary_record_sha256"]="0"*64
    out["primary_record_sha256"]=domain_hash("API_RESEARCHER_POST_PRIMARY_V1",out,excluded_field="primary_record_sha256")
    validate_artifact("API_RESEARCHER_POST_PRIMARY_V1",out)
    return out

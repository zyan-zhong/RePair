"""Condition-specific, coverage-aware Analyzer metrics and paired summaries."""

from __future__ import annotations
from collections import Counter
from collections.abc import Iterable,Mapping
import math, random

CONDITIONS=("A0","A1","A2","A3")
REGISTERED_SECONDARY_CONTRASTS=(("A1_VS_A0","A0","A1"),("A2_VS_A1","A1","A2"),("A3_VS_A2","A2","A3"))


def _ratio(n,d):
    return None if d==0 else n/d


def wilson95(n:int,d:int):
    if d==0: return None
    z=1.959963984540054
    p=n/d
    den=1+z*z/d
    center=(p+z*z/(2*d))/den
    half=z*math.sqrt(p*(1-p)/d+z*z/(4*d*d))/den
    return [max(0.0,center-half),min(1.0,center+half)]


def _binomial_probability(k:int,n:int,p:float=0.5)->float:
    return math.comb(n,k)*(p**k)*((1-p)**(n-k))


def exact_binomial_two_sided(k:int,n:int,p:float=0.5)->float|None:
    if n==0:
        return None
    if not 0<=k<=n:
        raise ValueError("invalid exact-binomial count")
    observed=_binomial_probability(k,n,p)
    total=sum(_binomial_probability(i,n,p) for i in range(n+1) if _binomial_probability(i,n,p)<=observed+1e-15)
    return min(1.0,total)


def holm_adjust(p_values:Mapping[str,float|None],*,alpha:float=0.05):
    finite=sorted(((name,p) for name,p in p_values.items() if p is not None),key=lambda x:(x[1],x[0]))
    m=len(finite); adjusted={}; running=0.0
    for rank,(name,p) in enumerate(finite):
        running=max(running,min(1.0,(m-rank)*p))
        adjusted[name]=min(1.0,running)
    for name,p in p_values.items():
        if p is None: adjusted[name]=None
    return {name:{"raw_p":p_values[name],"holm_adjusted_p":adjusted[name],"reject_at_alpha":None if adjusted[name] is None else adjusted[name]<=alpha} for name in p_values}


def _reason_census(rows,field):
    counter=Counter(str(r[field]) for r in rows if r.get(field))
    return [{"reason_code":key,"count":counter[key]} for key in sorted(counter)]


def _condition_report(rows, universe, protected_rows):
    u=set(universe)
    data=[r for r in rows if r["unit_id"] in u]
    if any(r.get("candidate_count",0) not in (0,1) for r in data):
        raise ValueError("K=1 violation in metric input")
    by={x:[r for r in data if r["unit_id"]==x] for x in universe}
    benefits={x for x,rs in by.items() if any(r.get("effect_label")=="Benefit" for r in rs)}
    harms={x for x,rs in by.items() if any(r.get("effect_label")=="Harm" for r in rs)}
    proposed={x for x,rs in by.items() if any(r.get("formal_candidate_proposed") for r in rs)}
    available={x for x,rs in by.items() if any(r.get("protocol_complete") for r in rs)}
    proposed_rows=[r for r in data if r.get("formal_candidate_proposed")]
    steps=sum(int(r.get("formal_verifier_env_steps",0)) for r in data)
    method_failure_rows=[r for r in data if r.get("method_failure_reason")]
    infrastructure_rows=[r for r in data if r.get("infrastructure_unavailable")]
    for row in infrastructure_rows:
        if not row.get("infrastructure_reason"):
            raise ValueError("infrastructure incident lacks explicit reason")
    method_failures={r["unit_id"] for r in method_failure_rows}
    infra={r["unit_id"] for r in infrastructure_rows}
    if method_failures & infra:
        raise ValueError("method failure and infrastructure sets overlap")
    p=[r for r in protected_rows if r["unit_id"] in {x["unit_id"] for x in protected_rows}]
    p_units={r["unit_id"] for r in p}
    p_harm={r["unit_id"] for r in p if r.get("effect_label")=="Harm"}
    curve=[]; repaired=set(); spent=0
    for r in sorted(data,key=lambda x:(x["frozen_priority"],x["unit_id"])):
        spent+=int(r.get("formal_verifier_env_steps",0))
        if r.get("effect_label")=="Benefit": repaired.add(r["unit_id"])
        curve.append({"environment_steps":spent,"repaired_unique_units":len(repaired)})
    out={
        "EVRY_reg":{"numerator":len(benefits),"denominator":len(universe)},
        "EVRY_avail":{"numerator":len(benefits & available),"denominator":len(available)},
        "failure_cohort_harm":{"numerator":len(harms),"denominator":len(universe)},
        "protected_cohort_harm":{"numerator":len(p_harm),"denominator":len(p_units)},
        "ProposalCoverage":{"numerator":len(proposed),"denominator":len(universe)},
        "VBP":{
            "numerator":sum(r.get("effect_label")=="Benefit" for r in proposed_rows),
            "denominator":len(proposed_rows),
        },
        "verification_cost":{"environment_steps":steps,
            "repaired_unique_unit_count":len(benefits),
            "steps_per_repaired_unique_unit":_ratio(steps,len(benefits))},
        "EVRY_at_B":{"primary_budget_unit":"FORMAL_VERIFIER_ENVIRONMENT_STEPS",
                     "points":curve},
        "method_failure_unit_ids":sorted(method_failures),
        "infrastructure_unavailable_unit_ids":sorted(infra),
        "method_failure_reason_census":_reason_census(method_failure_rows,"method_failure_reason"),
        "infrastructure_reason_census":_reason_census(infrastructure_rows,"infrastructure_reason"),
    }
    for name in ("EVRY_reg","EVRY_avail","failure_cohort_harm",
                 "protected_cohort_harm","ProposalCoverage","VBP"):
        r=out[name]; r["value"]=_ratio(r["numerator"],r["denominator"])
        r["wilson95"]=wilson95(r["numerator"],r["denominator"])
    return out


def aggregate_repair_discovery_by_condition(
    rows: Iterable[Mapping[str,object]],
    *,
    registered_universe: Iterable[str],
    protected_rows: Iterable[Mapping[str,object]]=(),
)->dict[str,object]:
    universe=list(registered_universe)
    if len(universe)!=len(set(universe)):
        raise ValueError("duplicate U_reg unit")
    data=list(rows)
    unknown={r["unit_id"] for r in data}-set(universe)
    if unknown:
        raise ValueError(f"metric rows outside U_reg: {sorted(unknown)}")
    result={}
    for condition in CONDITIONS:
        crows=[r for r in data if r["condition_id"]==condition]
        # Every unit-condition must be represented once at the method-result level.
        counts={u:sum(r["unit_id"]==u for r in crows) for u in universe}
        if any(v!=1 for v in counts.values()):
            raise ValueError(f"incomplete/duplicate condition rows for {condition}")
        prows=[r for r in protected_rows if r["condition_id"]==condition]
        result[condition]=_condition_report(crows,universe,prows)
    return {"schema_id":"ANALYZER_METRIC_REPORT_V1","conditions":result}


def paired_binary_summary(rows,*,condition_a,condition_b,success_label="Benefit"):
    data=list(rows); by={}
    for r in data:
        if r["condition_id"] in {condition_a,condition_b}:
            by.setdefault(r["unit_id"],{})[r["condition_id"]]=r.get("effect_label")
    complete={u:x for u,x in by.items() if set(x)=={condition_a,condition_b}}
    n=len(complete)
    a_success=sum(x[condition_a]==success_label for x in complete.values())
    b_success=sum(x[condition_b]==success_label for x in complete.values())
    gain=sum(x[condition_a]!=success_label and x[condition_b]==success_label for x in complete.values())
    loss=sum(x[condition_a]==success_label and x[condition_b]!=success_label for x in complete.values())
    p_a=_ratio(a_success,n); p_b=_ratio(b_success,n)
    return {
        "paired_unit_count":n,
        "condition_a_success_count":a_success,
        "condition_b_success_count":b_success,
        "condition_a_risk":p_a,
        "condition_b_risk":p_b,
        "risk_difference_b_minus_a":None if p_a is None else p_b-p_a,
        "relative_risk_b_over_a":None if p_a in (None,0.0) else p_b/p_a,
        "discordant_a0_b1":gain,
        "discordant_a1_b0":loss,
        "mcnemar_exact_denominator":gain+loss,
        "mcnemar_exact_p":exact_binomial_two_sided(min(gain,loss),gain+loss,0.5),
    }


def clustered_bootstrap_difference(
    rows,*,condition_a,condition_b,iterations=2000,seed=0
):
    data=list(rows); units=sorted({r["unit_id"] for r in data})
    lookup={(r["unit_id"],r["condition_id"]):r.get("effect_label")=="Benefit" for r in data}
    rng=random.Random(seed); diffs=[]
    for _ in range(iterations):
        sample=[rng.choice(units) for _ in units]
        a=sum(lookup.get((u,condition_a),False) for u in sample)/len(sample)
        b=sum(lookup.get((u,condition_b),False) for u in sample)/len(sample)
        diffs.append(b-a)
    diffs.sort()
    lo=diffs[int(0.025*(iterations-1))]
    hi=diffs[int(0.975*(iterations-1))]
    return [lo,hi]


def registered_secondary_contrast_report(rows,*,iterations=2000,seed=0,alpha=0.05):
    summaries={}; raw_p={}
    for contrast_id,condition_a,condition_b in REGISTERED_SECONDARY_CONTRASTS:
        summary=paired_binary_summary(rows,condition_a=condition_a,condition_b=condition_b)
        summary["clustered_bootstrap_risk_difference_95"]=clustered_bootstrap_difference(rows,condition_a=condition_a,condition_b=condition_b,iterations=iterations,seed=seed)
        summaries[contrast_id]=summary; raw_p[contrast_id]=summary["mcnemar_exact_p"]
    adjusted=holm_adjust(raw_p,alpha=alpha)
    for contrast_id in summaries: summaries[contrast_id]["multiplicity"]=adjusted[contrast_id]
    return {"multiplicity_family":"ANALYZER_SECONDARY_CONTRASTS","adjustment":"HOLM","alpha":alpha,"contrasts":summaries}

"""Deterministic task-family-balanced failure/success gold-panel selection."""

from __future__ import annotations
from collections import defaultdict
from collections.abc import Iterable,Mapping


FAILURE_LABELS=(
    "SINGLE_CANDIDATE","MULTI_CAUSAL","INDETERMINATE","INSUFFICIENT_EVIDENCE"
)


def _round_robin(rows,limit):
    by=defaultdict(list)
    for row in rows:
        by[row.get("task_family")].append(dict(row))
    for family in by:
        by[family].sort(
            key=lambda x:(-int(x.get("failure_burden",0)),
                          x["frozen_order"],x["task_id"])
        )
    families=sorted(by,key=lambda x:"" if x is None else str(x))
    out=[]; used=set()
    while len(out)<limit:
        progressed=False
        for family in families:
            while by[family] and by[family][0]["gamefile_sha256"] in used:
                by[family].pop(0)
            if by[family] and len(out)<limit:
                row=by[family].pop(0)
                used.add(row["gamefile_sha256"]); out.append(row); progressed=True
        if not progressed: break
    return out


def select_gold_panels(rows:Iterable[Mapping[str,object]],*,failure_count=36,success_count=12):
    data=list(rows)
    failure=_round_robin([r for r in data if r["outcome"]=="FAILURE"],failure_count)
    used={r["gamefile_sha256"] for r in failure}
    success=_round_robin(
        [r for r in data if r["outcome"]=="SUCCESS" and r["gamefile_sha256"] not in used],
        success_count,
    )
    return {
        "failure":failure,"success":success,
        "annotation_contract":{
            "failure_labels":list(FAILURE_LABELS),
            "supports_multiple_error_instances":True,
            "failure_fields":[
                "relevant_start","trigger","critical_window","resolution_status",
                "terminal_footprint","candidate_principal","alternative_error_instances",
            ],
            "success_fields":[
                "progress_events","necessary_transitions","useful_exploration",
                "self_recovery","candidate_redundancy","regression_guards",
            ],
            "blind_evaluator_required":True,
        },
    }

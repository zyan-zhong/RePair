#!/usr/bin/env python3
"""Freeze a panel-size-aware, outcome-blind Memory decision rule.

The formula is computed only from the pre-outcome registered cell manifest:
- all registered comparison groups must be complete;
- task-success net gain must be at least 5 percentage points (ceil, >=1 pair);
- FM3/last-round usable coverage and correct exposure must reach 10% (ceil);
- wrong/unsafe exposure is never allowed;
- harm tolerance is at most 1% of paired groups (floor).
"""
from __future__ import annotations
import argparse, hashlib, math, os
from pathlib import Path
from pchsi.evaluation.canonical_evidence import canonical_json_bytes, strict_json_loads
from pchsi.memory.scientific_decision import STAGE_1B, STAGE_2, STAGE_3


def rows(path: Path) -> list[dict[str, object]]:
    result=[]
    for raw in path.read_bytes().splitlines(keepends=True):
        if raw:
            value=strict_json_loads(raw)
            if not isinstance(value,dict) or canonical_json_bytes(value)!=raw:
                raise SystemExit("STOP=RULE_CELL_MANIFEST_NOT_CANONICAL")
            result.append(value)
    return result


def dsha(value: dict[str, object]) -> str:
    payload=dict(value); payload.pop("rule_sha256",None)
    return hashlib.sha256(b"FAILURE_MEMORY_REGISTERED_DECISION_RULE_V1\0"+canonical_json_bytes(payload)).hexdigest()


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--stage",required=True,choices=(STAGE_1B,STAGE_2,STAGE_3)); p.add_argument("--cell-manifest",required=True); p.add_argument("--primary-split"); p.add_argument("--output",required=True); a=p.parse_args()
    data=rows(Path(a.cell_manifest))
    selected=data
    if a.stage==STAGE_3:
        if a.primary_split not in {"VALID_SEEN","VALID_UNSEEN"}: raise SystemExit("STOP=STAGE3_PRIMARY_SPLIT_REQUIRED")
        selected=[r for r in data if r.get("split")==a.primary_split]
    elif a.primary_split is not None:
        raise SystemExit("STOP=PRIMARY_SPLIT_ONLY_STAGE3")
    if not selected: raise SystemExit("STOP=NO_PRIMARY_CELLS")
    groups={str(r["comparison_group_id"]) for r in selected}
    pair_count=len(groups)
    if a.stage==STAGE_2:
        rounds=sorted({int(r["round_index"]) for r in selected}); minimum_round_count=len(rounds)
        if len(rounds)<2 or rounds[0]!=0: raise SystemExit("STOP=STAGE2_ROUNDS_INVALID")
        coverage_population=sum(int(r["round_index"])==rounds[-1] for r in selected)
    else:
        minimum_round_count=0; coverage_population=sum(r["condition"]=="FM3_GATED_PRESCRIPTIVE" for r in selected)
    value={"schema_id":"FAILURE_MEMORY_REGISTERED_DECISION_RULE_V1","schema_version":1,"rule_sha256":"0"*64,"stage":a.stage,"primary_endpoint":"TASK_SUCCESS","primary_split":a.primary_split,"minimum_complete_pairs":pair_count,"minimum_absolute_success_gain":max(1,math.ceil(pair_count*0.05)),"minimum_coverage_count":max(1,math.ceil(coverage_population*0.10)),"minimum_correct_exposure_count":max(1,math.ceil(coverage_population*0.10)),"maximum_harm_count":math.floor(pair_count*0.01),"maximum_wrong_memory_count":0,"maximum_unsafe_memory_count":0,"minimum_round_count":minimum_round_count,"confidence_interval_method":"EXACT_TASK_PAIRED_COUNTS_V1","multiple_comparisons_policy":"REGISTERED_PRIMARY_COMPARISONS_ONLY_V1"}
    value["rule_sha256"]=dsha(value)
    out=Path(a.output)
    if out.exists() or out.is_symlink(): raise SystemExit("STOP=RULE_OUTPUT_EXISTS")
    out.parent.mkdir(parents=True,exist_ok=True); raw=canonical_json_bytes(value); fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as h: h.write(raw); h.flush(); os.fsync(h.fileno())
    print("FAILURE_MEMORY_OUTCOME_BLIND_DECISION_RULE_V1_PASS"); print("RULE_SHA256="+value["rule_sha256"]); print("PAIR_COUNT="+str(pair_count)); print("MINIMUM_ABSOLUTE_SUCCESS_GAIN="+str(value["minimum_absolute_success_gain"])); print("MINIMUM_COVERAGE_COUNT="+str(value["minimum_coverage_count"]))
if __name__=="__main__": main()

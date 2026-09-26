#!/usr/bin/env python3
"""Sequentially execute/resume Memory-owned stages and seal closure outputs.

For Slurm mode, at most one stage is submitted per invocation. Re-running the
same command after a stage finishes validates and aggregates that stage, then
advances to the next. This prevents Stage 3 from racing ahead of Stage 2.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

from pchsi.evaluation.canonical_evidence import canonical_json_bytes, strict_json_loads

APPROVAL = "EXECUTION_APPROVED_FAILURE_MEMORY_LIVE_STAGES_V1"


def canonical_object(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise SystemExit("STOP=CLOSURE_MANIFEST_NOT_REGULAR:" + str(path))
    raw = path.read_bytes(); value = strict_json_loads(raw)
    if not isinstance(value, dict) or raw not in {canonical_json_bytes(value), canonical_json_bytes(value)}:
        raise SystemExit("STOP=CLOSURE_MANIFEST_NOT_CANONICAL:" + str(path))
    return value


def check_binding(row: dict[str, object]) -> Path:
    if set(row) != {"path", "file_sha256", "size_bytes"}:
        raise SystemExit("STOP=CLOSURE_BOUND_INPUT_FIELDS")
    path = Path(str(row["path"]))
    if path.is_symlink() or not path.is_file():
        raise SystemExit("STOP=CLOSURE_BOUND_INPUT_MISSING:" + str(path))
    raw = path.read_bytes()
    if len(raw) != row["size_bytes"] or hashlib.sha256(raw).hexdigest() != row["file_sha256"]:
        raise SystemExit("STOP=CLOSURE_BOUND_INPUT_CHANGED:" + str(path))
    return path


def run(command: list[str]) -> None:
    print("RUN=" + " ".join(command), flush=True)
    subprocess.run(command, check=True)


def parse_cells(path: Path) -> list[str]:
    ids=[]
    for raw in path.read_bytes().splitlines(keepends=True):
        if raw:
            row=strict_json_loads(raw)
            if not isinstance(row,dict) or canonical_json_bytes(row)!=raw:
                raise SystemExit("STOP=CLOSURE_CELL_MANIFEST_NOT_CANONICAL")
            ids.append(str(row["cell_id"]))
    return ids


def cells_complete(*, live_root: Path, manifest: dict[str, object]) -> bool:
    cell_manifest = Path(str(manifest["operational_paths"]["cell_manifest"]))
    root = live_root / str(manifest["stage"]) / str(manifest["manifest_sha256"]) / "cells"
    for cell_id in parse_cells(cell_manifest):
        cell = root / cell_id
        if not (cell / "CELL_TERMINAL_RECEIPT_V1.json").is_file():
            return False
        if not (cell / "CELL_SCIENTIFIC_RESULT_V1.json").is_file():
            return False
        for name in ("POLICY_MEMORY_PACK_V1.json", "ANALYZER_MEMORY_PACK_V1.json", "RESEARCHER_MEMORY_PACK_V1.json"):
            if not (cell / name).is_file():
                return False
    return True


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--closure-manifest",required=True); p.add_argument("--phase",choices=("preflight","execute","finalize","all"),default="all"); a=p.parse_args()
    manifest_path=Path(a.closure_manifest); value=canonical_object(manifest_path)
    if value.get("schema_id")!="FAILURE_MEMORY_CLOSURE_EXECUTION_MANIFEST_V1" or value.get("schema_version")!=1:
        raise SystemExit("STOP=CLOSURE_MANIFEST_SCHEMA")
    expected=hashlib.sha256(b"FAILURE_MEMORY_CLOSURE_EXECUTION_MANIFEST_V1\0"+canonical_json_bytes({k:v for k,v in value.items() if k!="closure_execution_manifest_sha256"})).hexdigest()
    if value.get("closure_execution_manifest_sha256")!=expected: raise SystemExit("STOP=CLOSURE_MANIFEST_SELF_HASH")
    if value.get("scientific_execution_authorized") is not False or value.get("q4_analyzer_execution_included") is not False or value.get("q5_policy_training_included") is not False:
        raise SystemExit("STOP=CLOSURE_MANIFEST_SCOPE_OR_AUTHORITY_FLAGS")
    inputs={name:check_binding(row) for name,row in value["inputs"].items()}
    here=Path(__file__).resolve().parent; live_root=Path(value["live_output_root"]); closure_root=Path(value["closure_output_root"])
    stages=(("stage1b",inputs["stage1b_execution_manifest"]),("stage2",inputs["stage2_execution_manifest"]),("stage3",inputs["stage3_execution_manifest"]))
    for _,m in stages:
        run([sys.executable,str(here/"run_memory_live_cells_v2.py"),"--manifest",str(m),"--output-root",str(live_root),"--mode","preflight"])
    if a.phase=="preflight": print("FAILURE_MEMORY_CLOSURE_PREFLIGHT_V2_PASS"); return
    if a.phase in {"execute","all"} and os.environ.get("FAILURE_MEMORY_LIVE_EXECUTION_APPROVAL")!=APPROVAL:
        raise SystemExit("STOP=LIVE_EXECUTION_APPROVAL_MISSING")

    closure_root.mkdir(parents=True,exist_ok=True)
    authority_paths={}
    for name,m_path in stages:
        m=canonical_object(m_path)
        stage_root=live_root/str(m["stage"])/str(m["manifest_sha256"])
        authority_root=closure_root/"stage_authorities"/name
        authority_path=authority_root/"RESULT_AUTHORITY_V2.json"
        if authority_path.is_file() and not authority_path.is_symlink():
            authority_paths[name]=authority_path
            continue
        complete=cells_complete(live_root=live_root,manifest=m)
        if not complete:
            if a.phase=="finalize":
                print("FAILURE_MEMORY_STAGE_PENDING="+name); return
            mode="run-local" if value["execution_mode"]=="local" else "submit-slurm"
            if mode=="submit-slurm" and (stage_root/"slurm_array.sh").exists():
                print("FAILURE_MEMORY_STAGE_SLURM_ALREADY_SUBMITTED_PENDING="+name); return
            command=[sys.executable,str(here/"run_memory_live_cells_v2.py"),"--manifest",str(m_path),"--output-root",str(live_root),"--mode",mode]
            if mode=="submit-slurm": command += ["--max-parallel",str(value["max_parallel"])]
            run(command)
            if mode=="submit-slurm":
                print("FAILURE_MEMORY_STAGE_SLURM_SUBMITTED_PENDING="+name); return
            complete=cells_complete(live_root=live_root,manifest=m)
            if not complete: raise SystemExit("STOP=LOCAL_STAGE_DID_NOT_COMPLETE:"+name)
        cells_root=stage_root/"cells"
        run([sys.executable,str(here/"aggregate_memory_live_stage_v2.py"),"--execution-manifest",str(m_path),"--cells-root",str(cells_root),"--output-dir",str(authority_root)])
        authority_paths[name]=authority_path
        if a.phase=="execute":
            print("FAILURE_MEMORY_STAGE_EXECUTED_AND_AGGREGATED="+name)
            return

    matrix_path=closure_root/"FAILURE_MEMORY_Q1_Q5_MATRIX_V1.json"
    if not matrix_path.exists():
        run([sys.executable,str(here/"audit_memory_scientific_program_v1.py"),"--a0-result",str(inputs["a0_result"]),"--b-result",str(inputs["b_result"]),"--stage0-result",str(inputs["stage0_result"]),"--stage1b-authority",str(authority_paths["stage1b"]),"--stage2-authority",str(authority_paths["stage2"]),"--stage3-authority",str(authority_paths["stage3"]),"--expected-fixed-head",value["fixed_code_head"],"--expected-scientific-program-sha256",value["scientific_program_sha256"],"--output",str(matrix_path)])
    paper_root=closure_root/"paper_evidence"
    if not paper_root.exists():
        run([sys.executable,str(here/"export_memory_paper_evidence_v2.py"),"--stage0-result",str(inputs["stage0_result"]),"--a0-result",str(inputs["a0_result"]),"--b-result",str(inputs["b_result"]),"--stage1b-authority",str(authority_paths["stage1b"]),"--stage2-authority",str(authority_paths["stage2"]),"--stage3-authority",str(authority_paths["stage3"]),"--q1-q5-matrix",str(matrix_path),"--expected-fixed-head",value["fixed_code_head"],"--expected-scientific-program-sha256",value["scientific_program_sha256"],"--output-dir",str(paper_root)])
    handoff_root=closure_root/"handoff_and_closure"
    if not handoff_root.exists():
        run([sys.executable,str(here/"build_memory_q4_q5_handoff_v1.py"),"--stage0-result",str(inputs["stage0_result"]),"--a0-result",str(inputs["a0_result"]),"--b-result",str(inputs["b_result"]),"--stage1b-authority",str(authority_paths["stage1b"]),"--stage2-authority",str(authority_paths["stage2"]),"--stage3-authority",str(authority_paths["stage3"]),"--q1-q5-matrix",str(matrix_path),"--paper-evidence-manifest",str(paper_root/"PAPER_EVIDENCE_MANIFEST_V1.json"),"--expected-fixed-head",value["fixed_code_head"],"--expected-scientific-program-sha256",value["scientific_program_sha256"],"--output-dir",str(handoff_root)])
    print("FAILURE_MEMORY_V1_MEMORY_OWNED_CLOSURE_V2_PASS"); print("CLOSURE_ROOT="+str(closure_root)); print("Q4=HANDOFF_ONLY_NOT_EXECUTED"); print("Q5=HANDOFF_ONLY_NOT_EXECUTED")

if __name__=="__main__": main()

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

from pchsi.evaluation.canonical_evidence import canonical_json_bytes, strict_json_loads
from pchsi.memory.scientific_authority import load_scientific_result_authority_v2
from pchsi.memory.scientific_decision import FM0, FM1, FM2, FM3, STAGE_1B

SCRIPTS = Path(__file__).parents[2] / "scripts" / "memory"


def dsha(domain: str, value: dict, field: str) -> str:
    payload = dict(value); payload.pop(field, None)
    return hashlib.sha256(domain.encode() + b"\0" + canonical_json_bytes(payload)).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def make_rule(path: Path) -> dict:
    value = {
        "schema_id": "FAILURE_MEMORY_REGISTERED_DECISION_RULE_V1",
        "schema_version": 1, "rule_sha256": "0" * 64,
        "stage": STAGE_1B, "primary_endpoint": "TASK_SUCCESS", "primary_split": None,
        "minimum_complete_pairs": 1, "minimum_absolute_success_gain": 1,
        "minimum_coverage_count": 1, "minimum_correct_exposure_count": 1,
        "maximum_harm_count": 0, "maximum_wrong_memory_count": 0,
        "maximum_unsafe_memory_count": 0, "minimum_round_count": 0,
        "confidence_interval_method": "EXACT_TASK_PAIRED_COUNTS_V1",
        "multiple_comparisons_policy": "REGISTERED_PRIMARY_COMPARISONS_ONLY_V1",
    }
    value["rule_sha256"] = dsha("FAILURE_MEMORY_REGISTERED_DECISION_RULE_V1", value, "rule_sha256")
    write_json(path, value); return value


def make_executor(path: Path) -> None:
    path.write_text(r'''#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, os
from pathlib import Path
from pchsi.evaluation.canonical_evidence import canonical_json_bytes, strict_json_loads

def dsha(domain,value,field):
 p=dict(value); p.pop(field,None); return hashlib.sha256(domain.encode()+b"\0"+canonical_json_bytes(p)).hexdigest()
def w(path,value):
 path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(canonical_json_bytes(value))
def main():
 p=argparse.ArgumentParser(); p.add_argument("--execution-manifest"); p.add_argument("--cell-manifest"); p.add_argument("--cell-index",type=int); p.add_argument("--output-dir"); a=p.parse_args()
 manifest=strict_json_loads(Path(a.execution_manifest).read_bytes()); rows=[strict_json_loads(x) for x in Path(a.cell_manifest).read_bytes().splitlines() if x]; row=rows[a.cell_index]; root=Path(a.output_dir); condition=row["condition"]
 exposed=condition!="FM0_NO_MEMORY"
 if condition=="FM1_MATCHED_RAW_EPISODIC":
  policy_payload={
   "relevant_start":{
    "model_call_index":2,
    "pre_observation":"You are in a room.",
    "interface_feedback_before":None,
   },
   "events":[{
    "model_call_index":2,
    "pre_observation":"You are in a room.",
    "literal_action":"look",
    "normalized_action":"look",
    "submitted_environment_action":"look",
    "execution_status":"EXECUTED",
    "interface_feedback_before":None,
    "resulting_observation":"You see a table.",
    "visible_state_change_disposition":"STATE_CHANGED",
   }],
  }
 elif exposed:
  policy_payload={"activation_cues":[],"failure_pattern":"pattern","revalidate_on":[],"release_cues":[],"non_applicability_cues":[],"recovery_procedure":[]}
 else:
  policy_payload=None
 payloads={
  "policy": policy_payload,
  "analyzer": {},
  "researcher": {"heldout_aggregate_metrics":{},"train_side_records":[{"source_partition":"TRAIN_MEMORY_SOURCE"}]},
 }
 filenames={"policy":"POLICY_MEMORY_PACK_V1.json","analyzer":"ANALYZER_MEMORY_PACK_V1.json","researcher":"RESEARCHER_MEMORY_PACK_V1.json"}
 pack_shas={}
 for role,payload in payloads.items():
  pack={"schema_id":"FAILURE_MEMORY_ROLE_PACK_V1","schema_version":1,"role":role.upper(),"cell_id":row["cell_id"],"execution_manifest_sha256":manifest["manifest_sha256"],"payload":payload,"pack_sha256":"0"*64}; pack["pack_sha256"]=dsha("FAILURE_MEMORY_ROLE_PACK_V1",pack,"pack_sha256"); pp=root/filenames[role]; w(pp,pack); pack_shas[role]=hashlib.sha256(pp.read_bytes()).hexdigest()
 result={"schema_id":"FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1","schema_version":1,"cell_result_sha256":"0"*64,**row,"execution_manifest_sha256":manifest["manifest_sha256"],"stage":manifest["stage"],"success":exposed,"memory_exposed":exposed,"correct_memory_exposure":exposed,"wrong_memory_exposure":False,"unsafe_memory_exposure":False,"harm_observed":False,"abstained":not exposed,"old_failure_disposition":"AVOIDED" if exposed else "REPEATED","model_calls":1,"environment_steps":1,"memory_tokens":10 if exposed else 0,"prompt_tokens":100,"latency_ms":5,"evaluation_writeback_attempted":False,"same_round_memory_readback":False,"role_pack_sha256s":pack_shas}; result["cell_result_sha256"]=dsha("FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1",result,"cell_result_sha256"); w(root/"CELL_SCIENTIFIC_RESULT_V1.json",result)
 receipt={"schema_id":"FAILURE_MEMORY_CELL_TERMINAL_RECEIPT_V1","schema_version":1,"receipt_sha256":"0"*64,"cell_id":row["cell_id"],"execution_manifest_sha256":manifest["manifest_sha256"],"cell_result_sha256":result["cell_result_sha256"],"cell_complete":True,"scientific_outcome_produced":True,"infrastructure_error":False}; receipt["receipt_sha256"]=dsha("FAILURE_MEMORY_CELL_TERMINAL_RECEIPT_V1",receipt,"receipt_sha256"); w(root/"CELL_TERMINAL_RECEIPT_V1.json",receipt)
if __name__=="__main__": main()
''', encoding="utf-8")
    path.chmod(0o700)


def test_manifest_runner_aggregator_end_to_end(tmp_path: Path) -> None:
    ids = tmp_path / "ids"; ids.mkdir()
    artifacts = {}
    for name in ("scientific_protocol", "runtime_identity", "policy_identity", "environment_identity", "schedule", "snapshot"):
        path = ids / (name + ".json"); write_json(path, {"name": name}); artifacts[name] = path

    fm1_payload = {
        "relevant_start": {
            "model_call_index": 2,
            "pre_observation": "You are in a room.",
            "interface_feedback_before": None,
        },
        "events": [{
            "model_call_index": 2,
            "pre_observation": "You are in a room.",
            "literal_action": "look",
            "normalized_action": "look",
            "submitted_environment_action": "look",
            "execution_status": "EXECUTED",
            "interface_feedback_before": None,
            "resulting_observation": "You see a table.",
            "visible_state_change_disposition": "STATE_CHANGED",
        }],
    }
    template = ids / "representation_template.json"
    write_json(
        template,
        {
            "arms": [{
                "arm_id": "M1",
                "policy_visible_payload": fm1_payload,
            }],
        },
    )
    binding = ids / "a0_binding.json"
    write_json(
        binding,
        {
            "sources": [{
                "source_state_id": "task-1",
                "representation_template_path": str(template.resolve()),
                "representation_template_file_sha256": hashlib.sha256(
                    template.read_bytes()
                ).hexdigest(),
            }],
        },
    )
    panel = ids / "panel.json"
    write_json(
        panel,
        {
            "entries": [{
                "task_id": "task-1",
                "a0_binding_path": str(binding.resolve()),
                "representation_template_path": str(template.resolve()),
            }],
        },
    )
    artifacts["panel"] = panel

    program = ids / "scientific_program.json"; program_sha = "9" * 64; write_json(program, {"program_sha256": program_sha}); artifacts["scientific_program"] = program
    rule = ids / "rule.json"; make_rule(rule)
    cells = ids / "cells.jsonl"
    snapshot_sha = hashlib.sha256(artifacts["snapshot"].read_bytes()).hexdigest()
    rows = [{"cell_id":f"g1-{condition}","comparison_group_id":"g1","condition":condition,"round_index":None,"split":"TRAIN_RETRIEVAL_DEV","task_id":"task-1","task_family":"pick_and_place_simple","snapshot_sha256":snapshot_sha} for condition in (FM0,FM1,FM2,FM3)]
    cells.write_bytes(b"".join(canonical_json_bytes(row) for row in rows))
    executor = ids / "executor.py"; make_executor(executor)
    manifest = tmp_path / "execution_manifest.json"
    command = [sys.executable, str(SCRIPTS / "build_memory_live_execution_manifest_v2.py"), "--stage", STAGE_1B, "--fixed-head", "f"*40, "--scientific-protocol", str(artifacts["scientific_protocol"]), "--scientific-program", str(program), "--runtime-identity", str(artifacts["runtime_identity"]), "--policy-identity", str(artifacts["policy_identity"]), "--environment-identity", str(artifacts["environment_identity"]), "--panel", str(artifacts["panel"]), "--schedule", str(artifacts["schedule"]), "--cell-manifest", str(cells), "--cell-executor", str(executor), "--decision-rule", str(rule), "--snapshot", str(artifacts["snapshot"]), "--executor-code-approval", "CODE_APPROVED_FAILURE_MEMORY_LIVE_CELL_EXECUTOR_V1", "--output", str(manifest)]
    subprocess.run(command, check=True)
    env = dict(os.environ); env["FAILURE_MEMORY_LIVE_EXECUTION_APPROVAL"] = "EXECUTION_APPROVED_FAILURE_MEMORY_LIVE_STAGES_V1"
    live = tmp_path / "live"
    subprocess.run([sys.executable, str(SCRIPTS / "run_memory_live_cells_v2.py"), "--manifest", str(manifest), "--output-root", str(live), "--mode", "run-local"], check=True, env=env)
    manifest_value = strict_json_loads(manifest.read_bytes())
    cells_root = live / STAGE_1B / manifest_value["manifest_sha256"] / "cells"
    authority_root = tmp_path / "authority"
    subprocess.run([sys.executable, str(SCRIPTS / "aggregate_memory_live_stage_v2.py"), "--execution-manifest", str(manifest), "--cells-root", str(cells_root), "--output-dir", str(authority_root)], check=True)
    validated = load_scientific_result_authority_v2(path=authority_root/"RESULT_AUTHORITY_V2.json", expected_stage=STAGE_1B, expected_fixed_code_head="f"*40, expected_scientific_program_sha256=program_sha)
    assert validated.disposition("Q1") == "SUPPORTED"
    assert validated.disposition("Q2") == "NOT_SUPPORTED"
    assert validated.disposition("Q3") == "SUPPORTED"

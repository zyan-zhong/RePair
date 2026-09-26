#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path
from pchsi.research_intelligence.product_isolation import assert_separate_roots

REQUIRED = (
 "docs/research/HUMAN_TRAINING_RESEARCHER_TEMPLATE_V2.md",
 "src/pchsi/cognitive_runtime/researcher.py",
 "configs/cognitive_runtime/schemas/human_researcher_pre_v1.json",
 "configs/cognitive_runtime/schemas/human_researcher_post_v1.json",
 "configs/cognitive_runtime/schemas/api_researcher_pre_shadow_v1.json",
 "configs/cognitive_runtime/schemas/api_researcher_post_shadow_v1.json",
 "experiments/formal_analyzer/pi1_reference_v1/EXPERIMENT_MANIFEST.json",
 "experiments/formal_analyzer/pi1_reference_v1/RESULT_MANIFEST.json",
 "docs/protocol/F0F1_REPAIR_VERIFICATION_V2.md",
 "docs/project/REFERENCE_LOOP_WORKFLOW_COORDINATION_V1.md",
)

def sha(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest()
def canon(v): return (json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
def write(path: Path, v):
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists(): raise FileExistsError(path)
 path.write_bytes(canon(v) if not isinstance(v,str) else v.encode())

def main():
 p=argparse.ArgumentParser(); p.add_argument('--repo',required=True); p.add_argument('--output-dir',required=True)
 p.add_argument('--expected-head',required=True); p.add_argument('--round-id',required=True); p.add_argument('--parent-policy-id',required=True)
 p.add_argument('--human-scientific-root',required=True); p.add_argument('--benchmark-scientific-root',required=True); a=p.parse_args()
 repo=Path(a.repo).resolve(); out=Path(a.output_dir).resolve()
 assert_separate_roots(Path(a.human_scientific_root),Path(a.benchmark_scientific_root))
 head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
 if head!=a.expected_head: raise SystemExit('STOP=HEAD_MISMATCH')
 if subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip(): raise SystemExit('STOP=DIRTY')
 rows=[]
 for rel in REQUIRED:
  path=repo/rel; ok=path.is_file() and not path.is_symlink()
  rows.append({'relative_path':rel,'status':'PRESENT' if ok else 'MISSING','sha256':sha(path) if ok else None})
 missing=[r['relative_path'] for r in rows if r['status']!='PRESENT']
 discovered=[]
 for pattern in ('experiments/formal_analyzer/pi1_reference_v1/**/*.json','artifacts/**/*RESEARCHER_MEMORY_PACK*.json','experiments/round1/**/*.json'):
  for path in repo.glob(pattern):
   if path.is_file() and not path.is_symlink(): discovered.append({'relative_path':path.relative_to(repo).as_posix(),'sha256':sha(path)})
 discovered=sorted({x['relative_path']:x for x in discovered}.values(),key=lambda x:x['relative_path'])
 binding={'repository_head':head,'required_assets':rows,'discovered_human_round_assets':discovered}
 cutoff=hashlib.sha256(canon(binding)).hexdigest()
 report={'schema_id':'HUMAN_REFERENCE_ROUND_INPUT_PACKAGE_V3','scientific_product_domain':'HUMAN_REFERENCE_ROUND','status':'READY_FOR_HUMAN_PRE_COMPLETION' if not missing else 'QUERY_REQUIRED','round_id':a.round_id,'parent_policy_id':a.parent_policy_id,'repository_head':head,'evidence_cutoff_sha256':cutoff,'required_assets':rows,'missing_required_assets':missing,'discovered_human_round_assets':discovered,'benchmark_artifact_count':0,'benchmark_results_visible':False,'model_call':False,'environment_execution':False,'training_execution':False,'next_gate':'HUMAN_PRE_MANUAL_COMPLETION_AND_REVIEW' if not missing else 'QUERY_REQUIRED'}
 out.mkdir(parents=True,exist_ok=False); write(out/'HUMAN_REFERENCE_ROUND_INPUT_PACKAGE_V3.json',report)
 write(out/'HUMAN_RESEARCHER_PRE_WORKSHEET_V3.md',f"""# Human Researcher PRE Worksheet V3\n\nround_id: `{a.round_id}`\nparent_policy: `{a.parent_policy_id}`\nevidence_cutoff: `{cutoff}`\n\n## Candidate bottlenecks\n\nFor every candidate record evidence, counterevidence, expected value, harm risk, verification cost, task-family scope and prior NO-GO overlap.\n\n## Repair portfolio\n\nThe Research Planner must identify, abstract or compose key source-bound repair programs; select exactly one principal scientific change; and freeze F0/F1 budget, training plan and stop rule.\n\n## Prohibited evidence\n\nNo per-task strong-model benchmark request, response, action, trajectory or score may be read.\n""")
 write(out/'RESEARCH_REPAIR_PORTFOLIO_DRAFT_V1.json',{'schema_version':'RESEARCH_REPAIR_PORTFOLIO_DRAFT_V1','round_id':a.round_id,'parent_policy_id':a.parent_policy_id,'evidence_cutoff_sha256':cutoff,'candidate_bottlenecks':[],'candidates':[],'programs':[],'requires_human_completion':True,'causal_outcomes_visible':False})
 print('HUMAN_REFERENCE_ROUND_INPUTS_V3_PASS'); print('EVIDENCE_CUTOFF_SHA256='+cutoff); print('BENCHMARK_RESULT_COUNT=0')
if __name__=='__main__': main()

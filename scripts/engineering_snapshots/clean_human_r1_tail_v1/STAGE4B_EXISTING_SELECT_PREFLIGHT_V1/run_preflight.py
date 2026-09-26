#!/usr/bin/env python3
"""Isolated offline patch verification and evidence-to-SELECT preparation.

No scientific execution, no credential loading, no commit/push, no task sampling.
"""
from __future__ import annotations
import ast
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
import preflight as p
HERE=Path(__file__).resolve().parent


def cmd(args,cwd=None,env=None):
    result=subprocess.run(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    p.need(result.returncode==0,'COMMAND_FAILED:'+repr(args)+'\n'+result.stdout.decode(errors='replace'))
    return result.stdout


def verify_delivery():
    rows=(HERE/'PACKAGE_FILES.sha256').read_text().splitlines()
    for row in rows:
        h,name=row.split('  ',1);p.need(p.file_sha(HERE/name)==h,'DELIVERY_FILE_HASH:'+name)


def isolated_code(repo:Path,out:Path,base:str,source_files:dict)->tuple[Path,str]:
    code=out/'code';scope=json.loads((HERE/'PATCH_SCOPE.json').read_bytes())
    expected={str(Path(n).relative_to(repo)):h for n,h in source_files.items()}
    for rel,binding in scope.items():
        old=expected.get(rel);p.need(old==binding['before_file_sha256'],'PATCH_BASE_FILE:'+rel)
        expected[rel]=binding['after_file_sha256']
    if not code.exists():
        cmd(['git','worktree','add','--detach',str(code),base],cwd=repo)
    p.need(not code.is_symlink() and cmd(['git','rev-parse','HEAD'],cwd=code).decode().strip()==base,'CODE_WORKTREE_HEAD')
    p.need(not cmd(['git','diff','--cached','--name-only','-z'],cwd=code),'STAGED_CONTENT_NOT_EXPECTED')
    # Accept only exact unpatched or exact patched bytes, including retries.
    for rel,binding in scope.items():
        path=code/rel
        if path.exists():
            h=p.file_sha(path);p.need(h in {binding['before_file_sha256'],binding['after_file_sha256']},'PATCH_TARGET_CONFLICT:'+rel)
        else:p.need(binding['before_file_sha256'] is None,'PATCH_TARGET_MISSING:'+rel)
    for rel,binding in scope.items():
        path=code/rel;path.parent.mkdir(parents=True,exist_ok=True)
        raw=(HERE/'payload'/rel).read_bytes();p.need(p.sha(raw)==binding['after_file_sha256'],'PATCH_PAYLOAD_HASH')
        if not path.exists() or path.read_bytes()!=raw:path.write_bytes(raw)
    untracked=set(os.fsdecode(n) for n in cmd(['git','ls-files','--others','--exclude-standard','-z'],cwd=code).split(b'\0') if n)
    expected_new={n for n,s in scope.items() if s['before_file_sha256'] is None}
    p.need(untracked==expected_new,'CODE_UNTRACKED_SCOPE')
    for rel,h in expected.items():p.need(p.file_sha(code/rel)==h,'CODE_TREE_FILE_CHANGED:'+rel)
    for rel in scope:ast.parse((code/rel).read_text())
    tree_hash=p.sha(json.dumps(expected,sort_keys=True,separators=(',',':')).encode())
    return code,tree_hash


def main()->int:
    verify_delivery();cfg=json.loads((HERE/'current_request.json').read_bytes())
    repo=Path(cfg['repo']);vr=cfg['existing_verifier'];vpath=Path(vr['path'])
    p.need(p.file_sha(vpath.with_name('orchestration.py'))==vr['orchestration_sha256'],'EXISTING_ORCHESTRATION_CHANGED')
    sys.path.insert(0,str(vpath.parent))
    verifier=p.load_module(vpath,'_existing_select_code_verifier',vr['sha256'])
    source_files=verifier.strict_repo(repo,cfg['fixed_head'],cfg['fixed_tree'])
    helpers=p.load_helpers(repo,cfg['helpers']);h=helpers['handoff']
    src=cfg['source_review'];training=p.read_packet(Path(src['path']),src['sha256'],helpers)
    init=p.obj(training['INITIALIZATION_REQUEST.json']);ref=init['request']['source_review']
    planfiles=p.read_packet(Path(ref['path']),ref['sha256'],helpers)
    formal=Path(init['runtime']['formal_source']['path'])
    print('PHASE=REUSE_ORIGINAL_TRAINING_RECEIPT_AND_LEDGER_CHECKS',flush=True)
    audit=p.verify_training_evidence(training,planfiles,helpers,formal)
    token=p.sha(p.cb({'source_review_sha256':src['sha256'],'patch_scope':p.obj((HERE/'PATCH_SCOPE.json').read_bytes()),'evaluation_proposal':cfg['evaluation_proposal']}))
    out=Path(cfg['output_parent'])/token
    p.need(not any(x.is_symlink() for x in (out,*out.parents)),'OUTPUT_SYMLINK');out.mkdir(parents=True,exist_ok=True)
    print('PREFLIGHT_OUTPUT_ROOT='+str(out),flush=True)
    print('PHASE=VERIFY_ACTUAL_CANDIDATE_FILES_NO_MODEL_LOAD',flush=True)
    p.verify_adapter_files(Path(audit['candidate']['adapter_path']),audit['adapter_file_manifest'])
    # Base byte identity is rechecked by the original clean-base verifier.
    helpers['clean_adapter'].verify_clean_base(audit['base_binding'])
    refs=p.pool_references(planfiles)
    index=p.obj(planfiles['INPUT_ARTIFACT_INDEX.json'])
    preprefs=[r for r in index['artifacts'] if r['logical_name']=='TRAINING_PREPARATION']
    p.need(len(preprefs)==1,'TRAINING_PREPARATION_REFERENCE')
    pr=preprefs[0];prep=p.read_packet(Path(pr['path']),pr['sha256'],helpers)
    proofs=json.loads(prep['T2_SOURCE_PROOFS.json'])
    census={'proofs':proofs,'task_ids':[r['source_task_id'] for r in proofs]}
    cap=audit['plan']['policy_training_recipe']['per_task_state_cap']
    pools=p.load_bound_pool_metadata(refs,h,census,cap)
    from pchsi.evaluation.run_schedule import REPLICATE_SEEDS
    from pchsi.evaluation.budget import BudgetLimits
    from pchsi.research_intelligence.human_f0f1_runtime import continuation_request_contract_v1
    grid=p.draft_task_seed_grid(pools['TRAIN_SELECT'],REPLICATE_SEEDS)
    grid['source_metadata_ref']=refs['TRAIN_SELECT'];grid['episode_budget']=asdict(BudgetLimits())
    print('PHASE=ISOLATED_EXISTING_SELECT_I1_EXTENSION',flush=True)
    code,codehash=isolated_code(repo,out,cfg['fixed_head'],source_files)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(code/'src'))
    logs=out/'verification';logs.mkdir(exist_ok=True)
    # Run real existing SELECT, interface, evaluator and result-audit tests.
    testargs=[cfg['python'],'-B','-m','pytest','-q','-p','no:cacheprovider','tests/evaluation']
    result=subprocess.run(testargs,cwd=code,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    logpath=logs/('evaluation_'+p.sha(result.stdout)[:12]+'.txt');p.write_once(logpath,result.stdout)
    print(result.stdout.decode(errors='replace'),flush=True)
    p.need(result.returncode==0,'EXISTING_EVALUATION_REGRESSION_FAILED:'+str(logpath))
    # Original source worktree must still be exact; overlay worktree also closed.
    verifier.strict_repo(repo,cfg['fixed_head'],cfg['fixed_tree'])
    _,checked=isolated_code(repo,out,cfg['fixed_head'],source_files)
    p.need(checked==codehash,'OVERLAY_CHANGED_DURING_TESTS')
    contract=continuation_request_contract_v1('I1_EXECUTION_PROFILE_V1')
    runtime_draft={'schema_id':'CLEAN_SELECT_MODEL_BINDING_PROPOSAL_V1','source_training_review_sha256':src['sha256'],
        'base':audit['base_binding'],'parent_policy_id':audit['plan']['parent_policy_id'],
        'candidate_alias':audit['candidate']['candidate_alias'],'candidate_adapter_path':audit['candidate']['adapter_path'],
        'candidate_adapter_bundle_sha256':audit['adapter_bundle_sha256'],
        'training_seed':audit['plan']['policy_training_recipe']['budget']['training_seed'],
        'interface_contract':contract,'policy_request_schema_sha256':p.sha(p.cb(contract)),
        'memory':'OFF','harness':'OFF','dynamic_lora_updates':False,
        'existing_runtime_module':'pchsi.evaluation.select_policy_runtime',
        'existing_evaluator':'pchsi.evaluation.episode_evaluator.run_single_episode',
        'existing_result_audit':'pchsi.evaluation.select_result_audit.audit_select_cell_identity_chain',
        'base_handle_policy':'Reuse legacy base service handle only via explicit scientific-identity crosswalk; never infer R0 from its name.',
        'protocol_frozen':False,'live_driver_bound':False,'execution_authorized':False,'promotion_eligible':False}
    receipt={'schema_id':'EXISTING_SELECT_PREFLIGHT_RECEIPT_V1','source_head':cfg['fixed_head'],
        'source_tree':cfg['fixed_tree'],'training_review_sha256':src['sha256'],
        'training_plan_sha256':audit['training_plan_sha256'],'training_receipt_sha256':audit['stage_receipt_sha256'],
        'code_worktree':str(code),'code_closure_sha256':codehash,'code_fixed_commit_created':False,
        'original_worktree_unchanged':True,'candidate_files_verified':True,
        'pool_counts':{n:len(v) for n,v in pools.items()},'evaluation_tests_passed':True,
        'task_count':grid['task_count'],'paired_task_seed_cells':grid['paired_cells'],'condition_episodes':grid['condition_episodes'],
        'protocol_frozen':False,'live_driver_bound':False,'model_environment_training_execution':False,
        'promotion_eligible':False,'archive_provenance_complete':audit['archive_provenance_complete'],
        'next_gate':'SELECT_I1_CODE_REVIEW_AND_EVALUATION_PROTOCOL_FREEZE'}
    artifacts={'TRAINING_EVIDENCE_AUDIT.json':audit,'BOUND_POOL_REFERENCES.json':refs,'SELECT_GRID_PROPOSAL.json':grid,
        'MODEL_BINDING_PROPOSAL.json':runtime_draft,'SELECT_PREFLIGHT_RECEIPT.json':receipt}
    encoded={n:p.cb(v) for n,v in artifacts.items()}
    encoded['SELECT_I1_EXTENSION.patch']=(HERE/'SELECT_I1_EXTENSION.patch').read_bytes()
    encoded['PATCH_SCOPE.json']=(HERE/'PATCH_SCOPE.json').read_bytes()
    for name,raw in encoded.items():p.write_once(out/name,raw)
    encoded['verification/EVALUATION_TESTS.txt']=result.stdout
    encoded['FILES.sha256.json']=p.cb({n:p.sha(v) for n,v in encoded.items()})
    bundle=out/'SELECT_PREFLIGHT_REVIEW.zip'
    # A new review is content-addressed if only engineering test timing differs.
    if bundle.exists():
        with zipfile.ZipFile(bundle) as z:old={i.filename:z.read(i) for i in z.infolist()}
        if old!=encoded:bundle=out/('SELECT_PREFLIGHT_REVIEW_'+p.sha(encoded['FILES.sha256.json'])[:12]+'.zip')
    if not bundle.exists():
        with zipfile.ZipFile(bundle,'x',compression=zipfile.ZIP_DEFLATED) as z:
            for n,raw in sorted(encoded.items()):
                info=zipfile.ZipInfo(n,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
    print('TRAINING_EVIDENCE_REPRODUCED=true')
    print('CANDIDATE_ADAPTER_BYTES_VERIFIED=true')
    print('EXISTING_SELECT_I1_OFFLINE_TESTS_PASS=true')
    print('SOURCE_CORE_WORKTREE_MODIFIED=false')
    print('MODEL_ENVIRONMENT_TRAINING_EXECUTION=false')
    print('SELECT_PROTOCOL_FROZEN=false')
    print('SELECT_PROPOSAL_COUNTS='+json.dumps({'tasks':grid['task_count'],'paired_cells':grid['paired_cells'],'condition_episodes':grid['condition_episodes']}))
    print('NEXT_GATE='+receipt['next_gate'])
    print('REVIEW_BUNDLE='+str(bundle));print('REVIEW_BUNDLE_SHA256='+p.file_sha(bundle))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print('STOP='+type(exc).__name__+':'+str(exc),file=sys.stderr)
        raise SystemExit(21)

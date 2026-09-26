#!/usr/bin/env python3
"""Finish the already-reviewed SELECT code/protocol gate; never run evaluation."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import freeze_select as f
HERE=Path(__file__).resolve().parent


def load_module(path: Path,name: str,expected_sha: str):
    f.need(f.file_sha(path)==expected_sha,'BOUND_HELPER_BYTES:'+name)
    spec=importlib.util.spec_from_file_location(name,path);f.need(spec is not None and spec.loader is not None,'IMPORT_SPEC')
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


def verify_delivery():
    for line in (HERE/'PACKAGE_FILES.sha256').read_text().splitlines():
        h,n=line.split('  ',1);p=Path(n)
        f.need(not p.is_absolute() and '..' not in p.parts,'DELIVERY_INDEX_PATH')
        f.need(f.file_sha(HERE/p)==h,'DELIVERY_BYTES:'+n)


def dependencies(cfg: dict):
    repo=Path(cfg['repo']);base=cfg['base_head']
    f.need(f.git(repo,'rev-parse','HEAD').decode().strip()==base,'ORIGINAL_WORKTREE_HEAD')
    f.need(f.git(repo,'rev-parse','HEAD^{tree}').decode().strip()==cfg['base_tree'],'ORIGINAL_WORKTREE_TREE')
    # Verify all tracked bytes before importing project code or the old verifier.
    expected=f.expected_tree(repo,base,{})
    f.check_tree(repo,expected,base)
    sys.path.insert(0,str(repo/'src'))
    bound=cfg['preflight_package']
    root=Path(bound['path']);f.need(root.is_dir() and not root.is_symlink(),'PREFLIGHT_PACKAGE')
    for n,h in bound['files'].items():f.need(f.file_sha(root/n)==h,'PREFLIGHT_PACKAGE_BYTES:'+n)
    sys.path.insert(0,str(root))
    p=load_module(root/'preflight.py','_reviewed_select_preflight',bound['files']['preflight.py'])
    oldcfg=f.obj((root/'current_request.json').read_bytes())
    f.need(oldcfg['repo']==str(repo) and oldcfg['fixed_head']==base and oldcfg['fixed_tree']==cfg['base_tree'],'PREFLIGHT_SOURCE_BINDING')
    vr=oldcfg['existing_verifier'];vpath=Path(vr['path'])
    f.need(f.file_sha(vpath.with_name('orchestration.py'))==vr['orchestration_sha256'],'EXISTING_ORCHESTRATION_BYTES')
    sys.path.insert(0,str(vpath.parent))
    verifier=load_module(vpath,'_existing_select_fixed_verifier',vr['sha256'])
    verifier.strict_repo(repo,base,cfg['base_tree'])
    helpers=p.load_helpers(repo,oldcfg['helpers'])
    return repo,p,oldcfg,helpers,verifier


def authorize(d: dict, cfg: dict) -> None:
    from pchsi.round_control.role_authority import AuthorityPhaseV1,ResearchRoleV1,resolve_authority_plan
    context=cfg['authority_context']
    f.need(d['authority_phase']==context['phase'],'AUTHORITY_PHASE_MISMATCH')
    role=resolve_authority_plan(phase=AuthorityPhaseV1(context['phase']),takeover_evaluation=context.get('takeover_evaluation'))
    f.need(d['decision_actor']==role.primary_actor(ResearchRoleV1.RESEARCH_PLANNER_POST),'NOT_REGISTERED_PRIMARY')


def verify_server_inputs(p, oldcfg,helpers, data):
    # Reuse the original archive/contract/ledger checks rather than reimplementing them.
    training=p.read_packet(Path(oldcfg['source_review']['path']),oldcfg['source_review']['sha256'],helpers)
    init=p.obj(training['INITIALIZATION_REQUEST.json']);ref=init['request']['source_review']
    planfiles=p.read_packet(Path(ref['path']),ref['sha256'],helpers)
    audit=p.verify_training_evidence(training,planfiles,helpers,Path(init['runtime']['formal_source']['path']))
    f.need(audit==data['audit'],'TRAINING_AUDIT_REPRODUCTION_MISMATCH')
    p.verify_adapter_files(Path(data['model']['candidate_adapter_path']),audit['adapter_file_manifest'])
    helpers['clean_adapter'].verify_clean_base(data['model']['base'])
    refs=p.pool_references(planfiles);f.need(refs==data['refs'],'POOL_REFERENCE_CHANGED')
    index=p.obj(planfiles['INPUT_ARTIFACT_INDEX.json'])
    refs_pre=[r for r in index['artifacts'] if r['logical_name']=='TRAINING_PREPARATION']
    f.need(len(refs_pre)==1,'TRAINING_PREPARATION_REFERENCE')
    ref=refs_pre[0];prep=p.read_packet(Path(ref['path']),ref['sha256'],helpers)
    proofs=json.loads(prep['T2_SOURCE_PROOFS.json'])
    census={'proofs':proofs,'task_ids':[r['source_task_id'] for r in proofs]}
    pools=p.load_bound_pool_metadata(refs,helpers['handoff'],census,audit['plan']['policy_training_recipe']['per_task_state_cap'])
    from pchsi.evaluation.run_schedule import REPLICATE_SEEDS
    from pchsi.evaluation.budget import BudgetLimits
    from pchsi.research_intelligence.human_f0f1_runtime import continuation_request_contract_v1
    grid=p.draft_task_seed_grid(pools['TRAIN_SELECT'],REPLICATE_SEEDS)
    grid['source_metadata_ref']=refs['TRAIN_SELECT'];grid['episode_budget']=asdict(BudgetLimits())
    f.need(grid==data['grid'],'GRID_REPRODUCTION_MISMATCH')
    f.need(continuation_request_contract_v1('I1_EXECUTION_PROFILE_V1')==data['model']['interface_contract'],'INTERFACE_FACTORY_MISMATCH')
    return {'training_audit_equal':True,'candidate_bytes_verified':True,'base_bytes_verified':True,
            'pool_metadata_verified':True,'grid_reproduced':True,'metadata_counts':{k:len(v) for k,v in pools.items()},
            'models_loaded':False,'environment_execution':False}


def regression_dependencies(code: Path, base: str,out: Path) -> dict:
    # These are the same prerequisites that full pytest already requires.
    dep=f.obj((code/'configs/memory/package_b_failure_memory_dependency_v1.json').read_bytes())
    snapshot=Path(dep['active_snapshot_external_directory']);a9=Path(dep['a9_dependency_audit_external_path'])
    f.need(snapshot.is_dir() and not snapshot.is_symlink(),'FULL_REGRESSION_SNAPSHOT_MISSING:'+str(snapshot))
    f.need(f.file_sha(a9)==dep['a9_dependency_audit_sha256'],'FULL_REGRESSION_A9_MISSING_OR_CHANGED')
    # Compile the original default, fail-closed binary. Do not build or invoke real probe payloads.
    env=dict(os.environ,SOURCE_DATE_EPOCH=f.git(code,'show','-s','--format=%ct',base).decode().strip())
    result=f.command(['make','-C','native/s1_backend_probe','all'],code,env=env,check=False)
    f.write_once(out/('native_build_'+f.sha(result.stdout)[:12]+'.log'),result.stdout)
    f.need(result.returncode==0,'FULL_REGRESSION_NATIVE_BUILD_FAILED')
    binary=code/'native/s1_backend_probe/build/pchsi-s1-backend-probe'
    return {'b0_dependency_config_sha256':f.file_sha(code/'configs/memory/package_b_failure_memory_dependency_v1.json'),
            'b0_snapshot_path':str(snapshot),'b0_snapshot_sha256':dep['active_snapshot_sha256'],
            'a9_sha256':f.file_sha(a9),'native_binary_sha256':f.file_sha(binary),'real_probe_execution':False}


def run_regression(code: Path, expected: dict, base: str, cfg: dict,out: Path) -> dict:
    prereq=regression_dependencies(code,base,out)
    prior=out/'FULL_REGRESSION_PASS.json'
    if prior.exists():
        r=f.obj(prior.read_bytes())
        f.need(r['code_closure_sha256']==f.sha(f.cb(expected)) and r['prerequisites']==prereq,'REGRESSION_RECEIPT_INPUT_MISMATCH')
        f.need(f.file_sha(Path(r['log_path']))==r['log_sha256'] and f.file_sha(Path(r['junit_path']))==r['junit_sha256'],'REGRESSION_LOG_CHANGED')
        # The original B0 audit is rerun through the original test on a resume.
        env=dict(os.environ,PYTHONPATH=str(code/'src'),PYTHONDONTWRITEBYTECODE='1')
        check=f.command([cfg['python'],'-B','-m','pytest','-q','-p','no:cacheprovider','tests/memory/test_package_b_b0_dependency.py'],code,env=env,check=False)
        f.need(check.returncode==0,'BOUND_B0_DEPENDENCY_REVALIDATION_FAILED')
        print('EXISTING_EXACT_FULL_REGRESSION_REUSED=true',flush=True)
        return r
    env=dict(os.environ,PYTHONPATH=str(code/'src'),PYTHONDONTWRITEBYTECODE='1')
    for n in ['PYTEST_ADDOPTS','OPENAI_API_KEY','ANTHROPIC_API_KEY','GOOGLE_API_KEY']:env.pop(n,None)
    testroot=Path(tempfile.mkdtemp(prefix='full_',dir=out));junit=testroot/'junit.xml';log=testroot/'pytest.log'
    command=[cfg['python'],'-B','-m','pytest','-q','-p','no:cacheprovider','--junitxml='+str(junit)]
    print('PHASE=FULL_EXISTING_REPOSITORY_REGRESSION',flush=True)
    with log.open('xb') as stream:
        p=subprocess.Popen(command,cwd=code,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        assert p.stdout is not None
        for line in iter(p.stdout.readline,b''):
            stream.write(line);stream.flush();sys.stdout.buffer.write(line);sys.stdout.buffer.flush()
        rc=p.wait()
    f.need(rc==0,'FULL_REGRESSION_FAILED_LOG='+str(log))
    tree=ET.parse(junit);cases=tree.findall('.//testcase')
    f.need(cases and not tree.findall('.//failure') and not tree.findall('.//error') and not tree.findall('.//skipped'),'FULL_REGRESSION_NOT_ALL_EXECUTED_AND_PASSED')
    f.check_tree(code,expected,base)
    r={'schema_id':'SELECT_EXACT_FULL_REGRESSION_PASS_V1','code_closure_sha256':f.sha(f.cb(expected)),
       'passed_count':len(cases),'returncode':rc,'prerequisites':prereq,'log_path':str(log),'log_sha256':f.file_sha(log),
       'junit_path':str(junit),'junit_sha256':f.file_sha(junit),'original_tests_modified':False}
    f.write_once(prior,f.cb(r));return r


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument('--approve-decision');parser.add_argument('--decision',default=str(HERE/'decisions/current_protocol_decision.json'))
    args=parser.parse_args();verify_delivery();cfg=json.loads((HERE/'current_request.json').read_bytes())
    repo,p,oldcfg,helpers,verifier=dependencies(cfg)
    source=cfg['source_review'];files=f.read_review(Path(source['path']),source['sha256']);data=f.validate_review(files)
    d_raw=f.regular(Path(args.decision)).read_bytes();d=f.obj(d_raw)
    if not args.approve_decision:
        print('DECISION_APPROVAL_REQUIRED='+f.sha(d_raw));print('CODE_COMMIT_CREATED=false');print('SELECT_PROTOCOL_FROZEN=false');return 20
    d=f.approve_decision(d_raw,args.approve_decision,source['sha256'],files);authorize(d,cfg)
    f.need(data['receipt']['source_head']==cfg['base_head'] and data['receipt']['source_tree']==cfg['base_tree'],'BASE_CLOSURE_MISMATCH')
    code=Path(data['receipt']['code_worktree'])
    f.need(code==Path(source['path']).parent/'code' and code.is_dir() and not code.is_symlink(),'EXISTING_CODE_WORKTREE_PATH')
    scope=data['scope'];expected=f.expected_tree(repo,cfg['base_head'],scope)
    # Match the original preflight closure format (relative path -> SHA, no terminal LF).
    legacy=f.sha(json.dumps({n:s['sha256'] for n,s in expected.items()},sort_keys=True,separators=(',',':')).encode())
    f.need(legacy==data['receipt']['code_closure_sha256'],'PREFLIGHT_CODE_CLOSURE')
    f.check_tree(code,expected,cfg['base_head'])
    output=Path(cfg['output_parent'])/f.sha(f.cb({'source':source['sha256'],'decision_file_sha256':args.approve_decision,'closure':legacy}))
    output.mkdir(parents=True,exist_ok=True);f.need(not any(x.is_symlink() for x in (output,*output.parents)),'OUTPUT_SYMLINK')
    print('FREEZE_OUTPUT_ROOT='+str(output),flush=True)
    lock=open(output/'FREEZE.lock','a+b')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('FREEZE_ALREADY_RUNNING')
    try:
        print('PHASE=REUSE_APPROVED_TRAINING_AND_SELECT_INPUTS',flush=True)
        inputs=verify_server_inputs(p,oldcfg,helpers,data)
        f.write_once(output/'INPUT_REVALIDATION.json',f.cb(inputs))
        tests=run_regression(code,expected,cfg['base_head'],cfg,output)
        verifier.strict_repo(repo,cfg['base_head'],cfg['base_tree'])
        print('PHASE=COMMIT_EXACT_EXISTING_OVERLAY_NO_REPATCH',flush=True)
        fixed=f.freeze_code(code,cfg['base_head'],expected,scope,output)
        protocol=f.make_protocol(data,d,source['sha256'],fixed['head'],fixed['tree'],fixed['code_closure_sha256'])
        # Use the original protocol/record artifact index contract for downstream handoff.
        docs={'SELECT_EVALUATION_PROTOCOL_V1.json':f.cb(protocol),'PRIMARY_PROTOCOL_DECISION.json':d_raw,
              'FIXED_CODE.json':f.cb(fixed),'FULL_REGRESSION_PASS.json':f.cb(tests),'INPUT_REVALIDATION.json':f.cb(inputs),
              'SELECT_GRID_PROPOSAL.unchanged.json':files['SELECT_GRID_PROPOSAL.json'],
              'MODEL_BINDING_PROPOSAL.unchanged.json':files['MODEL_BINDING_PROPOSAL.json'],
              'BOUND_POOL_REFERENCES.unchanged.json':files['BOUND_POOL_REFERENCES.json'],
              'SOURCE_PREFLIGHT_RECEIPT.unchanged.json':files['SELECT_PREFLIGHT_RECEIPT.json'],
              'SELECT_I1_EXTENSION.unchanged.patch':files['SELECT_I1_EXTENSION.patch'],'PATCH_SCOPE.unchanged.json':files['PATCH_SCOPE.json']}
        docs['FIXED_CODE.patch']=(output/'FIXED_CODE.patch').read_bytes()
        docs['PRIMARY_DECISION_APPROVAL.json']=f.cb({
            'schema_id':'SELECT_CODE_PROTOCOL_APPROVAL_RECEIPT_V1',
            'decision_file_sha256':args.approve_decision,
            'decision_canonical_sha256':f.sha(f.cb(d)),
            'source_review_sha256':source['sha256'],
            'decision_actor':d['decision_actor'],'authority_phase':d['authority_phase'],
            'approval_scope':d['approval_scope'],'model_execution_authorized':False,
            'protocol_sha256':protocol['protocol_sha256'],'fixed_head':fixed['head'],
        })
        for n,b in docs.items():f.write_once(output/n,b)
        from round_training.receipts import build_input_artifact_index
        index=build_input_artifact_index(round_id=protocol['round_id'],stage_id='CLEAN_SELECT_CODE_PROTOCOL_FREEZE',refs=[
            {'logical_name':n,'path':str(output/n),'sha256':f.sha(b),'retention_class':'SCIENTIFIC_CONFIG'} for n,b in sorted(docs.items())])
        docs['INPUT_ARTIFACT_INDEX.json']=f.cb(index)
        nextstage={'schema_id':'EXISTING_SELECT_FROZEN_INPUT_HANDOFF_V1','round_id':protocol['round_id'],
          'protocol_path':str(output/'SELECT_EVALUATION_PROTOCOL_V1.json'),'protocol_sha256':protocol['protocol_sha256'],
          'protocol_file_sha256':f.sha(docs['SELECT_EVALUATION_PROTOCOL_V1.json']),
          'input_artifact_index_sha256':index['artifact_index_sha256'],'code_worktree':str(code),
          'fixed_head':fixed['head'],'fixed_tree':fixed['tree'],'local_fixed_ref':fixed['ref'],
          'original_worktree':str(repo),'original_worktree_modified':False,'remote_published':False,
          'code_history_bundle_path':str(output/'SELECT_CODE_HISTORY.bundle'),'code_history_bundle_sha256':f.file_sha(output/'SELECT_CODE_HISTORY.bundle'),
          'existing_evaluator':data['model']['existing_evaluator'],'existing_result_audit':data['model']['existing_result_audit'],
          'candidate_adapter_path':data['model']['candidate_adapter_path'],'candidate_adapter_bundle_sha256':data['model']['candidate_adapter_bundle_sha256'],
          'pool_metadata_refs':data['refs'],'evaluation_execution_authorized':False,'training_execution_authorized':False,
          'promotion_eligible':False,'archive_provenance_complete':False,
          'next_gate':'EXISTING_SELECT_LIVE_BINDING_AND_EXECUTION_AUTHORIZATION',
          'pending_live_requirements':['TYPED_SERVER_POLICY_CONDITION_SCHEDULE_MANIFESTS','CLEAN_ENVIRONMENT_RUNTIME_BINDING','LIVE_DRIVER_BINDING_AND_EXPLICIT_RESOURCE_AUTHORIZATION']}
        docs['NEXT_STAGE_BINDING.json']=f.cb(nextstage)
        # Collect the exact legacy live code now; do not execute its pilot defaults.
        legacy_root=code/'scripts/engineering_snapshots/stage0/human_pilot_stage0_offoff_execution_and_closeout_v1_9'
        for path in sorted((legacy_root/'stage0').glob('*.py')):
            docs['existing_live_sources/'+path.name]=path.read_bytes()
        reuse={'schema_id':'SELECT_LIVE_SOURCE_REUSE_V1','fixed_head':fixed['head'],
               'source_root_relative_path':str(legacy_root.relative_to(code)),
               'files':{n:f.sha(b) for n,b in docs.items() if n.startswith('existing_live_sources/')},
               'pilot_constants_authorized_for_clean_round':False,'live_source_execution_performed':False}
        docs['EXISTING_LIVE_SOURCE_REUSE.json']=f.cb(reuse)
        docs['verification/FULL_REGRESSION.log']=Path(tests['log_path']).read_bytes()
        docs['verification/FULL_REGRESSION.xml']=Path(tests['junit_path']).read_bytes()
        bundle=f.publish_review(output,docs)
        verifier.strict_repo(repo,cfg['base_head'],cfg['base_tree'])
        print('SELECT_CODE_FIXED=true');print('FIXED_HEAD='+fixed['head']);print('LOCAL_REVIEW_REF='+fixed['ref'])
        print('FULL_REPOSITORY_TESTS_PASS='+str(tests['passed_count']));print('SELECT_PROTOCOL_FROZEN=true')
        print('SELECT_PROTOCOL_SHA256='+protocol['protocol_sha256'])
        print('FROZEN_COUNTS='+json.dumps({k:data['grid'][k] for k in ['task_count','paired_cells','condition_episodes']}))
        print('SOURCE_CORE_WORKTREE_MODIFIED=false');print('REMOTE_PUBLICATION=false')
        print('MODEL_ENVIRONMENT_TRAINING_EXECUTION=false');print('EVALUATION_EXECUTION_AUTHORIZED=false')
        print('NEXT_GATE='+nextstage['next_gate']);print('REVIEW_BUNDLE='+str(bundle));print('REVIEW_BUNDLE_SHA256='+f.file_sha(bundle))
        return 0
    except Exception as exc:
        record={'error_type':type(exc).__name__,'reason':str(exc),'evaluation_execution_authorized':False,'model_environment_training_execution':False}
        f.write_once(output/('STOP_'+f.sha(f.cb(record))[:12]+'.json'),f.cb(record))
        raise
    finally:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print('STOP='+type(exc).__name__+':'+str(exc),flush=True)
        raise SystemExit(21)

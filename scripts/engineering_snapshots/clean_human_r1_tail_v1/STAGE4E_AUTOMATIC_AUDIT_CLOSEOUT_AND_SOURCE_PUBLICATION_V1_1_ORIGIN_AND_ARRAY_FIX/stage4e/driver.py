"""Server-side, synchronous prepare -> follow -> native audit -> FF publication.

This process never modifies the active code checkout or reads partial outcomes.
"""
from __future__ import annotations
import argparse
import fcntl
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from . import (GateError, regular, read_json, file_sha, require_file_sha, write_exact,
               write_bytes_exact, verify_inventory, next_operation, semantic_sha, safe_child)
from .audit import COMPLETE, execute_audit
from .source import (run, git, verify_active_repo, ensure_isolated_repo, stage_explicit,
                     commit_staged, publish_atomic, build_source_map, reject_secret,
                     SNAPSHOT_PREFIX, DOC_PREFIX)

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_RESULTS=(
    'TRAIN_SELECT_AGGREGATE.json','POLICY_DISPOSITION.json','NEXT_ROUND_CREATION.json',
    'STRONG_PRIMARY_HANDOFF.json','CLEAN_HUMAN_REFERENCE_CLOSEOUT.json','STAGE_ATTEMPT_RECEIPT.json',
)

def parse_accounting(raw: str, job_id: str) -> tuple[str,str] | None:
    found=[]
    for line in raw.splitlines():
        values=line.split('|')
        if len(values)>=3 and values[0].strip()==job_id:
            found.append((values[1].strip().split()[0].rstrip('+'),values[2].strip()))
    if len(found)>1:raise GateError('AMBIGUOUS_ACCOUNTING_PARENT')
    return found[0] if found else None

def decide(state, exit_code, completed, partial, resume_count, limit):
    if state=='COMPLETED' and exit_code!='0:0':return 'STOP'
    return next_operation(state=state,completion_present=completed,graceful_partial=partial,
                          resume_count=resume_count,max_resumptions=limit)

def parse_submitted_job(raw: str) -> str:
    values=re.findall(r'^JOB_ID=(\d+)$',raw,re.M)
    if len(values)!=1 or 'STAGE4D_FULL_SELECT_SUBMITTED' not in raw:
        raise GateError('SUBMISSION_RESULT_UNKNOWN_DO_NOT_RESUBMIT')
    return values[0]

def status(job_id: str) -> tuple[str,str] | None:
    p=subprocess.run(['sacct','-n','-P','-X','-j',job_id,'--format=JobIDRaw,State,ExitCode'],
                     text=True,capture_output=True,timeout=45)
    if p.returncode==0:
        result=parse_accounting(p.stdout,job_id)
        if result:return result
    p=subprocess.run(['squeue','-h','-j',job_id,'-o','%i|%T'],text=True,capture_output=True,timeout=45)
    if p.returncode==0:
        for line in p.stdout.splitlines():
            values=line.split('|')
            if len(values)==2 and values[0].strip()==job_id:return values[1].strip(),'UNKNOWN'
    return None

def check_authorization(module, binding: Path, root: Path, readiness_sha: str, auth_sha: str) -> None:
    auth=read_json(root/'STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_V1.json')
    expected=module.authorization_payload(binding_root=binding,readiness_receipt_sha256=readiness_sha)
    if auth!=expected:raise GateError('EXECUTION_AUTHORIZATION_CONTENT_CHANGED')
    if module.authorization_sha(auth)!=auth_sha:raise GateError('EXECUTION_AUTHORITY_CHANGED')

def base_gate(cfg: dict) -> Path:
    # Check existing code and frozen input identities only. No outcome ledger is opened here.
    for ref in cfg['input_refs']:
        require_file_sha(Path(ref['path']),ref['file_sha256'])
    for package in cfg['source_packages']:
        path=Path(package['root'])
        for name,digest in package['source_files'].items():
            require_file_sha(safe_child(path,name),digest)
    full=Path(cfg['full_package'])
    spec=importlib.util.spec_from_file_location('_stage4e_existing_full_contract',full/'stage4d_full/contract.py')
    if spec is None or spec.loader is None:raise GateError('EXISTING_FULL_CONTRACT_UNAVAILABLE')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    binding=Path(cfg['binding_root'])
    module.verify_binding_inventory(binding)
    module.validate_readiness_receipt(read_json(Path(cfg['readiness_receipt'])))
    active=module.verify_code_authority(binding)
    verify_active_repo(active,cfg)
    module.verify_scientific_grid(binding)
    check_authorization(module,binding,Path(cfg['execution_root']),cfg['readiness_sha256'],cfg['authorization_sha256'])
    return active

def test_command(args: list[str], *, cwd: Path, log: Path, env: dict) -> Path:
    # Preserve the actual process output; no PASS can be written from a guessed count.
    p=subprocess.run(args,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=3600)
    text='$ '+' '.join(args)+'\n'+p.stdout+f'\nEXIT_CODE={p.returncode}\n'
    # A failed earlier test may be diagnosed in a distinct invocation, never overwritten.
    name=log if not log.exists() else log.with_name(log.stem+'_'+str(os.getpid())+log.suffix)
    write_bytes_exact(name,text.encode())
    if p.returncode:raise GateError('SOURCE_INTEGRATION_TEST_FAILED:'+str(name))
    return name

def regression_prerequisites(cfg: dict, repo: Path, output: Path) -> dict:
    """Reuse the exact Stage4C prerequisite builder; never execute its main()."""
    stage4c=next(x for x in cfg['source_packages'] if x['name']=='STAGE4C_EXISTING_SELECT_FREEZE_V1')
    oldroot=Path(stage4c['root']);output.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'src'));sys.path.insert(0,str(oldroot))
    spec=importlib.util.spec_from_file_location('_stage4e_existing_regression_driver',oldroot/'run_freeze.py')
    if spec is None or spec.loader is None:raise GateError('NATIVE_REGRESSION_PREREQUISITES_UNAVAILABLE')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    value=module.regression_dependencies(repo,cfg['fixed_head'],output)
    write_exact(output/'NATIVE_PREREQUISITES.json',value)
    return value

def prepare(cfg: dict, control: Path) -> tuple[Path,Path]:
    active=base_gate(cfg);repo=Path(cfg['integration_repo'])
    ensure_isolated_repo(active=active,dest=repo,cfg=cfg)
    receipt_path=control/'SOURCE_PREPARATION.json'
    if receipt_path.exists():
        previous=read_json(receipt_path)
        if previous['delivery_manifest_sha256']!=file_sha(ROOT/'PACKAGE_FILES.sha256'):
            raise GateError('PREPARED_SOURCE_DELIVERY_CHANGED')
        if git(repo,'status','--porcelain'):raise GateError('PREPARED_SOURCE_DIRTY')
        for name,digest in previous['installed_file_sha256s'].items():require_file_sha(repo/name,digest)
        return active,repo
    installed=[];provenance=[]
    for package in cfg['source_packages']:
        for name,digest in package['source_files'].items():
            raw=regular(Path(package['root'])/name).read_bytes();reject_secret(raw,name)
            target=f"{SNAPSHOT_PREFIX}/{package['name']}/{name}"
            write_bytes_exact(safe_child(repo,target),raw);installed.append(target)
            provenance.append({'path':target,'source_path':str(Path(package['root'])/name),'file_sha256':digest,
                               'use':package['use'],'copied_bytes_unchanged':True})
    # This adapter is archived beside, not installed over, the running Stage4D package.
    self_name=cfg['delivery_name']
    for name in [*verify_inventory(ROOT), 'PACKAGE_FILES.sha256']:
        target=f'{SNAPSHOT_PREFIX}/{self_name}/{name}'
        raw=regular(ROOT/name).read_bytes();reject_secret(raw,name)
        write_bytes_exact(safe_child(repo,target),raw);installed.append(target)
    route=read_json(ROOT/'docs/ROUTE_SPEC.json')
    index,md=build_source_map(repo=repo,cfg=cfg,additional_names=installed,route=route)
    for suffix,value in [('FULL_CODE_CHAIN.json',index),('EXECUTION_SOURCE_PROVENANCE.json',{'files':provenance})]:
        name=f'{DOC_PREFIX}/{suffix}';write_exact(repo/name,value);installed.append(name)
    name=f'{DOC_PREFIX}/FULL_CODE_CHAIN.md';write_bytes_exact(repo/name,md.encode());installed.append(name)
    env=os.environ.copy();env['PYTHONPATH']=str(repo/'src');env['PYTHONDONTWRITEBYTECODE']='1'
    regression_prerequisites(cfg,repo,control/'verification')
    for key in ('PYTEST_ADDOPTS','OPENAI_API_KEY','ANTHROPIC_API_KEY','GOOGLE_API_KEY'):
        env.pop(key,None)
    junit=control/'verification'/f'full_repository_{os.getpid()}.xml'
    reports=[]
    reports.append(test_command([cfg['python'],'-m','pytest','-q','-p','no:cacheprovider','--junitxml='+str(junit),'tests'],cwd=repo,
                 log=control/'verification/FULL_REPOSITORY_TESTS.txt',env=env))
    xml=ET.parse(junit)
    if not xml.findall('.//testcase') or any(xml.findall('.//'+tag) for tag in ('failure','error','skipped')):
        raise GateError('FULL_NATIVE_REGRESSION_NOT_ALL_EXECUTED_AND_PASSED')
    print('FULL_NATIVE_REPOSITORY_TEST_COUNT='+str(len(xml.findall('.//testcase'))),flush=True)
    env['STAGE4E_TEST_REPO']=str(repo);env['STAGE4E_TEST_FULL_PACKAGE']=cfg['full_package']
    reports.append(test_command([cfg['python'],'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,
                 log=control/'verification/STAGE4E_WITH_NATIVE_TESTS.txt',env=env))
    reports.append(test_command([cfg['python'],'-m','unittest','discover','-s','native_tests','-v'],cwd=ROOT,
                 log=control/'verification/NATIVE_INTEGRATION_TESTS.txt',env=env))
    # Test reports are engineering-only. Real data stay outside this checkout.
    for report in reports:
        target=f'{DOC_PREFIX}/verification/{report.name}'
        write_bytes_exact(repo/target,regular(report).read_bytes());installed.append(target)
    stage_explicit(repo,installed)
    commit=commit_staged(repo,'Integrate clean Human round source chain and outcome-gated closeout')
    verify_active_repo(active,cfg)
    receipt={'schema_id':'CLEAN_SOURCE_PREPARATION_V1','fixed_head':cfg['fixed_head'],
             'integration_head':commit,'delivery_manifest_sha256':file_sha(ROOT/'PACKAGE_FILES.sha256'),
             'active_checkout_unchanged':True,'native_repository_tests_passed':True,
             'installed_file_sha256s':{x:file_sha(repo/x) for x in installed},
             'full_code_file_count':index['source_file_count'],'python_symbol_count':index['python_symbol_count'],
             'scientific_round_complete':False,'remote_publication_verified':False}
    write_exact(receipt_path,receipt)
    print('STAGE4E_SOURCE_PREPARATION_PASS',flush=True)
    print('ISOLATED_INTEGRATION_HEAD='+commit,flush=True)
    return active,repo

def follow(cfg: dict, control: Path, initial_job: str, once: bool) -> bool:
    root=Path(cfg['execution_root']);job=initial_job;resumptions=0;unknown=0;last=None
    # Recover known automatic submissions; ambiguity is a stop, never a second POST/sbatch.
    for i in range(cfg['max_automatic_resumptions']):
        receipt=control/f'RESUMPTION_{i+1}.json'
        intent=control/f'RESUMPTION_{i+1}.intent.json'
        if receipt.exists():
            obj=read_json(receipt)
            if obj['previous_job_id']!=job:raise GateError('RESUMPTION_LINEAGE_CHANGED')
            job=obj['job_id'];resumptions+=1
        elif intent.exists():raise GateError('SUBMISSION_INTENT_WITHOUT_RECEIPT_NO_AUTOMATIC_RETRY')
    while True:
        result=status(job)
        if result is None:
            unknown+=1
            if unknown>=5:raise GateError('ACCOUNTING_UNAVAILABLE_NO_OUTCOME_READ')
            if once:return False
            time.sleep(cfg['poll_seconds']);continue
        unknown=0;state,code=result
        if result!=last:print(f'STAGE4E_DEPENDENCY_JOB={job} STATE={state} EXIT_CODE={code}',flush=True);last=result
        complete=(root/COMPLETE).is_file()
        partial=False
        if state=='COMPLETED' and code=='0:0' and not complete:
            # Read only terminal status markers, never per-cell success values.
            out=Path(cfg['execution_log_root'])/f'full_select_{job}.out'
            if out.exists():partial='STAGE4D_FULL_SELECT_EXECUTION_GRACEFUL_PARTIAL' in out.read_text(encoding='utf-8',errors='replace')
        action=decide(state,code,complete,partial,resumptions,cfg['max_automatic_resumptions'])
        if action=='AUDIT':return True
        if action=='STOP':raise GateError(f'DEPENDENCY_NOT_AUDITABLE:{job}:{state}:{code}:resumes={resumptions}')
        if action=='WAIT':
            if once:return False
            time.sleep(cfg['poll_seconds']);continue
        # Only the original full SELECT launcher is permitted to resume exact registered work.
        last_id=regular(root/'LAST_JOB_ID.txt').read_text().strip()
        if last_id!=job:raise GateError('EXTERNAL_SUBMISSION_DETECTED_NO_DUPLICATE_AUTOMATIC_JOB')
        env=os.environ.copy();env['STAGE4D_FULL_SELECT_EXECUTION_APPROVAL']='APPROVE_STAGE4D_FULL_SELECT_EXECUTION_V1'
        attempt=resumptions+1
        write_exact(control/f'RESUMPTION_{attempt}.intent.json',{'previous_job_id':job,'attempt':attempt,
            'authorization_sha256':cfg['authorization_sha256'],'reason':'COMPLETED_GRACEFUL_PARTIAL_ONLY'})
        p=subprocess.run(['bash','./RUN_AUTHORIZE_AND_SUBMIT.sh'],cwd=cfg['full_package'],env=env,
                         text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900)
        write_bytes_exact(control/f'RESUMPTION_{attempt}.log',p.stdout.encode())
        if p.returncode:raise GateError('EXISTING_RESUMABLE_SUBMIT_FAILED_NO_RETRY')
        new= parse_submitted_job(p.stdout)
        write_exact(control/f'RESUMPTION_{attempt}.json',{'previous_job_id':job,'job_id':new,'attempt':attempt})
        job=new;resumptions=attempt;last=None

def finalize(cfg: dict, control: Path, repo: Path, active: Path) -> None:
    final=control/'FINAL_PUBLICATION_RECEIPT.json'
    if final.exists():
        obj=read_json(final)
        target=obj['commit']
        if git(repo,'rev-parse','HEAD')!=target or git(repo,'status','--porcelain'):
            raise GateError('FINAL_SOURCE_CHANGED')
        remote=git(repo,'ls-remote','origin','refs/heads/main',f"refs/heads/{cfg['publication_branch']}")
        refs={l.split()[1]:l.split()[0] for l in remote.splitlines()}
        if any(refs.get(x)!=target for x in ['refs/heads/main',f"refs/heads/{cfg['publication_branch']}"]):
            raise GateError('FINAL_REMOTE_REF_CHANGED')
        print('STAGE4E_FINAL_PUBLICATION_ALREADY_VERIFIED',flush=True);return
    base_gate(cfg)
    output=control/'results'
    # Run native imports against the isolated integration checkout in a fresh interpreter.
    run([cfg['python'],'-m','stage4e.driver','audit-once','--control',str(control),
         '--repo',str(repo)],cwd=ROOT,timeout=14400)
    closeout=read_json(output/'CLEAN_HUMAN_REFERENCE_CLOSEOUT.json')
    if closeout['status']!='EVALUATION_AND_DISPOSITION_CLOSED':raise GateError('CLOSEOUT_NOT_COMPLETE')
    names=[]
    for name in PUBLIC_RESULTS:
        target=f'{DOC_PREFIX}/results/{name}'
        write_bytes_exact(repo/target,regular(output/name).read_bytes());names.append(target)
    stage_explicit(repo,names)
    commit_staged(repo,'Seal audited clean Human diagnostic round and machine next-round handoff')
    verify_active_repo(active,cfg)
    result=publish_atomic(repo=repo,branch=cfg['publication_branch'],include_main=True,
                          approved_urls=cfg['allowed_origin_urls'])
    write_exact(final,result)
    print('STAGE4E_EVALUATION_DISPOSITION_AND_SOURCE_PUBLICATION_COMPLETE',flush=True)
    print('PUBLISHED_HEAD='+result['commit'],flush=True)
    print('NEXT_PARENT_POLICY=PI0_CLEAN',flush=True)
    print('CANDIDATE_PROMOTION_AUTHORIZED=false',flush=True)
    print('STRONG_PRIMARY_EXECUTION_AUTHORIZED=false',flush=True)
    print('NEXT_GATE=REGISTERED_TAKEOVER_METRICS_AND_NEXT_ROUND_BINDINGS',flush=True)

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('mode',choices=['prepare','prepare-follow-publish','audit-once'])
    p.add_argument('--job-id',default='156834')
    p.add_argument('--control');p.add_argument('--repo');p.add_argument('--once',action='store_true')
    a=p.parse_args();verify_inventory(ROOT);cfg=read_json(ROOT/'config.json')
    if not a.job_id.isdigit():raise GateError('NUMERIC_JOB_ID_REQUIRED')
    control=Path(a.control or cfg['control_root'])
    if control!=Path(cfg['control_root']):raise GateError('CONTROL_ROOT_CHANGED')
    if a.mode=='audit-once':
        repo=Path(a.repo or cfg['integration_repo'])
        if repo!=Path(cfg['integration_repo']):raise GateError('AUDIT_REPO_CHANGED')
        base_gate(cfg)
        execute_audit(cfg=cfg,output=control/'results',repo=repo,binding=Path(cfg['binding_root']),root=Path(cfg['execution_root']))
        return 0
    control.mkdir(parents=True,exist_ok=True)
    fd=os.open(control/'driver.lock',os.O_RDWR|os.O_CREAT,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        active,repo=prepare(cfg,control)
        if a.mode=='prepare':return 0
        if follow(cfg,control,a.job_id,a.once):finalize(cfg,control,repo,active)
        else:print('STAGE4E_PREPARED_DEPENDENCY_STILL_ACTIVE',flush=True)
    finally:os.close(fd)
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (GateError,OSError,subprocess.SubprocessError) as exc:
        print('STOP='+str(exc),file=sys.stderr,flush=True)
        raise SystemExit(1)

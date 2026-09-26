"""One registered recovery of array 156877; reuse the exact existing worker and audit.

This does not change the scientific plan or retry a scientific outcome. The
server must prove that all four previous workers stopped before cell execution.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SCRIPTS = Path('/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts')
OLD_NAME = 'STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX'
OLD_ROOT = SCRIPTS / OLD_NAME
OLD_MANIFEST = 'e34acc3e2254141ebe5297b643cbcc9d4aade383c627be9682128e2bc681f535'
FAILED_ARRAY = '156877'
EXCLUDED_NODE = 'd1n41a18g03'
PLAN_SHA = 'cea91dcfb65a6ddd7b1fd719cfaffedb9cfaa950287b19b776ac373260f9564a'
RECOVERY_REL = 'node_recovery_156877_v1'
FIRST_GENERATION = 2  # 0 remains failed; 1 stays reserved for the original controller.

class RecoveryError(ValueError):
    pass


def parse_failed_accounting(raw: str, uid: int) -> list[dict]:
    found = {}
    for line in raw.splitlines():
        v = [x.strip() for x in line.split('|')]
        if not v or not re.fullmatch(FAILED_ARRAY+r'_[0-3]',v[0]):
            continue
        if len(v)<7:
            raise RecoveryError('OLD_ACCOUNTING_FIELDS_MISSING')
        sid = int(v[0].rsplit('_',1)[1])
        if sid in found:
            raise RecoveryError('OLD_ACCOUNTING_DUPLICATE_ELEMENT')
        if (not v[1].isdigit() or v[2]!='FAILED' or v[3]!='1:0'
                or v[4]!=EXCLUDED_NODE or v[5]!=str(uid) or v[6]!='st4d_select_shard'):
            raise RecoveryError('OLD_ARRAY_NOT_EXACT_OWNED_FAILED_NODE_INCIDENT:'+v[0])
        found[sid] = {'shard':sid,'job_id':v[1],'state':v[2],'exit_code':v[3],
                      'node':v[4],'uid':uid,'job_name':v[6]}
    if set(found)!=set(range(4)) or len({v['job_id'] for v in found.values()})!=4:
        raise RecoveryError('OLD_ARRAY_ACCOUNTING_INCOMPLETE_OR_AMBIGUOUS')
    return [found[i] for i in range(4)]


def memory_failure(text: str) -> dict:
    matches = re.findall(r'Free memory on device\s*\(([0-9.]+)/([0-9.]+) GiB\) on\s*startup is less than desired GPU\s*memory utilization\s*\(([0-9.]+),\s*([0-9.]+) GiB\)',text)
    values = {(float(a),float(b),float(c),float(d)) for a,b,c,d in matches}
    if len(values)!=1:
        raise RecoveryError('EXACT_STARTUP_MEMORY_CAUSE_NOT_CONFIRMED')
    free,total,util,desired = next(iter(values))
    if not (0 <= free < desired <= total and util==0.9 and abs(total*util-desired)<0.03):
        raise RecoveryError('STARTUP_MEMORY_CONTRACT_CHANGED')
    return {'free_gib':free,'total_gib':total,'utilization':util,'requested_gib':desired}


def require_no_shard_outputs(root: Path) -> None:
    parallel = root/'parallel_v1'
    if parallel.is_symlink():
        raise RecoveryError('SYMLINK_PARALLEL_ROOT')
    for shard in range(4):
        base = parallel/f'shard_{shard}'
        if base.is_symlink():
            raise RecoveryError('SYMLINK_SHARD_ROOT')
        if base.exists():
            if not base.is_dir():
                raise RecoveryError('SHARD_ROOT_NOT_DIRECTORY')
            for path in base.rglob('*'):
                if path.is_symlink() or not path.is_dir():
                    raise RecoveryError('EXISTING_SHARD_OUTPUT_REQUIRES_SEPARATE_AUDIT:'+str(path))


def with_exclusion(command: list[str]) -> list[str]:
    if not command or command[0]!='sbatch' or any(x=='-x' or x.startswith('--exclude') for x in command):
        raise RecoveryError('UNEXPECTED_OR_ALREADY_EXCLUDED_SUBMISSION_COMMAND')
    return [command[0],'--exclude='+EXCLUDED_NODE,*command[1:]]


def shell(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command,text=True,capture_output=True,timeout=90)


def load_original(path: Path = OLD_ROOT):
    path = path.resolve()
    if hashlib.sha256((path/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=OLD_MANIFEST:
        raise RecoveryError('ORIGINAL_STAGE4E_MANIFEST_CHANGED')
    sys.path.insert(0,str(path))
    core=importlib.import_module('stage4e')
    ad=importlib.import_module('stage4e.array_driver')
    jobs=importlib.import_module('stage4e.array_jobs')
    driver=importlib.import_module('stage4e.driver')
    for module in (core,ad,jobs,driver):
        if not Path(module.__file__).resolve().is_relative_to(path):
            raise RecoveryError('ORIGINAL_IMPORT_ROOT_CHANGED')
    core.verify_inventory(path)
    return core,ad,jobs,driver


def preflight(core, ad, cfg: dict, state: Path, plan: dict, recovery: Path) -> dict:
    proof_path=recovery/'RECOVERY_AUTHORIZATION.json'
    if proof_path.exists():
        proof=core.read_json(proof_path)
        expected={'failed_array_id':FAILED_ARRAY,'excluded_node':EXCLUDED_NODE,'plan_sha256':PLAN_SHA,
                  'recovery_package_manifest_sha256':core.file_sha(ROOT/'PACKAGE_FILES.sha256')}
        if any(proof.get(k)!=v for k,v in expected.items()):
            raise RecoveryError('RECOVERY_PROOF_IDENTITY_CHANGED')
        for name,digest in proof['evidence_file_sha256s'].items():
            core.require_file_sha(Path(name),digest)
        return proof
    original=core.read_json(state/'SUBMISSION_0.json')
    if original != {'generation':0,'shards':[0,1,2,3],'job_id':FAILED_ARRAY,'plan_sha256':PLAN_SHA}:
        raise RecoveryError('FAILED_SUBMISSION_BINDING_CHANGED')
    if any(state.glob('SUBMISSION_[123456789]*.json')):
        raise RecoveryError('LATER_SUBMISSION_PRESENT_NO_UNREGISTERED_RETRY')
    root=Path(cfg['execution_root'])
    if (root/'LAST_JOB_ID.txt').read_text().strip()!=FAILED_ARRAY:
        raise RecoveryError('LAST_JOB_CHANGED_NO_DUPLICATE_SUBMISSION')
    if (state/'CONSOLIDATION.intent.json').exists() or (state/'attempts'/FAILED_ARRAY).exists():
        raise RecoveryError('PRIOR_WORKER_COMPLETION_OR_CONSOLIDATION_PRESENT')
    if ad.ledger_shas(root)!=plan['canonical_prefix_ledger_file_sha256s']:
        raise RecoveryError('CANONICAL_PREFIX_BYTES_CHANGED')
    live,_,_,_=ad.existing_modules(cfg)
    if live.canonical_completed_prefix(execution_root=root,binding_root=Path(cfg['binding_root']))!=plan['completed_prefix_count']:
        raise RecoveryError('CANONICAL_PREFIX_IDENTITY_CHANGED')
    require_no_shard_outputs(root)
    cmd=['sacct','-n','-P','-X','-j',FAILED_ARRAY,
         '--format=JobID%40,JobIDRaw%25,State%30,ExitCode,NodeList%60,UID,JobName%40']
    result=shell(cmd)
    if result.returncode:
        raise RecoveryError('OLD_ACCOUNTING_UNAVAILABLE')
    rows=parse_failed_accounting(result.stdout,os.getuid())
    evidence={str(state/'SUBMISSION_0.json'):core.file_sha(state/'SUBMISSION_0.json'),
              str(state/'PLAN.json'):core.file_sha(state/'PLAN.json')}
    facts=[]
    for row in rows:
        sid=row['shard'];job=row['job_id'];logs=Path(cfg['execution_log_root'])
        out=logs/f'full_select_array_{FAILED_ARRAY}_{sid}.out'
        err=logs/f'full_select_array_{FAILED_ARRAY}_{sid}.err'
        innerout=root/'runtime'/f'vllm_{job}_shard{sid}.out'
        innererr=root/'runtime'/f'vllm_{job}_shard{sid}.err'
        command=root/'runtime'/f'vllm_{job}_shard{sid}.command.json'
        data={p:core.regular(p).read_bytes().decode('utf-8',errors='replace') for p in (out,err,innerout,innererr)}
        context=f'STAGE4D_ARRAY_NODE={EXCLUDED_NODE} JOB={job} ARRAY={FAILED_ARRAY} SHARD={sid}'
        if context not in data[out] or 'VLLM_EXITED_EARLY:1' not in data[err] or 'wait_ready' not in data[err]:
            raise RecoveryError('OLD_WORKER_FAILURE_STAGE_NOT_BOUND:'+str(sid))
        combined='\n'.join(data.values())
        if any(s in combined for s in ('STAGE4D_SELECT_CELL_COMPLETE','STAGE4D_PARALLEL_SHARD_DONE','STAGE4D_ARRAY_SHARD_FINISHED')):
            raise RecoveryError('OLD_WORKER_SCIENTIFIC_ACTIVITY_MARKER:'+str(sid))
        mem=memory_failure(data[innerout]+'\n'+data[innererr])
        for path in (*data,command):evidence[str(path)]=core.file_sha(path)
        facts.append({**row,'memory_failure':mem,'failure_stage':'VLLM_INIT_DEVICE_BEFORE_EXECUTE_SHARD'})
    core.write_bytes_exact(recovery/'FAILED_ACCOUNTING.txt',result.stdout.encode())
    proof={'schema_id':'STAGE4D_NODE_STARTUP_RECOVERY_AUTHORIZATION_V1',
        'failed_array_id':FAILED_ARRAY,'excluded_node':EXCLUDED_NODE,'plan_sha256':PLAN_SHA,
        'authorization_sha256':cfg['authorization_sha256'],'binding_sha256':cfg['binding_sha256'],
        'recovery_package_manifest_sha256':core.file_sha(ROOT/'PACKAGE_FILES.sha256'),
        'original_controller_manifest_sha256':OLD_MANIFEST,
        'canonical_prefix_count':plan['completed_prefix_count'],
        'scientific_cell_execution_observed_in_failed_array':False,
        'evidence_file_sha256s':evidence,'failed_workers':facts,
        'scope':'ONE_EXPLICIT_INFRASTRUCTURE_REPLACEMENT_PLUS_ORIGINAL_GRACEFUL_PARTIAL_ALLOWANCE',
        'scientific_authorization_changed':False,'outcome_adaptive_rerun':False,
        'publication_authority':'REUSE_EXISTING_STAGE4E_ONLY_AFTER_COMPLETE_RESULT_AUDIT'}
    core.write_exact(proof_path,proof)
    print('STAGE4D_NODE_STARTUP_INCIDENT_VERIFIED_ALL_FOUR',flush=True)
    print('CANONICAL_PAIR_PREFIX='+str(plan['completed_prefix_count']),flush=True)
    return proof


def submit(core, ad, jobs, cfg: dict, state: Path, plan: dict, recovery: Path,
           generation: int, shards: tuple[int,...], predecessor: str) -> dict:
    receipt=state/f'SUBMISSION_{generation}.json';intent=state/f'SUBMISSION_{generation}.intent.json'
    native=jobs.submission_command(OLD_ROOT,Path(cfg['execution_root']),PLAN_SHA,shards,Path(cfg['execution_log_root']))
    command=with_exclusion(native)
    expected_intent={'generation':generation,'shards':list(shards),'plan_sha256':PLAN_SHA,
        'command':command,'authorization_sha256':cfg['authorization_sha256'],
        'recovery_authorization_file_sha256':core.file_sha(recovery/'RECOVERY_AUTHORIZATION.json'),
        'predecessor_array_job_id':predecessor,'excluded_nodes':[EXCLUDED_NODE]}
    if receipt.exists():
        value=core.read_json(receipt)
        if core.read_json(intent)!=expected_intent or value.get('generation')!=generation or value.get('shards')!=list(shards) or value.get('plan_sha256')!=PLAN_SHA or not str(value.get('job_id','')).isdigit():
            raise RecoveryError('RECOVERY_SUBMISSION_LINEAGE_CHANGED')
        pointer=Path(cfg['execution_root'])/'LAST_JOB_ID.txt'
        current=pointer.read_text().strip()
        if current not in (predecessor,value['job_id']):
            # A previously submitted graceful-partial successor must not be rewound.
            successor=state/f'SUBMISSION_{generation+1}.json'
            next_intent=state/f'SUBMISSION_{generation+1}.intent.json'
            if generation!=FIRST_GENERATION or not successor.is_file() or not next_intent.is_file():
                raise RecoveryError('EXTERNAL_JOB_POINTER_CHANGED')
            nxt=core.read_json(successor);ni=core.read_json(next_intent)
            if (nxt.get('job_id')!=current or nxt.get('generation')!=generation+1
                    or nxt.get('plan_sha256')!=PLAN_SHA or not current.isdigit()
                    or ni.get('predecessor_array_job_id')!=value['job_id']
                    or ni.get('recovery_authorization_file_sha256')!=expected_intent['recovery_authorization_file_sha256']):
                raise RecoveryError('RECOVERY_SUCCESSOR_LINEAGE_CHANGED')
        else:
            ad.write_pointer(pointer,value['job_id'])
        return value
    if intent.exists():
        raise RecoveryError('RECOVERY_SUBMISSION_AMBIGUOUS_INTENT_NO_RETRY')
    if (Path(cfg['execution_root'])/'LAST_JOB_ID.txt').read_text().strip()!=predecessor:
        raise RecoveryError('EXTERNAL_SUBMISSION_DETECTED')
    core.write_exact(intent,expected_intent)
    try: result=shell(command)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise RecoveryError('RECOVERY_SBATCH_AMBIGUOUS_NO_RETRY') from exc
    core.write_bytes_exact(state/f'SUBMISSION_{generation}.stdout',result.stdout.encode())
    core.write_bytes_exact(state/f'SUBMISSION_{generation}.stderr',result.stderr.encode())
    if result.returncode:raise RecoveryError('RECOVERY_SBATCH_FAILED_NO_RETRY')
    job=jobs.parse_parsable_job(result.stdout)
    value={'generation':generation,'shards':list(shards),'job_id':job,'plan_sha256':PLAN_SHA}
    core.write_exact(receipt,value)
    ad.write_pointer(Path(cfg['execution_root'])/'LAST_JOB_ID.txt',job)
    print('STAGE4D_NODE_EXCLUDED_ARRAY_SUBMITTED',flush=True)
    print('ARRAY_JOB_ID='+job+'\nEXCLUDED_NODE='+EXCLUDED_NODE+'\nARRAY_SHARDS='+','.join(map(str,shards)),flush=True)
    return value


def follow(core,ad,jobs,cfg,state,plan,recovery):
    statuses={};shards=(0,1,2,3);predecessor=FAILED_ARRAY
    for generation in (FIRST_GENERATION,FIRST_GENERATION+1):
        item=submit(core,ad,jobs,cfg,state,plan,recovery,generation,shards,predecessor)
        job=item['job_id'];unknown=0;previous=None
        while True:
            status,raw=jobs.query_array(job,shards)
            if raw!=previous:
                print('STAGE4E_RECOVERY_ARRAY_STATUS='+job+'\n'+raw.strip(),flush=True);previous=raw
            if status=='STOP':raise RecoveryError('RECOVERY_ARRAY_FAILED_NO_AUTOMATIC_RETRY:'+job)
            if status=='COMPLETE':break
            unknown=unknown+1 if status=='UNKNOWN' else 0
            if unknown>=5:raise RecoveryError('RECOVERY_ACCOUNTING_UNKNOWN')
            time.sleep(cfg['poll_seconds'])
        for shard in shards:statuses[shard]=ad.load_worker_status(cfg,state,plan,job,shard)
        if set(statuses)!=set(range(4)):raise RecoveryError('RECOVERY_SHARD_UNIVERSE_INCOMPLETE')
        shards=jobs.incomplete_shards(statuses)
        if not shards:return
        print('STAGE4D_RECOVERY_GRACEFUL_PARTIAL_SHARDS='+','.join(map(str,shards)),flush=True)
        predecessor=job
    raise RecoveryError('RECOVERY_GRACEFUL_PARTIAL_BUDGET_EXHAUSTED')


def archive_source(core,driver,repo: Path) -> None:
    # Add the recovery adapter to the isolated integration history; never to the active checkout.
    source=importlib.import_module('stage4e.source')
    if source.git(repo,'status','--porcelain'):
        raise RecoveryError('INTEGRATION_CHECKOUT_DIRTY')
    inventory=core.verify_inventory(ROOT)
    names=[];entries=[]
    for name in [*inventory,'PACKAGE_FILES.sha256']:
        raw=core.regular(ROOT/name).read_bytes();source.reject_secret(raw,name)
        target=f'{source.SNAPSHOT_PREFIX}/{ROOT.name}/{name}'
        core.write_bytes_exact(repo/target,raw);names.append(target)
        entries.append({'path':target,'source_path':str(ROOT/name),'file_sha256':hashlib.sha256(raw).hexdigest()})
    target=f'{source.DOC_PREFIX}/NODE_RECOVERY_SOURCE_PROVENANCE.json'
    core.write_exact(repo/target,{'schema_id':'NODE_RECOVERY_SOURCE_PROVENANCE_V1','files':entries,
        'original_worker_unchanged':True,'original_array_plan_sha256':PLAN_SHA,
        'code_chain':'recover.main -> preflight -> submit(original array_shard.sh) -> original shard_worker -> original load_worker_status -> original consolidate -> original driver.finalize',
        'excluded_node':EXCLUDED_NODE,'scientific_execution_claimed_by_source_archive':False})
    names.append(target);source.stage_explicit(repo,names)
    source.commit_staged(repo,'Archive exact node-excluded infrastructure recovery adapter')


def main() -> int:
    p=argparse.ArgumentParser();p.add_argument('--check-only',action='store_true');args=p.parse_args()
    core,ad,jobs,driver=load_original()
    core.verify_inventory(ROOT)
    cfg=core.read_json(OLD_ROOT/'config.json');control=Path(cfg['control_root'])
    root=Path(cfg['execution_root']);state=root/ad.STATE_REL;recovery=state/RECOVERY_REL
    if not (control/'SOURCE_PREPARATION.json').is_file():
        raise RecoveryError('EXISTING_SOURCE_PREPARATION_REQUIRED')
    if not (state/'PLAN.json').is_file():raise RecoveryError('EXISTING_ARRAY_PLAN_REQUIRED')
    fd=os.open(control/'driver.lock',os.O_CREAT|os.O_RDWR,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        active=driver.base_gate(cfg)
        plan=ad.freeze_plan(cfg,state,'156834')
        if plan['plan_sha256']!=PLAN_SHA:raise RecoveryError('REGISTERED_PLAN_CHANGED')
        if (root/driver.COMPLETE).exists():
            if not (recovery/'RECOVERY_AUTHORIZATION.json').exists():
                raise RecoveryError('COMPLETE_WITHOUT_THIS_RECOVERY_NO_ACTION')
            from stage4e.audit import completion_gate
            completion_gate(root,cfg)
            if args.check_only:return 0
            active,repo=driver.prepare(cfg,control)
            archive_source(core,driver,repo);driver.finalize(cfg,control,repo,active);return 0
        lock=os.open(root/'full_select_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            preflight(core,ad,cfg,state,plan,recovery)
        finally:os.close(lock)
        if args.check_only:
            print('RECOVERY_PREFLIGHT_PASS_NO_JOB_SUBMITTED',flush=True);return 0
        # Existing receipt validates source contents; full repository tests are not repeated unnecessarily.
        active,repo=driver.prepare(cfg,control)
        archive_source(core,driver,repo)
        follow(core,ad,jobs,cfg,state,plan,recovery)
        lock=os.open(root/'full_select_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            ad.consolidate(cfg,state,plan)
        finally:os.close(lock)
        driver.finalize(cfg,control,repo,active)
        return 0
    finally:os.close(fd)

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print('STOP='+str(exc),file=sys.stderr,flush=True)
        raise SystemExit(70)

"""Exact producer repair/reentry. Does not scan or copy old shard outputs."""
from __future__ import annotations
import argparse,fcntl,hashlib,json,os,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from recovery_core import *
from safe_io import safe_extract_zip
from submission_contract import build_array_sbatch_argv,parse_job_id
from request_hash_repair import materialize_request_repair

PACKAGE=Path(__file__).resolve().parent

def scoped_context(rt:Path):
    rt=rt.resolve();auth_path=rt/'ROUND_ROLLOUT_PRODUCER_AUTHORITY_V1.json';a=load_json(auth_path)
    if a.get('schema_id')!='ROUND_ROLLOUT_PRODUCER_AUTHORITY_V1':raise ValueError('PRODUCER_AUTHORITY_SCHEMA')
    old=Path(a['previous_rollout_state_root']);failed=Path(a['next_round_state_root'])
    if old.resolve()==failed.resolve():raise ValueError('FRESH_ROUND_ROOT_NOT_DISTINCT')
    material=load_json(rt/'R2_PRODUCER_MATERIALIZATION_V1.json')
    old_runner=parse_runner(require_file(Path(a['previous_state_local_runner_path']),a['previous_state_local_runner_sha256']))
    runner=parse_runner(require_file(Path(material['runner_path']),material['runner_sha256']))
    if Path(runner['--state-root']).resolve()!=failed.resolve() or Path(old_runner['--state-root']).resolve()!=old.resolve():raise ValueError('RUNNER_STATE_BINDING_MISMATCH')
    if Path(runner['--v1230-output-root']).resolve()!=Path(old_runner['--v1230-output-root']).resolve():raise ValueError('IMPLEMENTATION_ROOT_REBOUND')
    source=Path(a['producer_package_root'])
    hashes=load_json(PACKAGE/'audit/REVIEWED_SOURCE_HASHES.json')['hashes']
    for name in ('shard_worker.py','global_finalize.py','formal_rollout_support.py','shard_math.py','safe_io.py','submission_contract.py'):
        require_file(source/name,hashes['producer_source/'+name])
    if Path(runner['worker']).resolve()!=source.resolve()/'shard_worker.py':raise ValueError('WORKER_NOT_REGISTERED_PRODUCER')
    if Path(old_runner['python']).resolve()!=Path(sys.executable).resolve():raise ValueError('REQUIRES_REGISTERED_PYTHON_INTERPRETER')
    request=require_file(Path(a['next_rollout_request_path']),a['next_rollout_request_sha256'])
    previous_request=require_file(Path(a['previous_rollout_request_path']),a['previous_rollout_request_sha256'])
    if load_json(request)['round_id']==load_json(previous_request)['round_id']:raise ValueError('REQUEST_NOT_NEW_SCIENTIFIC_ROUND')
    plan=load_json(require_file(Path(material['shard_plan_path']),material['shard_plan_sha256']))
    previous_plan=load_json(require_file(Path(a['previous_shard_plan_path']),a['previous_shard_plan_sha256']))
    if plan['fresh_execution_attempt_ordinal']!=a['next_round_fresh_execution_attempt_ordinal']:raise ValueError('ATTEMPT_ORDINAL_AUTHORITY_CONFLICT')
    capsule=require_file(Path(old_runner['--capsule']),previous_plan['repaired_capsule_sha256'])
    inventory=load_json(PACKAGE/'audit/REVIEWED_CAPSULE_INVENTORY.json')
    if sha_file(capsule)!=inventory['sha256'] or sha_file(capsule)!=plan['repaired_capsule_sha256']:raise ValueError('CAPSULE_NOT_REVIEWED_INPUT_ASSET')
    check_capsule_inventory(capsule,inventory)
    missing=Path(runner['--capsule'])
    if not missing.is_relative_to(failed) or missing.name!=capsule.name:raise ValueError('MISSING_CAPSULE_SCOPE')
    gate=load_json(failed/'PCHSI_V1232K_GATE_FAILURE_V1.json')
    gate_id=plan['staged_release_gate']['initially_release_only_shard_id'];count=plan['shard_count']
    if type(count) is not int or count<=0 or type(gate_id) is not int or not 0<=gate_id<count:raise ValueError('SHARD_PLAN_CARDINALITY')
    if gate.get('gate_shard_id')!=gate_id or gate.get('reason')!='GATE_SHARD_FATAL:FileNotFoundError':raise ValueError('ORIGINAL_GATE_FAILURE_CHANGED')
    fatal_path=failed/'shards'/f'{gate_id:04d}'/'PCHSI_V1232S_SHARD_FATAL_V1.json'
    fatal=load_json(fatal_path)
    filename=validate_capsule_missing_fatal(fatal,missing)
    if missing.exists():raise ValueError('FAILED_CAPSULE_PATH_NOW_POPULATED_EXTERNAL_MUTATION')
    forbidden=['PCHSI_V1232K_FULL_ARRAY_RELEASE_RECEIPT_V1.json','round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json']
    for p in forbidden:
        if (failed/p).exists():raise ValueError('FAILED_ROOT_ADVANCED_DO_NOT_REEXECUTE:'+p)
    for sid in range(count):
        sh=failed/'shards'/f'{sid:04d}'
        for p in ('PCHSI_V1232S_ALLOCATION_PREFLIGHT_RESULT_V1.json','PCHSI_V1232S_PRELAUNCH_ENDPOINT_PROBE_V1.json','PCHSI_V1232S_SHARD_TERMINALS_V1.json'):
            if (sh/p).exists():raise ValueError('ORIGINAL_ATTEMPT_PROGRESS_NOT_ZERO:'+str(sh/p))
        for dirname in ('cell_terminals','rollout_run'):
            p=sh/dirname
            if p.exists() and (not p.is_dir() or next(p.iterdir(),None) is not None):raise ValueError('ORIGINAL_SCIENTIFIC_OUTPUT_PRESENT:'+str(p))
    return {'rt':rt,'authority':a,'authority_path':auth_path,'failed':failed,'old':old,'request':request,'plan':plan,
        'capsule':capsule,'worktree':Path(runner['--v1230-output-root'])/'build/worktree',
        'v1230':Path(runner['--v1230-output-root']),'gate':gate,'fatal_path':fatal_path,'fatal':fatal,'filename':filename}

def prepare(ctx,settings):
    rt=ctx['rt'];source_hashes=load_json(PACKAGE/'audit/PATCHED_SOURCE_IDENTITY.json')
    verify_source_identity(PACKAGE,source_hashes)
    identity={'request_sha256':sha_file(ctx['request']),'original_fatal_sha256':sha_file(ctx['fatal_path']),
        'capsule_sha256':sha_file(ctx['capsule']),'patch_identity':source_hashes,'settings':settings}
    digest=hashlib.sha256(b'R2_NATIVE_PRODUCER_SCOPE_RECOVERY_V1\0'+canonical_bytes(identity)).hexdigest()
    root=rt/'native_producer_recovery'/digest;root.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=(root/'RECOVERY_WRITER.lock').open('a+')
    try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('RECOVERY_WRITER_ALREADY_ACTIVE')
    req=root/'round_evidence/ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json';req.parent.mkdir(exist_ok=True)
    repair_receipt_path=root/'R2_ROLLOUT_REQUEST_CANONICAL_HASH_REPAIR_V1.json'
    # This uses a fresh temporary extraction of the registered input archive only.
    with tempfile.TemporaryDirectory(prefix='native_preflight_',dir=root) as temp:
        extracted=Path(temp)/'capsule';safe_extract_zip(ctx['capsule'],extracted)
        repair=materialize_request_repair(ctx['request'],ctx['worktree'],extracted,req,repair_receipt_path)
        print('R2_REQUEST_HASH_REPAIR=PASS',flush=True)
        print('SOURCE_EMBEDDED_REQUEST_SHA256='+repair['source_embedded_request_sha256'],flush=True)
        print('CANONICAL_EMBEDDED_REQUEST_SHA256='+repair['canonical_embedded_request_sha256'],flush=True)
        plan=dict(ctx['plan']);plan.update({'current_round_request_path':str(req),'current_round_request_file_sha256':sha_file(req),
            'infrastructure_recovery_identity':digest,'original_gate_failure_path':str(ctx['failed']/'PCHSI_V1232K_GATE_FAILURE_V1.json'),
            'original_gate_failure_sha256':sha_file(ctx['failed']/'PCHSI_V1232K_GATE_FAILURE_V1.json'),
            'request_hash_repair_receipt_path':str(repair_receipt_path),'request_hash_repair_receipt_sha256':sha_file(repair_receipt_path)})
        plan_path=root/'PCHSI_V1232K_SHARD_PLAN_V1.json';equal_or_new(plan_path,plan)
        script=root/'run_v1232k_array_task.sh'
        argv=[sys.executable,'-B',str(PACKAGE/'producer/shard_worker.py'),'--state-root',str(root),'--v1230-output-root',str(ctx['v1230']),
            '--capsule',str(ctx['capsule']),'--shard-plan',str(plan_path)]
        body='#!/usr/bin/env bash\nexec '+ ' '.join(shlex.quote(v) for v in argv)+' --shard-id "${SLURM_ARRAY_TASK_ID}"\n'
        if script.exists():
            if script.read_text()!=body:raise ValueError('BATCH_SCRIPT_CONFLICT')
        else:write_new_bytes(script,body.encode(),mode=0o700)
        slurm=load_json(extracted/'ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_SLURM_RESOURCE_PLAN_V1.json')
        native_output=root/'NATIVE_CPU_PREFLIGHT.json'
        print('NATIVE_CPU_PREFLIGHT=RUNNING',flush=True)
        cp=cmd([sys.executable,'-B',str(PACKAGE/'native_preflight.py'),'--capsule-root',str(extracted),'--worktree',str(ctx['worktree']),
            '--request',str(req),'--plan',str(plan_path),'--output',str(native_output)],timeout=settings['native_preflight_timeout_seconds'])
        # Diagnostics are immutable per invocation, never used as scientific input.
        if cp['returncode']!=0:
            print(cp['stdout'],end='',flush=True);print(cp['stderr'],end='',flush=True)
            raise ValueError('NATIVE_CPU_PREFLIGHT_FAILED:'+str(cp['returncode']))
        print(cp['stdout'],end='',flush=True)
        sbatch=build_array_sbatch_argv(slurm_plan=slurm,shard_count=plan['shard_count'],max_concurrent_shards=plan['max_concurrent_shards'],
            walltime_minutes=plan['derived_walltime_minutes_per_shard'],script_path=script,
            stdout_path=root/'slurm-%A_%a.out',stderr_path=root/'slurm-%A_%a.err',activation=digest)
    analyzer_output=root/'ANALYZER_NATIVE_API_PREFLIGHT.json'
    aq=cmd([sys.executable,'-B',str(PACKAGE/'analyzer_preflight.py'),'--root',str(root),'--output',str(analyzer_output)],timeout=settings['native_preflight_timeout_seconds'])
    if aq['returncode']!=0:
        print(aq['stdout'],end='',flush=True);print(aq['stderr'],end='',flush=True)
        raise ValueError('EXISTING_ANALYZER_API_PREFLIGHT_FAILED:'+str(aq['returncode']))
    print(aq['stdout'],end='',flush=True)
    runtime={'schema_id':'NATIVE_R2_RECOVERY_READY_V1','root':str(root),'source_round_tail':str(rt),
        'source_request':str(ctx['request']),'source_request_file_sha256':sha_file(ctx['request']),
        'request_path':str(req),'request_file_sha256':sha_file(req),
        'request_repair_receipt_path':str(repair_receipt_path),'request_repair_receipt_sha256':sha_file(repair_receipt_path),
        'round_id':load_json(req)['round_id'],'shard_plan_path':str(plan_path),'shard_plan_sha256':sha_file(plan_path),
        'capsule_path':str(ctx['capsule']),'capsule_sha256':sha_file(ctx['capsule']),
        'original_fatal_path':str(ctx['fatal_path']),'original_fatal_sha256':sha_file(ctx['fatal_path']),
        'analyzer_preflight_path':str(analyzer_output),'analyzer_preflight_sha256':sha_file(analyzer_output),
        'native_preflight_path':str(native_output),'native_preflight_sha256':sha_file(native_output),
        'gate_shard_id':plan['staged_release_gate']['initially_release_only_shard_id'],'sbatch_argv':sbatch,'settings':settings,
        'source_package':str(PACKAGE),'source_identity':source_hashes,'old_outputs_replayed':False,
        'scientific_request_semantics_changed':False,'serialized_integrity_hash_repaired':repair['mutation_scope']=='REQUEST_SHA256_ONLY',
        'new_scientific_round_created':False,'full_campaign_released':False}
    equal_or_new(root/'READY.json',runtime)
    return root,runtime,lock

def execute(ctx,root,ready):
    # One cross-package owner for this scientific request; no timestamp-derived reexecution.
    owner={'schema_id':'R2_NATIVE_RECOVERY_OWNER_V1','request_sha256':ready['request_file_sha256'],'root':str(root),'source_identity':ready['source_identity']}
    equal_or_new(ctx['rt']/'R2_NATIVE_PRODUCER_RECOVERY_OWNER_V1.json',owner)
    receipt_path=root/'SUBMISSION_RECEIPT.json';intent=root/'SUBMISSION_INTENT.json'
    if receipt_path.is_file():
        receipt=load_json(receipt_path)
        if receipt.get('ready_sha256')!=sha_file(root/'READY.json'):raise ValueError('SUBMISSION_READY_IDENTITY_CHANGED')
        print('STATUS=ADOPT_EXISTING_SUBMISSION_NO_RESEND',flush=True)
        print('R2_ARRAY_JOB_ID='+receipt['array_job_id'],flush=True)
        return
    if intent.exists():raise ValueError('SUBMISSION_INTENT_WITHOUT_RECEIPT_AMBIGUOUS_NO_RESEND')
    inactive=assert_old_array_inactive(str(ctx['gate']['array_job_id']),ctx['gate'],ctx['plan']['shard_count'],ready['gate_shard_id'])
    equal_or_new(root/'PREDECESSOR_CONTAINMENT.json',inactive)
    write_new_json(intent,{'schema_id':'NATIVE_R2_SUBMISSION_INTENT_V1','ready_sha256':sha_file(root/'READY.json'),'argv':ready['sbatch_argv']})
    r=cmd(ready['sbatch_argv'])
    write_new_json(root/'SUBMISSION_ATTEMPT.json',r)
    if r['returncode']!=0:raise ValueError('SUBMISSION_FAILED_NO_AUTO_RESEND:'+r['stderr'])
    job=parse_job_id(r['stdout'])
    receipt={'schema_id':'NATIVE_R2_SUBMISSION_RECEIPT_V1','array_job_id':job,'ready_sha256':sha_file(root/'READY.json'),'submitted_held':True}
    write_new_json(receipt_path,receipt)
    # Start the monitor before it releases the gate. The monitor owns that step.
    log=(root/'resident.log').open('ab',buffering=0)
    child_argv=[sys.executable,'-u','-B',str(PACKAGE/'supervise.py'),'--root',str(root)]
    write_new_json(root/'RESIDENT_START_INTENT.json',{'argv':child_argv,'array_job_id':job})
    try:
        p=subprocess.Popen(child_argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ))
    except OSError as exc:
        contained=cmd(['scancel',job])
        write_new_json(root/'RESIDENT_START_FAILURE_CONTAINMENT.json',{'array_job_id':job,'error_type':type(exc).__name__,'error_message':str(exc),'containment':contained})
        raise
    finally:
        log.close()
    write_new_json(root/'RESIDENT_LAUNCH.json',{'pid':p.pid,'host':socket.gethostname(),'argv':child_argv,'array_job_id':job})
    print('R2_ARRAY_JOB_ID='+job,flush=True)
    print('R2_GATE_ARRAY_ELEMENT='+job+'_'+str(ready['gate_shard_id']),flush=True)
    print('RESIDENT_PID='+str(p.pid),flush=True)
    print('RESIDENT_LOG='+str(root/'resident.log'),flush=True)
    print('STATUS=NATIVE_PRODUCER_RECOVERY_SUBMITTED_HELD_RESIDENT_STARTED',flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--round-tail-state-root',type=Path,required=True);ap.add_argument('--execute-if-safe',action='store_true')
    ap.add_argument('--watch-timeout-seconds',type=int,required=True);ap.add_argument('--analyzer-timeout-seconds',type=int,required=True)
    ap.add_argument('--native-preflight-timeout-seconds',type=int,default=600);ap.add_argument('--poll-seconds',type=int,default=30);ap.add_argument('--publication-grace-seconds',type=int,default=120)
    a=ap.parse_args();settings={k:v for k,v in vars(a).items() if k not in {'round_tail_state_root','execute_if_safe'}}
    if any(type(v) is not int or v<=0 for v in settings.values()):raise ValueError('TIMEOUT_AUTHORITY_INVALID')
    ctx=scoped_context(a.round_tail_state_root)
    print('EXACT_REGISTERED_CAPSULE_MISSING_ROOT=CONFIRMED',flush=True)
    print('ORIGINAL_FATAL_PATH='+str(ctx['fatal_path']),flush=True)
    print('ORIGINAL_MISSING_PATH='+ctx['filename'],flush=True)
    root,ready,lock=prepare(ctx,settings)
    print('RECOVERY_ROOT='+str(root),flush=True)
    print('CURRENT_REQUEST_SHA256='+ready['request_file_sha256'],flush=True)
    print('CURRENT_ROUND_SCOPE_AND_SHARED_SCHEDULE_PREFLIGHT=PASS',flush=True)
    if a.execute_if_safe:execute(ctx,root,ready)
    else:print('STATUS=NATIVE_PREFLIGHT_PASS_NO_SUBMISSION',flush=True)
    print('FULL_MAX10_AUTONOMOUS_CAMPAIGN_RELEASED=false',flush=True)
    lock.close();return 0

if __name__=='__main__':
    try:rc=main()
    except Exception as exc:
        print('STATUS=NATIVE_PRODUCER_RECOVERY_FAIL_CLOSED',flush=True)
        print('ERROR_TYPE='+type(exc).__name__,flush=True);print('ERROR_MESSAGE='+str(exc),flush=True)
        print('HUMAN_RETRY_DECISION_REQUIRED=false',flush=True);print('SAME_LOGICAL_SUBMISSION_RESEND_AUTHORIZED=false',flush=True)
        rc=20
    raise SystemExit(rc)

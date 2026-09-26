"""One monitor for one submitted recovery. Reuses existing producer and Analyzer.

The terminal flag distinguishes rollout proof, local Analyzer reentry, and the
NOT-YET-RELEASED full hierarchical/campaign execution. Never resubmits jobs.
"""
from __future__ import annotations
import argparse,fcntl,hashlib,json,os,signal,socket,subprocess,sys,time,traceback
from pathlib import Path
from recovery_core import *
from runtime_surface_preflight import validate_runtime_surface

def status(root:Path,value:dict):
    text=canonical_bytes(value);tmp=root/('RECOVERY_STATUS.tmp.'+str(os.getpid()))
    with tmp.open('wb') as f:f.write(text);f.flush();os.fsync(f.fileno())
    os.replace(tmp,root/'RECOVERY_STATUS.json')
    print(json.dumps(value,ensure_ascii=False,sort_keys=True),flush=True)

def terminal(root:Path,name:str,**fields):
    o={'schema_id':'NATIVE_R2_RECOVERY_TERMINAL_V1','status':name,
       'full_max10_autonomous_campaign_released':False,'full_hierarchical_analyzer_closed':False,
       'training_executed_by_recovery':False,'human_retry_decision_required':False,**fields}
    equal_or_new(root/'RECOVERY_TERMINAL.json',o);status(root,o);return o

def publication_ready(root:Path)->bool:
    ev=root/'round_evidence'
    return (ev/'ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json').is_file() and (ev/'PCHSI_V1232K_GLOBAL_TERMINAL_V1.json').is_file()

def validate_handoff(root:Path,ready:dict):
    hp=root/'round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json';h=load_json(hp)
    gt=load_json(root/'round_evidence/PCHSI_V1232K_GLOBAL_TERMINAL_V1.json')
    if gt.get('scientific_rollout_valid') is not True or gt.get('handoff_sha256')!=sha_file(hp) or Path(gt.get('handoff_path',''))!=hp:
        raise ValueError('GLOBAL_TERMINAL_HANDOFF_BINDING_MISMATCH')
    if h.get('schema_id')!='ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1' or h.get('scientific_rollout_valid') is not True:
        raise ValueError('ROLLOUT_HANDOFF_NOT_VALID')
    if h.get('round_id')!=ready['round_id'] or h.get('rollout_request_sha256')!=ready['request_file_sha256']:
        raise ValueError('HANDOFF_CURRENT_REQUEST_IDENTITY_MISMATCH')
    for pathkey,shakey in [('rollout_request_path','rollout_request_sha256'),('rollout_universe_path','rollout_universe_sha256'),('rollout_execution_binding_path','rollout_execution_binding_sha256'),('failure_cohort_path','failure_cohort_sha256'),('attempt_bundle_index_path','attempt_bundle_index_sha256')]:
        p=Path(h[pathkey]);require_file(p,h[shakey])
        if not p.resolve().is_relative_to(root.resolve()):raise ValueError('HANDOFF_OUTSIDE_CURRENT_RECOVERY_ROOT')
    if h.get('infrastructure_invalid_count')!=0 or h.get('protocol_invalid_count')!=0:raise ValueError('HANDOFF_INVALID_ROWS')
    return hp,h

def run(root:Path):
    root=root.resolve();lock=(root/'RESIDENT_WRITER.lock').open('a+')
    try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise ValueError('RESIDENT_ALREADY_ACTIVE')
    if (root/'RECOVERY_TERMINAL.json').exists():return
    ready=load_json(root/'READY.json');sub=load_json(root/'SUBMISSION_RECEIPT.json')
    if sha_file(root/'READY.json')!=sub['ready_sha256']:raise ValueError('READY_CHANGED_AFTER_SUBMISSION')
    verify_source_identity(Path(ready['source_package']),ready['source_identity'])
    require_file(Path(ready['request_path']),ready['request_file_sha256'])
    require_file(Path(ready['capsule_path']),ready['capsule_sha256'])
    require_file(Path(ready['shard_plan_path']),ready['shard_plan_sha256'])
    settings=ready['settings'];job=sub['array_job_id']
    status(root,{'status':'RESIDENT_STARTED_GATE_HELD','array_job_id':job,'pid':os.getpid(),'host':socket.gethostname()})
    release=root/'GATE_RELEASE_RECEIPT.json';release_intent=root/'GATE_RELEASE_INTENT.json'
    if not release.exists():
        if release_intent.exists():raise ValueError('GATE_RELEASE_AMBIGUOUS_NO_RESEND')
        target=job+'_'+str(ready['gate_shard_id']);write_new_json(release_intent,{'target':target})
        cp=cmd(['scontrol','release',target]);write_new_json(release,cp)
        if cp['returncode']!=0:raise ValueError('GATE_RELEASE_FAILED_NO_RESEND:'+cp['stderr'])
    if load_json(release).get('returncode')!=0:raise ValueError('GATE_RELEASE_FAILED_NO_RESEND')
    started=time.monotonic();empty_since=None;last=None
    while time.monotonic()-started<settings['watch_timeout_seconds']:
        fail=root/'PCHSI_V1232K_GATE_FAILURE_V1.json'
        if fail.exists():
            f=load_json(fail);fp=root/'shards'/f"{ready['gate_shard_id']:04d}"/'PCHSI_V1232S_SHARD_FATAL_V1.json'
            fatal=load_json(fp) if fp.exists() else None
            terminal(root,'RECOVERY_GATE_FAILED_NO_AUTOMATIC_SECOND_SUBMISSION',gate_failure=f,shard_fatal=fatal,
                gate_failure_sha256=sha_file(fail),r2_rollout_live_proven=False);return
        ff=root/'round_evidence/PCHSI_V1232K_GLOBAL_FINALIZE_FAILURE_V1.json'
        if ff.exists():
            terminal(root,'RECOVERY_FINALIZER_FAILED_NO_CELL_RERUN',finalizer_failure=load_json(ff),r2_rollout_live_proven=False);return
        hp=root/'round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json'
        if publication_ready(root):
            hp,h=validate_handoff(root,ready);break
        q=cmd(['squeue','--noheader','--jobs',job,'--format','%i|%T'])
        qstate=queue_state(q['returncode'],q['stdout'],q['stderr'])
        # A bounded publication grace allows the existing finalizer to finish.
        if qstate in {'EMPTY','NOT_IN_QUEUE'}:
            if empty_since is None:empty_since=time.monotonic()
            if time.monotonic()-empty_since>settings['publication_grace_seconds']:
                terminal(root,'ARRAY_INACTIVE_WITHOUT_VALID_HANDOFF',scheduler=q,r2_rollout_live_proven=False);return
        else:empty_since=None
        now={'status':'WAITING_FOR_NATIVE_SCIENTIFIC_HANDOFF','array_job_id':job,'queue_state':qstate,
            'elapsed_seconds':round(time.monotonic()-started),'queue_rows':q['stdout'].splitlines()}
        # One heartbeat per configured poll; scheduler RPC load is bounded.
        status(root,now);time.sleep(settings['poll_seconds'])
    else:
        terminal(root,'RECOVERY_WATCH_DEADLINE_NO_RESUBMISSION',r2_rollout_live_proven=False);return
    # Revalidate the same registered Analyzer worktree before any provider entry.
    from analyzer_preflight import existing_driver
    ar=load_json(require_file(Path(ready['analyzer_preflight_path']),ready['analyzer_preflight_sha256']))
    qmodule=existing_driver();repo,_=qmodule.discover_strong_repo(root)
    analyzer_surface=Path(__file__).resolve().parent/'audit/ANALYZER_RUNTIME_SURFACE_PREFLIGHT_V1.json'
    if str(repo)!=ar['repo_path'] or checked(['git','-C',str(repo),'rev-parse','HEAD'])!=ar['repo_head']:
        raise ValueError('ANALYZER_REPO_CHANGED_AFTER_PREFLIGHT')
    validate_runtime_surface(repo,None,analyzer_surface)
    qdriver=Path(ready['source_package'])/'vendor/V1232Q/v1232q_driver.py'
    intent=root/'ANALYZER_REENTRY_INTENT.json'
    if intent.exists():raise ValueError('ANALYZER_REENTRY_ALREADY_STARTED_NO_RESEND')
    args=[sys.executable,'-u','-B',str(qdriver),'--v1232k-state-root',str(root)]
    write_new_json(intent,{'argv':args,'handoff_path':str(hp),'handoff_sha256':sha_file(hp)})
    status(root,{'status':'VALID_ROLLOUT_AUTOMATIC_EXISTING_ANALYZER_REENTRY','round_id':h['round_id'],'r2_rollout_live_proven':True})
    logpath=root/'analyzer_reentry.log'
    with logpath.open('xb',buffering=0) as log:
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ))
        write_new_json(root/'ANALYZER_REENTRY_LAUNCH.json',{'argv':args,'pid':p.pid,'host':socket.gethostname()})
        try:rc=p.wait(timeout=settings['analyzer_timeout_seconds'])
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGTERM)
            try:p.wait(timeout=30)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
            terminal(root,'ANALYZER_DEADLINE_CALL_STATE_MUST_BE_RECONCILED_NO_RESEND',r2_rollout_live_proven=True,analyzer_reentry_rc=None);return
    terminal(root,('R2_VALID_ROLLOUT_AND_ANALYZER_LOCAL_PREP_COMPLETED' if rc==0 else 'R2_VALID_ROLLOUT_ANALYZER_TYPED_TERMINAL_NO_RESEND'),
        r2_rollout_live_proven=True,analyzer_reentry_rc=rc,analyzer_log_path=str(logpath),analyzer_log_sha256=sha_file(logpath),
        rollout_handoff_path=str(hp),rollout_handoff_sha256=sha_file(hp),
        remaining_scope='EXISTING_GROUP_ANALYZER_TAIL_AND_CAMPAIGN_CONSOLIDATION_NOT_EXECUTED_BY_V1232Q')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);n=a.parse_args()
    try:run(n.root)
    except Exception as exc:
        try:terminal(n.root,'RECOVERY_RESIDENT_CONTROL_ERROR_NO_RESEND',error_type=type(exc).__name__,error_message=str(exc),traceback=traceback.format_exc())
        except Exception:print(traceback.format_exc(),flush=True)
        raise SystemExit(20)

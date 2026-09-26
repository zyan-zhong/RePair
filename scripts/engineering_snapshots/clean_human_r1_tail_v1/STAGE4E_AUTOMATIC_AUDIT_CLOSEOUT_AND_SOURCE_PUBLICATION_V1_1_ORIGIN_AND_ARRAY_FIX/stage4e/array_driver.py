"""Independent Slurm shard placement around the unchanged Stage4D V1.3 worker.

The server-side coordinator runs synchronously. Only outcome-independent job
status and completeness are used before the existing Stage4E result audit.
"""
from __future__ import annotations
import argparse
import fcntl
import importlib
import importlib.metadata
import os
from pathlib import Path
import subprocess
import sys
import time
from . import (GateError, read_json, file_sha, require_file_sha, write_exact,
               write_bytes_exact, verify_inventory, semantic_sha)
from . import driver
from .array_jobs import (partition_from_prefix, parse_parsable_job, submission_command,
                         incomplete_shards, query_array, cancel_pending_once)
from .source import ensure_isolated_repo

ROOT = Path(__file__).resolve().parents[1]
STATE_REL = 'parallel_v1/independent_jobs_v1'


def existing_modules(cfg: dict):
    full = Path(cfg['full_package'])
    sys.path.insert(0, str(full))
    live = importlib.import_module('stage4d_full.live')
    shard_worker = importlib.import_module('stage4d_full.shard_worker')
    entry = importlib.import_module('stage4d_full.slurm_entry')
    parallel = importlib.import_module('stage4d_full.parallel')
    for module in (live, shard_worker, entry, parallel):
        if not Path(module.__file__).resolve().is_relative_to(full.resolve()):
            raise GateError('ORIGINAL_STAGE4D_IMPORT_ROOT_CHANGED')
    return live, shard_worker, entry, parallel


def ledger_shas(root: Path) -> dict:
    return {label:file_sha(root/'execution'/label/'cell_receipts.jsonl') for label in ('t0','t2')}


def freeze_plan(cfg: dict, state_root: Path, old_job: str) -> dict:
    path=state_root/'PLAN.json';root=Path(cfg['execution_root'])
    if path.exists():
        plan=read_json(path);digest=plan['plan_sha256']
        if semantic_sha({k:v for k,v in plan.items() if k!='plan_sha256'}) != digest:
            raise GateError('ARRAY_PLAN_HASH_CHANGED')
        expected={'old_pending_job_id':old_job,'authorization_sha256':cfg['authorization_sha256'],
                  'binding_sha256':cfg['binding_sha256'],'total_pair_count':cfg['pair_count'],
                  'controller_manifest_sha256':file_sha(ROOT/'PACKAGE_FILES.sha256'),
                  'original_full_package_manifest_sha256':file_sha(Path(cfg['full_package'])/'PACKAGE_FILES.sha256')}
        if any(plan.get(k)!=v for k,v in expected.items()):
            raise GateError('ARRAY_PLAN_BINDING_CHANGED')
        if plan['partitions'] != [list(x) for x in partition_from_prefix(plan['completed_prefix_count'],cfg['pair_count'])]:
            raise GateError('ARRAY_PARTITION_CHANGED')
        return plan
    live,_,_,_=existing_modules(cfg)
    prefix=live.canonical_completed_prefix(execution_root=root,binding_root=Path(cfg['binding_root']))
    if prefix == cfg['pair_count']:
        raise GateError('SELECT_ALREADY_COMPLETE_NO_ARRAY_REQUIRED')
    # Migration only starts at a complete canonical pair boundary, not halfway through a pair.
    context=live._prepare_live_context(execution_root=root,binding_root=Path(cfg['binding_root']))
    for label in ('t0','t2'):
        if len(context['legacy'].load_receipts(root/'execution'/label/'cell_receipts.jsonl')) != prefix:
            raise GateError('MIGRATION_REQUIRES_COMPLETE_CANONICAL_PAIR_BOUNDARY')
    value={'schema_id':'STAGE4D_INDEPENDENT_GPU_ARRAY_PLAN_V1','schema_version':1,
        'old_pending_job_id':old_job,'authorization_sha256':cfg['authorization_sha256'],
        'binding_sha256':cfg['binding_sha256'],'completed_prefix_count':prefix,
        'total_pair_count':cfg['pair_count'],'partitions':[list(x) for x in partition_from_prefix(prefix,cfg['pair_count'])],
        'canonical_prefix_ledger_file_sha256s':ledger_shas(root),
        'controller_manifest_sha256':file_sha(ROOT/'PACKAGE_FILES.sha256'),
        'original_full_package_manifest_sha256':file_sha(Path(cfg['full_package'])/'PACKAGE_FILES.sha256'),
        'scheduler':cfg['array_policy'],'scientific_authorization_changed':False,
        'old_completed_cells_reexecuted':False,'result_interpretation_authorized':False,'promotion_authorized':False}
    plan={**value,'plan_sha256':semantic_sha(value)};write_exact(path,plan)
    print('STAGE4D_ARRAY_PLAN_FROZEN='+plan['plan_sha256'],flush=True)
    print('CANONICAL_PAIR_PREFIX='+str(prefix),flush=True)
    print('SHARD_PAIR_COUNTS='+','.join(str(len(x)) for x in plan['partitions']),flush=True)
    return plan


def write_pointer(path: Path, value: str) -> None:
    """Operational pointer only; scientific artifacts always remain no-clobber."""
    tmp=path.with_name(path.name+'.tmp.'+str(os.getpid()))
    write_bytes_exact(tmp,(value+'\n').encode());os.replace(tmp,path)


def submit_generation(state_root: Path, root: Path, package: Path, logs: Path,
                      plan: dict, generation: int, shards: tuple[int,...]) -> dict:
    receipt=state_root/f'SUBMISSION_{generation}.json'
    intent=state_root/f'SUBMISSION_{generation}.intent.json'
    if receipt.exists():
        value=read_json(receipt)
        if (value.get('shards')!=list(shards) or value.get('generation')!=generation
                or value.get('plan_sha256')!=plan['plan_sha256'] or not str(value.get('job_id','')).isdigit()):
            raise GateError('ARRAY_SUBMISSION_LINEAGE_CHANGED')
        return value
    if intent.exists():
        raise GateError('ARRAY_SUBMISSION_INTENT_WITHOUT_RECEIPT_NO_AUTOMATIC_RETRY')
    logs.mkdir(parents=True,exist_ok=True)
    command=submission_command(package,root,plan['plan_sha256'],shards,logs)
    write_exact(intent,{'generation':generation,'shards':list(shards),'plan_sha256':plan['plan_sha256'],
                        'command':command,'authorization_sha256':plan['authorization_sha256']})
    try:
        p=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise GateError('ARRAY_SUBMISSION_AMBIGUOUS_NO_RETRY') from exc
    write_bytes_exact(state_root/f'SUBMISSION_{generation}.stdout',p.stdout.encode())
    write_bytes_exact(state_root/f'SUBMISSION_{generation}.stderr',p.stderr.encode())
    if p.returncode:
        raise GateError('ARRAY_SUBMISSION_FAILED_NO_AUTOMATIC_RETRY')
    job=parse_parsable_job(p.stdout)
    value={'generation':generation,'shards':list(shards),'job_id':job,'plan_sha256':plan['plan_sha256']}
    write_exact(receipt,value);write_pointer(root/'LAST_JOB_ID.txt',job)
    print('STAGE4D_INDEPENDENT_SINGLE_GPU_ARRAY_SUBMITTED',flush=True)
    print('ARRAY_JOB_ID='+job,flush=True)
    print('ARRAY_SHARDS='+','.join(map(str,shards)),flush=True)
    return value


def validate_native_status(value: dict, plan: dict, shard: int, job: str) -> None:
    count=len(partition_from_prefix(plan['completed_prefix_count'],plan['total_pair_count'])[shard])
    expected={'schema_id':'STAGE4D_PARALLEL_SHARD_STATUS_V1','schema_version':1,
        'slurm_job_id':job,'shard_id':shard,'completed_prefix_count_at_start':plan['completed_prefix_count'],
        'assigned_pair_count':count,'result_interpretation_authorized':False,'promotion_authorized':False}
    for key,want in expected.items():
        if type(value.get(key)) is not type(want) or value.get(key)!=want:
            raise GateError('NATIVE_SHARD_STATUS_BINDING_CHANGED:'+key)
    incomplete_shards({shard:value})
    if value.get('total_condition_cell_count') != value['t0_cell_count']+value['t2_cell_count']:
        raise GateError('NATIVE_SHARD_TOTAL_CHANGED')
    if type(value.get('graceful_partial')) is not bool or (not value['complete'] and not value['graceful_partial']):
        raise GateError('NATIVE_SHARD_TERMINATION_INVALID')


def marker_path(state_root: Path, master: str, shard: int) -> Path:
    return state_root/'attempts'/master/f'SHARD_{shard}.json'


def load_worker_status(cfg: dict, state_root: Path, plan: dict, master: str, shard: int) -> dict:
    marker=read_json(marker_path(state_root,master,shard))
    for key,want in {'array_job_id':master,'shard_id':shard,'plan_sha256':plan['plan_sha256']}.items():
        if type(marker.get(key)) is not type(want) or marker.get(key)!=want:
            raise GateError('ARRAY_WORKER_MARKER_IDENTITY_CHANGED')
    physical=marker.get('slurm_job_id','')
    if not isinstance(physical,str) or not physical.isdigit():raise GateError('ARRAY_WORKER_JOB_ID_INVALID')
    native=Path(cfg['execution_root'])/'parallel_v1'/f'shard_{shard}'/f'SHARD_STATUS_{physical}_V1.json'
    require_file_sha(native,marker['native_status_file_sha256'])
    value=read_json(native);validate_native_status(value,plan,shard,physical)
    return value


def worker(cfg: dict, execution_root: str, plan_sha: str) -> int:
    if Path(execution_root) != Path(cfg['execution_root']):raise GateError('ARRAY_EXECUTION_ROOT_CHANGED')
    root=Path(execution_root);state_root=root/STATE_REL
    plan=freeze_plan(cfg,state_root,read_json(state_root/'PLAN.json')['old_pending_job_id'])
    if plan_sha!=plan['plan_sha256']:raise GateError('ARRAY_WORKER_PLAN_SHA_CHANGED')
    master=os.environ.get('SLURM_ARRAY_JOB_ID','');sid=os.environ.get('SLURM_ARRAY_TASK_ID','');job=os.environ.get('SLURM_JOB_ID','')
    if not master.isdigit() or sid not in ('0','1','2','3') or not job.isdigit():raise GateError('ARRAY_JOB_CONTEXT_REQUIRED')
    shard=int(sid)
    # The receipt may arrive just after sbatch returns, before the job begins its first Python line.
    for _ in range(30):
        submits=[read_json(x) for x in state_root.glob('SUBMISSION_*.json') if '.intent.' not in x.name]
        matches=[x for x in submits if x.get('job_id')==master and shard in x.get('shards',[]) and x.get('plan_sha256')==plan_sha]
        if len(matches)==1:break
        if len(matches)>1:raise GateError('DUPLICATE_ARRAY_SUBMISSION_BINDING')
        time.sleep(1)
    else:raise GateError('ARRAY_WORKER_NOT_BOUND_TO_SUBMISSION_RECEIPT')
    if marker_path(state_root,master,shard).exists():
        load_worker_status(cfg,state_root,plan,master,shard)
        raise GateError('ARRAY_ATTEMPT_ALREADY_FINISHED_NO_SILENT_RERUN')
    driver.base_gate(cfg)
    if ledger_shas(root)!=plan['canonical_prefix_ledger_file_sha256s']:
        raise GateError('CANONICAL_PREFIX_CHANGED_DURING_ARRAY_EXECUTION')
    if importlib.metadata.version('vllm')!='0.11.0':raise GateError('ARRAY_VLLM_VERSION_CHANGED')
    _,shard_worker,_,parallel=existing_modules(cfg)
    fd=os.open(root/'full_select_execution.lock',os.O_CREAT|os.O_RDWR,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
        port=parallel.allocate_free_ports(1)[0]
        # Reuse the exact frozen worker, server builder and scientific cell executor.
        rc=shard_worker.main(['--execution-root',str(root),'--shard-id',str(shard),
            '--completed-prefix-count',str(plan['completed_prefix_count']),'--port',str(port),
            '--worker-budget-seconds',str(cfg['array_policy']['worker_budget_seconds'])])
        if rc!=0:raise GateError('ORIGINAL_SHARD_WORKER_FAILED')
        native=root/'parallel_v1'/f'shard_{shard}'/f'SHARD_STATUS_{job}_V1.json'
        value=read_json(native);validate_native_status(value,plan,shard,job)
        write_exact(marker_path(state_root,master,shard),{
            'schema_id':'STAGE4D_ARRAY_WORKER_COMPLETION_REF_V1','array_job_id':master,'shard_id':shard,
            'slurm_job_id':job,'plan_sha256':plan_sha,'native_status_file_sha256':file_sha(native),
            'node':os.uname().nodename,'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES',''),
            'controller_manifest_sha256':file_sha(ROOT/'PACKAGE_FILES.sha256'),
            'scientific_authorization_changed':False})
        print(f'STAGE4D_ARRAY_SHARD_FINISHED array={master} shard={shard} complete={value["complete"]}',flush=True)
        return 0
    finally:os.close(fd)


def follow_arrays(cfg: dict, state_root: Path, plan: dict) -> dict[int,dict]:
    statuses={};shards=(0,1,2,3)
    for generation in range(cfg['array_policy']['max_partial_resumptions']+1):
        submitted=submit_generation(state_root,Path(cfg['execution_root']),ROOT,Path(cfg['execution_log_root']),plan,generation,shards)
        job=submitted['job_id'];unknown=0;previous=None
        while True:
            state,raw=query_array(job,shards)
            if raw!=previous:
                print('STAGE4E_ARRAY_STATUS='+job+'\n'+raw.strip(),flush=True);previous=raw
            if state=='STOP':raise GateError('ARRAY_ELEMENT_FAILED_NO_AUTOMATIC_RETRY:'+job)
            if state=='COMPLETE':break
            unknown=unknown+1 if state=='UNKNOWN' else 0
            if unknown>=5:raise GateError('ARRAY_ACCOUNTING_UNAVAILABLE_NO_OUTCOME_READ')
            time.sleep(cfg['poll_seconds'])
        for shard in shards:statuses[shard]=load_worker_status(cfg,state_root,plan,job,shard)
        if set(statuses)!=set(range(4)):raise GateError('ARRAY_SHARD_UNIVERSE_INCOMPLETE')
        shards=incomplete_shards(statuses)
        if not shards:return statuses
        print('STAGE4D_ARRAY_GRACEFUL_PARTIAL_SHARDS='+','.join(map(str,shards)),flush=True)
    raise GateError('ARRAY_PARTIAL_RESUMPTION_BUDGET_EXHAUSTED_NO_RESULT_AUDIT')


def consolidate(cfg: dict, state_root: Path, plan: dict) -> None:
    root=Path(cfg['execution_root']);binding=Path(cfg['binding_root'])
    live,_,entry,_=existing_modules(cfg)
    # Validate every shard's exact full cell sequence before copying any output.
    context=live._prepare_live_context(execution_root=root,binding_root=binding)
    for shard,ordinals in enumerate(plan['partitions']):
        for label in ('T0','T2'):
            rows=context['legacy'].load_receipts(root/'parallel_v1'/f'shard_{shard}'/'execution'/label.lower()/'cell_receipts.jsonl')
            cells=[context['bundles'][label][2].cells[i] for i in ordinals]
            if len(rows)!=len(cells):raise GateError('ARRAY_EXACT_SHARD_COVERAGE_MISMATCH')
            for ordinal,row,cell in zip(ordinals,rows,cells,strict=True):
                live._validate_canonical_row(row=row,cell=cell,label=label,ordinal=ordinal)
    write_exact(state_root/'CONSOLIDATION.intent.json',{'plan_sha256':plan['plan_sha256'],
        'completed_prefix_count':plan['completed_prefix_count'],'all_shards_complete':True})
    # Original V1.3 consolidation keeps attempts, publication metadata and canonical hash chains.
    result=live.consolidate_shards(execution_root=root,binding_root=binding,completed_prefix_count=plan['completed_prefix_count'])
    if not result['complete']:raise GateError('ARRAY_CONSOLIDATION_NOT_COMPLETE')
    auth=read_json(root/'STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_V1.json')
    payload=entry._completion_payload(execution_root=root,auth=auth,execution=result)
    write_exact(root/driver.COMPLETE,payload)
    write_exact(state_root/'ARRAY_CONSOLIDATION_RECEIPT.json',{
        'schema_id':'STAGE4D_INDEPENDENT_JOBS_CONSOLIDATION_V1','plan_sha256':plan['plan_sha256'],
        'canonical_completion_file_sha256':file_sha(root/driver.COMPLETE),
        'canonical_ledger_file_sha256s':ledger_shas(root),'result_interpretation_authorized':False})
    print('STAGE4D_FULL_SELECT_EXECUTION_COMPLETE',flush=True)
    print('T0_CELL_COUNT=1775\nT2_CELL_COUNT=1775\nTOTAL_CONDITION_CELL_COUNT=3550',flush=True)


def main() -> int:
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('migrate-follow-publish','worker'))
    p.add_argument('--replace-pending-job',default='156834');p.add_argument('--execution-root');p.add_argument('--plan-sha')
    a=p.parse_args();verify_inventory(ROOT);cfg=read_json(ROOT/'config.json')
    if a.mode=='worker':return worker(cfg,a.execution_root or '',a.plan_sha or '')
    if not a.replace_pending_job.isdigit():raise GateError('NUMERIC_PENDING_JOB_REQUIRED')
    control=Path(cfg['control_root']);control.mkdir(parents=True,exist_ok=True)
    fd=os.open(control/'driver.lock',os.O_CREAT|os.O_RDWR,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        active=driver.base_gate(cfg);repo=Path(cfg['integration_repo'])
        ensure_isolated_repo(active=active,dest=repo,cfg=cfg)
        root=Path(cfg['execution_root']);state_root=root/STATE_REL;state_root.mkdir(parents=True,exist_ok=True)
        if (root/driver.COMPLETE).exists():
            # Do not cancel/resubmit after genuine scientific completion.
            from .audit import completion_gate
            completion_gate(root,cfg)
            active,repo=driver.prepare(cfg,control);driver.finalize(cfg,control,repo,active);return 0
        if not (state_root/'PLAN.json').exists():
            if (root/'LAST_JOB_ID.txt').read_text().strip()!=a.replace_pending_job:
                raise GateError('LAST_JOB_CHANGED_NO_PENDING_JOB_MIGRATION')
        cancel_pending_once(job=a.replace_pending_job,cfg=cfg,state_root=state_root)
        plan=freeze_plan(cfg,state_root,a.replace_pending_job)
        # Enqueue the four independent allocations before the CPU-only source regression.
        submit_generation(state_root,root,ROOT,Path(cfg['execution_log_root']),plan,0,(0,1,2,3))
        active,repo=driver.prepare(cfg,control)
        follow_arrays(cfg,state_root,plan)
        consolidate(cfg,state_root,plan)
        driver.finalize(cfg,control,repo,active)
        return 0
    finally:os.close(fd)


if __name__=='__main__':
    try:raise SystemExit(main())
    except (GateError,BlockingIOError) as exc:
        print('STOP='+str(exc),file=sys.stderr,flush=True)
        raise SystemExit(70)

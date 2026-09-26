"""Native submit-once ownership of current four-shard OFF/OFF execution."""
from __future__ import annotations
import argparse
import math
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT),str(ROOT/'live_adapter')]
from exact_bindings import (BindingError,file_ref,read_ref,read_json,immutable_json,immutable_bytes)
from entry.training_job import _publish_json


def _ref(path):
    ref=file_ref(path)
    return {'path':ref['path'],'sha256':ref['file_sha256']}


def _read(ref): return read_ref({'path':ref['path'],'file_sha256':ref['sha256']})


def parse_scheduler_status(*,job_id,squeue_stdout,sacct_stdout):
    """Exact root job row only; batch/extern rows cannot authorize resumption."""
    queue=[line.split('|') for line in squeue_stdout.strip().splitlines() if line.strip()]
    if queue:
        if len(queue)!=1 or len(queue[0])!=2 or queue[0][0]!=job_id:
            raise BindingError('OFFOFF_SQUEUE_CURRENT_JOB_IDENTITY')
        return {'job_id':job_id,'state':queue[0][1],'active':True}
    rows=[line.split('|') for line in sacct_stdout.strip().splitlines() if line.strip()]
    matches=[row for row in rows if row and row[0]==job_id]
    if not matches: return {'job_id':job_id,'state':'ACCOUNTING_PENDING','active':False}
    if len(matches)!=1 or len(matches[0])<3:
        raise BindingError('OFFOFF_SACCT_CURRENT_JOB_CARDINALITY')
    row=matches[0]
    state=row[1].split()[0].rstrip('+')
    return {'job_id':job_id,'state':state,'exit_code':row[2],'active':False}


def _query(job_id,timeout):
    queue=subprocess.run(['squeue','--noheader','--jobs',job_id,'--format','%i|%T'],
        capture_output=True,text=True,check=False,timeout=timeout)
    if queue.returncode and ('Invalid job id' not in queue.stderr or queue.stdout.strip()):
        raise BindingError('OFFOFF_SQUEUE_FAILED')
    accounting=''
    if not queue.stdout.strip():
        result=subprocess.run(['sacct','-X','--noheader','--parsable2','--jobs',job_id,
            '--format','JobIDRaw,State,ExitCode'],capture_output=True,text=True,check=False,timeout=timeout)
        if result.returncode: raise BindingError('OFFOFF_SACCT_FAILED')
        accounting=result.stdout
    return parse_scheduler_status(job_id=job_id,squeue_stdout=queue.stdout,sacct_stdout=accounting)


def _require_success(value):
    if value.get('state')!='COMPLETED' or value.get('exit_code')!='0:0' or value.get('active') is not False:
        raise BindingError('OFFOFF_RESUMPTION_REQUIRES_COMPLETED_0_0')


def _check_stop(root,parallel_ref):
    path=Path(root)/'OFFOFF_JOB_STOP.json'
    if path.exists():
        value=read_json(path)
        if value.get('schema_id')!='CURRENT_RESIDENT_OFFOFF_JOB_STOP_V1' or value.get('parallel_ref')!=parallel_ref:
            raise BindingError('OFFOFF_STOP_CURRENT_IDENTITY')
        raise BindingError('CURRENT_OFFOFF_PERSISTED_STOP:'+value['error_type']+':'+value['message'])


def execute_current_offoff_jobs(*,parallel_ref,output_root,deployment):
    """Submit/recover four exact native workers; resume only completed partials."""
    from entry.training_job import _clean_owner
    from offoff_binding.parallel import _load_parallel,_status,finalize_parallel
    from offoff_binding.native import Native,ARRAY_CONFIG
    root=Path(output_root).absolute()
    _check_stop(root,parallel_ref)
    parallel=_load_parallel(parallel_ref)
    binding=_read(parallel['binding_ref'])
    native=Native.load(binding['native_repo_root'],binding['source_refs'])
    operational=_read({'path':deployment['training_source_registration']['operational_request_ref']['path'],
                      'sha256':deployment['training_source_registration']['operational_request_ref']['sha256']})
    owner=_clean_owner(deployment['training_source_registration'],deployment['scientific_repo_root'])
    policy=parallel['array_policy']
    if policy['gpus_per_job']!=1 or policy['max_concurrent_jobs']!=policy['shards'] or policy['automatic_failed_job_retry'] is not False:
        raise BindingError('OFFOFF_REGISTERED_ARRAY_POLICY')
    settings=deployment['rollout_settings']
    for key in ('watch_timeout_seconds','native_preflight_timeout_seconds','publication_grace_seconds'):
        value=settings.get(key)
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
            raise BindingError('REGISTERED_OFFOFF_OPERATIONAL_LIMIT_REQUIRED:'+key)
    timeout=settings['native_preflight_timeout_seconds']
    grace=settings['publication_grace_seconds']
    poll=_read(native.sources[str(native.root/ARRAY_CONFIG)])['poll_seconds']
    python=Path(operational['python'])
    if not python.is_absolute() or not python.is_file():
        raise BindingError('REGISTERED_OFFOFF_PYTHON_UNAVAILABLE')
    root.mkdir(parents=True,exist_ok=True)
    resources={'partition':policy['partition'],'time':policy['walltime']}
    # Only the current immutable submission receipts identify jobs we may cancel.
    owned={}; done={}; runs={}

    def submit(shard,ordinal):
        shard_id=shard['shard_id'];jobroot=root/f'shard_{shard_id}/run_{ordinal:03d}'
        jobroot.mkdir(parents=True,exist_ok=True)
        request={'schema_id':'CURRENT_RESIDENT_OFFOFF_JOB_REQUEST_V1','parallel_ref':parallel_ref,
            'shard_id':shard_id,'resumption_ordinal':ordinal,'native_repo_root':binding['native_repo_root'],
            'result_path':str(jobroot/'OFFOFF_WORKER_RESULT.json'),
            'source_identity_sha256':deployment['entry_source_sha256']}
        request_path=jobroot/'OFFOFF_WORKER_REQUEST.json';immutable_json(request_path,request)
        argv=[str(python),'-B',str(Path(__file__).resolve()),'--worker',str(request_path),
              '--request-sha256',file_ref(request_path)['file_sha256']]
        script=jobroot/'offoff.sbatch'
        immutable_bytes(script,('#!/usr/bin/env bash\nexec '+' '.join(shlex.quote(x) for x in argv)+'\n').encode())
        receipt=owner.runner.submit_once(jobroot,'offoff',script,resources)
        if not isinstance(receipt.get('job_id'),str) or not receipt['job_id'].isdigit():
            raise BindingError('OFFOFF_NATIVE_SUBMISSION_JOB_ID')
        owned[receipt['job_id']]=(jobroot,_ref(jobroot/'offoff.SUBMIT_RECEIPT.json'))
        watch_path=jobroot/'WATCH_START.json'
        if not watch_path.exists():
            _publish_json(watch_path,{'job_id':receipt['job_id'],'started_at':time.time(),
                'request_ref':_ref(request_path),'parallel_ref':parallel_ref,'settings':settings})
        watch=read_json(watch_path)
        if (watch.get('job_id')!=receipt['job_id'] or watch.get('request_ref')!=_ref(request_path)
                or watch.get('parallel_ref')!=parallel_ref or watch.get('settings')!=settings):
            raise BindingError('OFFOFF_WATCH_CURRENT_IDENTITY')
        return {'ordinal':ordinal,'request_ref':_ref(request_path),'job_id':receipt['job_id'],
                'root':jobroot,'shard':shard,'watch':watch}

    def status_for(shard,ordinal):
        path=Path(shard['execution_root']).parent/f'SHARD_STATUS_{ordinal:03d}.json'
        ref=_ref(path)
        return ref,_status(ref,parallel_ref=parallel_ref,shard_id=shard['shard_id'],
            resumption_ordinal=ordinal,assigned=len(shard['ordinals']))

    try:
        for shard in parallel['shards']:
            ordinal=0
            # Fixed maximum from the registered native policy, never a directory census.
            for next_ordinal in range(1,policy['max_partial_resumptions']+1):
                authority_path=root/f'shard_{shard["shard_id"]}/RESUME_{next_ordinal:03d}.json'
                if not authority_path.exists(): break
                authority=read_json(authority_path)
                if (authority.get('schema_id')!='CURRENT_RESIDENT_OFFOFF_RESUMPTION_V1'
                        or authority.get('parallel_ref')!=parallel_ref or authority.get('shard_id')!=shard['shard_id']
                        or authority.get('resumption_ordinal')!=next_ordinal):
                    raise BindingError('OFFOFF_RESUME_AUTHORITY_IDENTITY')
                previous_root=root/f'shard_{shard["shard_id"]}/run_{next_ordinal-1:03d}'
                if (authority['completion_ref']!=_ref(previous_root/'SLURM_COMPLETION.json') or
                        authority['submission_ref']!=_ref(previous_root/'offoff.SUBMIT_RECEIPT.json')):
                    raise BindingError('OFFOFF_RESUME_PREVIOUS_JOB_REFS')
                completion=_read(authority['completion_ref']);_require_success(completion)
                previous_job=_read(authority['submission_ref'])
                if previous_job['job_id']!=completion['job_id']:
                    raise BindingError('OFFOFF_RESUME_COMPLETION_JOB_MISMATCH')
                previous_ref,previous=status_for(shard,next_ordinal-1)
                if authority['status_ref']!=previous_ref or previous['complete'] or not previous['graceful_partial']:
                    raise BindingError('OFFOFF_RESUME_REQUIRES_EXACT_GRACEFUL_PARTIAL')
                ordinal=next_ordinal
            runs[shard['shard_id']]=submit(shard,ordinal)
        while len(done)<policy['shards']:
            for shard_id,run in list(runs.items()):
                if shard_id in done: continue
                worker_stop=run['root']/'OFFOFF_WORKER_STOP.json'
                if worker_stop.exists():
                    stopped=read_json(worker_stop)
                    if stopped.get('request_ref')!=run['request_ref']:
                        raise BindingError('OFFOFF_WORKER_STOP_CURRENT_IDENTITY')
                    raise BindingError('CURRENT_OFFOFF_WORKER_STOP:'+stopped['error_type']+':'+stopped['message'])
                status=_query(run['job_id'],timeout)
                print('FORMAL_OFFOFF_JOB='+run['job_id']+' '+status['state'],flush=True)
                result_path=run['root']/'OFFOFF_WORKER_RESULT.json'
                if (time.time()-run['watch']['started_at']>=settings['watch_timeout_seconds']
                        and not (status['state']=='COMPLETED' and status.get('exit_code')=='0:0' and result_path.is_file())):
                    raise BindingError('OFFOFF_REGISTERED_JOB_WATCH_TIMEOUT_NO_RESEND')
                if status['active']: continue
                inactive=run['root']/'FIRST_INACTIVE.json'
                if not inactive.exists(): immutable_json(inactive,{'job_id':run['job_id'],'epoch':time.time()})
                if read_json(inactive)['job_id']!=run['job_id']:
                    raise BindingError('OFFOFF_INACTIVE_JOB_IDENTITY')
                if status['state']=='ACCOUNTING_PENDING':
                    if time.time()-read_json(inactive)['epoch']>=grace:
                        raise BindingError('OFFOFF_ACCOUNTING_NOT_PUBLISHED_NO_RESEND')
                    continue
                _require_success(status)
                completion_path=run['root']/'SLURM_COMPLETION.json';immutable_json(completion_path,status)
                if not result_path.is_file():
                    if time.time()-read_json(inactive)['epoch']>=grace:
                        raise BindingError('OFFOFF_COMPLETED_WITHOUT_NATIVE_WORKER_RESULT')
                    continue
                result=read_json(result_path)
                if result.get('request_ref')!=run['request_ref']:
                    raise BindingError('OFFOFF_WORKER_RESULT_CURRENT_REQUEST')
                status_ref,native_status=status_for(run['shard'],run['ordinal'])
                if result.get('status_ref')!=status_ref:
                    raise BindingError('OFFOFF_WORKER_RESULT_NATIVE_STATUS')
                if native_status['complete']:
                    done[shard_id]=status_ref
                    continue
                next_ordinal=run['ordinal']+1
                if next_ordinal>policy['max_partial_resumptions'] or not native_status['graceful_partial']:
                    raise BindingError('OFFOFF_GRACEFUL_PARTIAL_BUDGET_EXHAUSTED')
                authority={'schema_id':'CURRENT_RESIDENT_OFFOFF_RESUMPTION_V1','parallel_ref':parallel_ref,
                    'shard_id':shard_id,'resumption_ordinal':next_ordinal,
                    'completion_ref':_ref(completion_path),'status_ref':status_ref,
                    'submission_ref':owned[run['job_id']][1]}
                immutable_json(root/f'shard_{shard_id}/RESUME_{next_ordinal:03d}.json',authority)
                runs[shard_id]=submit(run['shard'],next_ordinal)
            if len(done)<policy['shards']: time.sleep(poll)
        return finalize_parallel(parallel_ref)
    except Exception as exc:
        containment=[]
        for job_id,(_,receipt_ref) in owned.items():
            if _read(receipt_ref)['job_id']!=job_id: raise BindingError('OFFOFF_CONTAINMENT_JOB_IDENTITY')
            try:
                response=subprocess.run(['scancel',job_id],capture_output=True,text=True,check=False,timeout=timeout)
                containment.append({'job_id':job_id,'submission_ref':receipt_ref,'returncode':response.returncode})
            except (OSError,subprocess.TimeoutExpired) as cancel_error:
                containment.append({'job_id':job_id,'submission_ref':receipt_ref,'error_type':type(cancel_error).__name__})
        _publish_json(root/'OFFOFF_JOB_STOP.json',{'schema_id':'CURRENT_RESIDENT_OFFOFF_JOB_STOP_V1',
            'parallel_ref':parallel_ref,'error_type':type(exc).__name__,'message':str(exc),
            'containment':containment,'blind_resend_authorized':False,'scientific_outcome_claimed':False})
        raise


def execute_current_offoff_job(*,start,current_inputs_ref,trained,output_root,deployment):
    """Driver API: accepted candidate -> frozen inputs -> native shards -> terminal."""
    from entry.candidate_runtime import publish_candidate
    from offoff_binding.native import Native
    from offoff_binding.registered_inputs import materialize_registered_inputs
    from offoff_binding.materialize import materialize
    from offoff_binding.parallel import materialize_parallel
    root=Path(output_root).absolute()
    candidate=publish_candidate(start=start,current_inputs_ref=current_inputs_ref,trained=trained,
        output_root=root/'candidate',source_registration=deployment['candidate_source_registration'])
    root.mkdir(parents=True,exist_ok=True)
    request_path=root/'CURRENT_REQUEST.json';immutable_json(request_path,start)
    request_ref=_ref(request_path)
    registration=deployment['offoff_source_registration']
    inputs=materialize_registered_inputs(registration=registration,request_ref=request_ref,
        parent_ref=candidate['parent_ref'],candidate_ref=candidate['candidate_ref'],
        current_runtime_ref=_read(current_inputs_ref)['runtime'],sink=root/'inputs')
    native=Native.load(registration['native_repo_root'],registration['source_refs'])
    binding_ref=materialize(native=native,request_ref=request_ref,parent_ref=candidate['parent_ref'],
        candidate_ref=candidate['candidate_ref'],protocol_ref=inputs['protocol_ref'],
        infrastructure_ref=inputs['infrastructure_ref'],sink=root/'binding')
    parallel_ref=materialize_parallel(binding_ref,sink=root/'parallel')
    terminal_ref=execute_current_offoff_jobs(parallel_ref=parallel_ref,output_root=root/'jobs',deployment=deployment)
    return {'terminal_ref':terminal_ref,'next_policy_input_refs':candidate['next_policy_input_refs'],
            'current_parent_context':candidate['current_parent_context']}


def worker(path,expected_sha):
    path=Path(path).absolute()
    request=read_ref({'path':str(path),'file_sha256':expected_sha})
    try:
        if (request.get('schema_id')!='CURRENT_RESIDENT_OFFOFF_JOB_REQUEST_V1'
                or Path(request['result_path'])!=path.parent/'OFFOFF_WORKER_RESULT.json'):
            raise BindingError('OFFOFF_WORKER_REQUEST_LAYOUT')
        from memory_binding.worker_bootstrap import bootstrap_current_and_children
        bootstrap_current_and_children(request['native_repo_root'])
        from offoff_binding.parallel import execute_parallel_worker
        from offoff_binding.native import Native
        binding=_read(_read(request['parallel_ref'])['binding_ref'])
        native=Native.load(binding['native_repo_root'],binding['source_refs'])
        port=native.parallel().allocate_free_ports(1)[0]
        status_ref=execute_parallel_worker(request['parallel_ref'],shard_id=request['shard_id'],
            resumption_ordinal=request['resumption_ordinal'],host='127.0.0.1',port=port)
        _publish_json(Path(request['result_path']),{'schema_id':'CURRENT_RESIDENT_OFFOFF_JOB_RESULT_V1',
            'request_ref':_ref(path),'status_ref':status_ref})
    except Exception as exc:
        _publish_json(path.parent/'OFFOFF_WORKER_STOP.json',{'request_ref':_ref(path),
            'error_type':type(exc).__name__,'message':str(exc),'blind_resend_authorized':False})
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',type=Path,required=True)
    parser.add_argument('--request-sha256',required=True)
    args=parser.parse_args()
    worker(args.worker,args.request_sha256)

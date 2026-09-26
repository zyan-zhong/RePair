"""Scheduler fixtures only. Native scientific chain is covered separately."""
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

from continuity_binding.api import read_ref,write_once
from test_binding import fixture,REPO
from offoff_binding.materialize import materialize
from offoff_binding.parallel import materialize_parallel
from offoff_binding.native import BASE_VERIFIER
from entry import offoff_job


@pytest.mark.parametrize('text,expected', [('777|COMPLETED|0:0\n','0:0'),('777|COMPLETED|1:0\n','1:0')])
def test_exact_accounting_root_job(text,expected):
    value=offoff_job.parse_scheduler_status(job_id='777',squeue_stdout='',sacct_stdout=text+'777.batch|COMPLETED|0:0\n')
    assert value['exit_code']==expected
    if expected=='0:0': offoff_job._require_success(value)
    else:
        with pytest.raises(ValueError,match='COMPLETED_0_0'): offoff_job._require_success(value)
    assert offoff_job.parse_scheduler_status(job_id='777',squeue_stdout='',sacct_stdout='777.batch|COMPLETED|0:0\n')['state']=='ACCOUNTING_PENDING'


def _setup(tmp_path):
    args=fixture(tmp_path)
    source=tmp_path/'fixture_rule.py'
    source.write_text('def decide(*,frozen_rule,aggregate):\n return {"decision":"ROLLBACK","decision_rule_id":frozen_rule["decision_rule_id"]}\n')
    source_ref={'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    args['native'].sources[str(source)]=source_ref
    rule_ref=write_once(tmp_path/'registered-rule.json',{'decision_rule_id':'SCHEDULER_FIXTURE_ONLY',
        'decision_producer':{'source_ref':source_ref,'entrypoint':'decide'}})
    args['protocol_ref']=write_once(tmp_path/'registered-protocol.json',{**read_ref(args['protocol_ref']),'promotion_rule_ref':rule_ref})
    binding_ref=materialize(**args,sink=tmp_path/'binding')
    parallel_ref=materialize_parallel(binding_ref,sink=tmp_path/'parallel')
    relative=str(Path(BASE_VERIFIER).parent).replace('\\','/')
    operational=write_once(tmp_path/'operational.json',{'python':sys.executable})
    registration={'clean_root_relative':relative,'operational_request_ref':operational,
        'source_files':{relative+'/'+name:hashlib.sha256((REPO/relative/name).read_bytes()).hexdigest()
                        for name in ('clean_adapter.py','run_stage.py')}}
    deployment={'scientific_repo_root':str(REPO),'training_source_registration':registration,
        'entry_source_sha256':'a'*64,'rollout_settings':{'watch_timeout_seconds':100,'native_preflight_timeout_seconds':2,'publication_grace_seconds':2}}
    return parallel_ref,deployment


@pytest.mark.parametrize('failed',[False,True,'watch_timeout'])
def test_actual_native_submit_once_and_completed_only_partial_resume(tmp_path,monkeypatch,failed):
    parallel_ref,deployment=_setup(tmp_path)
    parallel=read_ref(parallel_ref)
    from entry import training_job
    real_owner=training_job._clean_owner(deployment['training_source_registration'],REPO)
    submissions={};cancelled=[]
    def submit(script,log,resources):
        job_id=str(100+len(submissions))
        submissions[job_id]=(script.parent,resources)
        return job_id
    # Only the external sbatch transport is a fixture; native atomic intent and
    # receipt handling, exact-script adoption and resources are the real source.
    real_owner.runner.invoke_sbatch=submit
    monkeypatch.setattr(training_job,'_clean_owner',lambda *_:real_owner)
    monkeypatch.setattr(offoff_job.time,'sleep',lambda *_:None)
    monkeypatch.setattr(offoff_job.subprocess,'run',lambda argv,**_:cancelled.append(argv) or SimpleNamespace(returncode=0))
    def query(job_id,timeout):
        if failed=='watch_timeout':
            monkeypatch.setattr(offoff_job.time,'time',lambda:1e12)
            return {'job_id':job_id,'state':'RUNNING','active':True}
        if failed: return {'job_id':job_id,'state':'FAILED','exit_code':'1:0','active':False}
        jobroot=submissions[job_id][0]
        request=offoff_job.read_json(jobroot/'OFFOFF_WORKER_REQUEST.json')
        shard=parallel['shards'][request['shard_id']]
        partial=request['shard_id']==0 and request['resumption_ordinal']==0
        count=0 if partial else len(shard['ordinals'])
        status_ref=write_once(Path(shard['execution_root']).parent/f'SHARD_STATUS_{request["resumption_ordinal"]:03d}.json',
            {'schema_id':'CURRENT_NATIVE_OFFOFF_SHARD_STATUS_V1','parallel_ref':parallel_ref,
             'shard_id':request['shard_id'],'resumption_ordinal':request['resumption_ordinal'],
             'assigned_pair_count':len(shard['ordinals']),'parent_cell_count':count,'candidate_cell_count':count,
             'complete':not partial,'graceful_partial':partial})
        offoff_job.immutable_json(Path(request['result_path']),{'request_ref':offoff_job._ref(jobroot/'OFFOFF_WORKER_REQUEST.json'),
            'status_ref':status_ref})
        return {'job_id':job_id,'state':'COMPLETED','exit_code':'0:0','active':False}
    monkeypatch.setattr(offoff_job,'_query',query)
    import offoff_binding.parallel as module
    fixture_terminal=write_once(tmp_path/'scheduler-only-terminal.json',{'fixture_only':True,'no_scientific_claim':True})
    monkeypatch.setattr(module,'finalize_parallel',lambda _:fixture_terminal)
    args=dict(parallel_ref=parallel_ref,output_root=tmp_path/'jobs',deployment=deployment)
    if failed:
        with pytest.raises(ValueError,match='WATCH_TIMEOUT' if failed=='watch_timeout' else 'COMPLETED_0_0'):
            offoff_job.execute_current_offoff_jobs(**args)
        assert len(submissions)==4 and len(cancelled)==4
        assert not (tmp_path/'jobs/shard_0/RESUME_001.json').exists()
        with pytest.raises(ValueError,match='PERSISTED_STOP'):
            offoff_job.execute_current_offoff_jobs(**args)
        assert len(submissions)==4 and len(cancelled)==4
    else:
        assert offoff_job.execute_current_offoff_jobs(**args)==fixture_terminal
        assert len(submissions)==5 and not cancelled
        assert all(resources=={'partition':'gpu_a800','time':'03:30:00'} for _,resources in submissions.values())
        assert (tmp_path/'jobs/shard_0/RESUME_001.json').is_file()
        assert offoff_job.execute_current_offoff_jobs(**args)==fixture_terminal
        assert len(submissions)==5


def test_worker_bootstrap_failure_publishes_owned_stop(tmp_path,monkeypatch):
    request_path=tmp_path/'OFFOFF_WORKER_REQUEST.json'
    offoff_job.immutable_json(request_path,{'schema_id':'CURRENT_RESIDENT_OFFOFF_JOB_REQUEST_V1',
        'native_repo_root':str(tmp_path/'fixture-native'),'result_path':str(tmp_path/'OFFOFF_WORKER_RESULT.json')})
    import memory_binding.worker_bootstrap as bootstrap
    def fail(*_): raise RuntimeError('fixture bootstrap failure')
    monkeypatch.setattr(bootstrap,'bootstrap_current_and_children',fail)
    with pytest.raises(RuntimeError,match='bootstrap failure'):
        offoff_job.worker(request_path,offoff_job.file_ref(request_path)['file_sha256'])
    value=offoff_job.read_json(tmp_path/'OFFOFF_WORKER_STOP.json')
    assert value['request_ref']==offoff_job._ref(request_path)
    assert value['blind_resend_authorized'] is False

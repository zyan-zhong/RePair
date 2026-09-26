"""Isolated control-plane tests. Scheduler and provider execution are forbidden."""
import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import recover,supervise
from recovery_core import equal_or_new,load_json,sha_file

def ready_root(tmp_path):
    root=tmp_path/'recovery';root.mkdir();rt=tmp_path/'round';rt.mkdir()
    req=root/'request.json';equal_or_new(req,{'kind':'synthetic_test_request'})
    cap=root/'capsule.zip';cap.write_bytes(b'test-not-executed')
    plan=root/'plan.json';equal_or_new(plan,{'kind':'synthetic_plan'})
    ready={'request_file_sha256':sha_file(req),'request_path':str(req),'source_identity':{'schema_id':'NATIVE_PRODUCER_PATCH_SOURCE_IDENTITY_V1','files':{}},'source_package':str(Path(recover.__file__).parent),
           'round_id':'TEST-ROUND','capsule_path':str(cap),'capsule_sha256':sha_file(cap),'shard_plan_path':str(plan),'shard_plan_sha256':sha_file(plan),
           'sbatch_argv':['sbatch','--parsable','--hold','script.sh'],'gate_shard_id':0,
           'settings':{'watch_timeout_seconds':4,'poll_seconds':1,'publication_grace_seconds':1,'analyzer_timeout_seconds':3}}
    equal_or_new(root/'READY.json',ready)
    return root,{'rt':rt,'gate':{'array_job_id':'123'},'plan':{'shard_count':2}},ready

def test_submission_adopt_does_not_call_scheduler(tmp_path,monkeypatch):
    root,ctx,r=ready_root(tmp_path)
    equal_or_new(root/'SUBMISSION_RECEIPT.json',{'ready_sha256':sha_file(root/'READY.json'),'array_job_id':'678'})
    monkeypatch.setattr(recover,'cmd',lambda *a,**k:pytest.fail('scheduler called'))
    recover.execute(ctx,root,r)
    assert not (root/'SUBMISSION_INTENT.json').exists()

def test_ambiguous_submission_never_retries(tmp_path,monkeypatch):
    root,ctx,r=ready_root(tmp_path);equal_or_new(root/'SUBMISSION_INTENT.json',{'argv':r['sbatch_argv']})
    monkeypatch.setattr(recover,'cmd',lambda *a,**k:pytest.fail('scheduler called'))
    with pytest.raises(ValueError,match='AMBIGUOUS_NO_RESEND'):recover.execute(ctx,root,r)

def test_one_submission_monitor_spawn_failure_contains_held_array(tmp_path,monkeypatch):
    root,ctx,r=ready_root(tmp_path);calls=[]
    monkeypatch.setattr(recover,'assert_old_array_inactive',lambda *a,**k:{'status':'fixture_inactive'})
    def command(argv,**kwargs):
        calls.append(argv)
        return {'argv':argv,'returncode':0,'stdout':'678\n' if argv[0]=='sbatch' else '', 'stderr':''}
    monkeypatch.setattr(recover,'cmd',command)
    monkeypatch.setattr(recover.subprocess,'Popen',lambda *a,**k:(_ for _ in ()).throw(OSError('fixture_spawn_failure')))
    with pytest.raises(OSError):recover.execute(ctx,root,r)
    assert [x[0] for x in calls]==['sbatch','scancel']
    assert load_json(root/'RESIDENT_START_FAILURE_CONTAINMENT.json')['array_job_id']=='678'
    recover.execute(ctx,root,r)
    assert len(calls)==2

def test_handoff_without_global_terminal_not_released_to_analyzer(tmp_path):
    root,ctx,r=ready_root(tmp_path)
    assert supervise.publication_ready(root) is False
    p=root/'round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json';equal_or_new(p,{'scientific_rollout_valid':True})
    assert supervise.publication_ready(root) is False
    equal_or_new(p.parent/'PCHSI_V1232K_GLOBAL_TERMINAL_V1.json',{'scientific_rollout_valid':True})
    assert supervise.publication_ready(root) is True

def test_gate_failure_exits_without_accounting_spin(tmp_path,monkeypatch):
    root,ctx,r=ready_root(tmp_path)
    equal_or_new(root/'SUBMISSION_RECEIPT.json',{'ready_sha256':sha_file(root/'READY.json'),'array_job_id':'678'})
    equal_or_new(root/'GATE_RELEASE_RECEIPT.json',{'returncode':0})
    equal_or_new(root/'PCHSI_V1232K_GATE_FAILURE_V1.json',{'reason':'fixture fatal','array_job_id':'678'})
    monkeypatch.setattr(supervise,'cmd',lambda *a,**k:pytest.fail('accounting polled after durable failure'))
    supervise.run(root)
    t=load_json(root/'RECOVERY_TERMINAL.json')
    assert t['status']=='RECOVERY_GATE_FAILED_NO_AUTOMATIC_SECOND_SUBMISSION'
    assert t['r2_rollout_live_proven'] is False
    assert t['full_hierarchical_analyzer_closed'] is False

def test_release_error_is_not_treated_as_success_on_restart(tmp_path,monkeypatch):
    root,ctx,r=ready_root(tmp_path)
    equal_or_new(root/'SUBMISSION_RECEIPT.json',{'ready_sha256':sha_file(root/'READY.json'),'array_job_id':'678'})
    equal_or_new(root/'GATE_RELEASE_RECEIPT.json',{'returncode':1,'stderr':'fixture failed release'})
    monkeypatch.setattr(supervise,'cmd',lambda *a,**k:pytest.fail('release resent or monitor polled'))
    with pytest.raises(ValueError,match='GATE_RELEASE_FAILED'):supervise.run(root)

def test_successful_submission_has_single_intent_and_detached_monitor(tmp_path,monkeypatch):
    import types
    root,ctx,r=ready_root(tmp_path);calls=[];launches=[]
    monkeypatch.setattr(recover,'assert_old_array_inactive',lambda *a,**k:{'status':'fixture_inactive'})
    monkeypatch.setattr(recover,'cmd',lambda argv,**k:(calls.append(argv) or {'argv':argv,'returncode':0,'stdout':'678\n','stderr':''}))
    def spawn(argv,**kw):
        launches.append((argv,kw));assert kw['start_new_session'] is True
        assert (root/'RESIDENT_START_INTENT.json').exists()
        assert (root/'SUBMISSION_RECEIPT.json').exists()
        return types.SimpleNamespace(pid=999)
    monkeypatch.setattr(recover.subprocess,'Popen',spawn)
    recover.execute(ctx,root,r);recover.execute(ctx,root,r)
    assert len(calls)==1 and len(launches)==1
    assert load_json(root/'SUBMISSION_RECEIPT.json')['submitted_held'] is True

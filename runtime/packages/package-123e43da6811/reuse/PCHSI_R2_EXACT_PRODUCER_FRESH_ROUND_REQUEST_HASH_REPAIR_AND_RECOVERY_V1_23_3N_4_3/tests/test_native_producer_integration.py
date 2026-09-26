"""Native finalizer + native schedule/contracts; only external task types mocked.

All tasks, receipts and results below are synthetic isolated fixtures, not
scientific data. No scheduler, GPU, provider or environment is invoked.
"""
from __future__ import annotations
import hashlib,importlib.util,json,sys,types
from dataclasses import dataclass
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'producer'))
from safe_io import canonical_bytes,sha_file,write_new_json
from fresh_round_contract import schedule_for_attempt

@dataclass(frozen=True)
class Task:
    index:int;task_id:str;split:str;task_type:str;gamefile:str;gamefile_sha1:str;root:str;traj_file:str
@dataclass(frozen=True)
class Scheduled:
    scheduled_cell_id:str;task_index:int;task_id:str;seed:int

def module_from_file(name,path,monkeypatch):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,name,m);spec.loader.exec_module(m);return m

def install_native(monkeypatch):
    for name in ['pchsi','pchsi.round_control','pchsi.evaluation']:
        m=types.ModuleType(name);m.__path__=[];monkeypatch.setitem(sys.modules,name,m)
    task=types.ModuleType('pchsi.evaluation.task_manifest');task.FrozenTaskRecord=Task
    sched=types.ModuleType('pchsi.evaluation.run_schedule');sched.ScheduledCell=Scheduled
    sched.scheduled_cell_id=lambda *,task_index,seed:f't{task_index:04d}-s{seed:010d}'
    sched.execution_attempt_id=lambda *,scheduled_cell_id,attempt_ordinal:f'{scheduled_cell_id}-a{attempt_ordinal:03d}'
    monkeypatch.setitem(sys.modules,task.__name__,task);monkeypatch.setitem(sys.modules,sched.__name__,sched)
    native=module_from_file('pchsi.round_control.clean_execution_binding',ROOT/'tests/fixtures/clean_execution_binding.py',monkeypatch)
    roll=module_from_file('pchsi.round_control.rollout_collection',ROOT/'tests/fixtures/rollout_collection.py',monkeypatch)
    return native,roll,sched

def setup(tmp_path,monkeypatch,ordinal):
    native,roll,sched=install_native(monkeypatch)
    cap=tmp_path/'cap';cap.mkdir();worktree=tmp_path/'worktree'
    train=tmp_path/'train';train.mkdir();rows=[]
    for i in [10,12]:
        d=train/str(i);d.mkdir();files={}
        for name in ('game.tw-pddl','traj.json','initial.json'):
            p=d/name;p.write_text('synthetic-test-'+str(i)+name);files[name]=p
        game=files['game.tw-pddl'];traj=files['traj.json'];initial=files['initial.json']
        rows.append({'schema_id':'ALFWORLD_CLEAN_TRAIN_TASK_RECORD_V1','split':'train','train_pool':'TRAIN_UPDATE','index':i,'id':str(i),'task_type':'fixture',
          'gamefile_relpath':str(game.relative_to(train)),'traj_file_relpath':str(traj.relative_to(train)),'initial_state_relpath':str(initial.relative_to(train)),
          'gamefile_sha1':hashlib.sha1(game.read_bytes()).hexdigest(),'gamefile_sha256':sha_file(game),'traj_sha256':sha_file(traj),'initial_state_sha256':sha_file(initial)})
    manifest=cap/'TRAIN_UPDATE.jsonl';manifest.write_bytes(b''.join(canonical_bytes(x) for x in rows))
    runtime=cap/'runtime.json';write_new_json(runtime,{'policy_runtime_manifest_sha256':'a'*64})
    memory=cap/'memory.json';write_new_json(memory,{'active_snapshot_sha256':'b'*64})
    binding={'round_id':'OLD_ROUND','parent_policy_id':'parent','train_update_authority':{'manifest_sha256':sha_file(manifest),'train_root':str(train),'row_count':2,'rollout_seed':3},
        'memory_authority':{'runtime_identity_file_sha256':sha_file(memory),'active_snapshot_sha256':'b'*64,'token_budget_contract_sha256':'c'*64},
        'runtime_authority':{'runtime_binding_file_sha256':sha_file(runtime)}}
    bp=cap/'ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_EXECUTION_BINDING_V1.json';write_new_json(bp,binding)
    root=tmp_path/'fresh';ev=root/'round_evidence';ev.mkdir(parents=True)
    profile=ev/'ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1.json';write_new_json(profile,{'profile_kind':'I1','policy_version':'parent'})
    req=roll.RoundRolloutCollectionRequestV1(round_id='NEW_ROUND',execution_attempt_id='new-namespace',parent_policy_id='parent',parent_policy_artifact_sha256='a'*64,
        policy_runtime_binding_sha256=sha_file(runtime),execution_profile_sha256=sha_file(profile),train_update_manifest_sha256=sha_file(manifest),
        round_memory_runtime_authority_sha256=sha_file(memory),round_start_memory_snapshot_sha256='b'*64,token_budget_contract_sha256='c'*64,execution_namespace='new-namespace',rollout_seed=3)
    rp=ev/'ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json';write_new_json(rp,req.to_dict())
    plan={'shard_count':2,'total_schedule_count':2,'fresh_execution_attempt_ordinal':ordinal,'activation_id':req.execution_attempt_id,
        'current_round_request_path':str(rp),'current_round_request_file_sha256':sha_file(rp)}
    records=native.load_clean_train_pool_records(manifest_path=manifest,expected_manifest_sha256=sha_file(manifest),train_root=train,expected_pool='TRAIN_UPDATE',expected_count=2)
    base=native.build_clean_train_schedule(records=records,train_pool='TRAIN_UPDATE',seed=3)
    bound=schedule_for_attempt(base,ordinal,sched.execution_attempt_id)
    for i,cell in enumerate(bound):
        sr=root/'shards'/f'{i:04d}';sr.mkdir(parents=True)
        write_new_json(sr/'PCHSI_V1232S_SHARD_TERMINALS_V1.json',{'rows':[{'global_ordinal':i,'scientific_cell_id':cell.scientific_cell_id,
            'execution_attempt_id':cell.execution_attempt_id,'task_id':cell.cell.task_id,'task_index':cell.cell.task_index,
            'status':'SCIENTIFIC_FAILURE','success':False,'terminal_receipt_sha256':'d'*64,
            'attempt_bundle_root':str(sr/'rollout_run/attempts'),'attempt_terminal_path':str(sr/'terminal.json')}]})
    for rel in ['round_control/rollout_collection.py','round_control/clean_execution_binding.py','evaluation/episode_evaluator.py','round_control/attempt_receipts.py','evaluation/policy_attempt_adapter.py']:
        p=worktree/'src/pchsi'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# fixture hash target only\n')
    return root,cap,worktree,plan,bp,sha_file(rp),bound

@pytest.mark.parametrize('ordinal',[0,2])
def test_real_finalizer_uses_new_round_and_shared_schedule(tmp_path,monkeypatch,ordinal):
    root,cap,repo,plan,bp,rsha,schedule=setup(tmp_path,monkeypatch,ordinal)
    before=bp.read_bytes()
    module=module_from_file('tested_finalizer',ROOT/'producer/global_finalize.py',monkeypatch)
    assert module.try_finalize(state_root=root,worktree=repo,extracted_capsule=cap,shard_plan=plan) is True
    h=json.loads((root/'round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json').read_text())
    assert h['round_id']=='NEW_ROUND' and h['scientific_rollout_valid'] is True and h['rollout_request_sha256']==rsha
    index=json.loads((root/'round_evidence/ROUND_SHARDED_ATTEMPT_BUNDLE_INDEX_V1.json').read_text())
    assert all(r['attempt_bundle_path'].endswith(schedule[i].execution_attempt_id) for i,r in enumerate(index['rows']))
    assert bp.read_bytes()==before
    assert module.try_finalize(state_root=root,worktree=repo,extracted_capsule=cap,shard_plan=plan) is True

def test_old_worker_durably_records_exact_missing_capsule(tmp_path,monkeypatch):
    from recovery_core import validate_capsule_missing_fatal
    module=module_from_file('original_worker_missing_capsule',ROOT/'reviewed_original/shard_worker.py',monkeypatch)
    root=tmp_path/'run';root.mkdir();plan=root/'plan.json';capsule=root/'missing-input.zip'
    write_new_json(plan,{'shard_count':2,'staged_release_gate':{'initially_release_only_shard_id':0,'scientific_terminal_statuses':['SCIENTIFIC_SUCCESS','SCIENTIFIC_FAILURE']}})
    monkeypatch.delenv('SLURM_ARRAY_JOB_ID',raising=False)
    monkeypatch.setattr(sys,'argv',['worker','--state-root',str(root),'--v1230-output-root',str(tmp_path/'impl'),'--capsule',str(capsule),'--shard-plan',str(plan),'--shard-id','0'])
    assert module.main()==0
    fatal=json.loads((root/'shards/0000/PCHSI_V1232S_SHARD_FATAL_V1.json').read_text())
    assert validate_capsule_missing_fatal(fatal,capsule)==str(capsule)
    assert not (root/'shards/0000/PCHSI_V1232S_ALLOCATION_PREFLIGHT_RESULT_V1.json').exists()

def test_original_finalizer_reproduces_old_round_request_conflict(tmp_path,monkeypatch):
    root,cap,repo,plan,bp,rsha,schedule=setup(tmp_path,monkeypatch,0)
    module=module_from_file('original_finalizer_round_conflict',ROOT/'reviewed_original/global_finalize.py',monkeypatch)
    with pytest.raises(RuntimeError,match='GLOBAL_REQUEST_BYTES_CHANGED'):
        module.try_finalize(state_root=root,worktree=repo,extracted_capsule=cap,shard_plan=plan)
    assert not (root/'round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json').exists()

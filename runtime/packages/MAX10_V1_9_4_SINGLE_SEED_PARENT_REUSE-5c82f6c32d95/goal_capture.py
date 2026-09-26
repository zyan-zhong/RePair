"""Spawn-safe private observer. Original public worker messages are unchanged."""
from pathlib import Path
from functools import partial,lru_cache
import hashlib,json
from goal_metric import METRIC_ID,from_game,completion,state_facts

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def write_once(path,value):
    path=Path(path);raw=canonical(value)+b'\n';path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('GOAL_EVIDENCE_CHANGED')
    else:
        with path.open('xb') as stream:stream.write(raw)
    return {'path':str(path),'sha256':sha(raw)}

@lru_cache(maxsize=None)
def spec_for(path,expected_sha):
    raw=Path(path).read_bytes()
    if sha(raw)!=expected_sha:raise ValueError('GOAL_GAMEFILE_CHANGED')
    return from_game(json.loads(raw))

def goal_worker(connection,create_request_bytes,*,capture_path,identity,source_refs):
    for ref in source_refs:
        if sha(Path(ref['path']).read_bytes())!=ref['sha256']:raise ValueError('GOAL_SOURCE_CHANGED')
    from pchsi.evaluation.alfworld_worker import real_alfworld_worker_main
    from pchsi.evaluation.alfworld_worker_protocol import worker_message_from_bytes,ResetResult,StepResult,WorkerTerminalStatus,WorkerFailure
    from textworld.envs.pddl.pddl import PddlEnv
    from unittest.mock import patch
    create=worker_message_from_bytes(create_request_bytes)
    if create.exact_gamefile!=identity['gamefile'] or create.runtime_manifest_sha256!=identity['environment_runtime_manifest_sha256']:raise ValueError('GOAL_WORKER_IDENTITY')
    spec=spec_for(identity['gamefile'],identity['gamefile_sha256']);snapshot={};public={};closed=False;failed=False
    gather=PddlEnv._gather_infos
    def observe(env):
        gather(env)
        if env.request_infos.policy_commands or env.request_infos.intermediate_reward or 'walkthrough' in env.request_infos.extras:raise ValueError('GOAL_ORACLE_INFO_REQUESTED')
        facts=state_facts(env._pddl_state)
        relevant={(p,tuple(args)) for g in spec['groups'] for alt in g['alternatives'] for p,args,neg in alt}
        facts=facts & relevant;n,d=completion(spec,facts)
        won=bool(env.state['won'])
        if (n==d)!=won:raise ValueError('GOAL_FULL_SATISFACTION_DISAGREES_NATIVE_WON')
        snapshot.update(numerator=n,denominator=d,native_won=won,facts=sorted((p,list(args)) for p,args in facts))
    class PublicConnection:
        def recv_bytes(self):return connection.recv_bytes()
        def close(self):return connection.close()
        def send_bytes(self,raw):
            nonlocal closed,failed
            msg=worker_message_from_bytes(raw)
            if isinstance(msg,(ResetResult,StepResult)):
                public['final_observation_sha256']=sha(msg.observation.encode())
                if isinstance(msg,ResetResult):public['environment_step_count']=0
                else:public['environment_step_count']+=1
            if isinstance(msg,WorkerTerminalStatus):closed=msg.status=='CLOSED'
            if isinstance(msg,WorkerFailure):failed=True
            connection.send_bytes(raw)
    with patch.object(PddlEnv,'_gather_infos',observe):
        real_alfworld_worker_main(PublicConnection(),create_request_bytes)
    if closed and not failed and snapshot and public:
        write_once(capture_path,{'schema_id':'RESTRICTED_TERMINAL_GOAL_CAPTURE_V1','metric_id':METRIC_ID,
            'identity':identity,'source_refs':source_refs,'goal_spec_sha256':sha(canonical(spec)),
            'terminal_state_only':True,'public_protocol_unchanged':True,**snapshot,**public})

def install_cell_capture(live,source_refs):
    original=live._recover_or_execute_cell
    def execute(**kwargs):
        cell=kwargs['cell'];task=kwargs['task_access_record'];root=Path(kwargs['condition_root'])
        capture=root/'restricted_goal_progress'/cell.condition_cell_id/'TERMINAL_CAPTURE.json'
        identity={'condition_cell_id':cell.condition_cell_id,'gamefile':str(Path(task.gamefile).resolve()),
            'gamefile_sha256':task.gamefile_sha256,'environment_runtime_manifest_sha256':kwargs['preflight']['environment_runtime_manifest_sha256']}
        types=dict(kwargs['types']);adapter=types['SpawnedAlfworldAdapter']
        class PrivateCaptureAdapter:
            @staticmethod
            def start(**options):return adapter.start(**options,worker_target=partial(goal_worker,capture_path=str(capture),identity=identity,source_refs=source_refs))
        types['SpawnedAlfworldAdapter']=PrivateCaptureAdapter
        row=original(**{**kwargs,'types':types})
        loaded=kwargs['attempt_auditor'].load_attempt_directory_v1(root/'evaluator_run/attempts'/row['execution_attempt_id'])
        validate_capture(capture,loaded.episode_artifact,row,source_refs)
        write_once(capture.with_name('BOUND_GOAL_METRIC.json'),{'schema_id':'RESTRICTED_BOUND_GOAL_METRIC_V1',
            'condition_cell_id':row['condition_cell_id'],'execution_attempt_id':row['execution_attempt_id'],
            'attempt_bundle_sha256':row['attempt_bundle_sha256'],'capture_ref':{'path':str(capture),'sha256':sha(capture.read_bytes())}})
        return row
    live._recover_or_execute_cell=execute

def validate_capture(path,episode,row,source_refs):
    value=json.loads(Path(path).read_bytes());identity=value['identity']
    if value.get('metric_id')!=METRIC_ID or value['source_refs']!=source_refs:raise ValueError('GOAL_CAPTURE_SOURCE_IDENTITY')
    if identity['condition_cell_id']!=row['condition_cell_id'] or identity['gamefile_sha256']!=episode.gamefile_sha256 or identity['environment_runtime_manifest_sha256']!=episode.environment_runtime_manifest_sha256:raise ValueError('GOAL_CAPTURE_EPISODE_IDENTITY')
    budget=episode.final_budget
    steps=budget['environment_step_count'] if isinstance(budget,dict) else budget.environment_step_count
    if value['environment_step_count']!=steps or value['final_observation_sha256']!=episode.final_observation_sha256:raise ValueError('GOAL_CAPTURE_TERMINAL_STATE_MISMATCH')
    spec=spec_for(identity['gamefile'],identity['gamefile_sha256'])
    pair=completion(spec,{(p,tuple(args)) for p,args in value['facts']})
    if value['goal_spec_sha256']!=sha(canonical(spec)) or pair!=(value['numerator'],value['denominator']):raise ValueError('GOAL_CAPTURE_RECOMPUTATION_FAILED')
    if value['native_won']!=row['success'] or (pair[0]==pair[1])!=row['success']:raise ValueError('GOAL_CAPTURE_SUCCESS_CONFLICT')
    return pair

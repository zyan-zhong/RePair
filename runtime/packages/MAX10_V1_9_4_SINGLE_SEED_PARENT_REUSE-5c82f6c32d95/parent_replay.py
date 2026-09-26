"""Recover missing terminal goal metric by replaying audited actions, never a policy."""
from pathlib import Path
from functools import partial
import json
from goal_capture import goal_worker,validate_capture,write_once,sha

def replay(loaded,task,capture,source_refs):
    from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter
    e=loaded.episode_artifact
    identity={'condition_cell_id':e.condition_cell_id,'gamefile':str(Path(task.gamefile).resolve()),
        'gamefile_sha256':e.gamefile_sha256,'environment_runtime_manifest_sha256':e.environment_runtime_manifest_sha256}
    env=SpawnedAlfworldAdapter.start(exact_gamefile=Path(task.gamefile),registration_id='parent-replay-'+sha(e.execution_attempt_id.encode())[:24],
        runtime_manifest_sha256=e.environment_runtime_manifest_sha256,
        worker_target=partial(goal_worker,capture_path=str(capture),identity=identity,source_refs=source_refs))
    try:
        state=env.reset()
        if sha(state.observation.encode())!=e.initial_observation_sha256:raise ValueError('PARENT_REPLAY_INITIAL_STATE_MISMATCH')
        if loaded.traces and (state.observation,tuple(state.menu.commands))!=(loaded.traces[0].observation,tuple(loaded.traces[0].admissible_commands)):raise ValueError('PARENT_REPLAY_INITIAL_MENU_MISMATCH')
        for n,t in enumerate(loaded.public_transitions):
            if t.environment_step_index!=n or state.observation!=t.pre_action_observation or tuple(state.menu.commands)!=tuple(t.pre_action_admissible_commands):raise ValueError('PARENT_REPLAY_PRE_STATE_MISMATCH')
            state=env.step(t.submitted_action)
            if (state.observation,tuple(state.menu.commands),state.score,state.done,state.won)!=(t.resulting_observation,tuple(t.resulting_admissible_commands),t.score,t.done,t.won):raise ValueError('PARENT_REPLAY_POST_STATE_MISMATCH')
        if sha(state.observation.encode())!=e.final_observation_sha256:raise ValueError('PARENT_REPLAY_FINAL_STATE_MISMATCH')
    finally:
        status=env.close()
        if status.status!='CLOSED' or status.exit_code!=0:raise ValueError('PARENT_REPLAY_WORKER_NOT_CLEANLY_CLOSED')
    return validate_capture(capture,e,{'condition_cell_id':e.condition_cell_id,'success':e.success},source_refs)

def metric_for_source(*,cache,root,loaded,row,allow_replay):
    from continuity_binding.api import read_ref
    from parent_cache import ref
    from promotion_entry import ROOT,source_refs
    e=loaded.episode_artifact
    if 'goal_progress_ref' in cache.summary:
        metric=read_ref(cache.summary['goal_progress_ref'])
        rows=[r for r in metric['rows'] if r['label']==cache.arm and r['condition_cell_id']==e.condition_cell_id]
        if len(rows)!=1:raise ValueError('CACHE_SOURCE_METRIC_CELL_NOT_UNIQUE')
        m=rows[0];bound=read_ref(m['bound_metric_ref']);capture_ref=bound['capture_ref'];read_ref(capture_ref)
        refs=metric['source_refs']
        # Reusing a different measurement definition would not be a paired comparison.
        current_metric=next(r for r in source_refs() if Path(r['path']).name=='goal_metric.py')
        old_metric=next(r for r in refs if Path(r['path']).name=='goal_metric.py')
        if old_metric['sha256']!=current_metric['sha256']:raise ValueError('CACHE_METRIC_DEFINITION_CHANGED')
        pair=validate_capture(capture_ref['path'],e,row,refs)
        if pair!=(m['numerator'],m['denominator']):raise ValueError('CACHE_SOURCE_METRIC_CHANGED')
        metric_ref=m['bound_metric_ref']
    else:
        refs=source_refs();dest=ROOT/'runtime/restricted_parent_replays'/cache.origin['source_terminal_ref']['sha256']/cache.arm/e.condition_cell_id
        capture=dest/'TERMINAL_CAPTURE.json';certificate=dest/'REPLAY_CERTIFICATE.json'
        expected={'schema_id':'AUDITED_PARENT_ACTION_REPLAY_V1','source_terminal_ref':cache.origin['source_terminal_ref'],
            'condition_cell_id':e.condition_cell_id,'execution_attempt_id':row['execution_attempt_id'],'attempt_bundle_sha256':row['attempt_bundle_sha256'],
            'source_refs':refs,'environment_steps_replayed':len(loaded.public_transitions),'policy_calls':0,'fresh_scientific_episode':False}
        if not certificate.exists():
            if not allow_replay:raise ValueError('CACHE_GOAL_METRIC_MATERIALIZATION_MISSING')
            replay(loaded,cache.source['access'].records[e.task_index],capture,refs)
            write_once(certificate,{**expected,'capture_ref':ref(capture)})
        value=read_ref(ref(certificate))
        if value!={**expected,'capture_ref':ref(capture)}:raise ValueError('CACHE_REPLAY_CERTIFICATE_CHANGED')
        pair=validate_capture(capture,e,row,refs);metric_ref=ref(certificate)
    bound=read_ref(metric_ref)
    for key in ('execution_attempt_id','attempt_bundle_sha256'):
        if bound[key]!=row[key]:raise ValueError('CACHE_METRIC_ATTEMPT_CHANGED')
    dest=ROOT/'runtime/restricted_parent_metrics'/cache.origin['source_terminal_ref']['sha256']/cache.arm/e.condition_cell_id/'METRIC.json'
    return write_once(dest,{'schema_id':'REUSED_PARENT_GOAL_METRIC_V1','condition_cell_id':e.condition_cell_id,
        'execution_attempt_id':row['execution_attempt_id'],'attempt_bundle_sha256':row['attempt_bundle_sha256'],
        'numerator':pair[0],'denominator':pair[1],'bound_metric_ref':metric_ref})

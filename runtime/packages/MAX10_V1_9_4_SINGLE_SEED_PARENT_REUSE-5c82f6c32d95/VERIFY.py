from pathlib import Path
import sys,json,hashlib,subprocess,collections
from promotion_entry import ROOT,verify,load,future_deployment,source_refs,seed_inputs

def server():
    a,prior,identity,prepared=load()
    from entry.registration import build_deployment
    from memory_binding.worker_bootstrap import bootstrap_current_and_children
    from continuity_binding.api import read_ref
    boundary=read_ref(a['promotion_boundary_ref'])
    assert boundary['round_index']==a['promotion_activation_after_round_index']
    assert boundary['request']['path']==a['promotion_excluded_request_ref']['path'] or read_ref(boundary['request'])==read_ref({'path':a['promotion_excluded_request_ref']['path'],'sha256':a['promotion_excluded_request_ref']['file_sha256']})
    base=Path(a['base_source_root']);deployment=build_deployment(base,entry_source_sha256=hashlib.sha256((base/'PACKAGE_FILES.sha256').read_bytes()).hexdigest())
    bootstrap_current_and_children(deployment['scientific_repo_root'])
    from goal_capture import spec_for,goal_worker,validate_capture,write_once
    from functools import partial
    from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter
    from types import SimpleNamespace
    future=future_deployment(deployment,a);rule=read_ref(future['promotion_rule_ref'])
    tasks=read_ref(deployment['offoff_source_registration']['assets']['task_access'])['records']
    counts=collections.Counter();witnesses=[]
    for task in tasks:
        spec=spec_for(task['gamefile'],task['gamefile_sha256']);counts[sum(g['count'] for g in spec['groups'])]+=1
        witnesses.append(sum(len(g['alternatives']) for g in spec['groups']))
    env_sha=deployment['offoff_source_registration']['assets']['environment_runtime']['sha256']
    selected={}
    for task in tasks:selected.setdefault(task['task_type'],task)
    import uuid
    diagnostic_root=ROOT/'validation'/'diagnostics'/uuid.uuid4().hex
    results=[]
    for i,task in enumerate(selected.values()):
        dest=diagnostic_root/task['task_id']/'TERMINAL_CAPTURE.json'
        identity_fields={'condition_cell_id':'DIAGNOSTIC-'+task['task_id'],'gamefile':task['gamefile'],'gamefile_sha256':task['gamefile_sha256'],'environment_runtime_manifest_sha256':env_sha}
        env=SpawnedAlfworldAdapter.start(exact_gamefile=Path(task['gamefile']),registration_id='goal-diagnostic-'+str(i),runtime_manifest_sha256=env_sha,
            worker_target=partial(goal_worker,capture_path=str(dest),identity=identity_fields,source_refs=source_refs()))
        try:
            public=env.reset();steps=0
            if i%2==1:
                public=env.step(public.menu.commands[0]);steps=1
        finally:env.close()
        cap=json.loads(dest.read_bytes())
        episode=SimpleNamespace(gamefile_sha256=task['gamefile_sha256'],environment_runtime_manifest_sha256=env_sha,final_budget={'environment_step_count':steps},final_observation_sha256=hashlib.sha256(public.observation.encode()).hexdigest())
        validate_capture(dest,episode,{'condition_cell_id':identity_fields['condition_cell_id'],'success':cap['native_won']},source_refs())
        results.append(cap)
    # Native materialization exercised without any Slurm/model execution.
    import entry.offoff_job as job,entry.candidate_runtime as candidate,offoff_binding.registered_inputs as inputs
    from candidate_labels import load_publisher,load_registered_inputs
    from unittest.mock import patch
    from goal_runtime import installed
    class Checked(Exception):pass
    start=read_ref({'path':a['promotion_excluded_request_ref']['path'],'sha256':a['promotion_excluded_request_ref']['file_sha256']})
    trained_ref=a['preserved_training_select_refs']['training/TRAINING_JOB_RESULT.json'];trained=read_ref({'path':trained_ref['path'],'sha256':trained_ref['file_sha256']})['result']
    def no_submit(**kwargs):
        parallel=read_ref(kwargs['parallel_ref']);binding=read_ref(parallel['binding_ref']);protocol=read_ref(binding['input_refs']['protocol_ref'])
        assert protocol['promotion_rule_ref']==future['promotion_rule_ref'] and binding['memory_state']==binding['harness_state']=='OFF'
        assert binding['paired_cell_count']==len(tasks)*len(rule['replicate_seeds'])
        resource=read_ref(rule['select_parallel_resource_ref']);shards=parallel['shards']
        assert len(shards)==min(resource['shard_count'],resource['max_concurrent_shards'],binding['paired_cell_count'])
        ordinals=[n for s in shards for n in s['ordinals']]
        assert sorted(ordinals)==list(range(binding['paired_cell_count']))
        assert max(len(s['ordinals']) for s in shards)-min(len(s['ordinals']) for s in shards)<=1
        from offoff_binding.native import Native
        from offoff_binding.execute import _registered_decider
        _registered_decider(Native.load(binding['native_repo_root'],binding['source_refs']),rule)
        print('V2_NATIVE_SELECT_MATERIALIZATION_NO_SUBMISSION_PASS '+json.dumps({'replicate_seeds':protocol['replicate_seeds'],'paired_cells':binding['paired_cell_count'],'shards':len(shards),'pairs_per_shard':[len(s['ordinals']) for s in shards]}),flush=True)
        raise Checked()
    with installed(),patch.object(candidate,'publish_candidate',load_publisher(a['candidate_publisher_ref'])),patch.object(inputs,'materialize_registered_inputs',seed_inputs(load_registered_inputs(a['registered_inputs_source_ref']))),patch.object(job,'execute_current_offoff_jobs',no_submit):
        try:job.execute_current_offoff_job(start=start,current_inputs_ref=a['current_inputs_ref'],trained=trained,output_root=ROOT/'validation/NO_LAUNCH_SELECT',deployment=future)
        except Checked:pass
        else:raise ValueError('NATIVE_SELECT_VALIDATION_BOUNDARY_NOT_REACHED')
    print(json.dumps({'all_registered_tasks':len(tasks),'condition_distribution':dict(counts),'maximum_witness_alternatives':max(witnesses),
        'native_spawned_worker_diagnostics':len(results),'zero_action_terminal_cases':sum(r['environment_step_count']==0 for r in results),
        'one_action_terminal_cases':sum(r['environment_step_count']==1 for r in results),'policy_calls':0,'slurm_submissions':0,'git_mutations':0}),flush=True)
    from runtime_regression import run
    run(deployment,future,a)
    from reuse_regression import run as reuse_regression
    reuse_regression(deployment,future,a)
    from current_cutover import materialize as materialize_cutover
    cutover_ref=materialize_cutover(a)
    print('CURRENT_FIXED_SEED_CUTOVER_BINDING_MATERIALIZED_NO_DECISION '+json.dumps(cutover_ref),flush=True)

if __name__=='__main__':
    verify()
    test=subprocess.run([sys.executable,'-m','pytest','-q',str(ROOT/'test_metric.py'),str(ROOT/'test_integration.py'),str(ROOT/'test_parent_cache.py')],cwd=ROOT)
    if test.returncode:raise SystemExit(test.returncode)
    if '--server' in sys.argv:server()
    print('GOAL_FRACTION_VERIFY_PASS',flush=True)

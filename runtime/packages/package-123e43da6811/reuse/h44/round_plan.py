"""Materialize current source and branch bindings from the accepted handoff only."""
from pathlib import Path
from io_utils import read_json,put_json,digest_file,sha,canonical,verify_extract
from source_adapter import load_source_rows,register_source
from option_adapter import compile_option
from deployment import resolve_memory,resolve_gamefiles
ROOT=Path(__file__).resolve().parent


def prepare_plan(*,capture_zip,expected_sha256,run_root,locators,operations):
    run_root=Path(run_root)
    capture=run_root/'input'
    verify_extract(Path(capture_zip),expected_sha256,capture)
    request=read_json(capture/'current_rollout/ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json')
    handoff=read_json(capture/'pre_root/V1232V_PLANNER_BOUND_F0F1_LAUNCH_HANDOFF_V1.json')
    source_rows=load_source_rows(capture)
    # The actor source is fixed by the input proof and package provenance, not current HEAD.
    provenance=read_json(ROOT/'assets/source_revision.json')
    episode_commits={r['bundle'].episode_artifact.evaluator_commit for r in source_rows}
    if episode_commits and episode_commits!={provenance['actor_commit']}:
        raise ValueError('package actor source differs from selected rollout evidence')
    memory=resolve_memory(request=request,locators=locators)
    gamefiles=resolve_gamefiles(request=request,source_rows=source_rows,locators=locators)
    runtime_path=capture/'actor_runtime/runtime_binding.json'
    if digest_file(runtime_path)!=request['policy_runtime_binding_sha256']:
        raise ValueError('captured runtime differs from current rollout request')
    runtime=read_json(runtime_path)
    from pchsi.research_intelligence.human_f0f1_runtime import load_continuation_runtime_binding_v2
    load_continuation_runtime_binding_v2(runtime_path,expected_file_sha256=request['policy_runtime_binding_sha256'],expected_model=runtime['served_model_name'])
    memory_copy=run_root/'authority/MEMORY_RUNTIME.json'
    from io_utils import write_new_or_equal
    write_new_or_equal(memory_copy,Path(memory['path']).read_bytes())
    if digest_file(memory_copy)!=memory['file_sha256']:
        raise ValueError('Memory runtime is not original canonical bytes')
    states=[];branch_bindings=[]
    for row in source_rows:
        fp=row['fingerprint'];selected=row['handoff_state'];candidate=row['candidate']
        srdir=run_root/'states'/fp['fingerprint_sha256']
        source=register_source(row,exact_gamefile=Path(gamefiles[fp['source_task_id']]['gamefile']))
        source_path=srdir/'REGISTERED_REPLAY_SOURCE_V1.json'
        from io_utils import write_new_or_equal
        write_new_or_equal(source_path,source.canonical_bytes())
        registration=compile_option(candidate)
        status=registration['status']
        contract_path=srdir/'TYPED_OPTION_CONTRACT_V2.json'
        if registration['contract'] is not None:put_json(contract_path,registration['contract'])
        put_json(srdir/'SEMANTICS_REGISTRATION.json',registration)
        state={'source_state_sha256':selected['source_state_sha256'],
               'native_source_fingerprint_sha256':fp['fingerprint_sha256'],
               'source_candidate_sha256':candidate['candidate_sha256'],
               'state_index':selected['state_index'],'semantics_status':status,
               'semantics_reason':registration.get('reason'),
               'public_task_goal':row['source_call'].public_task_goal,
               'source_task_id':fp['source_task_id'],
               'source_gamefile_sha256':fp['source_gamefile_sha256'],
               'registered_source_path':str(source_path),
               'registered_source_file_sha256':digest_file(source_path)}
        states.append(state)
        for branch in handoff['branch_plan']:
            if branch['source_state_sha256']!=selected['source_state_sha256']:continue
            if branch['f1_candidate_sha256']!=(candidate['candidate_sha256'] if branch['arm']=='F1' else None):
                raise ValueError('branch candidate differs from selected original')
            if registration['contract'] is None:continue
            binding={
              'schema_id':'CURRENT_MEMORY_AWARE_NATIVE_BRANCH_BINDING_V1',
              'branch_key_sha256':branch['branch_key_sha256'],
              'arm':branch['arm'],'paired_seed':branch['paired_seed'],
              'replicate_index':branch['replicate_index'],
              'source_state_sha256':selected['source_state_sha256'],
              'native_source_fingerprint_sha256':fp['fingerprint_sha256'],
              'source_candidate_sha256':candidate['candidate_sha256'],
              'replay_source_path':str(source_path),'replay_source_file_sha256':digest_file(source_path),
              'runtime_path':str(runtime_path),'runtime_file_sha256':digest_file(runtime_path),
              'memory_runtime_path':str(memory_copy),'memory_runtime_file_sha256':digest_file(memory_copy),
              'typed_contract_path':str(contract_path),'typed_contract_file_sha256':digest_file(contract_path),
              'active_snapshot_sha256':request['round_start_memory_snapshot_sha256'],
              'policy_model':runtime['served_model_name'],'public_task_goal':row['source_call'].public_task_goal,
              'policy_timeout_seconds':operations['policy_timeout_seconds']}
            binding['binding_sha256']=sha(canonical(binding))
            path=run_root/'bindings'/(branch['branch_key_sha256']+'.json');put_json(path,binding)
            branch_bindings.append({'path':str(path),'file_sha256':digest_file(path),'binding':binding})
    plan={'schema_id':'CURRENT_ACCEPTED_PRE_NATIVE_EXECUTION_PLAN_V1',
          'capture_zip_sha256':expected_sha256,'round_id':request['round_id'],
          'runtime_path':str(runtime_path),'runtime_file_sha256':digest_file(runtime_path),
          'source_request':request,'handoff':handoff,'states':states,
          'branch_bindings':branch_bindings,'operations':operations,
          'scope_notice':read_json(capture/'native_execution_gate/HYPOTHESIS_SCOPE_NOTICE_V1.json'),
          'native_environment_execution_performed':False,'max10_released':False}
    plan['plan_sha256']=sha(canonical(plan));put_json(run_root/'EXECUTION_PLAN.json',plan)
    return plan

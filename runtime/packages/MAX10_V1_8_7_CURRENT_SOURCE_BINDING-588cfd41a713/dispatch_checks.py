"""Actual GPU import path plus native branch behavior, with fake policy/environment."""
from pathlib import Path
import sys,json,importlib.util,hashlib

def main():
    from gpu_entry import prepare_gpu
    prepare_gpu()
    from condition_entry import ROOT
    a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    from exact_bindings import read_ref
    accepted=read_ref({'path':a['immutable_refs']['accepted_pre']['path'],'file_sha256':a['immutable_refs']['accepted_pre']['sha256']})
    handoff=read_ref(accepted['handoff']);selected=handoff['selected_states'][0];candidate=selected['candidate']
    root=Path(a['h44_package']['root']);path=root/'tests/test_branch_flow.py'
    manifest=dict((n,s) for s,n in (line.split(maxsplit=1) for line in read_ref(a['h44_package']['manifest'],as_bytes=True).decode().splitlines()))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['tests/test_branch_flow.py']:raise ValueError('BRANCH_TEST_SOURCE_CHANGED')
    spec=importlib.util.spec_from_file_location('registered_h44_branch_regression',path);fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
    # Retain the previous short-option branch behavior as well.
    for name in ['test_f1_uses_native_memory_prepare_process_after_option','test_f0_never_executes_option_and_retains_original_budget',
                 'test_journal_intent_precedes_environment_result','test_f1_own_state_retrieval_not_copied_from_f0',
                 'test_f0_source_prompt_mismatch_prevents_all_effects','test_actual_native_budget_api_used_not_call_index_as_step_count']:
        getattr(fixtures,name)()
    from option_adapter import compile_option,decide,validate_contract
    from native_branch import run_branch_core
    from pchsi.evaluation.budget import BudgetState,BudgetLimits
    from io_utils import sha
    contract=compile_option(candidate)['contract'];menu=tuple(selected['source_context']['admissible_commands'])
    # Visible objects must not suppress an exact intervention as a search option would.
    d=decide(contract,executed_actions=[],observation='You see a mug 1.',menu=menu,environment_done=False)
    assert d['action']==candidate['exact_action']
    assert decide(contract,executed_actions=[candidate['exact_action']],observation='',menu=(),environment_done=False)['decision']=='STOP'
    for altered in [menu[::-1],tuple(x for x in menu if x!=candidate['exact_action'])]:
        try:decide(contract,executed_actions=[],observation='',menu=altered,environment_done=False)
        except ValueError:pass
        else:raise AssertionError('ALTERED_FULL_MENU_ACCEPTED')
    for arm in ['F0','F1']:
        memory,policy,env=fixtures.Memory(),fixtures.Policy(),fixtures.Env();budget=BudgetState(2,1,0,1,1);limits=BudgetLimits();events=[]
        args=dict(public_task_goal='registered behavior regression',observation='You see a mug 1.',executed_transitions=(),
            policy_visible_commands=menu,harness_visible_commands=menu,environment_commands=menu,
            interface_feedback=None,budget_state=budget,budget_limits=limits)
        initial=memory.prepare(**args)
        # F0 uses a command in the frozen menu; F1 continues from the post-intervention menu.
        if arm=='F0':
            def act(**kw):return json.dumps({'action':candidate['exact_action']}),{'prompt':kw['prepared'].prompt_text}
            policy.act=act
            old_step=env.step
            def step(action):
                result=old_step(action);result.done=True;result.won=True;return result
            env.step=step
        result=run_branch_core(arm=arm,source_prompt_sha256=sha(initial.prompt_text.encode()),goal=args['public_task_goal'],
            observation=args['observation'],commands=menu,history=(),budget=budget,feedback=None,source_call_index=2,seed=19,
            memory_adapter=memory,policy=policy,environment=env,contract=contract,limits=limits,event_sink=events.append)
        if arm=='F1':
            assert env.actions==[candidate['exact_action'],'finish'] and result['option_environment_step_count']==1
            assert result['final_budget']['policy_attempt_count']==3 and result['final_budget']['environment_step_count']==3
            assert result['intervention_sequence'][0]['role']=='REGISTERED_EXACT_ACTION_INTERVENTION'
        else:
            assert env.actions==[candidate['exact_action']] and result['option_environment_step_count']==0
    print(json.dumps({'schema_id':'ACTUAL_GPU_DISPATCH_NATIVE_REGRESSION_V1','existing_short_option_checks':6,
        'exact_action_checks':6,'actual_gpu_entry_imported':True,'full_menu_drift_rejected':True,'one_environment_step_no_fabricated_policy_call':True,
        'provider_call_count':0,'real_environment_actions':0,'slurm_submission_count':0}))

if __name__=='__main__':main()

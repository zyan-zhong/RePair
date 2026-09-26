"""Behavioral tests use the exact registered branch core and native budget/parser."""
import base64
import copy
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
import os
PACKAGE=HERE.parent
AUTHORITY=json.loads((PACKAGE/'AUTHORITY.json').read_bytes())
BASE=Path(os.environ.get('PCHSI_TEST_NATIVE_H44',AUTHORITY['native_h44_root']))
sys.path[:0] = [str(HERE), str(BASE), str(BASE / 'native_repo/src')]


def runtime():
    spec = importlib.util.find_spec('cue_strategy')
    assert spec is not None, 'the cue strategy runtime has not been implemented'
    return __import__('cue_strategy')


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def fixture_contract(change=None,program=None):
    m = runtime()
    from pchsi.evaluation.action_trace import sha256_string_sequence
    from pchsi.reference_loop.canonical import domain_hash
    strategy = dict(principal_bottleneck='The object is inside a closed cabinet.',
                    current_subgoal='Expose and collect the object.',
                    expected_next_event='The open cabinet reveals an object.',
                    expected_state_change='The object becomes available to take.',
                    progress_criterion='The object is placed at the goal.',
                    recovery_trigger='The expected object is absent.',
                    fallback_condition='Choose another admissible search action.',
                    action='open cabinet 1')
    strategy.update(change or {})
    plan = m.build_plan(experiment_id='validation-one', source_state_sha256='1' * 64,
        menu_sha256=sha256_string_sequence(['open cabinet 1']), goal='Put the object on the shelf.',
        strategy=strategy, original_candidate_sha256='2' * 64, original_proposal_sha256='3' * 64,
        source_observation_sha256=sha('A closed cabinet is here.'),program=program)
    candidate = dict(schema_id='ANALYZER_REPAIR_CANDIDATE_V1', schema_version=1,
        source_state_sha256='1' * 64, menu_sha256=plan['menu_sha256'], candidate_kind='FAILURE_REPAIR',
        candidate_status='EXECUTABLE_EXACT_ACTION', exact_action=strategy['action'], option_actions=[],
        termination_condition=None, source_proposal_sha256=plan['strategy_plan_sha256'],
        requires_environment_verification=True, live_menu_revalidation_required=True,
        all_intervention_actions_count_against_environment_budget=True, candidate_sha256='0' * 64)
    candidate['candidate_sha256'] = domain_hash(candidate['schema_id'], candidate, excluded_field='candidate_sha256')
    return m, plan, candidate, m.bind_contract(candidate, plan)


def native_module(monkeypatch):
    # File locking is outside run_branch_core; Windows lacks the POSIX module.
    if sys.platform == 'win32':
        monkeypatch.setitem(sys.modules, 'fcntl', types.SimpleNamespace())
    path = HERE.parent / 'fixtures/native_branch.py'
    spec = importlib.util.spec_from_file_location('_v207_test_native_branch', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeEnvironment:
    def __init__(self, done=True):
        self.actions = []
        self.done = done

    def step(self, action):
        from pchsi.evaluation.action_trace import sha256_string_sequence
        expected = ['open cabinet 1', 'take object 1 from cabinet 1', 'move object 1 to shelf 1']
        assert action == expected[len(self.actions)]
        self.actions.append(action)
        position = len(self.actions)
        obs = ['An object is visible.', 'You hold the object.', 'Object is on the shelf.'][position - 1]
        menu = [expected[position]] if position < 3 else ['look']
        terminal = position == 3 and self.done
        return types.SimpleNamespace(observation=obs, menu=types.SimpleNamespace(commands=tuple(menu),
            sequence_sha256=sha256_string_sequence(menu)), score=int(terminal), done=terminal, won=terminal)


class FakePolicy:
    """Only transport/model generation is fake; evidence construction is native."""
    def __init__(self, invalid=False):
        from pchsi.research_intelligence.human_f0f1_runtime import continuation_request_contract_v1
        self.prompts = []
        self.invalid = invalid
        self.runtime = {'served_model_name': 'frozen-policy',
                        'continuation_request_contract': continuation_request_contract_v1('R0_EXECUTION_PROFILE_V1')}

    def act(self, *, prepared, seed, model_call_index, goal, observation, commands, history, budget, feedback):
        from pchsi.evaluation.policy_call_evidence import build_policy_call_evidence, PolicyCallTransportEvidenceV1
        from pchsi.research_intelligence.human_f0f1_runtime import build_bound_continuation_request_v1
        prompt = prepared.prompt_text
        self.prompts.append(prompt)
        response = 'invalid' if self.invalid else json.dumps({'action': commands[0]})
        rid = 'branch-c' + str(model_call_index)
        request = build_bound_continuation_request_v1(runtime=self.runtime, prompt_text=prompt, seed=seed, request_id=rid)
        wire = request.to_wire_dict()
        body = dict(id=rid, choices=[dict(message=dict(content=response), finish_reason='stop', token_ids=[2])],
                    usage=dict(prompt_tokens=1, completion_tokens=1), prompt_token_ids=[1])
        generation = types.SimpleNamespace(provider_request_id=rid, raw_response_text=response,
            finish_reason='stop', prompt_tokens=1, completion_tokens=1, prompt_token_ids=(1,), token_ids=(2,), latency_ms=1)
        rendered = types.SimpleNamespace(rendered_prompt_text=prompt, rendered_prompt_text_sha256=sha(prompt),
            rendered_token_ids=(1,), prompt_token_count=1)
        transport = PolicyCallTransportEvidenceV1(json.dumps(wire).encode(), 200,
            (('x-request-id', rid), ('content-type', 'application/json'), ('content-length', None)),
            json.dumps(body).encode(), 1)
        evidence = build_policy_call_evidence(model_call_index=model_call_index, public_task_goal=goal,
            observation=observation, admissible_commands=commands, executed_history=history,
            interface_feedback_before=feedback, budget_before=budget, request=request,
            expected_prompt=rendered, generation=generation, transport_evidence=transport)
        return response, evidence.to_dict()


def execute(monkeypatch, arm='F1', *, invalid=False, max_steps=30,program=None):
    from pchsi.evaluation.budget import BudgetState, BudgetLimits
    from pchsi.evaluation.policy_attempt_adapter import RawPolicyAttemptAdapterV1
    import option_adapter
    m, plan, candidate, contract = fixture_contract(program=program)
    module = native_module(monkeypatch)
    restore = m.install_dispatch(option_adapter, module, None, {plan['strategy_plan_sha256']: plan})
    memory = RawPolicyAttemptAdapterV1()
    budget = BudgetState(); limits = BudgetLimits(max_environment_steps=max_steps)
    goal = plan['goal']; obs = 'A closed cabinet is here.'; menu = ('open cabinet 1',)
    prepared = memory.prepare(public_task_goal=goal, observation=obs, executed_transitions=(),
        policy_visible_commands=menu, harness_visible_commands=menu, environment_commands=menu,
        interface_feedback=None, budget_state=budget, budget_limits=limits)
    policy = FakePolicy(invalid=invalid); env = FakeEnvironment(); events = []
    try:
        result = module.run_branch_core(arm=arm, source_prompt_sha256=sha(prepared.prompt_text), goal=goal,
            observation=obs, commands=menu, history=(), budget=budget, feedback=None, source_call_index=4,
            seed=17, memory_adapter=memory, policy=policy, environment=env, contract=contract,
            limits=limits, event_sink=events.append)
    finally:
        restore()
    return m, contract, result, policy, env, events, prepared.prompt_text


def test_distinct_plans_with_same_first_action_do_not_alias():
    m, p1, c1, k1 = fixture_contract()
    _, p2, c2, k2 = fixture_contract({'recovery_trigger': 'The cabinet contains a different object.'})
    assert c1['exact_action'] == c2['exact_action']
    assert p1['strategy_plan_sha256'] != p2['strategy_plan_sha256']
    assert m.execution_identity(c1, p1) != m.execution_identity(c2, p2)
    assert k1['contract_sha256'] != k2['contract_sha256']

def phase_program():
    return [{'purpose':'Acquire and place through live menu affordances','complete_when_any':[],
        'rules':[{'when_all':[],'command':{'kind':'PREFIX_SUFFIX','text':prefix,'suffix':''},'max_uses':1}
                 for prefix in ['take object ','move object ']]}]

def test_guarded_plan_executes_more_than_first_action_and_replays(monkeypatch):
    m,contract,result,policy,env,*_=execute(monkeypatch,program=phase_program())
    assert result['terminal_success'] is True
    assert result['option_environment_step_count']==3
    assert result['policy_call_count_from_source']==0
    assert result['final_budget']['policy_attempt_count']==0
    assert result['final_budget']['environment_step_count']==3
    m.validate_branch_evidence(result,contract,arm='F1')
    damaged=copy.deepcopy(result);damaged['strategy_execution']['guarded_trace'][1]['rule']=1
    with pytest.raises(ValueError,match='GUARDED_TRACE_REPLAY'):m.validate_branch_evidence(damaged,contract,arm='F1')

def test_guarded_plan_cannot_spend_extra_environment_budget(monkeypatch):
    from pchsi.evaluation.budget import BudgetLimits
    m,contract,result,policy,env,*_=execute(monkeypatch,program=phase_program(),max_steps=2)
    assert len(env.actions)==2 and not policy.prompts
    assert result['terminal_reason']=='ENVIRONMENT_STEP_BUDGET_EXHAUSTED'
    m.validate_branch_evidence(result,contract,arm='F1',budget_limits=BudgetLimits(max_environment_steps=2))


def test_contract_rejects_detached_plan_and_tampering():
    m, plan, candidate, contract = fixture_contract()
    changed = copy.deepcopy(plan); changed['strategy']['current_subgoal'] = 'A different plan'
    with pytest.raises(ValueError): m.bind_contract(candidate, changed)
    changed = copy.deepcopy(candidate); changed['source_proposal_sha256'] = 'f' * 64
    with pytest.raises(ValueError): m.bind_contract(changed, plan)
    changed = copy.deepcopy(contract); changed['plan']['goal'] = 'Other goal'
    with pytest.raises(ValueError): m.validate_contract(changed)


def test_f1_keeps_complete_plan_on_each_live_policy_call(monkeypatch):
    m, contract, result, policy, env, events, _ = execute(monkeypatch)
    assert env.actions == ['open cabinet 1', 'take object 1 from cabinet 1', 'move object 1 to shelf 1']
    assert result['option_environment_step_count'] == 1
    assert result['policy_call_count_from_source'] == 2
    assert result['final_budget']['environment_step_count'] == 3
    assert result['final_budget']['policy_attempt_count'] == 2
    assert 'An object is visible.' in policy.prompts[0]
    assert 'You hold the object.' in policy.prompts[1]
    for prompt in policy.prompts:
        for text in contract['plan']['strategy'].values(): assert text in prompt
    intents = [e['prompt_sha256'] for e in events if e['type'] == 'POLICY_CALL_INTENT']
    assert intents == [sha(p) for p in policy.prompts]
    m.validate_branch_evidence(result, contract, arm='F1')


def test_f0_prompt_and_native_budget_are_unchanged(monkeypatch):
    m, contract, result, policy, env, events, original = execute(monkeypatch, 'F0')
    assert policy.prompts[0] == original
    assert result['option_environment_step_count'] == 0
    assert result['final_budget']['policy_attempt_count'] == 3
    assert result['final_budget']['environment_step_count'] == 3
    assert all('CUE_GUIDED_STRATEGY_V1' not in p for p in policy.prompts)
    m.validate_branch_evidence(result, contract, arm='F0')


def test_native_budget_stops_strategy_without_an_extra_policy_call(monkeypatch):
    from pchsi.evaluation.budget import BudgetLimits
    m, contract, result, policy, env, _, _ = execute(monkeypatch, max_steps=1)
    assert env.actions == ['open cabinet 1']
    assert policy.prompts == []
    assert result['terminal_reason'] == 'ENVIRONMENT_STEP_BUDGET_EXHAUSTED'
    m.validate_branch_evidence(result, contract, arm='F1', budget_limits=BudgetLimits(max_environment_steps=1))


def test_native_protocol_failure_limit_is_preserved(monkeypatch):
    m, contract, result, policy, env, _, _ = execute(monkeypatch, invalid=True)
    assert env.actions == ['open cabinet 1']
    assert len(policy.prompts) == 3
    assert result['final_budget']['protocol_failure_count'] == 3
    assert result['terminal_reason'] == 'CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED'
    m.validate_branch_evidence(result, contract, arm='F1')


@pytest.mark.parametrize('damage', ['missing_trace', 'wrong_budget', 'wrong_action', 'wrong_stop', 'missing_call',
                                   'wrong_role', 'inflated_budget_limit'])
def test_verifier_rejects_incomplete_or_changed_strategy_execution(monkeypatch, damage):
    m, contract, result, *_ = execute(monkeypatch)
    altered = copy.deepcopy(result)
    if damage == 'missing_trace': altered['strategy_execution']['calls'].pop()
    elif damage == 'wrong_budget': altered['final_budget']['environment_step_count'] -= 1
    elif damage == 'wrong_action': altered['environment_transitions_from_source'][1]['action'] = 'look'
    elif damage == 'wrong_stop': altered['terminal_reason'] = 'ENVIRONMENT_STEP_BUDGET_EXHAUSTED'
    elif damage == 'missing_call': altered['policy_calls'].pop()
    elif damage == 'wrong_role': altered['environment_transitions_from_source'][1]['role'] = 'REGISTERED_SHORT_OPTION_INTERVENTION'
    elif damage == 'inflated_budget_limit': altered['strategy_execution']['budget_limits']['max_environment_steps'] = 1000
    with pytest.raises(ValueError): m.validate_branch_evidence(altered, contract, arm='F1')


def test_unknown_contracts_still_delegate_to_existing_dispatch():
    m, plan, _, _ = fixture_contract()
    option = types.SimpleNamespace(compile_option=lambda c: ('legacy', c),
        validate_contract=lambda c: c, decide=lambda c, **k: {'decision': 'STOP', 'reason': 'legacy'})
    branch = types.SimpleNamespace(run_branch_core=lambda **kw: {'legacy': kw['arm']},
        validate_contract=option.validate_contract, decide=option.decide)
    restore = m.install_dispatch(option, branch, None, {plan['strategy_plan_sha256']: plan})
    try:
        assert option.compile_option({'source_proposal_sha256': 'a' * 64})[0] == 'legacy'
        assert branch.run_branch_core(arm='F0', contract={'schema_id': 'legacy'}) == {'legacy': 'F0'}
    finally: restore()


@pytest.mark.parametrize('change', ['model', 'seed'])
def test_verifier_binds_actual_native_wire_to_frozen_runtime(monkeypatch, change):
    m, contract, result, policy, *_ = execute(monkeypatch)
    changed = copy.deepcopy(policy.runtime)
    seed = 17
    if change == 'model': changed['served_model_name'] = 'another-policy'
    else: seed = 18
    with pytest.raises(ValueError):
        m.validate_branch_evidence(result, contract, arm='F1', native_runtime=changed, expected_seed=seed)

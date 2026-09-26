"""Registered public phase programs around the native paired branch loop.

The plan supplies public guidance, not a new model, action parser or budget.
Its initial action and finite public rules precede the same frozen policy with
full-plan guidance until the native terminal. Rules use current public menus;
prose is never executed as code or interpreted as a hidden-state predicate.
"""
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
import re

PLAN_SCHEMA = 'GUARDED_STRATEGY_PLAN_V1'
SCHEMA = 'GUARDED_STRATEGY_CONTRACT_V1'
COMPILER = 'PUBLIC_PHASE_RULES_THEN_FROZEN_POLICY_FULL_PLAN_CUE_V1'
SCOPE = 'COMPLETE_REGISTERED_GUARDED_STRATEGY_INTERVENTION'
TEXT_FIELDS = ('principal_bottleneck', 'current_subgoal', 'expected_next_event',
               'expected_state_change', 'progress_criterion', 'recovery_trigger',
               'fallback_condition', 'action')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _text_sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _domain(domain, value):
    return hashlib.sha256(domain.encode() + b'\0' + canonical(value)).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def build_plan(*, experiment_id, source_state_sha256, menu_sha256, goal, strategy,
               original_candidate_sha256, original_proposal_sha256, source_observation_sha256,program=None):
    plan = dict(schema_id=PLAN_SCHEMA, schema_version=1, experiment_id=experiment_id,
        source_state_sha256=source_state_sha256, menu_sha256=menu_sha256,
        source_observation_sha256=source_observation_sha256, goal=goal, strategy=deepcopy(strategy),
        original_candidate_sha256=original_candidate_sha256, original_proposal_sha256=original_proposal_sha256,
        program=deepcopy(program if program is not None else []))
    plan['strategy_plan_sha256'] = _domain(PLAN_SCHEMA, plan)
    return validate_plan(plan)


def validate_plan(plan):
    fields = {'schema_id', 'schema_version', 'experiment_id', 'source_state_sha256', 'menu_sha256',
              'source_observation_sha256', 'goal', 'strategy', 'original_candidate_sha256',
              'original_proposal_sha256', 'strategy_plan_sha256','program'}
    _require(isinstance(plan, dict) and set(plan) == fields, 'STRATEGY_PLAN_FIELDS')
    _require(plan['schema_id'] == PLAN_SCHEMA and type(plan['schema_version']) is int and plan['schema_version'] == 1,
             'STRATEGY_PLAN_SCHEMA')
    for field in ('source_state_sha256', 'menu_sha256', 'source_observation_sha256',
                  'original_candidate_sha256', 'original_proposal_sha256', 'strategy_plan_sha256'):
        _require(_sha(plan[field]), 'STRATEGY_PLAN_SHA:' + field)
    for field in ('experiment_id', 'goal'):
        _require(isinstance(plan[field], str) and bool(plan[field].strip()) and len(plan[field]) <= 8192,
                 'STRATEGY_PLAN_TEXT:' + field)
    _require(isinstance(plan['strategy'], dict) and set(plan['strategy']) == set(TEXT_FIELDS), 'STRATEGY_FIELDS')
    for field, value in plan['strategy'].items():
        _require(isinstance(value, str) and bool(value.strip()) and len(value) <= 8192 and '\0' not in value,
                 'STRATEGY_TEXT:' + field)
    action = plan['strategy']['action']
    from guarded_strategy import validate_program
    validate_program(plan['program'])
    _require(action == action.strip() and '\n' not in action and '\r' not in action, 'STRATEGY_INITIAL_ACTION')
    _require(plan['strategy_plan_sha256'] == _domain(PLAN_SCHEMA,
             {k: v for k, v in plan.items() if k != 'strategy_plan_sha256'}), 'STRATEGY_PLAN_HASH')
    return deepcopy(plan)


def bind_contract(candidate, plan):
    plan = validate_plan(plan)
    from pchsi.research_intelligence.human_f0f1_runtime import validate_candidate_content_hash_v1
    validate_candidate_content_hash_v1(candidate, expected_candidate_sha256=candidate['candidate_sha256'])
    _require(candidate['candidate_status'] == 'EXECUTABLE_EXACT_ACTION' and
             candidate['option_actions'] == [] and candidate['termination_condition'] is None,
             'STRATEGY_EXACT_ENVELOPE_REQUIRED')
    _require(candidate['exact_action'] == plan['strategy']['action'] and
             candidate['source_proposal_sha256'] == plan['strategy_plan_sha256'] and
             candidate['source_state_sha256'] == plan['source_state_sha256'] and
             candidate['menu_sha256'] == plan['menu_sha256'], 'STRATEGY_CANDIDATE_BINDING')
    for field in ('live_menu_revalidation_required', 'all_intervention_actions_count_against_environment_budget',
                  'requires_environment_verification'):
        _require(candidate[field] is True, 'STRATEGY_NATIVE_INVARIANT:' + field)
    contract = dict(schema_id=SCHEMA, schema_version=1, compiler_id=COMPILER, plan=plan,
        source_state_sha256=candidate['source_state_sha256'], source_candidate_sha256=candidate['candidate_sha256'],
        complete_registered_candidate=deepcopy(candidate), dispatch_mode='GUARDED_PHASES_THEN_CUE_GUIDED_POLICY',
        option_actions=[candidate['exact_action']], max_intervention_steps=1+sum(r['max_uses'] for p in plan['program'] for r in p['rules']),
        causal_verification_scope=SCOPE, standalone_action_causal_effect_claimed=False,
        full_plan_cue_on_every_f1_policy_call=True, native_budget_limits_unchanged=True,
        frozen_policy_unchanged=True, extra_external_model_calls_allowed=False,
        cue_active_until_native_episode_or_budget_terminal=True)
    contract['execution_identity_sha256'] = _domain('CUE_GUIDED_EXECUTION_IDENTITY_V1', contract)
    contract['contract_sha256'] = _domain(SCHEMA, contract)
    return contract


def execution_identity(candidate, plan):
    return bind_contract(candidate, plan)['execution_identity_sha256']


def validate_contract(contract):
    _require(isinstance(contract, dict) and contract.get('schema_id') == SCHEMA, 'STRATEGY_CONTRACT_SCHEMA')
    expected = bind_contract(contract['complete_registered_candidate'], contract['plan'])
    _require(contract == expected, 'STRATEGY_CONTRACT_IDENTITY')
    return deepcopy(expected)


def decide(contract, *, executed_actions, observation, menu, environment_done):
    contract = validate_contract(contract)
    actions = contract['option_actions']; executed = list(executed_actions)
    _require(type(environment_done) is bool and executed == actions[:len(executed)] and len(executed) <= 1,
             'STRATEGY_INITIAL_ACTION_PREFIX')
    if environment_done:
        return {'decision': 'STOP', 'reason': 'ENVIRONMENT_DONE'}
    if executed:
        return {'decision': 'STOP', 'reason': 'REGISTERED_INITIAL_ACTION_COMPLETE_CUE_CONTINUES'}
    if actions[0] not in menu:
        return {'decision': 'STOP', 'reason': 'NEXT_REGISTERED_ACTION_NOT_ADMISSIBLE'}
    return {'decision': 'EXECUTE', 'action': actions[0], 'registered_action_index': 0}


def render_cued_prompt(base_prompt, plan):
    plan = validate_plan(plan)
    _require(isinstance(base_prompt, str) and bool(base_prompt), 'STRATEGY_BASE_PROMPT')
    cue = {'goal': plan['goal'], 'strategy_plan_sha256': plan['strategy_plan_sha256'], **plan['strategy']}
    return (base_prompt + '\n\n<CUE_GUIDED_STRATEGY_V1>\n' + canonical(cue).decode() +
        '\nUse this complete plan as guidance for the current state. The initial action has already been attempted. '
        'Read the current observation, executed history and admissible menu on every step. '
        'Apply recovery and fallback guidance when relevant; choose only a currently admissible action. '
        'Keep the original response format.\n</CUE_GUIDED_STRATEGY_V1>')


def _decision_record(decision):
    return {'budget_before': asdict(decision.budget_before), 'budget_after': asdict(decision.budget_after),
            'attempt_outcome': decision.attempt_outcome.value,
            'should_call_env': decision.should_call_env, 'action': decision.candidate_environment_action,
            'termination_reason': None if decision.termination_reason is None else decision.termination_reason.value,
            'feedback_code': None if decision.feedback_code is None else decision.feedback_code.value}


class _CuedMemory:
    def __init__(self, native, plan, calls):
        self.native, self.plan, self.calls = native, plan, calls
        self.prepares = 0
        self.base_by_prepared = {}

    def prepare(self, **kwargs):
        prepared = self.native.prepare(**kwargs)
        self.prepares += 1
        # The native loop first prepares only to prove source eligibility. Its
        # policy loop prepares again after the exact intervention.
        if self.prepares > 1 and prepared.precondition.should_call_policy:
            base = prepared.prompt_text
            prepared = replace(prepared, prompt_text=render_cued_prompt(base, self.plan))
            self.base_by_prepared[id(prepared)] = base
        return prepared

    def process(self, **kwargs):
        decision = self.native.process(**kwargs)
        _require(bool(self.calls) and 'decision' not in self.calls[-1], 'STRATEGY_POLICY_PROCESS_ORDER')
        self.calls[-1]['decision'] = _decision_record(decision)
        return decision


class _CuedPolicy:
    def __init__(self, native, memory, calls):
        self.native, self.memory, self.calls = native, memory, calls

    def act(self, **kwargs):
        prepared = kwargs['prepared']
        base = self.memory.base_by_prepared.pop(id(prepared), None)
        _require(base is not None, 'STRATEGY_CUE_PREPARATION_MISSING')
        generated, evidence = self.native.act(**kwargs)
        _require(evidence.get('prompt_text') == prepared.prompt_text and
                 evidence.get('raw_response_text') == generated, 'STRATEGY_ACTUAL_POLICY_EVIDENCE_MISMATCH')
        self.calls.append({'model_call_index': kwargs['model_call_index'], 'base_prompt_text': base,
                           'base_prompt_sha256': _text_sha(base), 'prompt_sha256': _text_sha(prepared.prompt_text),
                           'policy_call_sha256': digest(evidence)})
        return generated, evidence


def _run_strategy(native, kwargs):
    from pchsi.evaluation.action_trace import sha256_string_sequence
    contract = validate_contract(kwargs['contract']); plan = contract['plan']; arm = kwargs['arm']
    _require(arm in ('F0', 'F1'), 'STRATEGY_BRANCH_ARM')
    _require(kwargs['goal'] == plan['goal'] and _text_sha(kwargs['observation']) == plan['source_observation_sha256']
             and sha256_string_sequence(kwargs['commands']) == plan['menu_sha256'] and
             plan['strategy']['action'] in kwargs['commands'], 'STRATEGY_REPLAY_SOURCE_CONTEXT')
    record = {'schema_id': 'CUE_GUIDED_BRANCH_EXECUTION_V1', 'contract': contract, 'arm': arm,
        'causal_verification_scope': SCOPE, 'standalone_action_causal_effect_claimed': False,
        'source_prompt_sha256': kwargs['source_prompt_sha256'], 'source_call_index': kwargs['source_call_index'],
        'source_observation': kwargs['observation'], 'source_commands': list(kwargs['commands']),
        'source_history': [asdict(x) for x in kwargs['history']], 'source_budget': asdict(kwargs['budget']),
        'budget_limits': asdict(kwargs['limits']), 'calls': []}
    current = dict(kwargs)
    from guarded_strategy import Engine
    import types
    engine=Engine(plan['program'],plan['strategy']['action'])
    if arm=='F1':
        def guarded_decide(contract,**kw):return engine.decide(kw['executed_actions'],kw['observation'],kw['menu'],kw['environment_done'])
        run=types.FunctionType(native.__code__,{**native.__globals__,'decide':guarded_decide},native.__name__,native.__defaults__,native.__closure__)
        run.__kwdefaults__=native.__kwdefaults__
    else:run=native
    if arm == 'F1':
        memory = _CuedMemory(kwargs['memory_adapter'], plan, record['calls'])
        current['memory_adapter'] = memory
        current['policy'] = _CuedPolicy(kwargs['policy'], memory, record['calls'])
    result = run(**current)
    record['guarded_trace']=engine.trace if arm=='F1' else []
    result['strategy_execution'] = record
    validate_branch_evidence(result, contract, arm=arm, budget_limits=kwargs['limits'],
                            native_runtime=getattr(kwargs['policy'], 'runtime', None), expected_seed=kwargs['seed'])
    return result


def validate_branch_evidence(result, contract, *, arm, budget_limits=None, native_runtime=None, expected_seed=None):
    """Replay every recorded policy response through the native parser/budget.

    File hashes, paired branch identity and passing source replay remain the
    caller's existing verifier duties. This supplements those checks with full
    cue, public-state, action, budget and terminal consistency.
    """
    from pchsi.evaluation.action_trace import sha256_string_sequence
    from pchsi.evaluation.budget import BudgetState, BudgetLimits
    from pchsi.evaluation.policy_call_evidence import PolicyCallEvidenceV1
    from pchsi.evaluation.runtime_core import (validate_runtime_preconditions, process_completed_generation,
                                              finalize_environment_result)
    from pchsi.research_intelligence.human_f0f1_runtime import reserve_registered_repair_environment_step_v1
    contract = validate_contract(contract); plan = contract['plan']; record = result.get('strategy_execution', {})
    if native_runtime is not None:
        _require(type(expected_seed) is int, 'STRATEGY_FROZEN_SEED_REQUIRED')
    _require(arm in ('F0', 'F1') and record.get('schema_id') == 'CUE_GUIDED_BRANCH_EXECUTION_V1' and
             record.get('contract') == contract and record.get('arm') == arm and
             record.get('causal_verification_scope') == SCOPE and
             record.get('standalone_action_causal_effect_claimed') is False, 'STRATEGY_BRANCH_CONTRACT')
    calls = result['policy_calls']; traces = record['calls']; steps = result['environment_transitions_from_source']
    intervention = result['intervention_sequence']
    _require(len(calls) == result['policy_call_count_from_source'] and len(steps) == result['environment_step_count_from_source']
             and len(intervention) == result['option_environment_step_count'], 'STRATEGY_POPULATION')
    _require(len(traces) == (len(calls) if arm == 'F1' else 0), 'STRATEGY_CUE_CALL_POPULATION')
    _require((1<=len(intervention)<=contract['max_intervention_steps']) if arm=='F1' else len(intervention)==0, 'STRATEGY_INITIAL_ACTION_POPULATION')
    budget = BudgetState(**record['source_budget']); limits = budget_limits or BudgetLimits()
    _require(record['budget_limits'] == asdict(limits), 'STRATEGY_NATIVE_BUDGET_LIMITS')
    observation = record['source_observation']; menu = record['source_commands']; history = deepcopy(record['source_history'])
    _require(_text_sha(observation) == plan['source_observation_sha256'] and
             sha256_string_sequence(menu) == plan['menu_sha256'], 'STRATEGY_SOURCE_CONTEXT')
    offset = 0; terminal = None; success = False; feedback = None

    def consume(step, action, before, after, index=None):
        nonlocal observation, menu, history, terminal, success
        _require(step['action'] == action and step['pre_observation'] == observation and step['pre_menu'] == menu and
                 step['pre_observation_sha256'] == _text_sha(observation) and
                 step['pre_menu_sequence_sha256'] == sha256_string_sequence(menu) and
                 step['budget_before'] == asdict(before) and step['budget_after'] == asdict(after), 'STRATEGY_TRANSITION')
        if index is not None:
            _require(step.get('model_call_index') == index and step.get('role') == 'FROZEN_POLICY_CONTINUATION',
                     'STRATEGY_ACTION_CALL_INDEX')
        else:
            _require(step.get('role') == 'REGISTERED_SHORT_OPTION_INTERVENTION', 'STRATEGY_INTERVENTION_ROLE')
        observation = step['resulting_observation']; menu = step['resulting_menu']
        _require(step['resulting_observation_sha256'] == _text_sha(observation) and
                 step['resulting_menu_sequence_sha256'] == sha256_string_sequence(menu) and
                 type(step['done']) is bool and type(step['won']) is bool, 'STRATEGY_RESULTING_STATE')
        history.append({'action': action, 'resulting_observation': observation})
        if step['done']:
            terminal, success = 'ENVIRONMENT_TERMINATED', step['won']

    if arm == 'F1':
        from guarded_strategy import Engine
        engine=Engine(plan['program'],plan['strategy']['action']);executed=[]
        for i,step in enumerate(intervention):
            _require(terminal is None and i<len(steps) and steps[i]==step and step.get('registered_action_index')==i,'STRATEGY_INITIAL_ACTION_TRACE')
            decision=engine.decide(executed,observation,menu,False)
            _require(decision['decision']=='EXECUTE' and decision['action']==step['action'] and step['action'] in menu,'GUARDED_ACTION_REPLAY')
            after=reserve_registered_repair_environment_step_v1(budget,limits)
            consume(step,decision['action'],budget,after);budget=after;offset+=1;executed.append(step['action'])
        if terminal=='ENVIRONMENT_TERMINATED':
            expected_stop='ENVIRONMENT_DONE'
        else:
            decision=engine.decide(executed,observation,menu,False)
            if decision['decision']=='STOP':expected_stop=decision['reason']
            else:
                _require(budget.environment_step_count>=limits.max_environment_steps,'GUARDED_PREMATURE_RETURN')
                expected_stop='ENVIRONMENT_STEP_BUDGET_EXHAUSTED';terminal=expected_stop
        _require(record.get('guarded_trace')==engine.trace,'GUARDED_TRACE_REPLAY')

    for position, call in enumerate(calls):
        _require(terminal is None, 'STRATEGY_CALL_AFTER_TERMINAL')
        evidence = PolicyCallEvidenceV1.from_dict(call['policy_call'])
        data = evidence.to_dict(); index = record['source_call_index'] + position
        _require(call['model_call_index'] == index == evidence.model_call_index and
                 data['public_task_goal'] == plan['goal'] and data['observation'] == observation and
                 data['admissible_commands'] == menu and data['executed_history'] == history and
                 data['budget_before'] == asdict(budget), 'STRATEGY_POLICY_LIVE_CONTEXT')
        if position > 0 or arm == 'F1':
            _require(data['interface_feedback_before'] == feedback, 'STRATEGY_POLICY_FEEDBACK')
        wire = json.loads(evidence.request_wire_bytes)
        _require(wire.get('messages') == [{'role': 'user', 'content': data['prompt_text']}], 'STRATEGY_POLICY_WIRE_PROMPT')
        if native_runtime is not None:
            from pchsi.research_intelligence.human_f0f1_runtime import validate_continuation_wire_v1
            validate_continuation_wire_v1(runtime=native_runtime, raw=evidence.request_wire_bytes,
                expected_prompt=evidence.prompt_text, expected_seed=expected_seed,
                expected_request_id=evidence.client_request_id)
        if arm == 'F1':
            trace = traces[position]
            _require(trace['model_call_index'] == index and trace['base_prompt_sha256'] == _text_sha(trace['base_prompt_text'])
                     and data['prompt_text'] == render_cued_prompt(trace['base_prompt_text'], plan)
                     and trace['prompt_sha256'] == data['prompt_sha256'] and
                     trace['policy_call_sha256'] == digest(data), 'STRATEGY_CUE_WIRE_IDENTITY')
        elif position == 0:
            _require(data['prompt_sha256'] == record['source_prompt_sha256'], 'STRATEGY_F0_SOURCE_PROMPT')
        pre = validate_runtime_preconditions(policy_visible_commands=menu, harness_visible_commands=menu,
            environment_commands=menu, budget_state=budget, budget_limits=limits)
        _require(pre.should_call_policy, 'STRATEGY_POLICY_NATIVE_PRECONDITION')
        decision = process_completed_generation(raw_response=data['raw_response_text'], visible_admissible_commands=menu,
            precondition_result=pre, budget_limits=limits)
        if arm == 'F1':
            _require(traces[position].get('decision') == _decision_record(decision), 'STRATEGY_NATIVE_DECISION')
        before = budget; budget = decision.budget_after
        if decision.should_call_env:
            _require(offset < len(steps), 'STRATEGY_ACTION_TRACE_MISSING')
            step = steps[offset]; offset += 1
            final = finalize_environment_result(decision, environment_terminated=step['done'], infrastructure_error=False)
            consume(step, decision.candidate_environment_action, before, final.budget_after, index)
            budget = final.budget_after; feedback = None
            if terminal is None and final.termination_reason is not None:
                terminal = final.termination_reason.value
        else:
            feedback = None if decision.feedback_code is None else decision.feedback_code.value
            if decision.termination_reason is not None:
                terminal = decision.termination_reason.value
    _require(offset == len(steps), 'STRATEGY_UNBOUND_ENVIRONMENT_ACTION')
    if terminal is None:
        pre = validate_runtime_preconditions(policy_visible_commands=menu, harness_visible_commands=menu,
            environment_commands=menu, budget_state=budget, budget_limits=limits)
        _require(not pre.should_call_policy and pre.termination_reason is not None, 'STRATEGY_INCOMPLETE_CONTINUATION')
        terminal = pre.termination_reason.value
    _require(result['final_budget'] == asdict(budget) and result['terminal_reason'] == terminal and
             type(result['terminal_success']) is bool and result['terminal_success'] == success and
             result['evidence_complete'] is True and result['scientific_outcome_produced'] is True and
             result['automatic_retry_count'] == 0, 'STRATEGY_TERMINAL_OR_BUDGET')
    if arm == 'F1':
        _require(result['typed_option_stop_reason'] == expected_stop, 'STRATEGY_INITIAL_STOP_REASON')
    return True


def install_dispatch(option, native_branch, round_plan, plans):
    """Install on the registered modules in both controller and GPU processes.

    `plans` is a mapping keyed by strategy_plan_sha256. The returned callable
    restores original functions, useful for bounded in-process invocations.
    """
    registry = {key: validate_plan(value) for key, value in plans.items()}
    _require(all(key == value['strategy_plan_sha256'] for key, value in registry.items()), 'STRATEGY_REGISTRY_KEY')
    previous = [(option, name, getattr(option, name)) for name in ('compile_option', 'validate_contract', 'decide')]
    previous += [(native_branch, name, getattr(native_branch, name)) for name in ('run_branch_core', 'validate_contract', 'decide')]
    if round_plan is not None:
        previous.append((round_plan, 'compile_option', round_plan.compile_option))
    old_compile, old_validate, old_decide = option.compile_option, option.validate_contract, option.decide
    old_run = native_branch.run_branch_core

    def compile_option(candidate):
        plan = registry.get(candidate.get('source_proposal_sha256'))
        if plan is None:
            return old_compile(candidate)
        return {'status': 'COMPILED', 'reason': None, 'contract': bind_contract(candidate, plan)}

    option.compile_option = compile_option
    option.validate_contract = lambda c: validate_contract(c) if c.get('schema_id') == SCHEMA else old_validate(c)
    option.decide = lambda c, **kw: decide(c, **kw) if c.get('schema_id') == SCHEMA else old_decide(c, **kw)
    native_branch.validate_contract, native_branch.decide = option.validate_contract, option.decide
    native_branch.run_branch_core = lambda **kw: _run_strategy(old_run, kw) if kw['contract'].get('schema_id') == SCHEMA else old_run(**kw)
    if round_plan is not None:
        round_plan.compile_option = compile_option

    def restore():
        for module, name, value in reversed(previous):
            setattr(module, name, value)
    return restore

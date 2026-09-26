"""Current-round adapter for the existing native replay / policy / Memory APIs.

Derived from the captured typed-short-option branch runner. Environment execution,
policy serialization, parsing, budgets, retrieval and evidence construction remain
owned by the unchanged native modules. This file only connects their interfaces.
"""
from __future__ import annotations
import fcntl
import os
import sys
from pathlib import Path
from typing import Any, Callable
from io_utils import canonical, sha, read_json, put_json, digest_file
from option_adapter import validate_contract, decide

ROOT = Path(__file__).resolve().parent
NATIVE = ROOT / 'native_repo'
if str(NATIVE/'src') not in sys.path:
    sys.path.insert(0, str(NATIVE/'src'))


def budget_dict(state):
    return {key: getattr(state, key) for key in (
        'policy_attempt_count', 'environment_step_count', 'protocol_failure_count',
        'inadmissible_action_count', 'consecutive_nonexecuted_attempt_count')}


def _feedback(value):
    from pchsi.evaluation.raw_policy_prompt import InterfaceFeedbackCode
    return None if value is None else InterfaceFeedbackCode(value)


def _menu_sha(commands):
    from pchsi.evaluation.action_trace import sha256_string_sequence
    return sha256_string_sequence(tuple(commands))



def _assert_source_replay_pass(report):
    # SOURCE_STATE_REPLAY_REPORT_V1 exposes status/failure_code and the two
    # content-addressed fingerprints. It does not expose `exact_match`.
    if getattr(report, 'status', None) != 'PASS':
        raise ValueError('source replay did not pass')
    if getattr(report, 'failure_code', None) is not None:
        raise ValueError('source replay failure code is non-null')
    source_sha = getattr(report, 'source_fingerprint_sha256', None)
    replay_sha = getattr(report, 'replay_fingerprint_sha256', None)
    if source_sha is None or replay_sha is None or source_sha != replay_sha:
        raise ValueError('source replay fingerprint mismatch')

def run_branch_core(*, arm: str, source_prompt_sha256: str, goal: str,
                    observation: str, commands: tuple[str, ...], history: tuple,
                    budget: Any, feedback: Any, source_call_index: int,
                    seed: int, memory_adapter: Any, policy: Any, environment: Any,
                    contract: dict, limits: Any,
                    event_sink: Callable[[dict], None] = lambda event: None) -> dict:
    """Run a verified source continuation; dependencies are injectable for tests."""
    from pchsi.evaluation.raw_policy_prompt import ExecutedTransition
    from pchsi.evaluation.runtime_core import finalize_environment_result
    from pchsi.research_intelligence.human_f0f1_runtime import reserve_registered_repair_environment_step_v1
    if arm not in ('F0', 'F1'):
        raise ValueError('unknown branch arm')
    validate_contract(contract)
    transitions, calls, intervention = [], [], []
    idx = source_call_index
    outcome = None
    stop_reason = None
    option_stop = None

    def prepare():
        return memory_adapter.prepare(
            public_task_goal=goal, observation=observation,
            executed_transitions=history, policy_visible_commands=commands,
            harness_visible_commands=commands, environment_commands=commands,
            interface_feedback=feedback, budget_state=budget, budget_limits=limits)

    initial = prepare()
    if not initial.precondition.should_call_policy:
        raise ValueError('registered source no longer permits a policy attempt')
    # F0 actually asks the policy at the frozen source state, so source-prompt
    # parity is part of the same-state comparator. F1 intervenes *before* its
    # first policy call; requiring the counterfactual branch to reproduce the
    # parent source prompt would incorrectly bind it to a prompt that is never
    # sent. If F1 performs zero intervention steps and falls back to a source-
    # state policy call, parity is checked at that actual call below.
    if arm == 'F0' and sha(initial.prompt_text.encode()) != source_prompt_sha256:
        raise ValueError('current Memory adapter does not reproduce exact source prompt')

    def step(action, role, before, **extra):
        event_sink({'type': 'ENVIRONMENT_ACTION_INTENT', 'role': role,
                    'action': action, 'budget_before': budget_dict(before), **extra})
        state = environment.step(action)
        row = {
            'role': role, 'action': action,
            'pre_observation': observation, 'pre_menu': list(commands),
            'pre_observation_sha256': sha(observation.encode()),
            'pre_menu_sequence_sha256': _menu_sha(commands),
            'resulting_observation': state.observation,
            'resulting_menu': list(state.menu.commands),
            'resulting_observation_sha256': sha(state.observation.encode()),
            'resulting_menu_sequence_sha256': state.menu.sequence_sha256,
            'score': state.score, 'done': state.done, 'won': state.won,
            'budget_before': budget_dict(before), **extra,
        }
        event_sink({'type': 'ENVIRONMENT_ACTION_RESULT', **row})
        return state, row

    if arm == 'F1':
        executed = []
        while outcome is None:
            decision = decide(contract, executed_actions=executed,
                              observation=observation, menu=commands,
                              environment_done=False)
            if decision['decision'] == 'STOP':
                option_stop = decision['reason']
                break
            # A spent budget is a scientific terminal, not an infrastructure error.
            if budget.environment_step_count >= limits.max_environment_steps:
                outcome = False
                stop_reason = 'ENVIRONMENT_STEP_BUDGET_EXHAUSTED'
                option_stop = stop_reason
                break
            action = decision['action']
            before = budget
            budget = reserve_registered_repair_environment_step_v1(budget, limits)
            state, row = step(action, 'REGISTERED_SHORT_OPTION_INTERVENTION', before,
                              registered_action_index=decision['registered_action_index'])
            row['budget_after'] = budget_dict(budget)
            intervention.append(row)
            transitions.append(row)
            executed.append(action)
            history = (*history, ExecutedTransition(action, state.observation))
            observation, commands, feedback = state.observation, tuple(state.menu.commands), None
            if state.done:
                outcome, stop_reason, option_stop = bool(state.won), 'ENVIRONMENT_TERMINATED', 'ENVIRONMENT_DONE'

    while outcome is None:
        prepared = prepare()
        if (arm == 'F1' and not intervention and idx == source_call_index
                and sha(prepared.prompt_text.encode()) != source_prompt_sha256):
            raise ValueError('zero-intervention F1 source prompt differs from frozen source prompt')
        if not prepared.precondition.should_call_policy:
            reason = prepared.precondition.termination_reason
            outcome, stop_reason = False, None if reason is None else reason.value
            break
        before = budget
        event_sink({'type': 'POLICY_CALL_INTENT', 'model_call_index': idx,
                    'seed': seed, 'prompt_sha256': sha(prepared.prompt_text.encode())})
        generated, evidence = policy.act(
            prepared=prepared, seed=seed, model_call_index=idx,
            goal=goal, observation=observation, commands=commands,
            history=history, budget=budget, feedback=feedback)
        exposure = getattr(prepared.adapter_state, 'exposure', None)
        call = {'model_call_index': idx, 'policy_call': evidence,
                'memory_exposure': None if exposure is None else exposure.to_dict()}
        calls.append(call)
        event_sink({'type': 'POLICY_CALL_RESULT', **call})
        decision = memory_adapter.process(
            raw_response=generated, visible_admissible_commands=commands,
            prepared=prepared, budget_limits=limits)
        budget = decision.budget_after
        idx += 1
        if not decision.should_call_env:
            feedback = decision.feedback_code
            if decision.termination_reason is not None:
                outcome, stop_reason = False, decision.termination_reason.value
            continue
        action = decision.candidate_environment_action
        if action is None:
            raise ValueError('native runtime authorized environment without action')
        state, row = step(action, 'FROZEN_POLICY_CONTINUATION', before,
                          model_call_index=idx - 1)
        decision = finalize_environment_result(
            decision, environment_terminated=state.done, infrastructure_error=False)
        budget = decision.budget_after
        row['budget_after'] = budget_dict(budget)
        transitions.append(row)
        history = (*history, ExecutedTransition(action, state.observation))
        observation, commands, feedback = state.observation, tuple(state.menu.commands), None
        if state.done:
            outcome, stop_reason = bool(state.won), 'ENVIRONMENT_TERMINATED'
        elif decision.termination_reason is not None:
            outcome, stop_reason = False, decision.termination_reason.value
    return {
        'evidence_complete': True, 'scientific_outcome_produced': True,
        'terminal_success': outcome, 'terminal_reason': stop_reason,
        'final_budget': budget_dict(budget), 'intervention_sequence': intervention,
        'typed_option_stop_reason': option_stop,
        'policy_calls': calls, 'environment_transitions_from_source': transitions,
        'option_environment_step_count': len(intervention),
        'policy_call_count_from_source': len(calls),
        'environment_step_count_from_source': len(transitions), 'automatic_retry_count': 0,
    }


class NativePolicy:
    def __init__(self, *, runtime, renderer, binding, service_lease=None):
        from pchsi.evaluation.policy_client import HttpPolicyTransport, PolicyClient
        self.runtime, self.renderer, self.binding = runtime, renderer, binding
        self.operational_attempt_id = None if service_lease is None else service_lease.get('operational_attempt_id')
        self.client = PolicyClient(transport=HttpPolicyTransport(
            base_url=runtime['policy_base_url'] if service_lease is None else service_lease['policy_base_url'],
            timeout_seconds=float(binding['policy_timeout_seconds'])))

    def act(self, *, prepared, seed, model_call_index, goal, observation,
            commands, history, budget, feedback):
        from pchsi.evaluation.policy_call_evidence import build_policy_call_evidence
        from pchsi.research_intelligence.human_f0f1_runtime import (
            build_bound_continuation_request_v1, validate_continuation_wire_v1)
        rendered = self.renderer.render(prompt_text=prepared.prompt_text)
        attempt_ns = str(getattr(self, 'operational_attempt_id', None) or '')
        suffix = ('-' + attempt_ns[:12]) if attempt_ns else ''
        rid = self.binding['branch_key_sha256'] + suffix + '-c' + str(model_call_index)
        request = build_bound_continuation_request_v1(
            runtime=self.runtime, prompt_text=prepared.prompt_text,
            seed=seed, request_id=rid)
        if rendered.prompt_token_count + request.to_wire_dict()['max_tokens'] > self.runtime['context_window_tokens']:
            raise ValueError('continuation prompt exceeds frozen context window')
        validate_continuation_wire_v1(
            runtime=self.runtime, raw=request.to_wire_bytes(),
            expected_prompt=prepared.prompt_text, expected_seed=seed, expected_request_id=rid)
        result = self.client.generate_with_evidence(request=request, expected_prompt=rendered)
        evidence = build_policy_call_evidence(
            model_call_index=model_call_index, public_task_goal=goal,
            observation=observation, admissible_commands=commands,
            executed_history=history, interface_feedback_before=feedback,
            budget_before=budget, request=request, expected_prompt=rendered,
            generation=result.generation, transport_evidence=result.transport_evidence)
        return result.generation.raw_response_text, evidence.to_dict()


def execute_native_branch(binding: dict, output_dir: Path, *, service_lease=None) -> dict:
    """Single-writer, write-ahead branch execution with immutable resume semantics."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir/'WRITER.lock').open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _execute_locked(binding, output_dir, service_lease=service_lease)


def _execute_locked(binding: dict, output_dir: Path, *, service_lease=None) -> dict:
    expected_binding_sha = sha(canonical({k:v for k,v in binding.items() if k!='binding_sha256'}))
    if binding.get('binding_sha256') != expected_binding_sha:
        raise ValueError('branch binding hash mismatch')
    result_path, intent_path = output_dir/'BRANCH_TERMINAL.json', output_dir/'BRANCH_INTENT.json'
    if result_path.exists():
        result = read_json(result_path)
        if result.get('binding_sha256') != binding['binding_sha256']:
            raise ValueError('existing branch terminal belongs to another binding')
        if result.get('evidence_sha256') != sha(canonical({k:v for k,v in result.items() if k!='evidence_sha256'})):
            raise ValueError('existing branch terminal identity mismatch')
        return result
    if intent_path.exists():
        raise ValueError('AMBIGUOUS_PARTIAL_BRANCH_NO_REEXECUTION')
    if service_lease is not None:
        if service_lease.get('runtime_file_sha256')!=binding['runtime_file_sha256'] or service_lease.get('served_model_name')!=binding['policy_model']:
            raise ValueError('policy service lease model/runtime mismatch')
        if service_lease.get('lease_sha256')!=sha(canonical({k:v for k,v in service_lease.items() if k!='lease_sha256'})):
            raise ValueError('policy service lease hash mismatch')
    put_json(intent_path, {'schema_id':'NATIVE_BRANCH_INTENT_V1', 'binding_sha256':binding['binding_sha256']})
    from pchsi.evaluation.budget import BudgetLimits
    from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter
    from pchsi.memory.a0_replay_session import replay_source_decision_state_hold_open_v1
    from pchsi.memory.source_state_contracts import RegisteredReplaySourceV1
    from pchsi.evaluation.raw_policy_prompt import ExecutedTransition
    from pchsi.evaluation.rendered_prompt import LocalTokenizerPromptRenderer, HuggingFaceTokenizerFactory
    from pchsi.evaluation.policy_attempt_adapter import RoundMemoryPolicyAttemptAdapterV1
    from pchsi.research_intelligence.human_f0f1_runtime import load_continuation_runtime_binding_v2
    session = None
    events = []
    def event(value):
        put_json(output_dir/'events'/f'{len(events):06d}.json', value)
        events.append(value)
    result = {
        'schema_id':'CURRENT_MEMORY_AWARE_F0F1_BRANCH_EVIDENCE_V1', 'schema_version':1,
        'binding_sha256':binding['binding_sha256'], 'branch_key_sha256':binding['branch_key_sha256'],
        'source_state_sha256':binding['source_state_sha256'],
        'native_source_fingerprint_sha256':binding['native_source_fingerprint_sha256'],
        'source_candidate_sha256':binding['source_candidate_sha256'],
        'arm':binding['arm'], 'continuation_seed':binding['paired_seed'],
        'replicate_index':binding['replicate_index'],
        'evidence_complete':False, 'scientific_outcome_produced':False,
        'automatic_retry_count':0,
    }
    try:
        for field in ('replay_source','runtime','memory_runtime','typed_contract'):
            if digest_file(Path(binding[field+'_path'])) != binding[field+'_file_sha256']:
                raise ValueError(field+' file identity mismatch')
        source = RegisteredReplaySourceV1.from_json(Path(binding['replay_source_path']).read_bytes())
        if source.expected_source_fingerprint.fingerprint_sha256 != binding['native_source_fingerprint_sha256']:
            raise ValueError('native source fingerprint differs from namespace bridge')
        if digest_file(Path(source.exact_gamefile)) != source.source_gamefile_sha256:
            raise ValueError('current exact gamefile hash mismatch')
        runtime = load_continuation_runtime_binding_v2(
            binding['runtime_path'], expected_file_sha256=binding['runtime_file_sha256'],
            expected_model=binding['policy_model'])
        memory = RoundMemoryPolicyAttemptAdapterV1(
            runtime_identity_path=Path(binding['memory_runtime_path']),
            expected_runtime_identity_file_sha256=binding['memory_runtime_file_sha256'])
        if memory.snapshot_sha256 != binding['active_snapshot_sha256']:
            raise ValueError('Memory snapshot differs from frozen current round')
        renderer = LocalTokenizerPromptRenderer(
            model_path=runtime['base_model_local_path'], revision=runtime['tokenizer_revision'],
            chat_template_sha256=runtime['chat_template_sha256'], tokenizer_factory=HuggingFaceTokenizerFactory())
        policy = NativePolicy(runtime=runtime, renderer=renderer, binding=binding, service_lease=service_lease)
        contract = read_json(Path(binding['typed_contract_path']))
        if contract['source_state_sha256'] != binding['source_state_sha256'] or contract['source_candidate_sha256'] != binding['source_candidate_sha256']:
            raise ValueError('typed contract/original candidate namespace mismatch')
        adapter = SpawnedAlfworldAdapter.start(
            exact_gamefile=Path(source.exact_gamefile), registration_id=binding['branch_key_sha256'],
            runtime_manifest_sha256=source.runtime_manifest_sha256)
        session = replay_source_decision_state_hold_open_v1(source=source, adapter=adapter)
        _assert_source_replay_pass(session.report)
        event({'type':'SOURCE_REPLAY_REPORT', 'report':session.report.to_dict()})
        history = tuple(ExecutedTransition(t.action,s.observation) for t,s in zip(source.transitions,session.step_states,strict=True))
        core = run_branch_core(
            arm=binding['arm'], source_prompt_sha256=source.base_policy_input_sha256,
            goal=binding['public_task_goal'], observation=session.current_observation,
            commands=session.current_commands, history=history, budget=source.budget_state,
            feedback=_feedback(source.interface_feedback_code), source_call_index=source.model_call_index,
            seed=binding['paired_seed'], memory_adapter=memory, policy=policy,
            environment=session.adapter, contract=contract, limits=BudgetLimits(), event_sink=event)
        result.update(core)
        result.update(status='SCIENTIFIC_OUTCOME_COMPLETE', source_replay_report=session.report.to_dict())
    except Exception as exc:
        result.update(status='BRANCH_INFRASTRUCTURE_OR_PROTOCOL_INVALID',
                      error_type=type(exc).__name__, error_message=str(exc))
    finally:
        if session is not None:
            try:
                session.close()
            except Exception as exc:
                result['cleanup_error']={'type':type(exc).__name__, 'message':str(exc)}
                result['evidence_complete']=False
                result['scientific_outcome_produced']=False
                result['status']='BRANCH_CLEANUP_INVALID'
    result['service_lease_sha256']=None if service_lease is None else service_lease['lease_sha256']
    result['journal_event_count']=len(events)
    result['evidence_sha256']=sha(canonical(result))
    put_json(result_path,result)
    return result

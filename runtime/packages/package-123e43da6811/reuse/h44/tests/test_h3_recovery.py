from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from io_utils import canonical, put_json, read_json, sha
from recovery import diagnose, materialize_recovery
from native_branch import run_branch_core
from option_adapter import compile_option
from pchsi.evaluation.budget import BudgetLimits, BudgetState
from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.policy_attempt_adapter import RoundMemoryPolicyAttemptAdapterV1


def _hash_record(value, field):
    value[field] = sha(canonical({k: v for k, v in value.items() if k != field}))
    return value


def _make_prior(tmp_path: Path, *, f0_error=('PolicyTransportError','HTTP transport failed'),
                f1_error=('PolicyTransportError','HTTP transport failed'),
                missing_arm=None, scientific_zero_intervention=False):
    root = tmp_path / 'prior'; root.mkdir()
    k0='a'*64; k1='b'*64; state='c'*64; cand='d'*64; fp='e'*64; bindsha0='1'*64;bindsha1='2'*64
    handoff={'branch_plan':[
        {'branch_key_sha256':k0,'source_state_sha256':state,'replicate_index':0,'arm':'F0','paired_seed':17,'f1_candidate_sha256':None},
        {'branch_key_sha256':k1,'source_state_sha256':state,'replicate_index':0,'arm':'F1','paired_seed':17,'f1_candidate_sha256':cand},
    ],'paired_seeds':[17],'paired_repetitions_per_state':1,'stable_direction_min_pairs':4}
    b0={'branch_key_sha256':k0,'binding_sha256':bindsha0,'source_candidate_sha256':cand,'native_source_fingerprint_sha256':fp}
    b1={'branch_key_sha256':k1,'binding_sha256':bindsha1,'source_candidate_sha256':cand,'native_source_fingerprint_sha256':fp}
    plan={'schema_id':'CURRENT_ACCEPTED_PRE_NATIVE_EXECUTION_PLAN_V1','handoff':handoff,
          'states':[{'source_state_sha256':state,'source_candidate_sha256':cand}],
          'branch_bindings':[{'path':'/tmp/f0','file_sha256':'0'*64,'binding':b0},{'path':'/tmp/f1','file_sha256':'0'*64,'binding':b1}],
          'round_id':'R','operations':{},'runtime_path':'/tmp/r','runtime_file_sha256':'0'*64,
          'capture_zip_sha256':'0'*64,'source_request':{},'scope_notice':{},
          'native_environment_execution_performed':False,'max10_released':False}
    plan['plan_sha256']=sha(canonical(plan)); put_json(root/'EXECUTION_PLAN.json',plan)
    for arm,key,binding,error in [('F0',k0,b0,f0_error),('F1',k1,b1,f1_error)]:
        if arm==missing_arm: continue
        bdir=root/'branches'/key; bdir.mkdir(parents=True)
        put_json(bdir/'BRANCH_INTENT.json',{'schema_id':'NATIVE_BRANCH_INTENT_V1','binding_sha256':binding['binding_sha256']})
        if scientific_zero_intervention:
            term={'schema_id':'CURRENT_MEMORY_AWARE_F0F1_BRANCH_EVIDENCE_V1','schema_version':1,
                  'binding_sha256':binding['binding_sha256'],'branch_key_sha256':key,
                  'source_state_sha256':state,'native_source_fingerprint_sha256':fp,'source_candidate_sha256':cand,
                  'arm':arm,'continuation_seed':17,'replicate_index':0,'evidence_complete':True,
                  'scientific_outcome_produced':True,'terminal_success':False,
                  'option_environment_step_count':0 if arm=='F1' else 0,'automatic_retry_count':0}
        else:
            term={'schema_id':'CURRENT_MEMORY_AWARE_F0F1_BRANCH_EVIDENCE_V1','schema_version':1,
                  'binding_sha256':binding['binding_sha256'],'branch_key_sha256':key,
                  'source_state_sha256':state,'native_source_fingerprint_sha256':fp,'source_candidate_sha256':cand,
                  'arm':arm,'continuation_seed':17,'replicate_index':0,'evidence_complete':False,
                  'scientific_outcome_produced':False,'automatic_retry_count':0,
                  'status':'BRANCH_INFRASTRUCTURE_OR_PROTOCOL_INVALID','error_type':error[0],'error_message':error[1]}
        _hash_record(term,'evidence_sha256'); put_json(bdir/'BRANCH_TERMINAL.json',term)
    verifier={'schema_id':'CURRENT_ROUND_INDEPENDENT_VERIFIER_RESULT_V1','plan_sha256':plan['plan_sha256'],
              'round_id':'R','status':'NO_SCIENTIFICALLY_COMPLETE_PAIRS','scientifically_complete_pair_count':0,
              'frozen_pair_count':1,'selected_state_count':1,'planned_branch_count':2,'stable_effect_counts':{},
              'state_results':[],'pair_results':[],'branch_records':[],'diagnostics':[],
              'hypothesis_scope_notice':{},'comparison':'SELECTED_REPAIR_VS_PARENT_CONTINUATION_NOT_A3_VS_A2',
              'automatic_environment_effect_assignment':True,'human_decision_count':0,
              'training_authorized_by_this_verifier':False,'max10_released':False}
    verifier['environment_result_package_sha256']=sha(canonical(verifier));
    (root/'verifier').mkdir();put_json(root/'verifier/ENVIRONMENT_RESULT_PACKAGE.json',verifier)
    term={'schema_id':'CURRENT_CAUSAL_EXECUTION_CONTROLLER_TERMINAL_V1','plan_sha256':plan['plan_sha256'],
          'full_round_closed':False,'next_round_launched':False,'max10_released':False,
          'training_execution_count':0,'human_scientific_decision_count':0,
          'environment_result_package_sha256':verifier['environment_result_package_sha256'],
          'verifier_status':'NO_SCIENTIFICALLY_COMPLETE_PAIRS','status':'NATIVE_INFRA_OR_PROTOCOL_INVALID_NO_SCIENTIFIC_NO_TRAIN'}
    put_json(root/'ROUND_EXECUTION_TERMINAL.json',term)
    put_json(root/'GPU_JOB_TERMINAL.json',{'schema_id':'CURRENT_NATIVE_GPU_JOB_RESULT_V1','plan_sha256':plan['plan_sha256'],'status':'NO_SCIENTIFICALLY_COMPLETE_PAIRS'})
    return root


def test_transient_invalid_pair_is_machine_retryable_and_plan_bytes_are_reused(tmp_path):
    prior=_make_prior(tmp_path)
    census=diagnose(prior)
    assert census['retry_mode']=='ALL_INCOMPLETE_PAIRS_PAIRED_OPERATIONAL_RETRY'
    assert census['automatic_pair_retry_authorized'] is True
    recovery=materialize_recovery(prior,census)
    assert (recovery/'EXECUTION_PLAN.json').read_bytes()==(prior/'EXECUTION_PLAN.json').read_bytes()
    authority=read_json(recovery/'PAIR_RECOVERY_AUTHORITY.json')
    assert authority['pair_level_retry_not_single_arm_retry'] is True
    assert authority['top_up_state_count']==0 and authority['replacement_state_count']==0


def test_missing_branch_terminal_is_ambiguous_and_not_retried(tmp_path):
    prior=_make_prior(tmp_path,missing_arm='F1')
    census=diagnose(prior)
    assert census['automatic_pair_retry_authorized'] is False
    assert any('MISSING_BRANCH_TERMINAL' in reason for reason in census['pair_rows'][0]['reasons'])


def test_f0_source_prompt_equivalence_failure_is_not_blindly_retried(tmp_path):
    prior=_make_prior(tmp_path,f0_error=('ValueError','current Memory adapter does not reproduce exact source prompt'))
    census=diagnose(prior)
    assert census['automatic_pair_retry_authorized'] is False
    assert 'F0_SOURCE_PROMPT_EQUIVALENCE_FAILED' in census['pair_rows'][0]['reasons']


def test_f1_preintervention_source_prompt_mismatch_is_known_package_fix(tmp_path):
    prior=_make_prior(tmp_path,f1_error=('ValueError','current Memory adapter does not reproduce exact source prompt'))
    census=diagnose(prior)
    assert census['automatic_pair_retry_authorized'] is True
    assert 'H3_FIX_F1_PREINTERVENTION_SOURCE_PROMPT_PARITY' in census['pair_rows'][0]['reasons']


def test_scientific_zero_intervention_pair_is_missingness_not_retry(tmp_path):
    prior=_make_prior(tmp_path,scientific_zero_intervention=True)
    census=diagnose(prior)
    assert census['automatic_pair_retry_authorized'] is False
    assert 'SCIENTIFIC_ZERO_INTERVENTION_PROTOCOL_MISSINGNESS' in census['pair_rows'][0]['reasons']


class _Memory(RoundMemoryPolicyAttemptAdapterV1):
    def __init__(self):
        self._runtime={'active_snapshot_sha256':'c'*64,'token_budget_contract_sha256':'d'*64}
    def _payload(self,query): return (), 'M0', None,None,None,0
class _Env:
    def __init__(self): self.actions=[]
    def step(self,action):
        self.actions.append(action)
        cmds=('finish',)
        return SimpleNamespace(observation='You arrive at desk 1.',menu=SimpleNamespace(commands=cmds,sequence_sha256=sha256_string_sequence(cmds)),done=action=='finish',won=action=='finish',score=1 if action=='finish' else 0)
class _Policy:
    def act(self,*,prepared,**kw): return json.dumps({'action':'finish'}), {'prompt':prepared.prompt_text}

def _contract():
    c={'candidate_status':'EXECUTABLE_SHORT_OPTION','source_state_sha256':'a'*64,'candidate_sha256':'b'*64,
       'option_actions':['go to desk 1'],
       'termination_condition':'Stop the search options when the pen becomes visible or carried, when the current admissible menu changes such that the next option is unavailable, or when the episode terminates; after each executed action, re-read the resulting observation and current menu.'}
    return compile_option(c)['contract']


def test_f1_does_not_require_unsent_source_prompt_but_f0_still_does():
    m=_Memory();e=_Env();p=_Policy();budget=BudgetState();limits=BudgetLimits()
    # F1 intervenes before a policy call; the source prompt is never sent.
    out=run_branch_core(arm='F1',source_prompt_sha256='0'*64,goal='x',observation='x',
        commands=('go to desk 1','finish'),history=(),budget=budget,feedback=None,
        source_call_index=0,seed=17,memory_adapter=m,policy=p,environment=e,contract=_contract(),limits=limits)
    assert out['option_environment_step_count']==1
    # F0 really does call at the source state and must preserve the exact source prompt.
    with pytest.raises(ValueError,match='source prompt'):
        run_branch_core(arm='F0',source_prompt_sha256='0'*64,goal='x',observation='x',
            commands=('go to desk 1','finish'),history=(),budget=BudgetState(),feedback=None,
            source_call_index=0,seed=17,memory_adapter=_Memory(),policy=_Policy(),environment=_Env(),contract=_contract(),limits=limits)

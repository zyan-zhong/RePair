import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from io_utils import sha
from option_adapter import compile_option
from pchsi.evaluation.budget import BudgetLimits, BudgetState
from pchsi.evaluation.action_trace import sha256_string_sequence
from pchsi.evaluation.policy_attempt_adapter import RoundMemoryPolicyAttemptAdapterV1
from native_branch import run_branch_core

class Memory(RoundMemoryPolicyAttemptAdapterV1):
    def __init__(self):
        self._runtime={'active_snapshot_sha256':'c'*64,'token_budget_contract_sha256':'d'*64}
        self.prepared=[];self.processed=0
    def _payload(self, query):return (), 'M0', None,None,None,0
    def prepare(self,**kw):
        self.prepared.append((kw['observation'],kw['budget_state'].policy_attempt_count))
        return super().prepare(**kw)
    def process(self,**kw):
        self.processed+=1
        return super().process(**kw)
class Env:
    def __init__(self):self.actions=[]
    def step(self,action):
        self.actions.append(action)
        obs='You arrive at the desk. On the desk, you see a pencil 2.'
        cmds=('finish',)
        return SimpleNamespace(observation=obs,menu=SimpleNamespace(commands=cmds,sequence_sha256=sha256_string_sequence(cmds)),done=action=='finish',won=action=='finish',score=1 if action=='finish' else 0)
class Policy:
    def __init__(self):self.seeds=[]
    def act(self,*,prepared,seed,**kw):
        self.seeds.append(seed)
        return json.dumps({'action':'finish'}), {'prompt':prepared.prompt_text,'source_context':kw['observation']}
def contract():
    candidate={'candidate_status':'EXECUTABLE_SHORT_OPTION','source_state_sha256':'a'*64,'candidate_sha256':'b'*64,
      'option_actions':['go to desk 1'],
      'termination_condition':'Stop the search options when the pen becomes visible or carried, when the current admissible menu changes such that the next option is unavailable, or when the episode terminates; after each executed action, re-read the resulting observation and current menu.'}
    return compile_option(candidate)['contract']
def execute(arm):
    m,p,e=Memory(),Policy(),Env();events=[]
    budget=BudgetState(2,1,0,1,1);limits=BudgetLimits()
    args=dict(public_task_goal='find an object',observation='You see a shelf 1.',executed_transitions=(),
      policy_visible_commands=('go to desk 1','finish'),harness_visible_commands=('go to desk 1','finish'),
      environment_commands=('go to desk 1','finish'),interface_feedback=None,budget_state=budget,budget_limits=limits)
    source=m.prepare(**args)
    r=run_branch_core(arm=arm,source_prompt_sha256=sha(source.prompt_text.encode()),goal=args['public_task_goal'],
      observation=args['observation'],commands=args['policy_visible_commands'],history=(),budget=budget,feedback=None,
      source_call_index=2,seed=19,memory_adapter=m,policy=p,environment=e,contract=contract(),limits=limits,event_sink=events.append)
    return r,m,p,e,events

def test_f1_uses_native_memory_prepare_process_after_option():
    r,m,p,e,events=execute('F1')
    assert r['terminal_success'] is True and m.processed==1
    assert e.actions==['go to desk 1','finish'] and p.seeds==[19]
    assert r['final_budget']['policy_attempt_count']==3
    assert r['final_budget']['environment_step_count']==3
    assert r['policy_calls'][0]['memory_exposure'] is not None

def test_f0_never_executes_option_and_retains_original_budget():
    r,m,p,e,events=execute('F0')
    assert e.actions==['finish'] and r['intervention_sequence']==[]
    assert r['final_budget']['policy_attempt_count']==3
    assert r['final_budget']['environment_step_count']==2

def test_journal_intent_precedes_environment_result():
    r,m,p,e,events=execute('F1')
    assert [v['type'] for v in events][:2]==['ENVIRONMENT_ACTION_INTENT','ENVIRONMENT_ACTION_RESULT']
    assert events[2]['type']=='POLICY_CALL_INTENT'

def test_f1_own_state_retrieval_not_copied_from_f0():
    r0,m0,_,_,_=execute('F0');r1,m1,_,_,_=execute('F1')
    assert m0.prepared[-1][0]!=m1.prepared[-1][0]
    assert 'pencil' in m1.prepared[-1][0]

def test_f0_source_prompt_mismatch_prevents_all_effects():
    m,p,e=Memory(),Policy(),Env()
    with pytest.raises(ValueError,match='source prompt'):
        run_branch_core(arm='F0',source_prompt_sha256='0'*64,goal='x',observation='x',commands=('finish',),history=(),
          budget=BudgetState(),feedback=None,source_call_index=0,seed=19,memory_adapter=m,policy=p,environment=e,contract=contract(),limits=BudgetLimits())
    assert e.actions==[] and p.seeds==[]

def test_actual_native_budget_api_used_not_call_index_as_step_count():
    r,*_=execute('F1')
    assert r['option_environment_step_count']==1 and r['policy_call_count_from_source']==1
    assert r['final_budget']['environment_step_count']==3

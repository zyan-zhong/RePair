from __future__ import annotations
import pytest
from pchsi.evaluation.alfworld_worker_protocol import CloseRequest,CreateEnvironmentRequest,EnvironmentCreated,ResetRequest,ResetResult,StepRequest,StepResult,WorkerFailure,WorkerTerminalStatus,worker_message_from_bytes,worker_message_from_dict

def _messages():
    return (CreateEnvironmentRequest('/tmp/game.tw-pddl','reg','a'*64),ResetRequest(),StepRequest('look'),CloseRequest(),EnvironmentCreated('/tmp/game.tw-pddl','reg'),ResetResult('initial',('look','inventory'),'/tmp/game.tw-pddl'),StepResult('after',('inventory',),0,False,False,None),WorkerFailure('step','STEP_FAILED','RuntimeError','bounded'),WorkerTerminalStatus('CLOSED',None,None))
def test_worker_messages_are_closed_canonical_and_round_trip():
    for message in _messages():
        assert worker_message_from_bytes(message.to_bytes())==message
        bad=dict(message.to_dict()); bad['unknown']=1
        with pytest.raises(ValueError,match='unknown'): worker_message_from_dict(bad)
def test_no_environment_object_or_raw_infos_crosses_ipc():
    names=set()
    for message in _messages(): names.update(message.to_dict())
    assert names.isdisjoint({'infos','environment','env','expert_plan','facts','policy_commands'})

from pathlib import Path
import os,base64
from native_branch import NativePolicy
from source_adapter import load_source_rows
from io_utils import read_json,sha,canonical
from pchsi.evaluation.rendered_prompt import RenderedPromptEvidence
from pchsi.evaluation.policy_client import PolicyClient
from pchsi.evaluation.budget import BudgetState
from pchsi.evaluation.raw_policy_prompt import ExecutedTransition

INP=Path(os.environ['PCHSI_TEST_EVIDENCE_ROOT'])
def test_actual_native_policy_transport_and_evidence_api():
    rows=load_source_rows(INP);call=rows[0]['source_call']
    runtime=read_json(INP/'actor_runtime/runtime_binding.json')
    rendered=RenderedPromptEvidence(call.prompt_sha256,runtime['chat_template_sha256'],call.rendered_prompt_sha256,
      tuple(call.rendered_prompt_token_ids),sha(canonical(list(call.rendered_prompt_token_ids))),
      call.rendered_prompt_token_count,call.rendered_prompt_text)
    class Renderer:
        def render(self,*,prompt_text):
            assert prompt_text==call.prompt_text
            return rendered
    captured=[]
    class Transport:
        def post_exact(self,*,path,body,headers):
            captured.append(body)
            return call.http_status,dict(call.response_headers_allowlisted),base64.b64decode(call.raw_response_body_base64)
    p=NativePolicy.__new__(NativePolicy)
    p.runtime=runtime;p.renderer=Renderer();p.client=PolicyClient(transport=Transport());p.binding={'branch_key_sha256':'a'*64}
    from types import SimpleNamespace
    response,evidence=p.act(prepared=SimpleNamespace(prompt_text=call.prompt_text),seed=17,model_call_index=2,
      goal=call.public_task_goal,observation=call.observation,commands=call.admissible_commands,
      history=tuple(ExecutedTransition(*x) for x in call.executed_history),budget=BudgetState(**dict(call.budget_before)),
      feedback=None)
    assert response==call.raw_response_text
    assert evidence['schema_id']=='POLICY_CALL_EVIDENCE_V1'
    assert evidence['request_wire_sha256']==sha(captured[0])

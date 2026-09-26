from __future__ import annotations
import json
import pytest
from pchsi.evaluation.canonical_evidence import canonical_json_bytes, sha256_bytes, sha256_text
from pchsi.evaluation.policy_client import HttpPolicyTransport, PolicyClient, PromptTokenMismatchError
from pchsi.evaluation.policy_request import E1PolicyRequestV1
from pchsi.evaluation.rendered_prompt import RenderedPromptEvidence

class FakeTransport:
    def __init__(self,ids=(11,12,13)): self.ids=ids; self.calls=[]
    def post_exact(self,*,path,body,headers):
        self.calls.append((path,body,dict(headers)))
        response={"id":"chatcmpl","model":"Qwen2.5-3B-Instruct-E1","choices":[{"index":0,"message":{"role":"assistant","content":"{\"action\":\"look\"}"},"finish_reason":"stop","token_ids":[21]}],"usage":{"prompt_tokens":len(self.ids),"completion_tokens":1},"prompt_token_ids":list(self.ids)}
        return 200,{"x-request-id":"provider"},json.dumps(response).encode()

def _expected():
    ids=(11,12,13)
    return RenderedPromptEvidence(sha256_text("PROMPT"),sha256_text("template"),sha256_text("rendered"),ids,sha256_bytes(canonical_json_bytes(list(ids))),3)
def _request(): return E1PolicyRequestV1("PROMPT",17,"client")

def test_prompt_token_ids_must_match_local_rendering() -> None:
    client=PolicyClient(transport=FakeTransport((11,12,999)),clock_ns=iter([0,1_000_000]).__next__)
    with pytest.raises(PromptTokenMismatchError): client.generate(request=_request(),expected_prompt=_expected())

class Response:
    status=307
    def read(self): return b"redirect"
    def getheaders(self): return []
class Connection:
    def __init__(self): self.requests=[]; self.closed=False
    def request(self,method,path,*,body,headers): self.requests.append((method,path,body,dict(headers)))
    def getresponse(self): return Response()
    def close(self): self.closed=True
class Factory:
    def __init__(self): self.calls=[]; self.connection=Connection()
    def __call__(self,**kwargs): self.calls.append(kwargs); return self.connection

def test_policy_transport_sends_exact_bytes_no_redirect_no_retry() -> None:
    factory=Factory(); transport=HttpPolicyTransport(base_url="http://127.0.0.1:8000",connection_factory=factory)
    status,_,body=transport.post_exact(path="/v1/chat/completions",body=b"{}\n",headers={"Content-Type":"application/json"})
    assert status==307 and body==b"redirect"
    assert len(factory.calls)==1 and len(factory.connection.requests)==1 and factory.connection.closed

def test_policy_client_posts_once_and_preserves_exact_request_bytes() -> None:
    transport=FakeTransport(); client=PolicyClient(transport=transport,clock_ns=iter([1_000_000,7_000_000]).__next__)
    generation=client.generate(request=_request(),expected_prompt=_expected())
    assert len(transport.calls)==1
    assert transport.calls[0][0]=="/v1/chat/completions"
    assert transport.calls[0][1]==_request().to_wire_bytes()
    assert generation.latency_ms==6

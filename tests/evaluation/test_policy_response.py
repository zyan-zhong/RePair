from __future__ import annotations
import json
import pytest
from pchsi.evaluation.policy_response import PolicyResponseError, parse_policy_response

def _body(finish_reason="stop", prompt_ids=None):
    if prompt_ids is None: prompt_ids=[101,102,103]
    return json.dumps({
        "id":"chatcmpl-provider",
        "model":"Qwen2.5-3B-Instruct-E1",
        "choices":[{"index":0,"message":{"role":"assistant","content":"{\"action\":\"look\"}"},"finish_reason":finish_reason,"token_ids":[201,202]}],
        "usage":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5},
        "prompt_token_ids":prompt_ids,
    },sort_keys=True,separators=(",",":")).encode()

def test_policy_response_requires_http_200_single_choice_usage_and_ids() -> None:
    with pytest.raises(PolicyResponseError):
        parse_policy_response(status_code=500,headers={},body=_body(),client_request_id="c",latency_ms=1)
    root=json.loads(_body()); root["choices"]=[]
    with pytest.raises(PolicyResponseError):
        parse_policy_response(status_code=200,headers={},body=json.dumps(root).encode(),client_request_id="c",latency_ms=1)
    root=json.loads(_body()); root["usage"]["prompt_tokens"]=True
    with pytest.raises(PolicyResponseError):
        parse_policy_response(status_code=200,headers={},body=json.dumps(root).encode(),client_request_id="c",latency_ms=1)
    root=json.loads(_body()); root["prompt_token_ids"]=None
    with pytest.raises(PolicyResponseError):
        parse_policy_response(status_code=200,headers={},body=json.dumps(root).encode(),client_request_id="c",latency_ms=1)

def test_length_finish_is_completed_generation() -> None:
    body=_body("length")
    generation=parse_policy_response(status_code=200,headers={"x-request-id":"provider"},body=body,client_request_id="client",latency_ms=5)
    assert generation.finish_reason=="length"
    assert generation.raw_response_body==body
    assert generation.raw_response_text=='{"action":"look"}'
    assert generation.prompt_token_ids==(101,102,103)
    assert generation.token_ids==(201,202)

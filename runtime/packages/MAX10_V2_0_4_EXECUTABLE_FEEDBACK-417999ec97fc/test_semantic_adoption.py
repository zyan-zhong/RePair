import json,hashlib
import pytest
from semantic_adoption import adopt

def domain_hash(schema,value,excluded_field=None):
    return hashlib.sha256(json.dumps({k:v for k,v in value.items() if k!=excluded_field},sort_keys=True).encode()).hexdigest()

def fixture(tmp_path):
    call=tmp_path/('a'*64);call.mkdir();raw=b'{}';sha=hashlib.sha256(raw).hexdigest()
    for name in ('raw_request.json','raw_response.json'):(call/name).write_bytes(raw)
    bundle={'provider_request':{}};bundle['request_body_sha256']=domain_hash('',{})
    logical={'logical_call_id':call.name,'terminal_method_status':'SEMANTIC_INVALID','contributing_attempt_id':call.name+':0','request_body_sha256':bundle['request_body_sha256']}
    logical['logical_call_sha256']=domain_hash('',logical)
    attempt={'logical_call_id':call.name,'transport_attempt_id':call.name+':0','terminal_attempt_status':'SUCCEEDED','raw_request_sha256':sha,'raw_response_sha256':sha}
    attempt['attempt_sha256']=domain_hash('',attempt)
    error={'failure_class':'METHOD_OUTPUT_INVALID','counts_as_method_failure':True,'error_type':'ValueError','message':'dangling IDs'}
    for name,value in [('logical_call.json',logical),('attempt_000.json',attempt),('rendered_request.json',bundle),('validation_error.json',error)]:
        (call/name).write_text(json.dumps(value))
    return call

def test_verified_invalid_output_reused_without_resend(tmp_path):
    call=fixture(tmp_path);before={p.name:p.read_bytes() for p in call.iterdir()}
    got=adopt(call,lambda _:pytest.fail('native falsely requires method_result'),domain_hash)
    assert got['status']=='SEMANTIC_INVALID' and not got['hard_stop'] and got['reused_terminal']
    assert not got['same_logical_call_resend_authorized'] and got['validated_artifact_sha256'] is None
    assert before=={p.name:p.read_bytes() for p in call.iterdir()}

def test_corrupt_wire_never_adopted(tmp_path):
    call=fixture(tmp_path);(call/'raw_response.json').write_text('changed')
    with pytest.raises(ValueError,match='WIRE_SHA'):adopt(call,lambda _:None,domain_hash)

def test_missing_logical_stays_native_fail_closed(tmp_path):
    def native(call):raise RuntimeError('PARTIAL')
    with pytest.raises(RuntimeError,match='PARTIAL'):adopt(tmp_path,native,domain_hash)

def test_feedback_child_preserves_registered_durable_worker():
    from pathlib import Path
    text=Path(__file__).with_name('feedback_worker.py').read_text()
    assert 'return transport_worker.main()' in text
    assert 'return recipe_worker.main()' not in text

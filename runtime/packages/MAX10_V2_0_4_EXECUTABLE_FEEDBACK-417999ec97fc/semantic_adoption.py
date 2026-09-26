"""Adopt native invalid-output terminals that correctly have no method_result file."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import json,hashlib

def adopt(call,native,domain_hash):
    call=Path(call);logical_path=call/'logical_call.json'
    if not logical_path.is_file() or (call/'method_result.json').exists():return native(call)
    logical=json.loads(logical_path.read_bytes())
    if logical.get('terminal_method_status')!='SEMANTIC_INVALID':return native(call)
    if domain_hash('LOGICAL_CALL_RECORD_V1',logical,excluded_field='logical_call_sha256')!=logical['logical_call_sha256']:raise ValueError('INVALID_TERMINAL_LOGICAL_SHA')
    if logical['logical_call_id']!=call.name:raise ValueError('INVALID_TERMINAL_CALL_ID')
    contributing=logical['contributing_attempt_id'];cid,index=contributing.rsplit(':',1)
    if cid!=call.name or not index.isdecimal():raise ValueError('INVALID_TERMINAL_ATTEMPT_ID')
    attempt=json.loads((call/('attempt_'+format(int(index),'03d')+'.json')).read_bytes())
    if domain_hash('TRANSPORT_ATTEMPT_RECORD_V1',attempt,excluded_field='attempt_sha256')!=attempt['attempt_sha256']:raise ValueError('INVALID_TERMINAL_ATTEMPT_SHA')
    if attempt['logical_call_id']!=call.name or attempt['transport_attempt_id']!=contributing or attempt['terminal_attempt_status']!='SUCCEEDED':raise ValueError('INVALID_TERMINAL_TRANSPORT_NOT_COMPLETE')
    for name,key in [('raw_request.json','raw_request_sha256'),('raw_response.json','raw_response_sha256')]:
        if hashlib.sha256((call/name).read_bytes()).hexdigest()!=attempt[key]:raise ValueError('INVALID_TERMINAL_WIRE_SHA')
    bundle=json.loads((call/'rendered_request.json').read_bytes())
    if bundle['request_body_sha256']!=logical['request_body_sha256'] or domain_hash('COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1',bundle['provider_request'])!=logical['request_body_sha256']:raise ValueError('INVALID_TERMINAL_RENDER_SHA')
    error=json.loads((call/'validation_error.json').read_bytes())
    if error.get('failure_class')!='METHOD_OUTPUT_INVALID' or error.get('counts_as_method_failure') is not True:raise ValueError('INVALID_TERMINAL_VALIDATION_EVIDENCE_REQUIRED')
    return {'logical_call_id':call.name,'call_dir':str(call),'status':'SEMANTIC_INVALID',
        'method_failure_reason':str(error['error_type'])+':'+str(error['message']),
        'validated_artifact_sha256':None,'hard_stop':False,'reused_terminal':True,
        'same_logical_call_resend_authorized':False,'transport_attempt_id':contributing,
        'transport_attempt_count':int(index)+1}

@contextmanager
def installed():
    from pchsi.cognitive_runtime import registry_runner
    from pchsi.reference_loop.canonical import domain_hash
    native=registry_runner._adopt_terminal
    with patch.object(registry_runner,'_adopt_terminal',lambda call:adopt(call,native,domain_hash)):yield

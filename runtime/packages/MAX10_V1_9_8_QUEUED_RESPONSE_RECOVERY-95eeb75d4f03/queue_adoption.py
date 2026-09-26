from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import json,hashlib

def verify_target(a):
    target=a['queue_recovery_target'];values={}
    for n,ref in target['call_refs'].items():
        raw=Path(ref['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('QUEUE_TARGET_SOURCE_CHANGED:'+n)
        values[n]=json.loads(raw)
    logical=values['logical_call.json'];method=values['method_result.json'];attempt=values['attempt_000.json']
    assert logical['logical_call_id']==target['logical_call_id'] and logical['terminal_method_status']=='INFRASTRUCTURE_UNAVAILABLE'
    assert method['failure_class']=='KNOWN_RESPONSE_RETRIEVAL_UNAVAILABLE' and method['message'].endswith('DURABLE_POLL_DEADLINE_WITH_RESPONSE_ID')
    assert attempt['bytes_transmission_state']=='CONFIRMED_SENT' and attempt['provider_response_id']
    assert a['queue_policy']['max_infrastructure_attempt_restarts']>=target['original_transport_attempts_consumed']
    return values

@contextmanager
def installed_adoption(a,identity):
    import adapter
    from repair import verify_terminal
    from group_recovery import adopt_successor,pin_successor
    from entry.campaign_owner import _write_once
    from transport_entry import ROOT,ref
    values=verify_target(a);target=a['queue_recovery_target'];old=values['logical_call.json'];native_group=adapter.run_group_tail
    recovery=Path(target['call_dir']).parent/'registered_queue_recoveries'/identity
    def group(binding,stage_values,core,prepared,accesses,out):
        native=core.u.execute_or_reuse
        def execute(**kw):
            bundle=core.api['render_stage_request'](stage_id=kw['stage_id'],projection=kw['projection'])
            cid=core.u.expected_logical_call_id(**{k:kw[k] for k in ('unit_identity','stage_id','condition_id','round_id','policy_version','domain_hash')},request_body_sha256=bundle['request_body_sha256'])
            if cid!=target['logical_call_id']:return native(**kw)
            if str(Path(kw['runtime_root'])/cid)!=target['call_dir'] or bundle!=values['rendered_request.json']:
                raise ValueError('QUEUE_RECOVERY_SCIENTIFIC_BINDING_CHANGED')
            expected={k:old[k] for k in ('stage_id','condition_id','round_id','policy_version','scientific_unit_identity_sha256','request_body_sha256')}
            if expected['scientific_unit_identity_sha256']!=kw['unit_identity']['identity_sha256']:raise ValueError('QUEUE_RECOVERY_UNIT_CHANGED')
            mapping={'schema_id':'REGISTERED_SAME_INPUT_QUEUE_RECOVERY_V1','original_logical_call_id':cid,
                'remediation_logical_call_id':cid,'recovery_root':str(recovery),'original_logical_call_ref':target['call_refs']['logical_call.json'],
                'authority_ref':ref(ROOT/'AUTHORITY.json'),'same_scientific_input':True,'original_terminal_preserved':True,
                'generation_requires_empty_cancellation':True}
            pin_successor(target['call_dir'],mapping);_write_once(recovery/'RECOVERY_AUTHORITY.json',mapping)
            call=recovery/'calls'/cid;claim=recovery/'STARTED.json'
            if (call/'logical_call.json').exists():result=adopt_successor(call,expected,core.api,core.domain_hash)
            else:
                if claim.exists() or call.exists():raise RuntimeError('PARTIAL_QUEUE_RECOVERY_NO_BLIND_RESEND')
                _write_once(claim,{'logical_call_id':cid,'authority_ref':mapping['authority_ref']})
                kw_native={k:kw[k] for k in ('unit_identity','stage_id','condition_id','round_id','policy_version','projection','task_access')}
                # First recovery attempt handles the already-created job. Any new
                # generation must fit inside the original remaining retry budget.
                result=core.api['execute_one'](**kw_native,output_root=recovery/'calls',
                    max_infrastructure_attempt_restarts=a['queue_policy']['max_infrastructure_attempt_restarts']-target['original_transport_attempts_consumed'])
            result={**result,'original_logical_call_id':cid,'reused_terminal_call':bool(result.get('reused_terminal',False)),
                'registered_queue_recovery_authority':ref(recovery/'RECOVERY_AUTHORITY.json')}
            print('REGISTERED_GROUP_RECOVERY '+json.dumps({'original_logical_call_id':cid,'logical_call_id':cid,'status':result['status']}),flush=True)
            return result
        with patch.object(core.u,'execute_or_reuse',execute):return native_group(binding,stage_values,core,prepared,accesses,out)
    with patch.object(adapter,'run_group_tail',group):yield

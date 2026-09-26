"""Exact durable group recovery; original exhausted evidence remains immutable."""
from pathlib import Path
from functools import wraps
import json,os
from transport_scope import remaining_attempts

def require(ok,reason):
    if not ok:raise ValueError(reason)

def pin_successor(old_call,mapping):
    """One mapping across all future package/authority revisions."""
    path=Path(old_call)/'REGISTERED_TRANSPORT_CONTINUATION.json'
    if path.exists():
        require(not path.is_symlink() and json.loads(path.read_bytes())==mapping,'ORIGINAL_GROUP_ALREADY_HAS_DIFFERENT_SUCCESSOR')
    else:
        with path.open('x',encoding='utf8') as stream:
            json.dump(mapping,stream,sort_keys=True);stream.flush();os.fsync(stream.fileno())
    if os.name=='posix':
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

def adopt_successor(call,expected,api,domain_hash):
    from repair import verify_terminal
    logical=json.loads((Path(call)/'logical_call.json').read_bytes())
    if (Path(call)/'validation_error.json').is_file() and not (Path(call)/'method_result.json').exists():
        # The shared native adopter first verifies logical ID, attempt identity,
        # canonical request bytes and request-domain SHA before this branch.
        try:verify_terminal(call,expected=expected)
        except RuntimeError as exc:
            require(str(exc)=='UNSUPPORTED_PARTIAL_TERMINAL_NO_RESEND:'+logical['terminal_method_status'],'SUCCESSOR_TERMINAL_PROOF_FAILED')
        else:raise ValueError('SUCCESSOR_VALIDATION_TERMINAL_EXPECTED')
        error=json.loads((Path(call)/'validation_error.json').read_bytes())
        index=int(logical['contributing_attempt_id'].rsplit(':',1)[1]);attempt=json.loads((Path(call)/('attempt_%03d.json'%index)).read_bytes())
        import hashlib
        require(attempt['bytes_transmission_state']=='CONFIRMED_SENT' and attempt['terminal_attempt_status']=='SUCCEEDED'
            and attempt['raw_response_sha256']==hashlib.sha256((Path(call)/'raw_response.json').read_bytes()).hexdigest(),'SUCCESSOR_VALIDATION_RESPONSE_PROOF_REQUIRED')
        return {'logical_call_id':logical['logical_call_id'],'call_dir':str(call),'status':logical['terminal_method_status'],
            'hard_stop':bool(error.get('hard_stop',False)),'method_failure_reason':error.get('message'),'reused_terminal':True}
    return verify_terminal(call,expected=expected)

def durable_successor(root,cid,authority,execute,adopt):
    root=Path(root);claim=root/'STARTED.json';call=root/'calls'/cid
    expected={'logical_call_id':cid,'authority':authority}
    if claim.exists():
        require(not claim.is_symlink() and json.loads(claim.read_bytes())==expected,'SUCCESSOR_CLAIM_CHANGED')
        require((call/'logical_call.json').is_file(),'PARTIAL_SUCCESSOR_NO_RESEND')
        return adopt(call)
    require(not call.exists() and not call.is_symlink(),'PARTIAL_SUCCESSOR_WITHOUT_CLAIM')
    root.mkdir(parents=True,exist_ok=True)
    with claim.open('x',encoding='utf8') as stream:
        json.dump(expected,stream,sort_keys=True);stream.flush();os.fsync(stream.fileno())
    if os.name=='posix':
        for p in (root,*root.parents):
            fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
    return execute()

def validate_old(authority):
    from continuation import read_ref
    from repair import verify_terminal
    from pchsi.reference_loop.canonical import domain_hash
    a=authority['repair'];refs=a['refs'];values={k:read_ref(v) for k,v in refs.items()}
    call=Path(a['call_dir']);logical=values['logical_call.json'];method=values['method_result.json'];attempt=values['attempt_000.json'];meta=values['transport_http_meta.json']
    require(call.name==a['logical_call_id']==logical['logical_call_id'],'OLD_GROUP_CALL_CHANGED')
    require(logical['terminal_method_status']=='INFRASTRUCTURE_UNAVAILABLE' and logical['stage_id']=='G-A2','OLD_GROUP_STATUS_CHANGED')
    require(method['hard_stop'] is True and method['infrastructure_retry_budget_exhausted'] is True and method['transport_attempt_count']==a['consumed_attempts'],'OLD_EXHAUSTION_CHANGED')
    require(a['consumed_attempts']==1 and attempt['transport_attempt_index']==0 and attempt['logical_call_id']==a['logical_call_id'],'OLD_ATTEMPT_COUNT_CHANGED')
    require(attempt['attempt_sha256']==domain_hash('TRANSPORT_ATTEMPT_RECORD_V1',attempt,excluded_field='attempt_sha256'),'OLD_ATTEMPT_SHA_CHANGED')
    require(attempt['bytes_transmission_state']=='NOT_SENT' and attempt['retry_class']=='SAFE_PRE_SEND'
        and attempt['raw_response_sha256'] is None and attempt['provider_response_id'] is None,'OLD_NOT_SENT_PROOF_REQUIRED')
    require(meta.get('http_status') is None and not (call/'raw_response.json').exists() and not (call/'validated_artifact.json').exists(),'OLD_RESPONSE_PREVENTS_RECOVERY')
    verify_terminal(call)
    return values

def group_wrapper(native,core,authority,scope,recovery_root,observe,*,dry_run=False):
    from repair import verify_terminal
    from continuation import file_ref
    a=authority['repair'];old=validate_old(authority);logical=old['logical_call.json']
    @wraps(native)
    def execute(**kw):
        rendered=core.api['render_stage_request'](stage_id=kw['stage_id'],projection=kw['projection'])
        identity_args={k:kw[k] for k in ('unit_identity','stage_id','condition_id','round_id','policy_version','domain_hash')}
        cid=core.u.expected_logical_call_id(**identity_args,request_body_sha256=rendered['request_body_sha256'])
        expected={k:kw[k] for k in ('stage_id','condition_id','round_id','policy_version')}
        expected.update(scientific_unit_identity_sha256=kw['unit_identity']['identity_sha256'],request_body_sha256=rendered['request_body_sha256'])
        path=Path(kw['runtime_root'])/cid
        if cid!=a['logical_call_id']:
            if (path/'logical_call.json').is_file():
                row=json.loads((path/'logical_call.json').read_bytes())
                if row['terminal_method_status']=='ACCEPTED':verify_terminal(path,expected=expected)
            result=native(**kw)
            if observe:observe({'stage_id':kw['stage_id'],'round_id':kw['round_id'],'unit_identity':kw['unit_identity']},result)
            return result
        require(path==Path(a['call_dir']),'RECOVERY_PATH_CHANGED')
        require(all(logical[k]==v for k,v in expected.items()),'RECOVERY_NATIVE_IDENTITY_CHANGED')
        require(rendered==old['rendered_request.json'],'RECOVERY_SCIENTIFIC_REQUEST_CHANGED')
        remaining=remaining_attempts(scope['max_infrastructure_attempt_restarts'],a['consumed_attempts'])
        scientific_id=core.domain_hash('REGISTERED_GROUP_TRANSPORT_CONTINUATION_V1',{
            'startup_authority_sha256':authority['_authority_sha256'],'original_logical_call_sha256':logical['logical_call_sha256'],
            'campaign_authority_sha256':scope['campaign_authority_sha256'],'consumed_attempts':a['consumed_attempts']})
        fields={k:v for k,v in kw['unit_identity'].items() if k not in ('schema_id','schema_version','identity_sha256')};fields['scientific_unit_id']=scientific_id
        unit=core.identity(**fields)
        new_id=core.u.expected_logical_call_id(**{**identity_args,'unit_identity':unit},request_body_sha256=rendered['request_body_sha256'])
        mapping={'schema_id':'REGISTERED_GROUP_TRANSPORT_CONTINUATION_V1','original_logical_call_id':cid,
            'remediation_logical_call_id':new_id,'original_logical_call_ref':a['refs']['logical_call.json'],
            'startup_authority_sha256':authority['_authority_sha256'],'campaign_authority_ref':scope['campaign_authority_ref'],
            'consumed_attempts':a['consumed_attempts'],'maximum_new_attempts':remaining,
            'request_body_sha256':rendered['request_body_sha256'],'old_terminal_unchanged':True,'original_budget_remains_exhausted':True}
        if dry_run:return {'status':'RECOVERY_PREFLIGHT_NO_SEND','mapping':mapping,'original_identity':kw['unit_identity'],'remediation_identity':unit}
        from entry.campaign_owner import _write_once
        pin_successor(path,{**mapping,'recovery_root':str(recovery_root)})
        _write_once(Path(recovery_root)/'RECOVERY_AUTHORITY.json',mapping)
        forwarded={k:kw[k] for k in ('stage_id','condition_id','round_id','policy_version','projection','task_access')}
        new_expected={**expected,'scientific_unit_identity_sha256':unit['identity_sha256']}
        result=durable_successor(recovery_root,new_id,mapping,
            lambda:core.api['execute_one'](**forwarded,output_root=Path(recovery_root)/'calls',unit_identity=unit,max_infrastructure_attempt_restarts=remaining-1),
            lambda p:adopt_successor(p,new_expected,core.api,core.domain_hash))
        result={**result,'original_logical_call_id':cid,'reused_terminal_call':bool(result.get('reused_terminal',False)),
            'transport_continuation_authority':file_ref(Path(recovery_root)/'RECOVERY_AUTHORITY.json')}
        if observe:observe({'stage_id':kw['stage_id'],'round_id':kw['round_id'],'unit_identity':unit},result)
        print('REGISTERED_GROUP_RECOVERY '+json.dumps({'original_logical_call_id':cid,'logical_call_id':new_id,'status':result['status']}),flush=True)
        return result
    return execute

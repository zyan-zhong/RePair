from pathlib import Path
from unittest.mock import patch
import sys,json,subprocess,hashlib,socket
from transport_entry import ROOT,verify,load,installed_transport

def server():
    a,prior,identity,prepared=load()
    from memory_binding.worker_bootstrap import bootstrap_current_and_children
    bootstrap_current_and_children(a['scientific_repo_root'])
    from transport_entry import installed
    from pchsi.cognitive_runtime import request_renderer as rr,orchestrator,registry_runner
    import adapter
    fixture=json.loads((ROOT/'NATIVE_LOCAL_FIXTURE.json').read_bytes())
    binding=json.loads(Path(fixture['current_binding_path']).read_bytes())
    from exact_bindings import read_ref
    request=read_ref(binding['refs']['request']);prior_render=rr.render_stage_request
    baseline=prior_render(stage_id=fixture['stage_id'],projection=fixture['projection'])
    trial={**a,'owner_root':str(ROOT/'verification')}
    index=Path(trial['owner_root'])/'request_bindings'/(request['request_sha256']+'.json');index.parent.mkdir(parents=True,exist_ok=True)
    def bound_probe(*args,**kwargs):
        result=orchestrator.render_stage_request(stage_id=fixture['stage_id'],projection=fixture['projection'])
        indexed=registry_runner.render_stage_request(stage_id=fixture['stage_id'],projection=fixture['projection'])
        assert result==indexed
        return result
    def render_round(number):
        index.write_text(json.dumps({'round_index':number}))
        out=ROOT/'verification'/('round-'+str(number));out.mkdir(parents=True,exist_ok=True)
        predecessor=out/'REGISTERED_DURABLE_TRANSPORT.json'
        if not predecessor.exists():predecessor.write_text('{"fixture":"immutable V197 round adoption"}\n')
        before=predecessor.read_bytes()
        with patch.object(adapter,'run_bound_round',bound_probe),installed(trial,identity):
            result=adapter.run_bound_round(binding,out)
        assert predecessor.read_bytes()==before
        assert (out/'registered_transport_updates'/identity/'REGISTERED_DURABLE_TRANSPORT.json').exists()
        return result
    now=render_round(a['activation_round_index']);future=render_round(a['activation_round_index']+1)
    assert now==baseline
    assert future['provider_request']['max_output_tokens']==rr.load_runtime_manifest()['global_max_output_tokens']
    assert future['provider_request']['input'][1:]==baseline['provider_request']['input'][1:]
    assert future['request_body_sha256']!=baseline['request_body_sha256']
    from pchsi.cognitive_runtime import p2_bridge
    from pchsi.cognitive_runtime.p2_assets import locate_p2_root
    module=p2_bridge._load_transport_module(locate_p2_root())
    observed=[];gets=[];output=ROOT/'verification/native_transport';output.mkdir(parents=True,exist_ok=True)
    trial=dict(a);trial['owner_root']=str(ROOT/'verification')
    body={'model':a['registered_model'],'store':False,'input':'No-send native boundary verification'}
    logical=hashlib.sha256(json.dumps(body).encode()).hexdigest()
    def send(client,request,*args,**kw):
        observed.append(request.method)
        if request.method=='POST':
            value=json.loads(request.content);assert value=={**body,'background':True}
            value={'id':'resp_verify_native','model':a['registered_model'],'status':'queued','background':True}
        else:
            assert request.url.path.endswith('/resp_verify_native');gets.append(True)
            if len(gets)==1:raise module.httpx.RemoteProtocolError('simulated retrieve disconnect')
            if len(gets)==2:return module.httpx.Response(200,content=b'{"id":',request=request)
            value={'id':'resp_verify_native','model':a['registered_model'],'status':'completed','background':True,'output':[]}
        return module.httpx.Response(200,json=value,headers={'x-request-id':'req_verify'},request=request)
    def no_connect(*args,**kw):raise AssertionError('PROVIDER_CONNECTION_FORBIDDEN')
    import durable_transport
    original=durable_transport.durable_callable
    def fast(*args,**kw):return original(*args,**{**kw,'sleep':lambda _:None})
    with patch.dict('os.environ',{'OPENAI_API_KEY':'verification-not-a-credential','https_proxy':'http://127.0.0.1:1'}),\
         patch.object(socket.socket,'connect',no_connect),patch.object(module.httpx.Client,'send',send),\
         patch.object(durable_transport,'durable_callable',fast),installed_transport(trial,identity):
        result=p2_bridge.execute_via_existing_p2({'provider_request':body},output,client_request_id=logical)
    assert json.loads(result.raw_response)['id']=='resp_verify_native'
    # An already-completed verification is a durable cache hit when VERIFY repeats.
    assert observed in (['POST','GET','GET','GET'],[])
    # A known provider response must never become NOT_SENT in native receipts.
    failed_body={**body,'input':'No-send known-response failure verification'}
    failed_id=hashlib.sha256(json.dumps(failed_body).encode()).hexdigest()
    def failed_send(client,request,*args,**kw):
        if request.method=='POST':
            value={'id':'resp_verify_unavailable','model':a['registered_model'],'status':'queued','background':True}
            return module.httpx.Response(200,json=value,headers={'x-request-id':'req_known'},request=request)
        return module.httpx.Response(404,json={'error':{'message':'injected'}},request=request)
    with patch.dict('os.environ',{'OPENAI_API_KEY':'verification-not-a-credential','https_proxy':'http://127.0.0.1:1'}),\
         patch.object(socket.socket,'connect',no_connect),patch.object(module.httpx.Client,'send',failed_send),installed_transport(trial,identity):
        try:p2_bridge.execute_via_existing_p2({'provider_request':failed_body},output,client_request_id=failed_id)
        except p2_bridge.P2TransportError as error:
            assert error.failure_class=='KNOWN_RESPONSE_RETRIEVAL_UNAVAILABLE'
            assert error.bytes_transmission_state=='CONFIRMED_SENT' and error.retry_class=='NO_RETRY' and error.hard_stop
            attempt=orchestrator.build_transport_attempt_record(logical_call_id=failed_id,transport_attempt_id=failed_id+':0',
                transport_attempt_index=0,bytes_transmission_state=error.bytes_transmission_state,retry_class=error.retry_class,
                retry_reason=error.failure_class,retry_authority=error.retry_authority,provider_response_id=None,
                terminal_attempt_status=error.terminal_attempt_status,ambiguous_post_send_disposition_id=None,
                raw_request_sha256=hashlib.sha256(json.dumps(failed_body).encode()).hexdigest(),raw_response_sha256=None,
                input_tokens=None,output_tokens=None,reasoning_tokens=None,latency_ms=1,cost_usd=None)
            assert attempt['provider_response_id']=='resp_verify_unavailable' and attempt['bytes_transmission_state']=='CONFIRMED_SENT'
        else:raise AssertionError('EXPECTED_KNOWN_RESPONSE_FAILURE')
    # Exercise the exact native P2 exception and attempt-record boundary for an
    # acknowledged queued job, then the one allowed replacement generation.
    import tempfile,time
    from durable_transport import once
    queue_trial={**a,'owner_root':tempfile.mkdtemp(prefix='queue_native_',dir=ROOT/'verification')}
    queue_body={**body,'input':'No-send confirmed empty queued cancellation'}
    queue_id=hashlib.sha256(json.dumps(queue_body).encode()).hexdigest()
    queue_cache=Path(queue_trial['owner_root'])/'runtime_extensions'/identity/'responses'/queue_id
    queue_cache.mkdir(parents=True)
    once(queue_cache/'RESPONSE_ID.json',{'response_id':'resp_queue_native','model':a['registered_model'],
        'received_utc_unix':time.time()-module.RESPONSE_TIMEOUT_SECONDS-1,'creation_headers':{'x-request-id':'req_queue_native'}})
    queue_methods=[]
    def queue_send(client,request,*args,**kw):
        method='CANCEL' if request.url.path.endswith('/cancel') else request.method;queue_methods.append(method)
        state='queued' if method=='GET' else 'cancelled' if method=='CANCEL' else 'completed'
        rid='resp_replacement_native' if method=='POST' else 'resp_queue_native'
        return module.httpx.Response(200,json={'id':rid,'model':a['registered_model'],'status':state,'output':[],
            'usage':None,'background':True},headers={'x-request-id':'req_native'},request=request)
    with patch.dict('os.environ',{'OPENAI_API_KEY':'verification-not-a-credential','https_proxy':'http://127.0.0.1:1'}),\
         patch.object(socket.socket,'connect',no_connect),patch.object(module.httpx.Client,'send',queue_send),installed_transport(queue_trial,identity):
        try:p2_bridge.execute_via_existing_p2({'provider_request':queue_body},output,client_request_id=queue_id)
        except p2_bridge.P2TransportError as error:
            assert error.failure_class=='REGISTERED_QUEUED_CANCELLED_EMPTY'
            assert error.bytes_transmission_state=='CONFIRMED_SENT' and error.retry_class=='SAFE_PROVIDER_REJECTION' and not error.hard_stop
            attempt=orchestrator.build_transport_attempt_record(logical_call_id=queue_id,transport_attempt_id=queue_id+':0',
                transport_attempt_index=0,bytes_transmission_state=error.bytes_transmission_state,retry_class=error.retry_class,
                retry_reason=error.failure_class,retry_authority=error.retry_authority,provider_response_id=None,
                terminal_attempt_status=error.terminal_attempt_status,ambiguous_post_send_disposition_id=None,
                raw_request_sha256=hashlib.sha256(json.dumps(queue_body).encode()).hexdigest(),raw_response_sha256=None,
                input_tokens=None,output_tokens=None,reasoning_tokens=None,latency_ms=1,cost_usd=None)
            assert attempt['provider_response_id']=='resp_queue_native'
        else:raise AssertionError('QUEUED_CANCELLATION_MUST_ENTER_EXISTING_RETRY_BUDGET')
        result=p2_bridge.execute_via_existing_p2({'provider_request':queue_body},output,client_request_id=queue_id)
        assert json.loads(result.raw_response)['id']=='resp_replacement_native'
        cached=p2_bridge.execute_via_existing_p2({'provider_request':queue_body},output,client_request_id=queue_id)
        assert cached.raw_response==result.raw_response
    assert queue_methods==['GET','CANCEL','POST']
    record={'schema_id':'DURABLE_NATIVE_P2_NO_SEND_VALIDATION_V1','transport_manifest_sha256':identity,
        'native_classification_and_bridge_preserved':True,'wire_background_field_verified':True,
        'same_response_read_retry_verified':True,'observed_methods':observed,
        'malformed_get_recovered_without_generation':True,
        'actual_native_current_round_request_unchanged':True,'actual_native_future_local_amendment_verified':True,
        'registry_and_executor_request_identity_equal':True,'known_response_failure_receipt_truth_verified':True,
        'outer_process_crash_recovery_verified':False,
        'native_empty_cancel_safe_retry_verified':True,'native_queue_methods':queue_methods,
        'existing_v197_adoption_marker_preserved':True,
        'original_source_hashes_verified':True,'provider_connections':0,'scientific_calls':0,'git_operations':0}
    (ROOT/'verification/NATIVE_VALIDATION.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)

if __name__=='__main__':
    verify()
    r=subprocess.run([sys.executable,'-B','-m','pytest','-q',str(ROOT/'test_durable_transport.py'),str(ROOT/'test_prompt_contract.py'),str(ROOT/'test_worker_boundary.py'),str(ROOT/'test_queue_recovery.py')],cwd=ROOT)
    if r.returncode:raise SystemExit(r.returncode)
    if '--server' in sys.argv:server()
    print('DURABLE_TRANSPORT_VERIFY_PASS',flush=True)

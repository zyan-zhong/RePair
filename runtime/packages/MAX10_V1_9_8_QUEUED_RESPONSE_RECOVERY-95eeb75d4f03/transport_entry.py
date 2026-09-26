from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from unittest.mock import patch
import hashlib,json,sys,importlib,subprocess
ROOT=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ref(path):return {'path':str(path),'sha256':digest(path)}
def verify():
    manifest=ROOT/'PACKAGE_FILES.sha256';seen=set()
    for line in manifest.read_text().splitlines():
        expected,name=line.split(maxsplit=1);part=PurePosixPath(name)
        if part.is_absolute() or '..' in part.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_PATH')
        seen.add(name);path=ROOT/name
        if path.is_symlink() or digest(path)!=expected:raise ValueError('PACKAGE_SOURCE_CHANGED:'+name)
    return digest(manifest)

def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());prior_root=Path(a['transport_predecessor_root'])
    if digest(prior_root/'PACKAGE_FILES.sha256')!=a['transport_predecessor_manifest_sha256']:raise ValueError('TRANSPORT_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(prior_root));prior=importlib.import_module('budget_entry');prepared=prior.load()
    for source in a['transport_source_refs']:
        if digest(source['path'])!=source['sha256']:raise ValueError('TRANSPORT_REGISTERED_SOURCE_CHANGED')
    return a,prior,identity,prepared

@contextmanager
def installed_transport(a,identity):
    from pchsi.cognitive_runtime import p2_bridge,orchestrator
    from queue_recovery import queue_callable,CancelledEmpty,active_directory
    native=p2_bridge._validated_transport_callable
    cache=Path(a['owner_root'])/'runtime_extensions'/identity/'responses'
    source=ref(ROOT/'AUTHORITY.json')
    native_error=p2_bridge._error;native_attempt=orchestrator.build_transport_attempt_record;known_failures={};attempt_acks={}
    def callable_(module):
        fn=native(module)
        durable=queue_callable(fn,module,cache,source,a)
        def execute(*,api_key,body,client_request_id):
            if client_request_id=='registered-configuration-preflight-no-send':
                return fn(api_key=api_key,body=body,client_request_id=client_request_id)
            try:return durable(api_key=api_key,body=body,client_request_id=client_request_id)
            except CancelledEmpty as error:
                message='REGISTERED_QUEUED_CANCELLED_EMPTY:'+client_request_id
                known_failures[message]={'ack':error.ack,'safe_cancel':True};attempt_acks[client_request_id]=error.ack
                raise module.HaltBatch(message) from error
            except module.HaltBatch as error:
                directory,_=active_directory(cache,client_request_id,a)
                ack=directory/'RESPONSE_ID.json'
                if not ack.exists():raise
                message='KNOWN_RESPONSE_RETRIEVAL_UNAVAILABLE:'+client_request_id+':'+str(error)
                value=json.loads(ack.read_bytes());known_failures[message]={'ack':value,'safe_cancel':False};attempt_acks[client_request_id]=value
                raise module.HaltBatch(message) from error
        return execute
    def error(message,**kwargs):
        if message in known_failures:
            safe=known_failures[message]['safe_cancel']
            kwargs={**kwargs,'failure_class':'REGISTERED_QUEUED_CANCELLED_EMPTY' if safe else 'KNOWN_RESPONSE_RETRIEVAL_UNAVAILABLE','bytes_transmission_state':'CONFIRMED_SENT',
                'retry_class':'SAFE_PROVIDER_REJECTION' if safe else 'NO_RETRY','terminal_attempt_status':'INFRASTRUCTURE_ERROR',
                'logical_method_status':'INFRASTRUCTURE_UNAVAILABLE','counts_as_method_failure':False,'hard_stop':not safe,
                'response_headers':known_failures[message]['ack']['creation_headers']}
        return native_error(message,**kwargs)
    def attempt(**kwargs):
        if kwargs.get('retry_reason') in ('KNOWN_RESPONSE_RETRIEVAL_UNAVAILABLE','REGISTERED_QUEUED_CANCELLED_EMPTY'):
            ack=attempt_acks[kwargs['logical_call_id']]
            kwargs={**kwargs,'bytes_transmission_state':'CONFIRMED_SENT','provider_response_id':ack['response_id']}
        return native_attempt(**kwargs)
    with patch.object(p2_bridge,'_validated_transport_callable',callable_),patch.object(p2_bridge,'_error',error),\
         patch.object(orchestrator,'build_transport_attempt_record',attempt):yield

@contextmanager
def installed(a,identity):
    import adapter
    from pchsi.cognitive_runtime import request_renderer as rr,orchestrator,registry_runner
    from pchsi.reference_loop.canonical import domain_hash
    from exact_bindings import read_ref,immutable_json
    from prompt_contract import amend
    native=adapter.run_bound_round;native_run=subprocess.run
    def bound(binding_path,*args,**kwargs):
        binding=binding_path if isinstance(binding_path,dict) else json.loads(Path(binding_path).read_bytes())
        request=read_ref(binding['refs']['request'])
        index=json.loads((Path(a['owner_root'])/'request_bindings'/(request['request_sha256']+'.json')).read_bytes())
        if index['round_index']<a['activation_round_index']:raise ValueError('DURABLE_HISTORICAL_ROUND_REEXECUTION_FORBIDDEN')
        out=Path(args[0]) if args and args[0] is not None else Path(kwargs.get('output_root') or binding['output_root'])
        enabled=index['round_index']>a['prompt_activation_after_round_index']
        source=ref(ROOT/'AUTHORITY.json')
        immutable_json(out/'registered_transport_updates'/identity/'REGISTERED_DURABLE_TRANSPORT.json',{'schema_id':'REGISTERED_ROUND_DURABLE_TRANSPORT_V1',
            'request_sha256':request['request_sha256'],'round_id':request['round_id'],'authority_ref':source,
            'transport_manifest_sha256':identity,'local_prompt_amendment_enabled':enabled,
            'same_logical_call_generation_retry':False,'same_response_retrieval_retry':True})
        original_render=rr.render_stage_request
        def render(*,stage_id,projection,**kw):
            result=original_render(stage_id=stage_id,projection=projection,**kw)
            if not enabled or stage_id not in ('L-A0','L-A1'):return result
            manifest=rr.load_runtime_manifest()
            result=amend(result,global_ceiling=manifest['global_max_output_tokens'],authority_ref=source,
                hash_request=lambda value:domain_hash('COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1',value))
            from pchsi.reference_loop.canonical import canonical_json_bytes
            if len(canonical_json_bytes(result['provider_request']))+manifest['global_max_output_tokens']>a['planner_context_policy']['min_model_context_window_tokens']:
                raise ValueError('LOCAL_REGISTERED_CONTEXT_BUDGET_EXCEEDED_NO_SEND')
            return result
        from queue_adoption import installed_adoption
        with installed_transport(a,identity),installed_adoption(a,identity),patch.object(rr,'render_stage_request',render),\
             patch.object(orchestrator,'render_stage_request',render),patch.object(registry_runner,'render_stage_request',render):
            return native(binding_path,*args,**kwargs)
    def run(args,*pos,**kw):
        if isinstance(args,(list,tuple)) and len(args)>2 and str(args[2])==a['post_worker_ref']['path']:
            if digest(args[2])!=a['post_worker_ref']['sha256']:raise ValueError('POST_WORKER_CHANGED')
            args=list(args);args[2]=str(ROOT/'transport_worker.py')
        return native_run(args,*pos,**kw)
    with patch.object(adapter,'run_bound_round',bound),patch.object(subprocess,'run',run):yield

def run(invocation):
    a,prior,identity,prepared=load()
    import budget_bridge,entry.progress as progress
    native=budget_bridge.installed;old=progress.update
    @contextmanager
    def combined(*args,**kwargs):
        with native(*args,**kwargs),installed(a,identity):yield
    def update(owner,**fields):return old(owner,**{**fields,'durable_transport_entry_root':str(ROOT),'durable_transport_manifest_sha256':identity})
    with patch.object(budget_bridge,'installed',combined),patch.object(progress,'update',update):return prior.run(invocation)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))

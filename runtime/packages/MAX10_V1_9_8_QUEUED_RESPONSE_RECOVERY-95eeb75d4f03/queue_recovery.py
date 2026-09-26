"""Recover an acknowledged queued job only after an empty cancellation terminal."""
from pathlib import Path
import json,time,os,hashlib,base64

class CancelledEmpty(RuntimeError):
    def __init__(self,ack,proof):super().__init__('REGISTERED_QUEUED_CANCELLED_EMPTY');self.ack=ack;self.proof=proof

def write_once(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()+b'\n'
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('QUEUE_RECOVERY_IMMUTABLE_CONFLICT')
    else:
        with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())

def resolve_pending(module,ack,directory,request,*,wait_limit,now=time.time,sleep=time.sleep):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    proof_path=directory/'CANCELLED_EMPTY.json'
    if proof_path.exists():
        proof=json.loads(proof_path.read_bytes())
        if proof['response_id']!=ack['response_id']:raise module.HaltBatch('QUEUE_CANCELLATION_ID_CHANGED')
        raw=Path(proof['raw_ref']['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=proof['raw_ref']['sha256']:raise module.HaltBatch('QUEUE_CANCELLATION_PROOF_CHANGED')
        raise CancelledEmpty(ack,proof)
    transient=(OSError,)
    if hasattr(module,'httpx'):transient+=(module.httpx.TransportError,)
    def call(method):
        for ordinal in range(len(module.BACKOFF_SECONDS)+1):
            try:
                status,headers,raw=request(method,response_id=ack['response_id'])
                if status==429 or 500<=status<600:raise OSError('RETRYABLE_PROVIDER_HTTP')
            except transient as error:
                if ordinal==len(module.BACKOFF_SECONDS):raise module.HaltBatch('QUEUE_RECOVERY_READ_UNAVAILABLE:'+type(error).__name__) from error
                sleep(module.BACKOFF_SECONDS[ordinal]);continue
            digest=hashlib.sha256(raw).hexdigest();raw_path=directory/(digest+'.json')
            if raw_path.exists():
                if raw_path.read_bytes()!=raw:raise module.HaltBatch('QUEUE_RAW_HASH_COLLISION')
            else:raw_path.write_bytes(raw)
            try:value=json.loads(raw)
            except (ValueError,UnicodeError):
                if ordinal==len(module.BACKOFF_SECONDS):raise module.HaltBatch('QUEUE_RECOVERY_MALFORMED_RESPONSE')
                sleep(module.BACKOFF_SECONDS[ordinal]);continue
            if status!=200 or not isinstance(value,dict):raise module.HaltBatch('QUEUE_RECOVERY_HTTP_OR_SHAPE:'+str(status))
            if value.get('id')!=ack['response_id'] or value.get('model')!=ack['model']:raise module.HaltBatch('QUEUE_RECOVERY_RESPONSE_IDENTITY')
            return status,headers,raw,value,{'path':str(raw_path),'sha256':digest}
    while True:
        status,headers,raw,value,raw_ref=call('GET')
        state=value.get('status')
        if state=='queued':
            if value.get('output')!=[]:raise module.HaltBatch('QUEUED_RESPONSE_HAS_OUTPUT_NO_CANCEL')
            write_once(directory/'CANCEL_INTENT.json',{'response_id':ack['response_id'],'reason':'REGISTERED_QUEUE_WAIT_EXHAUSTED','queued_response_ref':raw_ref})
            status,headers,raw,value,raw_ref=call('POST_CANCEL')
            if value.get('status')=='cancelled':
                usage=value.get('usage');output_tokens=None if usage is None else usage.get('output_tokens')
                if value.get('output')!=[] or (usage is not None and (type(output_tokens) is not int or output_tokens!=0)):
                    raise module.HaltBatch('CANCELLED_RESPONSE_HAS_OUTPUT_NO_REGENERATION')
                proof={'schema_id':'REGISTERED_EMPTY_QUEUED_CANCELLATION_V1','response_id':ack['response_id'],
                    'raw_ref':raw_ref,'output':[],'usage':usage,'safe_retry_basis':'CONFIRMED_CANCELLED_WITHOUT_MODEL_OUTPUT'}
                write_once(proof_path,proof);raise CancelledEmpty(ack,proof)
            if value.get('status') in ('queued','in_progress'):
                raise module.HaltBatch('CANCELLATION_NOT_CONFIRMED_NO_REGENERATION')
            # Completion won the race: return its existing output without regeneration.
            return status,headers,raw
        if state=='in_progress':
            remaining=ack['received_utc_unix']+wait_limit-now()
            if remaining<=0:raise module.HaltBatch('IN_PROGRESS_TOTAL_WAIT_EXHAUSTED_NO_CANCEL')
            sleep(min(module.BACKOFF_SECONDS[-1],remaining));continue
        return status,headers,raw

def provider_operation(module,api_key,method,*,response_id):
    transport=module.httpx.HTTPTransport(proxy=os.environ['https_proxy'],retries=0)
    with module.httpx.Client(transport=transport,trust_env=False,timeout=module.CONNECT_TIMEOUT_SECONDS,follow_redirects=False,http2=False) as client:
        url='https://'+module.API_HOST+module.API_PATH+'/'+response_id
        headers={'Authorization':'Bearer '+api_key,'Accept':'application/json','Accept-Encoding':'identity','Cache-Control':'no-cache'}
        response=client.get(url,headers=headers) if method=='GET' else client.post(url+'/cancel',headers=headers)
    return response.status_code,module.normalize_allowlisted_headers(dict(response.headers)),response.content

def active_directory(root,cid,authority):
    base=Path(root)/cid;index=base/'QUEUE_ATTEMPTS.jsonl'
    rows=[json.loads(x) for x in index.read_bytes().splitlines()] if index.exists() else []
    for ordinal,row in enumerate(rows):
        if row['cancelled_generation_ordinal']!=ordinal:raise ValueError('QUEUE_ATTEMPT_INDEX_GAP')
        p=Path(row['proof_ref']['path'])
        if hashlib.sha256(p.read_bytes()).hexdigest()!=row['proof_ref']['sha256']:raise ValueError('QUEUE_ATTEMPT_PROOF_CHANGED')
    ordinal=len(rows)
    if ordinal>authority['queue_policy']['max_infrastructure_attempt_restarts']:raise ValueError('QUEUE_RETRY_BUDGET_EXCEEDED')
    if ordinal:return base/'queue_attempts'/str(ordinal)/cid,ordinal
    target=authority['queue_recovery_target']
    if cid==target['logical_call_id']:
        for ref in target['cache_refs'].values():
            if hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest()!=ref['sha256']:raise ValueError('REGISTERED_QUEUE_ORIGIN_CHANGED')
        return Path(target['cache_root']),0
    return base,0

def queue_callable(native,module,root,authority_ref,authority,*,base_factory=None,request=None,sleep=time.sleep,now=time.time):
    from durable_transport import durable_callable,once,append,lock
    base_factory=base_factory or durable_callable
    def execute(*,api_key,body,client_request_id):
        base=Path(root)/client_request_id;base.mkdir(parents=True,exist_ok=True)
        once(base/'QUEUE_POLICY_BINDING.json',{'logical_call_id':client_request_id,'authority_ref':authority_ref,
            'original_request_sha256':hashlib.sha256(body).hexdigest(),'policy':authority['queue_policy']})
        directory,ordinal=active_directory(root,client_request_id,authority)
        effective_authority=authority_ref
        if directory!=base and ordinal==0:
            binding=json.loads((directory/'REQUEST_BINDING.json').read_bytes())
            if binding['original_request_sha256']!=hashlib.sha256(body).hexdigest():raise module.HaltBatch('QUEUE_RECOVERY_ORIGINAL_REQUEST_CHANGED')
            effective_authority=binding['authority_ref']
        fn=base_factory(native,module,directory.parent,effective_authority)
        try:return fn(api_key=api_key,body=body,client_request_id=client_request_id)
        except module.HaltBatch as error:
            if str(error)!='DURABLE_POLL_DEADLINE_WITH_RESPONSE_ID':raise
        ack=json.loads((directory/'RESPONSE_ID.json').read_bytes())
        with lock(base/'QUEUE_RECOVERY.lock'):
            operation=request or (lambda method,**kw:provider_operation(module,api_key,method,**kw))
            try:
                result=resolve_pending(module,ack,directory/'registered_queue_resolution',operation,
                    wait_limit=module.RESPONSE_TIMEOUT_SECONDS*(1+authority['queue_policy']['max_infrastructure_attempt_restarts']),now=now,sleep=sleep)
            except CancelledEmpty as error:
                proof_path=directory/'registered_queue_resolution/CANCELLED_EMPTY.json'
                current,current_ordinal=active_directory(root,client_request_id,authority)
                if current_ordinal==ordinal:
                    append(base/'QUEUE_ATTEMPTS.jsonl',{'cancelled_generation_ordinal':ordinal,'response_id':ack['response_id'],
                        'proof_ref':{'path':str(proof_path),'sha256':hashlib.sha256(proof_path.read_bytes()).hexdigest()}})
                raise
            status,headers,raw=result
            once(directory/'TERMINAL.json',{'http_status':status,'headers':headers,'raw_base64':base64.b64encode(raw).decode(),'raw_sha256':hashlib.sha256(raw).hexdigest()})
            return result
    return execute

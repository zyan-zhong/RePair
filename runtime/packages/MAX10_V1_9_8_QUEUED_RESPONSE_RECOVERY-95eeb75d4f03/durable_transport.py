"""One registered generation, durable response identity, retryable read-only retrieval."""
from pathlib import Path
from contextlib import contextmanager
import base64,hashlib,json,os,re,time

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()

def once(path,value):
    raw=canonical(value)+b'\n'
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('DURABLE_REQUEST_IDENTITY_CHANGED:'+path.name)
        return
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())

def append(path,value):
    with path.open('ab') as stream:stream.write(canonical(value)+b'\n');stream.flush();os.fsync(stream.fileno())

@contextmanager
def lock(path):
    with path.open('a+b') as stream:
        if os.name=='posix':
            import fcntl
            fcntl.flock(stream,fcntl.LOCK_EX)
        else:
            import msvcrt
            stream.seek(0);stream.write(b'0');stream.flush();stream.seek(0)
            msvcrt.locking(stream.fileno(),msvcrt.LK_LOCK,1)
        try:yield
        finally:
            if os.name=='posix':fcntl.flock(stream,fcntl.LOCK_UN)
            else:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)

def retrieve(module,*,api_key,response_id,remaining_seconds):
    # Reuse the exact P2 host, proxy, TLS defaults and no-redirect policy.
    timeout=min(float(module.CONNECT_TIMEOUT_SECONDS),remaining_seconds)
    transport=module.httpx.HTTPTransport(proxy=os.environ['https_proxy'],retries=0)
    with module.httpx.Client(transport=transport,trust_env=False,timeout=timeout,follow_redirects=False,http2=False) as client:
        response=client.get('https://'+module.API_HOST+module.API_PATH+'/'+response_id,
            headers={'Authorization':'Bearer '+api_key,'Accept':'application/json','Accept-Encoding':'identity'})
    return response.status_code,module.normalize_allowlisted_headers(dict(response.headers)),response.content

def durable_callable(native,module,root,authority_ref,*,get=None,sleep=time.sleep,clock=time.monotonic):
    """Creation retries remain the native orchestrator's responsibility and budget."""
    root=Path(root)
    def execute(*,api_key,body,client_request_id):
        if not re.fullmatch('[0-9a-f]{64}',client_request_id):raise ValueError('DURABLE_LOGICAL_ID_INVALID')
        request=json.loads(body)
        if request.get('store') is not False or 'previous_response_id' in request:raise ValueError('DURABLE_STATELESS_CONTRACT_REQUIRED')
        if request.get('background') not in (None,True):raise ValueError('DURABLE_BACKGROUND_CONFLICT')
        wire=canonical({**request,'background':True})
        directory=root/client_request_id;directory.mkdir(parents=True,exist_ok=True)
        with lock(directory/'LOCK'):
            once(directory/'REQUEST_BINDING.json',{'schema_id':'REGISTERED_DURABLE_RESPONSE_BINDING_V1',
                'logical_call_id':client_request_id,'original_request_sha256':sha(body),'wire_request_sha256':sha(wire),
                'authority_ref':authority_ref,'transport_only_added_fields':{'background':True},
                'store':False,'no_ambiguous_create_resend':True})
            once(directory/'WIRE_REQUEST.json',json.loads(wire))
            terminal=directory/'TERMINAL.json';ack_path=directory/'RESPONSE_ID.json';events=directory/'EVENTS.jsonl'
            def event(**fields):append(events,{'utc_unix':time.time(),**fields})
            def cached():
                value=json.loads(terminal.read_bytes());raw=base64.b64decode(value['raw_base64'])
                if sha(raw)!=value['raw_sha256']:raise ValueError('DURABLE_TERMINAL_HASH')
                return value['http_status'],value['headers'],raw
            def finish(status,headers,raw):
                once(terminal,{'http_status':status,'headers':headers,'raw_base64':base64.b64encode(raw).decode(),'raw_sha256':sha(raw)})
                event(kind='TERMINAL_CACHED',status=json.loads(raw).get('status'),raw_sha256=sha(raw))
                return status,headers,raw
            if terminal.exists():return cached()
            if ack_path.exists():ack=json.loads(ack_path.read_bytes())
            else:
                history=[json.loads(line) for line in events.read_bytes().splitlines()] if events.exists() else []
                if history and history[-1]['kind'] not in ('CREATE_NOT_SENT','CREATE_RETRYABLE_HTTP'):
                    raise module.HaltCaseAmbiguous('CREATION_WITHOUT_RESPONSE_ID_NO_RESEND')
                event(kind='CREATE_INTENT',wire_request_sha256=sha(wire))
                try:status,headers,raw=native(api_key=api_key,body=wire,client_request_id=client_request_id)
                except ConnectionError:
                    event(kind='CREATE_NOT_SENT');raise
                except BaseException:
                    # Preserve the unresolved intent, including a process interruption.
                    raise
                if not 200<=status<300:
                    kind='CREATE_RETRYABLE_HTTP' if status==429 or 500<=status<=599 else 'CREATE_REJECTED_HTTP'
                    event(kind=kind,http_status=status,raw_sha256=sha(raw))
                    # Original P2 bridge classifies HTTP errors under its frozen policy.
                    return status,headers,raw
                response=json.loads(raw);rid=response.get('id')
                if not isinstance(rid,str) or not re.fullmatch(r'resp_[A-Za-z0-9_-]+',rid) or response.get('model')!=request['model']:
                    raise module.HaltBatch('DURABLE_RESPONSE_IDENTITY_INVALID')
                ack={'schema_id':'REGISTERED_PROVIDER_RESPONSE_ID_V1','response_id':rid,'model':response['model'],
                    'received_utc_unix':time.time(),'creation_headers':headers,'creation_raw_sha256':sha(raw)}
                once(ack_path,ack);once(directory/'CREATE_RESPONSE.json',response)
                event(kind='RESPONSE_ID_DURABLE',response_id=rid,status=response.get('status'))
                if response.get('status') not in ('queued','in_progress'):return finish(status,headers,raw)
                if response.get('background') is not True:raise module.HaltBatch('DURABLE_BACKGROUND_NOT_ACCEPTED')
            elapsed=max(0.,time.time()-ack['received_utc_unix'])
            deadline=clock()+max(0.,float(module.RESPONSE_TIMEOUT_SECONDS)-elapsed)
            delays=tuple(module.BACKOFF_SECONDS);failure_count=0
            transient=(OSError,)
            if hasattr(module,'httpx'):transient+=(module.httpx.TransportError,)
            while clock()<deadline:
                remaining=deadline-clock()
                try:
                    fetch=get or (lambda **kw:retrieve(module,**kw))
                    status,headers,raw=fetch(api_key=api_key,response_id=ack['response_id'],remaining_seconds=remaining)
                except transient as error:
                    event(kind='RETRIEVE_RETRY',error_type=type(error).__name__,response_id=ack['response_id'])
                    failure_count+=1
                else:
                    event(kind='RETRIEVE_HTTP',http_status=status,raw_sha256=sha(raw),response_id=ack['response_id'])
                    if status==429 or 500<=status<=599:failure_count+=1
                    elif status!=200:raise module.HaltBatch('DURABLE_RETRIEVE_HTTP_'+str(status))
                    else:
                        try:
                            response=json.loads(raw)
                            if not isinstance(response,dict):raise ValueError('RESPONSE_NOT_OBJECT')
                        except (ValueError,UnicodeError):
                            event(kind='RETRIEVE_MALFORMED_RETRY',raw_sha256=sha(raw),response_id=ack['response_id'])
                            failure_count+=1
                        else:
                            if response.get('id')!=ack['response_id'] or response.get('model')!=ack['model']:
                                raise module.HaltBatch('DURABLE_RESPONSE_IDENTITY_MISMATCH')
                            if response.get('status') not in ('queued','in_progress'):return finish(status,headers,raw)
                            failure_count=0
                delay=delays[min(max(0,failure_count-1),len(delays)-1)]
                sleep(min(float(delay),max(0.,deadline-clock())))
            event(kind='POLL_DEADLINE',response_id=ack['response_id'])
            raise module.HaltBatch('DURABLE_POLL_DEADLINE_WITH_RESPONSE_ID')
    return execute

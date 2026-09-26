from pathlib import Path
from types import SimpleNamespace
import json,pytest
from queue_recovery import resolve_pending,CancelledEmpty

class Halt(RuntimeError):pass
M=SimpleNamespace(HaltBatch=Halt,RESPONSE_TIMEOUT_SECONDS=600,CONNECT_TIMEOUT_SECONDS=30,BACKOFF_SECONDS=(5,20))
ACK={'response_id':'resp_original','model':'registered','received_utc_unix':0,'creation_headers':{}}
def value(status,**extra):return {'id':'resp_original','model':'registered','status':status,'output':[],'usage':None,**extra}
def reply(v):return 200,{},json.dumps(v).encode()

def test_queued_timeout_requires_confirmed_empty_cancellation(tmp_path):
    events=[]
    def request(method,**kw):
        events.append(method)
        return reply(value('queued' if method=='GET' else 'cancelled'))
    with pytest.raises(CancelledEmpty):resolve_pending(M,ACK,tmp_path,request,wait_limit=1800,now=lambda:1400,sleep=lambda _:None)
    assert events==['GET','POST_CANCEL']
    assert json.loads((tmp_path/'CANCELLED_EMPTY.json').read_bytes())['response_id']=='resp_original'

def test_completion_wins_cancellation_race_and_is_adopted(tmp_path):
    methods=[]
    def request(method,**kw):
        methods.append(method);return reply(value('queued' if method=='GET' else 'completed',output=[] if method=='GET' else [{'text':'existing result'}]))
    assert json.loads(resolve_pending(M,ACK,tmp_path,request,wait_limit=1800,now=lambda:1400,sleep=lambda _:None)[2])['status']=='completed'
    assert not (tmp_path/'CANCELLED_EMPTY.json').exists()

@pytest.mark.parametrize('bad',[value('cancelled',output=[{'text':'partial'}]),value('cancelled',usage={'output_tokens':1}),value('queued'),value('cancelled',id='resp_other')])
def test_no_retry_without_empty_matching_cancel_terminal(tmp_path,bad):
    def request(method,**kw):return reply(value('queued') if method=='GET' else bad)
    with pytest.raises(Halt):resolve_pending(M,ACK,tmp_path,request,wait_limit=1800,now=lambda:1400,sleep=lambda _:None)
    assert not (tmp_path/'CANCELLED_EMPTY.json').exists()

def test_in_progress_is_read_only_until_completion(tmp_path):
    calls=[];clock=[610]
    def request(method,**kw):calls.append(method);return reply(value('in_progress' if len(calls)==1 else 'completed'))
    assert resolve_pending(M,ACK,tmp_path,request,wait_limit=1800,now=lambda:clock[0],sleep=lambda s:clock.__setitem__(0,clock[0]+s))[0]==200
    assert calls==['GET','GET']

def test_cancel_retry_reuses_exact_id_after_disconnect(tmp_path):
    methods=[]
    def request(method,**kw):
        methods.append((method,kw['response_id']))
        if len(methods)==2:raise OSError('cancel response lost')
        return reply(value('queued' if method=='GET' else 'cancelled'))
    with pytest.raises(CancelledEmpty):resolve_pending(M,ACK,tmp_path,request,wait_limit=1800,now=lambda:1400,sleep=lambda _:None)
    assert methods==[('GET','resp_original'),('POST_CANCEL','resp_original'),('POST_CANCEL','resp_original')]

def test_cancelled_generation_advances_once_and_new_response_is_cached(tmp_path):
    from queue_recovery import queue_callable
    cid='c'*64;root=tmp_path/cid;root.mkdir();(root/'RESPONSE_ID.json').write_text(json.dumps(ACK))
    policy={'queue_policy':{'max_infrastructure_attempt_restarts':2},'queue_recovery_target':{'logical_call_id':'f'*64}}
    body=json.dumps({'model':'registered','store':False,'input':'same evidence'}).encode();posts=[]
    def post(**kw):posts.append(kw);return reply(value('completed',id='resp_replacement'))
    def request(method,**kw):return reply(value('queued' if method=='GET' else 'cancelled'))
    fn=queue_callable(post,M,tmp_path,{},policy,request=request,sleep=lambda _:None)
    with pytest.raises(CancelledEmpty):fn(api_key='secret',body=body,client_request_id=cid)
    assert posts==[]
    for _ in range(2):assert json.loads(fn(api_key='secret',body=body,client_request_id=cid)[2])['id']=='resp_replacement'
    assert len(posts)==1
    assert len((root/'QUEUE_ATTEMPTS.jsonl').read_text().splitlines())==1

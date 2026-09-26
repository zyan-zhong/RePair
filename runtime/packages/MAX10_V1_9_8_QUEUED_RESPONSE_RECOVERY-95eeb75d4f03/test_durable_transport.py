from pathlib import Path
from types import SimpleNamespace
import json
import pytest

def transport_module():
    import durable_transport
    return durable_transport

class Ambiguous(RuntimeError): pass
class Halt(RuntimeError): pass

def fixture_module():
    return SimpleNamespace(HaltCaseAmbiguous=Ambiguous,HaltBatch=Halt,
        RESPONSE_TIMEOUT_SECONDS=600,CONNECT_TIMEOUT_SECONDS=30,BACKOFF_SECONDS=(5,20))

BODY=json.dumps({'model':'registered-model','store':False,'input':'unchanged scientific evidence'}).encode()
def reply(status='queued',rid='resp_registered'):
    return 200,{'x-request-id':'req_test'},json.dumps({'id':rid,'model':'registered-model','status':status,'background':True}).encode()

def test_one_creation_retrieves_same_response_after_connection_failure(tmp_path):
    module=transport_module();sent=[];fetched=[]
    def post(**kw):sent.append(kw);return reply()
    def get(**kw):
        fetched.append(kw['response_id'])
        if len(fetched)==1:raise OSError('temporary disconnect')
        return reply('completed')
    fn=module.durable_callable(post,fixture_module(),tmp_path,{'sha256':'a'*64},get=get,sleep=lambda _:None)
    result=fn(api_key='secret',body=BODY,client_request_id='c'*64)
    assert json.loads(result[2])['status']=='completed'
    assert len(sent)==1 and fetched==['resp_registered']*2
    assert json.loads(sent[0]['body'])=={**json.loads(BODY),'background':True}
    assert 'secret' not in ''.join(p.read_text() for p in (tmp_path/('c'*64)).iterdir() if p.is_file())

def test_reentry_after_ack_never_creates_again(tmp_path):
    module=transport_module();sent=[]
    def post(**kw):sent.append(kw);return reply()
    def interrupted(**kw):raise KeyboardInterrupt()
    fn=module.durable_callable(post,fixture_module(),tmp_path,{},get=interrupted,sleep=lambda _:None)
    with pytest.raises(KeyboardInterrupt):fn(api_key='secret',body=BODY,client_request_id='c'*64)
    fn=module.durable_callable(post,fixture_module(),tmp_path,{},get=lambda **kw:reply('completed'),sleep=lambda _:None)
    assert json.loads(fn(api_key='secret',body=BODY,client_request_id='c'*64)[2])['status']=='completed'
    assert len(sent)==1

def test_unknown_creation_is_not_resubmitted(tmp_path):
    module=transport_module();sent=[]
    def post(**kw):sent.append(kw);raise Ambiguous('RemoteProtocolError')
    fn=module.durable_callable(post,fixture_module(),tmp_path,{},sleep=lambda _:None)
    for _ in range(2):
        with pytest.raises(Ambiguous):fn(api_key='secret',body=BODY,client_request_id='c'*64)
    assert len(sent)==1

def test_proven_not_sent_can_use_native_retry_budget(tmp_path):
    module=transport_module();sent=[]
    def post(**kw):
        sent.append(kw)
        if len(sent)==1:raise ConnectionError('not sent')
        return reply('completed')
    fn=module.durable_callable(post,fixture_module(),tmp_path,{},sleep=lambda _:None)
    with pytest.raises(ConnectionError):fn(api_key='secret',body=BODY,client_request_id='c'*64)
    assert fn(api_key='secret',body=BODY,client_request_id='c'*64)[0]==200
    assert len(sent)==2

def test_changed_body_under_same_logical_id_is_blocked(tmp_path):
    module=transport_module();sent=[]
    def post(**kw):sent.append(kw);return reply('completed')
    fn=module.durable_callable(post,fixture_module(),tmp_path,{},sleep=lambda _:None)
    fn(api_key='secret',body=BODY,client_request_id='c'*64)
    with pytest.raises(ValueError,match='REQUEST_IDENTITY'):
        fn(api_key='secret',body=BODY+b' ',client_request_id='c'*64)
    assert len(sent)==1

def test_complete_response_cache_and_incomplete_are_not_regenerated(tmp_path):
    module=transport_module();sent=[]
    def post(**kw):sent.append(kw);return reply('incomplete')
    fn=module.durable_callable(post,fixture_module(),tmp_path,{},sleep=lambda _:None)
    for _ in range(2):assert json.loads(fn(api_key='secret',body=BODY,client_request_id='c'*64)[2])['status']=='incomplete'
    assert len(sent)==1

def test_wrong_retrieved_id_is_rejected(tmp_path):
    module=transport_module()
    fn=module.durable_callable(lambda **kw:reply(),fixture_module(),tmp_path,{},
        get=lambda **kw:reply('completed','resp_wrong'),sleep=lambda _:None)
    with pytest.raises(Halt,match='RESPONSE_IDENTITY'):
        fn(api_key='secret',body=BODY,client_request_id='c'*64)

def test_polling_has_frozen_deadline_and_keeps_response_id(tmp_path):
    module=transport_module();now=[0]
    def sleep(seconds):now[0]+=seconds
    fn=module.durable_callable(lambda **kw:reply(),fixture_module(),tmp_path,{},
        get=lambda **kw:reply(),sleep=sleep,clock=lambda:now[0])
    with pytest.raises(Halt,match='POLL_DEADLINE'):
        fn(api_key='secret',body=BODY,client_request_id='c'*64)
    assert now[0]<=600
    assert json.loads((tmp_path/('c'*64)/'RESPONSE_ID.json').read_text())['response_id']=='resp_registered'

def test_unrecognized_send_error_cannot_open_new_creation(tmp_path):
    module=transport_module();sent=[]
    def post(**kw):sent.append(kw);raise RuntimeError('unknown')
    fn=module.durable_callable(post,fixture_module(),tmp_path,{})
    with pytest.raises(RuntimeError):fn(api_key='secret',body=BODY,client_request_id='c'*64)
    with pytest.raises(Ambiguous):fn(api_key='secret',body=BODY,client_request_id='c'*64)
    assert len(sent)==1

def test_truncated_get_response_retries_same_id_without_another_generation(tmp_path):
    module=transport_module();sent=[];fetched=[]
    def post(**kw):sent.append(kw);return reply()
    def get(**kw):
        fetched.append(kw['response_id'])
        if len(fetched)==1:return 200,{},b'{"id":'
        if len(fetched)==2:return 200,{},b'[]'
        return reply('completed')
    fn=module.durable_callable(post,fixture_module(),tmp_path,{},get=get,sleep=lambda _:None)
    assert fn(api_key='secret',body=BODY,client_request_id='c'*64)[0]==200
    assert len(sent)==1 and fetched==['resp_registered']*3

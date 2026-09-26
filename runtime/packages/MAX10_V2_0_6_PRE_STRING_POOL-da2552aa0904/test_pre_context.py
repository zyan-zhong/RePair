from pathlib import Path
from copy import deepcopy
import json,hashlib
import pytest
import pool_context as pc

def canon(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def fixture():return json.loads(Path(__file__).with_name('PRE_REQUEST_FIXTURE.json').read_bytes())
def policy():return json.loads(Path(__file__).with_name('AUTHORITY.json').read_bytes())['pre_context_encoding_policy']
def h(v):return hashlib.sha256(canon(v)).hexdigest()

def test_current_full_request_fits_without_losing_any_projection_value():
    f=fixture();old=f['bundle'];saved=deepcopy(old)
    assert len(canon(old['provider_request']))>f['budget']
    new=pc.amend(old,policy=policy(),authority_ref={'path':'registered','sha256':'a'},hash_request=h)
    assert len(canon(new['provider_request']))<=f['budget']
    document=json.loads(new['provider_request']['input'][1]['content'][0]['text'])
    restored=pc.restore(document['projection'],document['encoding']['file_ref_roots'])
    assert canon(restored)==canon(old['input_projection'])
    assert new['input_projection']==old['input_projection'] and old==saved
    for key in ('text','model','reasoning','max_output_tokens','tools','truncation','store'):
        assert new['provider_request'][key]==old['provider_request'][key]
    assert new['request_body_sha256']==h(new['provider_request'])!=old['request_body_sha256']

def test_mixed_scalar_types_empty_records_and_nested_relations_roundtrip():
    v={'a':[{'x':False,'y':[]},{'x':0,'y':{}},{'x':0.0,'y':None}],
       'b':[{'shared':'some long repeated named constant','v':{'x':1,'k':'same'}},
            {'shared':'some long repeated named constant','v':{'x':2,'k':'same'}}],
       'c':[{},{}],'d':{'path':'/registered/owner/a.json','file_sha256':'a'*64},
       'e':{'path':'/other/owner/a.json','file_sha256':'b'*64}}
    encoded=pc.compact(v,{'campaign_owner':'/registered/owner'})
    assert canon(pc.restore(encoded,{'campaign_owner':'/registered/owner'}))==canon(v)

def test_corrupt_tables_are_rejected_instead_of_silent_row_loss():
    with pytest.raises(ValueError):
        pc.restore({'$table':{'row_count':2,'constants':{},'columns':{'x':[1]}}},{})
    with pytest.raises(ValueError):
        pc.restore({'$table':{'row_count':1,'constants':{'x':1},'columns':{'x':[2]}}},{})

def test_non_pre_calls_are_unchanged():
    old=fixture()['bundle'];old['stage_id']='X'
    assert pc.amend(old,policy=policy(),authority_ref={},hash_request=h) is old

def test_reserved_markers_in_source_are_rejected():
    with pytest.raises(ValueError):pc.compact({'$table':{'literal':'source'}},{})

def test_large_future_memory_keeps_all_prior_round_lessons_and_stays_in_budget():
    f=fixture();old=deepcopy(f['bundle']);memory=old['input_projection']['blind_input']['prior_closed_round_research_memory']
    # Stress inherited closed-round context, not sampling or truncating it.
    memory['lessons']=memory['lessons']*5
    old['provider_request']['input'][1]['content'][0]['text']=canon(old['input_projection']).decode()
    new=pc.amend(old,policy=policy(),authority_ref={},hash_request=h)
    assert len(canon(new['provider_request']))<=f['budget']
    doc=json.loads(new['provider_request']['input'][1]['content'][0]['text'])
    assert canon(pc.restore(doc['projection'],doc['encoding']['file_ref_roots']))==canon(old['input_projection'])

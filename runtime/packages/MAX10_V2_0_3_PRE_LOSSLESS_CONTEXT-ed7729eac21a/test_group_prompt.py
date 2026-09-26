from copy import deepcopy
from types import SimpleNamespace
import hashlib,json
import pytest
import group_prompt as gp
from types import ModuleType
import sys

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def bundle(stage='G-A2'):
    request={'input':[{'role':'system','content':[{'type':'input_text','text':'original group contract'}]},
        {'role':'user','content':[{'type':'input_text','text':'frozen evidence and memory'}]}],
        'model':'registered-model','max_output_tokens':16384,'text':{'format':{'schema':{'required':['existing']}}}}
    return {'stage_id':stage,'provider_request':request,'request_body_sha256':digest(request),
        'input_projection':{'memory':'OFF' if stage=='G-A2' else 'registered-memory'},
        'input_projection_sha256':'p','runtime_manifest_sha256':'r','stage_spec':{'unchanged':True}}

@pytest.mark.parametrize('stage',['G-A2','G-A3'])
def test_only_system_guidance_changes_and_identity_rehashes(stage):
    old=bundle(stage);saved=deepcopy(old)
    new=gp.amend(old,authority_ref={'path':'registered','sha256':'a'},hash_request=digest)
    assert old==saved
    assert new['request_body_sha256']==digest(new['provider_request'])!=old['request_body_sha256']
    assert new['input_projection']==old['input_projection']
    assert new['provider_request']['input'][1:]==old['provider_request']['input'][1:]
    for key in ['model','max_output_tokens','text']:
        assert new['provider_request'][key]==old['provider_request'][key]
    assert new['provider_request']['input'][0]['content'][0]['text'].startswith('original group contract')
    assert 'single action is sufficient' in new['provider_request']['input'][0]['content'][0]['text']
    assert new['registered_group_prompt_amendment']['base_request_body_sha256']==old['request_body_sha256']

@pytest.mark.parametrize('stage',['L-A0','L-A1','C','R-PRE-PRIMARY-V2','R-POST-PRIMARY-V1'])
def test_unrelated_stages_are_exactly_unchanged(stage):
    old=bundle(stage);assert gp.amend(old,authority_ref={},hash_request=digest) is old

def test_amendment_is_idempotent_and_rejects_authority_drift():
    a={'path':'registered','sha256':'a'}
    value=gp.amend(bundle(),authority_ref=a,hash_request=digest)
    assert gp.amend(value,authority_ref=a,hash_request=digest)==value
    with pytest.raises(ValueError,match='AUTHORITY'):
        gp.amend(value,authority_ref={'sha256':'b'},hash_request=digest)

def test_all_rendering_routes_match_and_restore_on_failure():
    original=lambda **kw:bundle(kw['stage_id'])
    core=SimpleNamespace(api={'render_stage_request':original},rr=SimpleNamespace(render_stage_request=original),
        orch=SimpleNamespace(render_stage_request=original),runner=SimpleNamespace(render_stage_request=original),
        domain_hash=lambda domain,value:digest(value))
    with pytest.raises(RuntimeError):
        with gp.rendering_scope(core,{'path':'registered','sha256':'a'}):
            values=[fn(stage_id='G-A2') for fn in (core.api['render_stage_request'],core.rr.render_stage_request,
                core.orch.render_stage_request,core.runner.render_stage_request)]
            assert all(v==values[0] for v in values)
            assert values[0]['request_body_sha256']!=original(stage_id='G-A2')['request_body_sha256']
            raise RuntimeError('exit')
    assert all(fn is original for fn in (core.api['render_stage_request'],core.rr.render_stage_request,
        core.orch.render_stage_request,core.runner.render_stage_request))

@pytest.mark.parametrize('round_index,sha,enabled',[(3,'prior',False),(4,'current',True),(4,'mechanical-retry',True),(5,'next',True)])
def test_registered_round_scope_and_retry(monkeypatch,tmp_path,round_index,sha,enabled):
    adapter=ModuleType('adapter');exact=ModuleType('exact_bindings');calls=[]
    original=lambda **kw:bundle(kw['stage_id'])
    core=SimpleNamespace(api={'render_stage_request':original},rr=SimpleNamespace(render_stage_request=original),
        orch=SimpleNamespace(render_stage_request=original),runner=SimpleNamespace(render_stage_request=original),
        domain_hash=lambda domain,value:digest(value))
    adapter.run_group_tail=lambda binding,values,core,prepared,accesses,out:core.api['render_stage_request'](stage_id='G-A2')
    native=adapter.run_group_tail
    request={'request_sha256':sha,'round_id':'r'+str(round_index)}
    docs={'frozen-index':{'round_index':4,'request':{'path':'first-request'}},
        'first-request':{'request_sha256':'current','round_id':'r4'},'request':request}
    exact.read_ref=lambda ref:deepcopy(docs[ref['path']])
    exact.immutable_json=lambda path,value:calls.append((str(path),value))
    monkeypatch.setitem(sys.modules,'adapter',adapter);monkeypatch.setitem(sys.modules,'exact_bindings',exact)
    (tmp_path/'AUTHORITY.json').write_text('{}');(tmp_path/'request_bindings').mkdir()
    (tmp_path/'request_bindings'/(sha+'.json')).write_text(json.dumps({'round_index':round_index,'request':{'path':'request'}}))
    a={'owner_root':str(tmp_path),'group_prompt_activation':{'round_index':4,'request_sha256':'current','index_ref':{'path':'frozen-index'}}}
    with gp.installed(a,'manifest',tmp_path):
        value=adapter.run_group_tail({'refs':{'request':{'path':'request'}}},{},core,[],{},tmp_path)
    assert ('registered_group_prompt_amendment' in value)==enabled
    assert len(calls)==(2 if enabled else 1)
    assert adapter.run_group_tail is native

def test_real_historical_request_fixtures_preserve_contracts():
    from pathlib import Path
    path=Path(__file__).with_name('GROUP_REQUEST_FIXTURES.json')
    assert path.exists(),'Registered historical fixtures required'
    for row in json.loads(path.read_bytes()):
        old=row['bundle'];new=gp.amend(old,authority_ref={'path':'authority','sha256':'sha'},hash_request=digest)
        if old['stage_id'] in ('G-A2','G-A3','X'):
            assert new['provider_request']['text']==old['provider_request']['text']
            assert new['input_projection']==old['input_projection']
            assert new['provider_request']['input'][1:]==old['provider_request']['input'][1:]
        else:assert new is old

def test_guidance_only_names_existing_schema_fields():
    from pathlib import Path
    rows=json.loads(Path(__file__).with_name('GROUP_REQUEST_FIXTURES.json').read_bytes())
    for row in rows[:2]:
        schema=row['bundle']['provider_request']['text']['format']['schema']
        fields=schema['properties']['mechanism_hypotheses']['items']['properties']
        assert 'statement' in fields and 'uncertainty' in fields
        assert 'mechanism_hypotheses[].statement' in gp.GUIDANCE
        assert 'mechanism_hypothesis field' not in gp.GUIDANCE

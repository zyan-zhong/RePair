from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
import json,hashlib,pytest
from repair_feedback import amend,group_scope,WorkerDispatch,eligible
from trajectory_facts import project,history_summary,researcher_summary,canonical
import pre_context
from repair_guidance import PRE_GUIDANCE

ROOT=Path(__file__).parent
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()

def test_native_group_fixtures_keep_schema_data_and_all_aliases_equal():
    for f in json.loads((ROOT/'GROUP_REQUEST_FIXTURES.json').read_bytes()):
        old=f['bundle'];native=lambda **kw:deepcopy(old)
        core=SimpleNamespace(api={'render_stage_request':native},rr=SimpleNamespace(render_stage_request=native),
            orch=SimpleNamespace(render_stage_request=native),runner=SimpleNamespace(render_stage_request=native),domain_hash=lambda _,v:digest(v))
        with group_scope(core):
            values=[fn(stage_id=old['stage_id']) for fn in [core.api['render_stage_request'],core.rr.render_stage_request,core.orch.render_stage_request,core.runner.render_stage_request]]
            assert all(v==values[0] for v in values)
            new=values[0]
            assert new['input_projection']==old['input_projection']
            assert new['provider_request']['text']==old['provider_request']['text']
            assert new['provider_request']['input'][1:]==old['provider_request']['input'][1:]
            assert amend(new,digest)==new

def test_l_and_c_are_unchanged():
    for stage in ('L-A0','L-A1','C'):
        v={'stage_id':stage};assert amend(v,digest) is v

def test_current_pre_with_all_closed_round_facts_fits_losslessly():
    f=json.loads((ROOT/'PRE_REQUEST_FIXTURE.json').read_bytes());b=f['bundle']
    facts=[history_summary(project(r['verifier'])) for r in json.loads((ROOT/'TRAJECTORY_FIXTURES.json').read_bytes())]
    b['input_projection']['blind_input']['prior_closed_round_trajectory_facts']={'rounds':facts}
    b['provider_request']['input'][0]['content'][0]['text']+=PRE_GUIDANCE
    a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    v=pre_context.amend(b,policy=a['pre_context_encoding_policy'],authority_ref={},hash_request=digest)
    assert len(canonical(v['provider_request']).encode())<=f['budget']
    doc=json.loads(v['provider_request']['input'][1]['content'][0]['text'])
    assert pre_context.restore(doc['projection'],doc['encoding']['file_ref_roots'])==b['input_projection']

def test_aggregates_cover_all_seeds_and_keep_failure_evidence():
    fs=json.loads((ROOT/'TRAJECTORY_FIXTURES.json').read_bytes())
    for f in fs:
        facts=project(f['verifier']);h=history_summary(facts)
        assert sum(r['branch_count'] for r in h['state_arm_aggregates'])==facts['branch_count']
    r3=history_summary(project(fs[2]['verifier']))
    assert any(r['maximum_consecutive_action_runs'].get('cool egg 2 with fridge 1')==25 for r in r3['state_arm_aggregates'])
    assert any(r['inadmissible_parsed_action_totals'].get('move cd 1 to dresser 1')==15 for r in r3['state_arm_aggregates'])

def test_worker_only_replaces_exact_registered_bridge():
    seen=[];record=[];native=SimpleNamespace(run=lambda argv,**kw:seen.append(argv))
    proxy=WorkerDispatch(native,'/registered/recipe_worker.py','/registered/feedback_worker.py',record.append)
    argv=['python','-B','/registered/recipe_worker.py','--request','/registered/request.json']
    proxy.run(argv,check=False)
    assert argv[2]=='/registered/recipe_worker.py' and seen[0][2]=='/registered/feedback_worker.py'
    assert record==['/registered/request.json']
    with pytest.raises(ValueError):proxy.run(['python','arbitrary.py'])

def test_activation_uses_registered_round_index_and_rejects_sha_drift(tmp_path):
    request={'request_sha256':'req','round_id':'round'};raw=json.dumps(request).encode();p=tmp_path/'request.json';p.write_bytes(raw)
    ref={'path':str(p),'sha256':hashlib.sha256(raw).hexdigest()};(tmp_path/'request_bindings').mkdir()
    a={'owner_root':str(tmp_path),'repair_activation':{'round_index':5}};binding={'refs':{'request':ref}}
    for index,active in [(4,False),(5,True),(6,True)]:
        (tmp_path/'request_bindings/req.json').write_text(json.dumps({'round_index':index,'request':ref}))
        assert eligible(a,binding)==active
    p.write_text('{}')
    with pytest.raises(ValueError):eligible(a,binding)

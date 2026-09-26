from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import importlib.util,json,hashlib
import pytest
import group_prompt as gp

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def fixtures():return [r['bundle'] for r in json.loads(Path(__file__).with_name('GROUP_REQUEST_FIXTURES.json').read_bytes())]

def test_x_amendment_changes_only_system_and_rehashes_real_request():
    old=next(b for b in fixtures() if b['stage_id']=='X');saved=deepcopy(old)
    new=gp.amend(old,authority_ref={'path':'registered','sha256':'a'},hash_request=digest)
    assert new['provider_request']!=old['provider_request']
    restored=deepcopy(new['provider_request']);restored['input'][0]=old['provider_request']['input'][0]
    assert restored==old['provider_request']
    assert new['request_body_sha256']==digest(new['provider_request'])!=old['request_body_sha256']
    for key in ('input_projection','input_projection_sha256','stage_spec','runtime_manifest_sha256'):
        assert new[key]==old[key]
    assert old==saved
    assert gp.amend(new,authority_ref={'path':'registered','sha256':'a'},hash_request=digest)==new
    with pytest.raises(ValueError,match='AUTHORITY'):
        gp.amend(new,authority_ref={'path':'changed'},hash_request=digest)

def test_x_all_identity_and_execution_routes_agree():
    old=next(b for b in fixtures() if b['stage_id']=='X')
    original=lambda **kw:deepcopy(old)
    core=SimpleNamespace(api={'render_stage_request':original},rr=SimpleNamespace(render_stage_request=original),
        orch=SimpleNamespace(render_stage_request=original),runner=SimpleNamespace(render_stage_request=original),
        domain_hash=lambda domain,v:digest(v))
    with gp.rendering_scope(core,{'path':'registered','sha256':'a'}):
        values=[fn(stage_id='X') for fn in (core.api['render_stage_request'],core.rr.render_stage_request,
            core.orch.render_stage_request,core.runner.render_stage_request)]
        assert values[0]['request_body_sha256']!=old['request_body_sha256']
        assert all(v==values[0] for v in values)
    assert core.api['render_stage_request'] is original

def test_completed_g_and_c_keep_request_identity_against_frozen_previous_source():
    spec=importlib.util.spec_from_file_location('_previous_prompt',Path(__file__).with_name('PREVIOUS_GROUP_PROMPT.py'))
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    for old in fixtures():
        if old['stage_id']=='X':continue
        before=prior.amend(old,authority_ref={},hash_request=digest)
        after=gp.amend(old,authority_ref={},hash_request=digest)
        assert after==before

import copy,json
from pathlib import Path
import pytest
from condition_contract import resolve_condition

def fixture():
    d=json.loads(Path(__file__).with_name('CURRENT_FIXTURE.json').read_bytes())
    return d['binding'],d['request']['value'],d['runtime']['value'],d['profile']['value']

def resolve(values):
    binding,request,runtime,profile=values
    accepted={k:binding[k] for k in ('parent_policy_id','round_id')}
    return resolve_condition(binding,request,runtime,profile,accepted,None)

def test_current_promoted_parent_is_valid_source_condition():
    v=fixture()
    assert resolve(v)==v[0]['parent_policy_id']+'::'+v[2]['continuation_request_contract']['profile_id']

def test_next_promoted_parent_and_round_are_derived_from_current_binding():
    b,r,t,p=fixture();new='policy-with-another-registered-adapter';rid='independent-next-round'
    b['parent_policy_id']=r['parent_policy_id']=t['policy_id']=p['policy_version']=new
    b['round_id']=r['round_id']=rid;t['served_model_name']=p['served_model_name']='new-runtime-alias'
    assert resolve((b,r,t,p))==new+'::'+t['continuation_request_contract']['profile_id']

@pytest.mark.parametrize('field',['policy_id','policy_runtime_manifest_sha256','adapter_bundle_sha256'])
def test_trained_parent_identity_drift_is_rejected(field):
    v=fixture();v[2][field]='foreign-identity'
    with pytest.raises(ValueError):resolve(v)

def test_unknown_runtime_schema_is_rejected():
    v=fixture();v[2]['schema_id']='UNKNOWN_RUNTIME'
    with pytest.raises(ValueError):resolve(v)

def test_profile_schema_is_still_required():
    v=fixture();v[3]['schema_id']='UNKNOWN_PROFILE'
    with pytest.raises(ValueError):resolve(v)

def test_trained_runtime_version_is_required():
    v=fixture();v[2]['schema_version']=99
    with pytest.raises(ValueError):resolve(v)

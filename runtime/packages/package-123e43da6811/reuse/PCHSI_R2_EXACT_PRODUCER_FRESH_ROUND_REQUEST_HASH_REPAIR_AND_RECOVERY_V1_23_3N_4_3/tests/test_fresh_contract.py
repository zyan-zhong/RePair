import hashlib, json, sys
from pathlib import Path
from dataclasses import dataclass
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'producer'))

def contract():
    assert (ROOT/'producer/fresh_round_contract.py').is_file(), 'fresh request/schedule binder missing'
    import fresh_round_contract as c
    return c

def fixture(tmp_path):
    c=contract()
    runtime={'policy_runtime_manifest_sha256':'a'*64}
    memory={'active_snapshot_sha256':'b'*64}
    rp=tmp_path/'runtime.json';rp.write_text(json.dumps(runtime))
    mp=tmp_path/'memory.json';mp.write_text(json.dumps(memory))
    profile={'profile_kind':'PROFILE','policy_version':'parent','arm_id':'I1'}
    binding={'round_id':'OLD_ROUND','parent_policy_id':'parent',
        'train_update_authority':{'manifest_sha256':'c'*64,'rollout_seed':3},
        'runtime_authority':{'runtime_binding_file_sha256':c.sha_file(rp)},
        'memory_authority':{'runtime_identity_file_sha256':c.sha_file(mp),'active_snapshot_sha256':'b'*64,'token_budget_contract_sha256':'d'*64}}
    request={'round_id':'NEW_ROUND','parent_policy_id':'parent','parent_policy_artifact_sha256':'a'*64,
        'policy_runtime_binding_sha256':c.sha_file(rp),'round_memory_runtime_authority_sha256':c.sha_file(mp),
        'round_start_memory_snapshot_sha256':'b'*64,'token_budget_contract_sha256':'d'*64,
        'train_update_manifest_sha256':'c'*64,'rollout_seed':3,
        'execution_profile_sha256':hashlib.sha256(c.canonical_bytes(profile)).hexdigest()}
    return c,request,binding,rp,mp,profile

def test_current_round_differs_without_mutating_archived_binding(tmp_path):
    c,r,b,rp,mp,p=fixture(tmp_path); before=json.dumps(b,sort_keys=True)
    c.validate_request_against_capsule(r,b,rp,mp,p)
    assert b['round_id']=='OLD_ROUND' and json.dumps(b,sort_keys=True)==before

@pytest.mark.parametrize('field',['parent_policy_id','parent_policy_artifact_sha256','policy_runtime_binding_sha256','round_memory_runtime_authority_sha256','round_start_memory_snapshot_sha256','token_budget_contract_sha256','train_update_manifest_sha256','rollout_seed','execution_profile_sha256'])
def test_mismatched_resource_authority_never_rebound(tmp_path,field):
    c,r,b,rp,mp,p=fixture(tmp_path);r[field]='different'
    with pytest.raises((ValueError,RuntimeError)):c.validate_request_against_capsule(r,b,rp,mp,p)

@pytest.mark.parametrize('ordinal',[-1,False,1.5,'0'])
def test_invalid_attempt_ordinal_rejected(ordinal):
    with pytest.raises(ValueError):contract().validate_attempt_ordinal(ordinal)

def test_exact_request_uses_native_class_and_detects_bad_hash(tmp_path,monkeypatch):
    c=contract()
    # Use the actual exported, dependency-free production request class.
    spec=importlib.util.spec_from_file_location('request_fixture',ROOT/'tests/fixtures/rollout_collection.py')
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    c.REQUEST_CLASS_FOR_TEST=m.RoundRolloutCollectionRequestV1
    kwargs={'round_id':'ROUND_X','execution_attempt_id':'exec-x','parent_policy_id':'parent',
       'execution_namespace':'exec-x','rollout_seed':3}
    for k in ('parent_policy_artifact_sha256','policy_runtime_binding_sha256','execution_profile_sha256','train_update_manifest_sha256','round_memory_runtime_authority_sha256','round_start_memory_snapshot_sha256','token_budget_contract_sha256'):kwargs[k]='a'*64
    req=m.RoundRolloutCollectionRequestV1(**kwargs).to_dict();path=tmp_path/'request.json';path.write_text(json.dumps(req))
    try:
        loaded=c.load_current_request(path,request_type=m.RoundRolloutCollectionRequestV1)
        assert loaded.to_dict()==req
        req['round_id']='tampered';path.write_text(json.dumps(req))
        with pytest.raises(ValueError):c.load_current_request(path,request_type=m.RoundRolloutCollectionRequestV1)
    finally:del c.REQUEST_CLASS_FOR_TEST

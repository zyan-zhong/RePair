import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from entry.source_recovery import select_owner
from rollout_adapter.materializer import canonical,put,ref,obj


def fixture(tmp_path,monkeypatch):
    from entry import rollout_recovery
    monkeypatch.setattr(rollout_recovery,'inspect_invalid',lambda *a:{'retry_class':'SAFE_LOCAL_RESOURCE_ISOLATION'})
    monkeypatch.setattr(rollout_recovery,'prove_inactive',lambda *a:{'all_registered_shards_terminal':True})
    package=tmp_path/'package';formal=tmp_path/'formal';base=formal/'campaign_owner'
    old=base/'source_recoveries'/('a'*64);initial={'request_sha256':'b'*64};authority={'restarts':2}
    files={'original_delegation':(base/'PRE_SUBMIT_SOURCE_RECOVERY.json',{'successor_owner_root':str(old)}),
        'owner_binding':(old/'OWNER_BINDING.json',{'initial':initial,'authority':authority,'native_driver_source_sha256':'a'*64}),
        'intent':(old/'attempts/000001/INTENT.json',{'start':initial}),
        'manifest':(old/'attempts/000001/rollout/MATERIALIZED_ROLLOUT.json',{'root':str(old/'attempts/000001/rollout')}),
        'submission':(old/'attempts/000001/rollout/SUBMISSION_RECEIPT.json',{}),
        'terminal':(old/'attempts/000001/rollout/round_evidence/PCHSI_V1232K_GLOBAL_TERMINAL_V1.json',{}),
        'handoff':(old/'attempts/000001/rollout/round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json',{})}
    for path,value in files.values():put(path,canonical(value))
    terminal_ref=ref(files['terminal'][0]);files['failure']=(old/'attempts/000001/rollout/RESIDENT_ROLLOUT_OPERATIONAL_STOP.json',{'status':'SCIENTIFIC_ROLLOUT_INVALID','terminal':terminal_ref})
    put(files['failure'][0],canonical(files['failure'][1]))
    proof={'schema_id':'FORMAL_POST_SUBMIT_INVALID_ROLLOUT_SOURCE_RECOVERY_V1',
        'predecessor_owner_root':str(old),'predecessor_source_sha256':'a'*64,
        'initial_request_sha256':initial['request_sha256'],'refs':{k:ref(p) for k,(p,_) in files.items()}}
    put(package/'authority/POST_SUBMIT_SOURCE_RECOVERY_V1.json',canonical(proof))
    return dict(bundle_root=package,formal_root=formal,initial=initial,authority=authority,
                entry_source_sha256='c'*64),old,files


def test_delegation_preserves_failure_and_does_not_reset_budget(tmp_path,monkeypatch):
    args,old,files=fixture(tmp_path,monkeypatch);before={str(p):p.read_bytes() for p,_ in files.values()}
    result=select_owner(**args,publish=True)
    assert result==old/'source_recoveries'/('c'*64)
    assert select_owner(**args,publish=True)==result
    value=obj(ref(old/'POST_SUBMIT_SOURCE_RECOVERY.json'))
    assert value['invalid_attempt_adopted_before_reentry'] and not value['recovery_budget_reset']
    assert all(Path(p).read_bytes()==v for p,v in before.items())
    with pytest.raises(ValueError,match='ANOTHER_SOURCE'):
        select_owner(**{**args,'entry_source_sha256':'d'*64},publish=True)


@pytest.mark.parametrize('trace',['transitions','attempts/000002','attempts/000001/analyzer','attempts/000001/training','attempts/000001/RESULT.json'])
def test_scientific_progress_cannot_be_restarted(tmp_path,monkeypatch,trace):
    args,old,_=fixture(tmp_path,monkeypatch);p=old/trace;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'{}')
    with pytest.raises(ValueError,match='PROGRESS_PRESENT'):select_owner(**args)


def test_inactive_failure_not_assumed(tmp_path,monkeypatch):
    args,old,_=fixture(tmp_path,monkeypatch)
    from entry import rollout_recovery
    def active(*a):raise ValueError('ARRAY_ACTIVE')
    monkeypatch.setattr(rollout_recovery,'prove_inactive',active)
    with pytest.raises(ValueError,match='ARRAY_ACTIVE'):select_owner(**args,publish=True)
    assert not (old/'POST_SUBMIT_SOURCE_RECOVERY.json').exists()

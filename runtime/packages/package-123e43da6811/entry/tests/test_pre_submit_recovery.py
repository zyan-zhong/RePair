from pathlib import Path
import hashlib
import json
import os
import sys
import pytest

PACKAGE=Path(os.environ.get('PCHSI_TEST_PACKAGE_ROOT',Path(__file__).resolve().parents[2]))
sys.path.insert(0,str(PACKAGE))
from entry.pre_submit_recovery import select_owner


def fixture(tmp_path):
    package=tmp_path/'package';formal=tmp_path/'formal';old=formal/'campaign_owner'
    initial={'request_sha256':'a'*64,'round_id':'r1','parent_policy_id':'parent'}
    authority={'max_valid_rounds':10}
    def write(path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(value).encode();path.write_bytes(raw)
        return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()}
    binding={'initial':initial,'authority':authority,'native_driver_source_sha256':'b'*64}
    values={'owner_binding':('OWNER_BINDING.json',binding),
        'intent':('attempts/000001/INTENT.json',{'start':initial,'native_driver_source_sha256':'b'*64}),
        'materialization':('attempts/000001/rollout/MATERIALIZED_ROLLOUT.json',{'request_sha256':'a'*64,'root':str(old/'attempts/000001/rollout')}),
        'failure':('attempts/000001/rollout/RESIDENT_ROLLOUT_OPERATIONAL_STOP.json',{'status':'NATIVE_PREFLIGHT_FAILED','preflight':{'returncode':1}})}
    proof={'schema_id':'FORMAL_PRE_SUBMIT_SOURCE_RECOVERY_V1','predecessor_owner_root':str(old),
        'predecessor_source_sha256':'b'*64,'request_sha256':'a'*64,
        'refs':{k:write(old/p,v) for k,(p,v) in values.items()}}
    write(package/'authority/PRE_SUBMIT_SOURCE_RECOVERY_V1.json',proof)
    args=dict(bundle_root=package,formal_root=formal,initial=initial,authority=authority,entry_source_sha256='c'*64)
    return args,old,proof


def test_valid_recovery_reuses_request_and_preserves_old_bytes(tmp_path):
    args,old,proof=fixture(tmp_path)
    before={r['path']:Path(r['path']).read_bytes() for r in proof['refs'].values()}
    assert select_owner(**args)==old/'source_recoveries'/('c'*64)
    assert select_owner(**args)==select_owner(**args)
    assert before=={p:Path(p).read_bytes() for p in before}
    assert not (old/'PRE_SUBMIT_SOURCE_RECOVERY.json').exists()


@pytest.mark.parametrize('trace',['SUBMISSION_INTENT.json','SUBMISSION_ATTEMPT.json','SUBMISSION_RECEIPT.json','GATE_RELEASE_INTENT.json','GATE_RELEASE_RECEIPT.json','round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json','round_evidence/PCHSI_V1232K_GLOBAL_TERMINAL_V1.json'])
def test_submission_trace_prevents_restart(tmp_path,trace):
    args,old,_=fixture(tmp_path);p=old/'attempts/000001/rollout'/trace
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'{}')
    with pytest.raises(ValueError,match='EXECUTION_TRACE'):select_owner(**args)


@pytest.mark.parametrize('trace',['CAMPAIGN_TERMINAL.json','transitions','attempts/000001/RESULT.json','attempts/000001/DRIVER_ROUND_RESULT.json','attempts/000001/analyzer','attempts/000001/training','attempts/000001/offoff'])
def test_scientific_progress_prevents_restart(tmp_path,trace):
    args,old,_=fixture(tmp_path);p=old/trace
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'{}')
    with pytest.raises(ValueError,match='EXECUTION_TRACE'):select_owner(**args)


def test_tampered_predecessor_rejected(tmp_path):
    args,old,_=fixture(tmp_path);(old/'OWNER_BINDING.json').write_bytes(b'{}')
    with pytest.raises(ValueError,match='REF_CHANGED'):select_owner(**args)


def test_changed_request_rejected(tmp_path):
    args,old,_=fixture(tmp_path);args['initial']=dict(args['initial'],parent_policy_id='other')
    with pytest.raises(ValueError,match='IDENTITY_OR_FAILURE'):select_owner(**args)


def test_other_attempt_rejected(tmp_path):
    args,old,_=fixture(tmp_path);(old/'attempts/000002').mkdir()
    with pytest.raises(ValueError,match='UNEXPECTED_ATTEMPT'):select_owner(**args)


@pytest.mark.parametrize('rc',[None,True,False,'1',0])
def test_invalid_failure_code_rejected(tmp_path,rc):
    args,old,proof=fixture(tmp_path)
    r=proof['refs']['failure'];p=Path(r['path']);value=json.loads(p.read_bytes())
    value['preflight']['returncode']=rc
    raw=json.dumps(value).encode();p.write_bytes(raw);r['sha256']=hashlib.sha256(raw).hexdigest()
    (args['bundle_root']/'authority/PRE_SUBMIT_SOURCE_RECOVERY_V1.json').write_text(json.dumps(proof))
    with pytest.raises(ValueError,match='IDENTITY_OR_FAILURE'):select_owner(**args)


@pytest.mark.skipif(sys.platform=='win32',reason='Windows symlinks may need extra privilege')
def test_successor_alias_rejected(tmp_path):
    args,old,proof=fixture(tmp_path);other=tmp_path/'elsewhere';other.mkdir()
    (old/'source_recoveries').symlink_to(other,target_is_directory=True)
    with pytest.raises(ValueError,match='ALIAS_FORBIDDEN'):select_owner(**args,publish=True)


@pytest.mark.skipif(sys.platform=='win32',reason='native resident uses Linux flock')
def test_shared_lock_and_immutable_unique_delegation(tmp_path):
    from entry.campaign_owner import campaign_lock,EntryError
    args,old,proof=fixture(tmp_path)
    with campaign_lock(old):
        successor=select_owner(**args,publish=True)
        with campaign_lock(successor):
            with pytest.raises(EntryError,match='WRITER_ALREADY_ACTIVE'):
                with campaign_lock(old):pass
            assert select_owner(**args,publish=True)==successor
            with pytest.raises(ValueError,match='ANOTHER_SOURCE'):
                select_owner(**dict(args,entry_source_sha256='d'*64),publish=True)
    assert (old/'PRE_SUBMIT_SOURCE_RECOVERY.json').is_file()

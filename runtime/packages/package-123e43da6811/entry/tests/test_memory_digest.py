"""The registered Memory contract uses a domain-separated semantic digest."""
from pathlib import Path
import hashlib
import json
import os
import sys
import types
import pytest

PACKAGE=Path(os.environ.get('PCHSI_TEST_PACKAGE_ROOT',Path(__file__).resolve().parents[2]))
NATIVE=Path(os.environ.get('PCHSI_NATIVE_FIXTURE',PACKAGE/'native_bba_full'))
sys.path.insert(0,str(NATIVE/'src'))
sys.path.insert(0,str(PACKAGE))
from rollout_adapter.materializer import EXACT_RESOLVER
from pchsi.memory.token_budget_contract import FailureMemoryTokenBudgetContractV1
import pchsi.memory.dev_snapshot_loader as loader


def fixture(tmp_path,monkeypatch):
    safe=types.ModuleType('safe_io')
    safe.load_json=lambda p:json.loads(Path(p).read_bytes())
    safe.sha_file=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    monkeypatch.setitem(sys.modules,'safe_io',safe)
    namespace={};exec(compile(EXACT_RESOLVER,'exact_inputs.py','exec'),namespace)
    source=NATIVE/'configs/memory/failure_memory_token_budget_contract_v1.json'
    contract=tmp_path/'contract.json';contract.write_bytes(source.read_bytes())
    semantic=FailureMemoryTokenBudgetContractV1.from_json(contract.read_bytes()).contract_sha256
    assert safe.sha_file(contract)!=semantic
    value={'token_budget_contract_path':str(contract),'token_budget_contract_sha256':semantic,
           'active_snapshot_directory':str(tmp_path/'snapshot'),'active_snapshot_sha256':'a'*64}
    for role in ('formal_b_result','source_runtime_binding'):
        p=tmp_path/(role+'.json');p.write_bytes(b'{}')
        value[role+'_path']=str(p);value[role+'_sha256']=safe.sha_file(p)
    calls=[]
    def native_contract_check(**kwargs):
        p=kwargs['token_budget_contract_path']
        if p.is_symlink() or not p.is_file():raise ValueError('invalid contract path')
        parsed=FailureMemoryTokenBudgetContractV1.from_json(p.read_bytes())
        if parsed.contract_sha256!=kwargs['expected_token_budget_contract_sha256']:
            raise ValueError('native semantic mismatch')
        calls.append(kwargs)
    monkeypatch.setattr(loader,'load_calibrated_dev_snapshot_v2',native_contract_check)
    authority=tmp_path/'memory.json'
    def run():
        authority.write_text(json.dumps(value),encoding='utf8')
        namespace['validate_memory_references'](authority)
    return run,value,contract,calls


def test_semantic_contract_is_delegated_to_original_loader(tmp_path,monkeypatch):
    run,value,contract,calls=fixture(tmp_path,monkeypatch)
    run()
    assert len(calls)==1
    assert calls[0]['expected_snapshot_sha256']==value['active_snapshot_sha256']
    assert calls[0]['expected_token_budget_contract_sha256']==value['token_budget_contract_sha256']


@pytest.mark.parametrize('mode',['semantic_identity','contract_payload','missing_contract','formal_b_result','source_runtime_binding'])
def test_invalid_memory_still_rejected(tmp_path,monkeypatch,mode):
    run,value,contract,calls=fixture(tmp_path,monkeypatch)
    if mode=='semantic_identity':value['token_budget_contract_sha256']='b'*64
    elif mode=='contract_payload':
        obj=json.loads(contract.read_bytes());obj['analyzer_model']+='changed'
        contract.write_text(json.dumps(obj),encoding='utf8')
    elif mode=='missing_contract':contract.unlink()
    else:Path(value[mode+'_path']).write_bytes(b'{"changed":true}')
    with pytest.raises((ValueError,FileNotFoundError)):run()
    assert calls==[]

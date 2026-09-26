from types import SimpleNamespace
import pytest
from budget_bridge import budgeted_builder, contract_identity

def test_budget_is_taken_from_registered_contract_and_validates_tokenizer():
    calls=[]
    native=lambda **kw:calls.append(kw) or kw
    tok=SimpleNamespace(tokenizer_id='t',tokenizer_revision='r')
    contract=SimpleNamespace(single_record_hard_ceiling=777,tokenizer_id='t',tokenizer_revision='r')
    wrapped=budgeted_builder(native,contract)
    assert wrapped(tokenizer=tok,hard_ceiling=256,record='unaltered')['hard_ceiling']==777
    assert calls[0]['record']=='unaltered'
    with pytest.raises(ValueError,match='TOKENIZER'):
        wrapped(tokenizer=SimpleNamespace(tokenizer_id='wrong',tokenizer_revision='r'),hard_ceiling=256)

def test_contract_identity_rejects_runtime_drift():
    c=SimpleNamespace(contract_sha256='registered')
    assert contract_identity(c,{'token_budget_contract_sha256':'registered'})
    with pytest.raises(ValueError,match='CONTRACT'):
        contract_identity(c,{'token_budget_contract_sha256':'different'})

def test_original_budget_builder_errors_remain_visible():
    def native(**kw):raise RuntimeError('SOURCE_INVALID')
    c=SimpleNamespace(single_record_hard_ceiling=888,tokenizer_id='t',tokenizer_revision='r')
    with pytest.raises(RuntimeError,match='SOURCE_INVALID'):
        budgeted_builder(native,c)(tokenizer=SimpleNamespace(tokenizer_id='t',tokenizer_revision='r'))

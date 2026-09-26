from pathlib import Path
import importlib,json,sys
import pytest

PKG=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PKG/'native_repo/src'))


def impl():
    try:return importlib.import_module('source_adapter')
    except ImportError:pytest.fail('native source registration adapter is missing')


def input_root():
    # Test fixture is external or a copied sanitized authority archive supplied by
    # package verification. Actual task IDs occur only in fixture data.
    import os
    p=Path(os.environ.get('PCHSI_TEST_EVIDENCE_ROOT',str(PKG/'tests/fixture')))
    if not p.is_dir():pytest.skip('real frozen source fixture not supplied')
    return p


def test_actual_native_sources_preserve_budgets_and_prompt(tmp_path):
    root=input_root();rows=impl().load_source_rows(root)
    assert len(rows)>0
    seen=[]
    for row in rows:
        src=impl().register_source(row,exact_gamefile=tmp_path/'game.tw-pddl',verify_gamefile=False)
        assert src.expected_source_fingerprint.fingerprint_sha256==row['fingerprint']['fingerprint_sha256']
        assert src.budget_state.policy_attempt_count==row['fingerprint']['budget_state']['policy_attempt_count']
        assert len(src.transitions)==row['fingerprint']['budget_state']['environment_step_count']
        seen.append(len(src.transitions))
    assert len(set(seen))>1


def test_source_game_hash_mismatch_refused(tmp_path):
    row=impl().load_source_rows(input_root())[0]
    game=tmp_path/'game.tw-pddl';game.write_bytes(b'wrong game')
    with pytest.raises(ValueError,match='gamefile'):
        impl().register_source(row,exact_gamefile=game)


def test_fingerprint_and_original_candidate_namespaces_remain_distinct():
    rows=impl().load_source_rows(input_root())
    for row in rows:
        assert row['candidate']['source_state_sha256']==row['handoff_state']['source_state_sha256']
        assert row['fingerprint']['fingerprint_sha256']!=row['candidate']['source_state_sha256']


def test_corrupt_fingerprint_is_not_rehashed_into_validity():
    row=impl().load_source_rows(input_root())[0]
    row['fingerprint']['model_call_index']+=1
    with pytest.raises(ValueError):impl().register_source(row,exact_gamefile=Path('/unused'),verify_gamefile=False)

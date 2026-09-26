import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'work/v17'), str(ROOT / 'work/v17/live_adapter')]
from post_binding.context import check_current_verifier, materialize_post_context
from exact_bindings import canonical, digest, BindingError


def captured():
    root = ROOT / 'work/v17/server_canary_paired_03'
    return (json.loads((root / 'EXECUTION_PLAN.json').read_bytes()),
            json.loads((root / 'verifier/ENVIRONMENT_RESULT_PACKAGE.json').read_bytes()))


def test_actual_paired_native_canary_identity_without_resealing():
    plan, verifier = captured()
    assert check_current_verifier(plan, verifier) == []
    assert verifier['scientifically_complete_pair_count'] == 10


def test_native_zero_benefit_skips_dataset_and_tokenizer(tmp_path):
    plan, verifier = captured()
    def forbidden(*a, **kw):
        pytest.fail('zero-Benefit attempted to invent training data')
    result = materialize_post_context(request={}, run_root=tmp_path, plan=plan,
        verifier=verifier, source_loader=forbidden, labels_loader=forbidden,
        tokenizer_loader=forbidden, receipt_loader=forbidden)
    assert result['recipe_context'] is None
    assert result['dataset'] is None
    assert (tmp_path / 'post/CURRENT_NATIVE_DATASET_CONTEXT.json').is_file()


def test_resealed_foreign_verifier_is_rejected():
    plan, verifier = captured()
    verifier['round_id'] = 'foreign'
    verifier['environment_result_package_sha256'] = digest(canonical({
        k: v for k, v in verifier.items() if k != 'environment_result_package_sha256'}))
    with pytest.raises(BindingError, match='VERIFIER_PLAN_IDENTITY'):
        check_current_verifier(plan, verifier)


def test_native_identity_is_not_alternative_no_lf_formula():
    plan, verifier = captured()
    verifier['environment_result_package_sha256'] = digest(canonical({
        k: v for k, v in verifier.items() if k != 'environment_result_package_sha256'}).rstrip(b'\n'))
    with pytest.raises(BindingError, match='OBJECT_HASH'):
        check_current_verifier(plan, verifier)

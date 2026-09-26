"""Exercise actual native POST and logical/attempt contracts, without a provider."""
from pathlib import Path
import copy
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'work/v17'), str(ROOT / 'work/v16/analyzer_adapter'),
    str(ROOT / 'work/reference_g2/PCHSI_PAPER_CRITICAL_CAUSAL_ROUND_EXECUTION_V1_23_3H4_4/native_repo/src')]
from exact_bindings import BindingError, canonical, digest, immutable_json, read_ref
from post_binding.runtime import prepare_projection, validate_post_output, adopt_recipe
from pchsi.cognitive_runtime.researcher_primary import finalize_api_post_primary_v1
from pchsi.cognitive_runtime.identity import build_logical_call_record, build_transport_attempt_record
from pchsi.reference_loop.canonical import domain_hash


def fixture(tmp_path, *, recipe=None, context=None, status='ACCEPTED'):
    logical_id = 'c' * 64
    projection = prepare_projection({'round_id': 'round-fixture-current',
        'primary_pre_record_sha256': 'a' * 64, 'environment_result_package_sha256': 'b' * 64}, context)
    value = dict(schema_id='API_RESEARCHER_POST_PRIMARY_V1', schema_version=1,
        round_id=projection['round_id'], primary_pre_record_sha256='a' * 64,
        environment_result_package_sha256='b' * 64, protocol_audit='fixture audit',
        observed_outcome='fixture observations', numerator=1, denominator=2,
        unexpected_evidence=[], hypothesis_status='UNRESOLVED', alternative_explanations=[],
        researcher_training_recommendation='NO_TRAIN' if recipe is None else 'TRAIN',
        researcher_promotion_recommendation='HOLD', lesson='fixture lesson',
        next_round_implication='retain frozen boundaries', primary_record_sha256='0' * 64,
        training_recipe=recipe)
    response = canonical({'status': 'completed', 'output': [{'type': 'message', 'content': [
        {'type': 'output_text', 'text': json.dumps(value)}]}]})
    response_sha = digest(response)
    artifact = validate_post_output(value, projection=projection, raw_response_sha256=response_sha,
        logical_call_id=logical_id, output_root=tmp_path, native_finalize=finalize_api_post_primary_v1)
    call = tmp_path / 'calls' / logical_id
    request = canonical({'model': 'fixture-provider', 'input': 'current frozen POST input'})
    expected = {'logical_call_id': logical_id, 'scientific_unit_identity_sha256': 'd' * 64,
        'stage_id': 'R-POST-PRIMARY-V1', 'condition_id': None, 'round_id': projection['round_id'],
        'policy_version': 'fixture-policy', 'request_body_sha256': domain_hash('COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1', json.loads(request)),
        'runtime_manifest_sha256': 'f' * 64}
    logical = build_logical_call_record(**expected, role='TRAINING_RESEARCHER',
        terminal_method_status=status,
        contributing_attempt_id=logical_id + ':0')
    attempt = build_transport_attempt_record(logical_call_id=logical_id, transport_attempt_id=logical_id + ':0',
        transport_attempt_index=0, bytes_transmission_state='CONFIRMED_SENT', retry_class='INITIAL',
        retry_reason=None, retry_authority='NOT_APPLICABLE', provider_response_id='fixture-response',
        terminal_attempt_status='SUCCEEDED', ambiguous_post_send_disposition_id=None,
        raw_request_sha256=digest(request), raw_response_sha256=response_sha, input_tokens=None,
        output_tokens=None, reasoning_tokens=None, latency_ms=None, cost_usd=None)
    for name, obj in [('logical_call.json', logical), ('attempt_000.json', attempt),
                      ('validated_artifact.json', artifact)]:
        immutable_json(call / name, obj)
    (call / 'raw_response.json').write_bytes(response)
    (call / 'raw_request.json').write_bytes(request)
    return {'call_dir': call, 'output_root': tmp_path, 'expected': expected,
            'projection': projection, 'native_finalize': finalize_api_post_primary_v1}, value, artifact


def test_native_no_train_same_call_adoption_with_no_dataset(tmp_path):
    args, value, artifact = fixture(tmp_path)
    base = copy.deepcopy(value); base.pop('training_recipe')
    assert artifact == finalize_api_post_primary_v1(base, projection=args['projection'])
    ref = adopt_recipe(**args)
    before = Path(ref['path']).read_bytes()
    assert adopt_recipe(**args) == ref
    assert Path(ref['path']).read_bytes() == before
    result = read_ref(ref)
    assert result['additional_provider_call_count'] == 0
    assert result['post_primary_record_sha256'] == artifact['primary_record_sha256']


@pytest.mark.parametrize('status', ['PENDING', 'SEMANTIC_INVALID', 'AMBIGUOUS_POST_SEND'])
def test_callback_output_is_not_logical_acceptance(tmp_path, status):
    args, _, _ = fixture(tmp_path, status=status)
    with pytest.raises(BindingError, match='REQUIRES_ACCEPTED'):
        adopt_recipe(**args)
    assert not (tmp_path / 'POST_ACCEPTED_RECIPE_BINDING.json').exists()


def test_current_round_identity_mismatch_rejected_before_accept(tmp_path):
    args, _, _ = fixture(tmp_path)
    args['expected']['round_id'] = 'wrong-round'
    with pytest.raises(BindingError, match='LOGICAL_IDENTITY:round_id'):
        adopt_recipe(**args)


def test_raw_response_tampering_rejected(tmp_path):
    args, _, _ = fixture(tmp_path)
    (args['call_dir'] / 'raw_response.json').write_bytes(b'{"output_text":"tampered"}')
    with pytest.raises(BindingError, match='FILE_SHA_MISMATCH'):
        adopt_recipe(**args)


def test_native_logical_hash_tamper_rejected(tmp_path):
    args, _, _ = fixture(tmp_path)
    path = args['call_dir'] / 'logical_call.json'
    value = json.loads(path.read_text()); value['runtime_manifest_sha256'] = '1' * 64
    path.write_text(json.dumps(value), encoding='utf8')
    with pytest.raises(BindingError, match='LOGICAL_DOMAIN_HASH'):
        adopt_recipe(**args)


def test_recovery_attempt_index_cannot_disagree_with_contributing_id(tmp_path):
    args, _, _ = fixture(tmp_path)
    path = args['call_dir'] / 'attempt_000.json'
    attempt = json.loads(path.read_text()); attempt['transport_attempt_index'] = 9
    attempt['attempt_sha256'] = domain_hash('TRANSPORT_ATTEMPT_RECORD_V1', attempt, excluded_field='attempt_sha256')
    path.write_text(json.dumps(attempt), encoding='utf8')
    with pytest.raises(BindingError, match='CONTRIBUTING_ATTEMPT_MISMATCH'):
        adopt_recipe(**args)


def test_recovery_requires_original_request_bytes(tmp_path):
    args, _, _ = fixture(tmp_path)
    (args['call_dir'] / 'raw_request.json').unlink()
    with pytest.raises(BindingError):
        adopt_recipe(**args)


def test_rehashed_different_request_cannot_be_adopted_as_current_request(tmp_path):
    args, _, _ = fixture(tmp_path)
    raw = canonical({'model': 'fixture-provider', 'input': 'another request'})
    (args['call_dir'] / 'raw_request.json').write_bytes(raw)
    path = args['call_dir'] / 'attempt_000.json'
    attempt = json.loads(path.read_text()); attempt['raw_request_sha256'] = digest(raw)
    attempt['attempt_sha256'] = domain_hash('TRANSPORT_ATTEMPT_RECORD_V1', attempt, excluded_field='attempt_sha256')
    path.write_text(json.dumps(attempt), encoding='utf8')
    with pytest.raises(BindingError, match='RAW_REQUEST_CURRENT_IDENTITY'):
        adopt_recipe(**args)


def test_train_without_current_materialized_dataset_rejected(tmp_path):
    args, value, _ = fixture(tmp_path)
    value['researcher_training_recommendation'] = 'TRAIN'
    value['training_recipe'] = {'epochs': 1}
    with pytest.raises(BindingError, match='CURRENT_DATASET_CONTEXT'):
        validate_post_output(value, projection=args['projection'], raw_response_sha256='1' * 64,
            logical_call_id='2' * 64, output_root=tmp_path, native_finalize=finalize_api_post_primary_v1)


def test_no_train_cannot_carry_optimizer_recipe(tmp_path):
    args, value, _ = fixture(tmp_path)
    value['training_recipe'] = {'epochs': 1}
    with pytest.raises(BindingError, match='NO_TRAIN_CANNOT'):
        validate_post_output(value, projection=args['projection'], raw_response_sha256='1' * 64,
            logical_call_id='2' * 64, output_root=tmp_path, native_finalize=finalize_api_post_primary_v1)


def test_positive_train_recipe_preserved_in_same_raw_response(tmp_path):
    context = {'dataset_sha256': '9' * 64, 'row_count': 8}
    recipe = {'epochs': 2, 'micro_batch_size': 1, 'gradient_accumulation_steps': 2,
        'learning_rate': 0.0001, 'weight_decay': 0.0, 'max_grad_norm': 1.0,
        'warmup_steps': 1, 'training_seed': 107, 'data_seed': 107,
        'dataset_sha256': context['dataset_sha256'],
        'data_semantics': 'VERIFIED_BENEFIT_DUAL_VIEW_COMPLETE_PAIRS', 'rationale': 'fixture choice'}
    args, _, _ = fixture(tmp_path, recipe=recipe, context=context)
    result = read_ref(adopt_recipe(**args))
    assert result['recipe_receipt']['recipe'] == recipe
    assert result['recipe_receipt']['training_execution_authorized'] is False


def test_recipe_cannot_be_replaced_after_native_acceptance(tmp_path):
    context = {'dataset_sha256': '9' * 64, 'row_count': 8}
    recipe = {'epochs': 2, 'micro_batch_size': 1, 'gradient_accumulation_steps': 2,
        'learning_rate': 0.0001, 'weight_decay': 0.0, 'max_grad_norm': 1.0,
        'warmup_steps': 1, 'training_seed': 107, 'data_seed': 107,
        'dataset_sha256': context['dataset_sha256'],
        'data_semantics': 'VERIFIED_BENEFIT_DUAL_VIEW_COMPLETE_PAIRS', 'rationale': 'fixture choice'}
    args, _, _ = fixture(tmp_path, recipe=recipe, context=context)
    path = tmp_path / 'recipe_decisions' / (args['expected']['logical_call_id'] + '.json')
    decision = json.loads(path.read_text()); decision['recipe']['epochs'] = 4
    path.write_text(json.dumps(decision), encoding='utf8')
    with pytest.raises(BindingError, match='RAW_RESPONSE_DECISION_DRIFT'):
        adopt_recipe(**args)

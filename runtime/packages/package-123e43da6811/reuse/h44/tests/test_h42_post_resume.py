import json
from pathlib import Path
from types import SimpleNamespace

from io_utils import canonical, digest_file, put_json, read_json, sha
from strong_post import _resolve_scientific_input_root
from post_resume import validate_verified_post_resume, resume
from tests.test_post import setup_post


def _fixture(tmp_path: Path):
    scientific = tmp_path / 'scientific'
    scientific.mkdir()
    plan, verifier = setup_post(scientific)

    runtime = scientific / 'input' / 'actor_runtime' / 'runtime_binding.json'
    runtime.parent.mkdir(parents=True, exist_ok=True)
    runtime.write_bytes(b'{"schema_id":"TEST_RUNTIME"}\n')
    plan['runtime_path'] = str(runtime)
    plan['runtime_file_sha256'] = digest_file(runtime)
    plan['plan_sha256'] = sha(canonical({k: v for k, v in plan.items() if k != 'plan_sha256'}))

    verifier['plan_sha256'] = plan['plan_sha256']
    verifier['status'] = 'VERIFIED_COMPLETE'
    verifier.pop('environment_result_package_sha256', None)
    verifier['environment_result_package_sha256'] = sha(canonical(verifier))

    recovery = tmp_path / 'recovery'
    recovery.mkdir()
    put_json(recovery / 'EXECUTION_PLAN.json', plan)
    put_json(recovery / 'verifier' / 'ENVIRONMENT_RESULT_PACKAGE.json', verifier)
    put_json(recovery / 'GPU_JOB_TERMINAL.json', {
        'schema_id': 'CURRENT_NATIVE_GPU_JOB_TERMINAL_TEST',
        'plan_sha256': plan['plan_sha256'],
        'status': 'VERIFIED_COMPLETE',
    })
    missing = recovery / 'input' / 'pre_root' / 'PCHSI_V1232Z_TERMINAL_V1.json'
    put_json(recovery / 'ROUND_EXECUTION_TERMINAL.json', {
        'schema_id': 'CURRENT_CAUSAL_EXECUTION_CONTROLLER_TERMINAL_V1',
        'status': 'CURRENT_EXECUTION_STOPPED_WITH_DIAGNOSTIC',
        'plan_sha256': plan['plan_sha256'],
        'environment_result_package_sha256': verifier['environment_result_package_sha256'],
        'verifier_status': 'VERIFIED_COMPLETE',
        'error_type': 'FileNotFoundError',
        'error_message': "[Errno 2] No such file or directory: '" + str(missing) + "'",
        'training_execution_count': 0,
        'full_round_closed': False,
        'next_round_launched': False,
        'max10_released': False,
        'human_scientific_decision_count': 0,
    })
    return scientific, recovery, plan, verifier


def _install_no_train_provider(monkeypatch, plan):
    import pchsi.cognitive_runtime.orchestrator as o

    calls = []
    def fake_p2(bundle, call_dir, *, client_request_id):
        calls.append(client_request_id)
        projection = bundle['input_projection']
        payload = {
            'schema_id': 'API_RESEARCHER_POST_PRIMARY_V1',
            'schema_version': 1,
            'round_id': plan['round_id'],
            'primary_pre_record_sha256': projection['primary_pre_record_sha256'],
            'environment_result_package_sha256': projection['environment_result_package_sha256'],
            'protocol_audit': 'verified complete fixture',
            'observed_outcome': 'neutral',
            'numerator': 0,
            'denominator': len(plan['states']),
            'unexpected_evidence': [],
            'hypothesis_status': 'UNRESOLVED',
            'alternative_explanations': ['fixture'],
            'researcher_training_recommendation': 'NO_TRAIN',
            'researcher_promotion_recommendation': 'HOLD',
            'lesson': 'fixture',
            'next_round_implication': 'retain parent',
            'primary_record_sha256': '0' * 64,
        }
        response = {
            'id': 'response-h42-fixture',
            'model': bundle['provider_request']['model'],
            'status': 'completed',
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(payload)}]}],
            'usage': {'input_tokens': 10, 'output_tokens': 10, 'output_tokens_details': {'reasoning_tokens': 0}},
        }
        return SimpleNamespace(http_status=200, response_headers={}, provider_http_request_id='fixture', raw_response=canonical(response))

    monkeypatch.setattr(o, 'execute_via_existing_p2', fake_p2)
    return calls


def test_post_input_is_resolved_from_hash_bound_plan_runtime_not_operational_root(tmp_path):
    scientific, recovery, plan, verifier = _fixture(tmp_path)
    resolved = _resolve_scientific_input_root(recovery, plan)
    assert resolved == (scientific / 'input')
    assert not (recovery / 'input').exists()


def test_post_resume_validates_verified_complete_without_requiring_recovery_input_copy(tmp_path):
    scientific, recovery, plan, verifier = _fixture(tmp_path)
    observed_plan, terminal, observed_verifier, input_root = validate_verified_post_resume(recovery)
    assert observed_plan['plan_sha256'] == plan['plan_sha256']
    assert observed_verifier['environment_result_package_sha256'] == verifier['environment_result_package_sha256']
    assert input_root == scientific / 'input'


def test_post_resume_executes_only_post_and_preserves_prior_diagnostic(tmp_path, monkeypatch):
    scientific, recovery, plan, verifier = _fixture(tmp_path)
    prior_bytes = (recovery / 'ROUND_EXECUTION_TERMINAL.json').read_bytes()
    calls = _install_no_train_provider(monkeypatch, plan)
    result = resume(recovery)
    assert result['post_terminal']['training_recommendation'] == 'NO_TRAIN'
    assert len(calls) == 1
    assert (recovery / 'ROUND_EXECUTION_TERMINAL.json').read_bytes() == prior_bytes
    assert (recovery / 'ROUND_EXECUTION_CONTINUATION_TERMINAL.json').is_file()
    assert (recovery / 'post' / 'NO_TRAINING_UPDATE_V1.json').is_file()
    assert result['training_execution_count'] == 0


def test_post_resume_rejects_runtime_byte_drift(tmp_path):
    scientific, recovery, plan, verifier = _fixture(tmp_path)
    Path(plan['runtime_path']).write_bytes(b'changed\n')
    try:
        validate_verified_post_resume(recovery)
    except ValueError as exc:
        assert 'POST_PLAN_RUNTIME_FILE_HASH_MISMATCH' in str(exc)
    else:
        raise AssertionError('tampered runtime bytes were accepted')


def test_post_resume_rejects_wrong_prior_error_class(tmp_path):
    scientific, recovery, plan, verifier = _fixture(tmp_path)
    terminal = read_json(recovery / 'ROUND_EXECUTION_TERMINAL.json')
    terminal['error_type'] = 'RuntimeError'
    path = recovery / 'ROUND_EXECUTION_TERMINAL.json'
    path.unlink()
    put_json(path, terminal)
    try:
        validate_verified_post_resume(recovery)
    except ValueError as exc:
        assert 'POST_RESUME_ERROR_TYPE_NOT_EXPECTED' in str(exc)
    else:
        raise AssertionError('wrong diagnostic class was accepted')

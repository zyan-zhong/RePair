from pathlib import Path
import controller
from io_utils import canonical, sha, put_json


def _plan(root: Path):
    plan = {
        'schema_id': 'CURRENT_ACCEPTED_PRE_NATIVE_EXECUTION_PLAN_V1',
        'round_id': 'r1',
        'source_request': {'parent_policy_id': 'parent'},
        'handoff': {'branch_plan': []},
        'states': [],
        'branch_bindings': [],
        'operations': {},
    }
    plan['plan_sha256'] = sha(canonical(plan))
    put_json(root/'EXECUTION_PLAN.json', plan)
    return plan


def test_controller_consumes_persisted_verifier_and_no_train_without_undefined_variable(tmp_path, monkeypatch):
    plan = _plan(tmp_path)
    put_json(tmp_path/'GPU_JOB_TERMINAL.json', {'plan_sha256': plan['plan_sha256'], 'status': 'VERIFIED_COMPLETE'})
    verifier = {
        'environment_result_package_sha256': 'a'*64,
        'status': 'VERIFIED_COMPLETE',
        'scientifically_complete_pair_count': 1,
    }
    monkeypatch.setattr('independent_verifier.verify_plan', lambda *a, **k: verifier)
    monkeypatch.setattr('strong_post.execute_post', lambda *a, **k: {
        'status': 'CAUSAL_ROUND_POST_NO_TRAIN_RECORDED_RESIDENT_HANDOFF_PENDING',
        'training_recommendation': 'NO_TRAIN',
        'provider_calls': 0,
    })
    rc = controller.run_controller(tmp_path)
    assert rc == 0
    terminal = controller.read_json(tmp_path/'ROUND_EXECUTION_TERMINAL.json')
    assert terminal['post_terminal']['training_recommendation'] == 'NO_TRAIN'
    assert terminal['status'] == 'CAUSAL_ROUND_POST_NO_TRAIN_RECORDED_RESIDENT_HANDOFF_PENDING'


def test_controller_train_route_is_a_successful_causal_terminal_not_max10_release(tmp_path, monkeypatch):
    plan = _plan(tmp_path)
    put_json(tmp_path/'GPU_JOB_TERMINAL.json', {'plan_sha256': plan['plan_sha256'], 'status': 'VERIFIED_COMPLETE'})
    verifier = {
        'environment_result_package_sha256': 'a'*64,
        'status': 'VERIFIED_COMPLETE',
        'scientifically_complete_pair_count': 1,
    }
    monkeypatch.setattr('independent_verifier.verify_plan', lambda *a, **k: verifier)
    monkeypatch.setattr('strong_post.execute_post', lambda *a, **k: {
        'status': 'CAUSAL_ROUND_POST_TRAIN_SELECTED_NATIVE_TRAINING_BINDING_PENDING',
        'training_recommendation': 'TRAIN',
        'provider_calls': 0,
    })
    rc = controller.run_controller(tmp_path)
    assert rc == 0
    terminal = controller.read_json(tmp_path/'ROUND_EXECUTION_TERMINAL.json')
    assert terminal['post_terminal']['training_recommendation'] == 'TRAIN'
    assert terminal['full_round_closed'] is False
    assert terminal['max10_released'] is False


def test_release_gate_allows_only_current_causal_round_and_not_training_or_max10():
    release=controller.require_current_causal_release()
    assert release['current_causal_round_live_execution_authorized'] is True
    assert release['training_execution_authorized'] is False
    assert release['next_round_launch_authorized'] is False
    assert release['max10_released'] is False

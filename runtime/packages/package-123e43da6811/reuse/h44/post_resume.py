from __future__ import annotations
import argparse
import fcntl
from pathlib import Path

from io_utils import canonical, digest_file, put_json, read_json, sha
from strong_post import execute_post, _resolve_scientific_input_root

ROOT = Path(__file__).resolve().parent


def _validate_hash_record(value: dict, field: str) -> None:
    expected = sha(canonical({k: v for k, v in value.items() if k != field}))
    if value.get(field) != expected:
        raise ValueError('record identity mismatch:' + field)


def validate_verified_post_resume(run_root: Path) -> tuple[dict, dict, dict, Path]:
    run_root = run_root.resolve()
    plan_path = run_root / 'EXECUTION_PLAN.json'
    terminal_path = run_root / 'ROUND_EXECUTION_TERMINAL.json'
    verifier_path = run_root / 'verifier' / 'ENVIRONMENT_RESULT_PACKAGE.json'
    gpu_path = run_root / 'GPU_JOB_TERMINAL.json'
    for path in (plan_path, terminal_path, verifier_path, gpu_path):
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError('POST_RESUME_REQUIRED_RECEIPT_MISSING:' + str(path))

    plan = read_json(plan_path)
    if plan.get('plan_sha256') != sha(canonical({k: v for k, v in plan.items() if k != 'plan_sha256'})):
        raise ValueError('POST_RESUME_PLAN_HASH_MISMATCH')

    terminal = read_json(terminal_path)
    verifier = read_json(verifier_path)
    gpu = read_json(gpu_path)

    if terminal.get('schema_id') != 'CURRENT_CAUSAL_EXECUTION_CONTROLLER_TERMINAL_V1':
        raise ValueError('POST_RESUME_TERMINAL_SCHEMA_MISMATCH')
    if terminal.get('status') != 'CURRENT_EXECUTION_STOPPED_WITH_DIAGNOSTIC':
        raise ValueError('POST_RESUME_TERMINAL_NOT_DIAGNOSTIC')
    if terminal.get('error_type') != 'FileNotFoundError':
        raise ValueError('POST_RESUME_ERROR_TYPE_NOT_EXPECTED')
    expected_missing = str(run_root / 'input' / 'pre_root' / 'PCHSI_V1232Z_TERMINAL_V1.json')
    if expected_missing not in str(terminal.get('error_message') or ''):
        raise ValueError('POST_RESUME_ERROR_MESSAGE_NOT_EXPECTED_INPUT_ROOT_DRIFT')
    if terminal.get('plan_sha256') != plan['plan_sha256']:
        raise ValueError('POST_RESUME_TERMINAL_PLAN_MISMATCH')
    if terminal.get('verifier_status') != 'VERIFIED_COMPLETE':
        raise ValueError('POST_RESUME_TERMINAL_VERIFIER_NOT_COMPLETE')
    if terminal.get('training_execution_count') not in (None, 0):
        raise ValueError('POST_RESUME_PRIOR_TRAINING_EXECUTED')
    if terminal.get('full_round_closed') is True or terminal.get('next_round_launched') is True:
        raise ValueError('POST_RESUME_ROUND_ALREADY_ADVANCED')

    if verifier.get('plan_sha256') != plan['plan_sha256']:
        raise ValueError('POST_RESUME_VERIFIER_PLAN_MISMATCH')
    if verifier.get('status') != 'VERIFIED_COMPLETE':
        raise ValueError('POST_RESUME_VERIFIER_NOT_COMPLETE')
    if verifier.get('scientifically_complete_pair_count', 0) <= 0:
        raise ValueError('POST_RESUME_NO_SCIENTIFICALLY_COMPLETE_PAIRS')
    _validate_hash_record(verifier, 'environment_result_package_sha256')
    if terminal.get('environment_result_package_sha256') != verifier['environment_result_package_sha256']:
        raise ValueError('POST_RESUME_TERMINAL_VERIFIER_SHA_MISMATCH')
    if gpu.get('plan_sha256') != plan['plan_sha256']:
        raise ValueError('POST_RESUME_GPU_PLAN_MISMATCH')

    # Exact failure happened before any provider call. Preserve that guarantee.
    calls = run_root / 'post' / 'calls'
    if calls.exists() and any(path.is_file() for path in calls.rglob('*')):
        raise ValueError('POST_RESUME_PRIOR_PROVIDER_CALL_EVIDENCE_PRESENT_NO_BLIND_RESUME')
    if (run_root / 'post' / 'POST_TERMINAL.json').exists():
        raise ValueError('POST_RESUME_POST_ALREADY_TERMINAL')

    scientific_input_root = _resolve_scientific_input_root(run_root, plan)
    return plan, terminal, verifier, scientific_input_root


def resume(run_root: Path) -> dict:
    run_root = run_root.resolve()
    lock_path = run_root / 'POST_RESUME.lock'
    with lock_path.open('a+b') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('POST_RESUME_ALREADY_ACTIVE')

        effective_path = run_root / 'ROUND_EXECUTION_CONTINUATION_TERMINAL.json'
        if effective_path.exists():
            return read_json(effective_path)

        plan, prior_terminal, verifier, scientific_input_root = validate_verified_post_resume(run_root)
        post = execute_post(run_root, plan, verifier)
        result = {
            'schema_id': 'CURRENT_CAUSAL_POST_CONTINUATION_TERMINAL_V1',
            'plan_sha256': plan['plan_sha256'],
            'prior_controller_terminal_sha256': digest_file(run_root / 'ROUND_EXECUTION_TERMINAL.json'),
            'environment_result_package_sha256': verifier['environment_result_package_sha256'],
            'verifier_status': verifier['status'],
            'scientifically_complete_pair_count': verifier['scientifically_complete_pair_count'],
            'scientific_input_authority_mode': 'PLAN_RUNTIME_PATH_ANCHORED_CAPTURE_ROOT',
            'scientific_input_runtime_file_sha256': plan['runtime_file_sha256'],
            'post_terminal': post,
            'training_execution_count': 0,
            'full_round_closed': False,
            'next_round_launched': False,
            'max10_released': False,
            'human_scientific_decision_count': 0,
        }
        recommendation = post.get('training_recommendation')
        if recommendation not in ('TRAIN', 'NO_TRAIN'):
            result['status'] = 'CURRENT_CAUSAL_POST_CONTINUATION_NOT_TERMINAL_NO_RESEND'
        else:
            result['status'] = post['status']
        result['continuation_terminal_sha256'] = sha(canonical(result))
        put_json(effective_path, result)
        return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--recovery-root', type=Path, required=True)
    ap.add_argument('--execute-post', action='store_true')
    args = ap.parse_args()

    plan, terminal, verifier, input_root = validate_verified_post_resume(args.recovery_root)
    print('POST_RESUME_VALIDATION=PASS', flush=True)
    print('POST_RESUME_PLAN_SHA256=' + plan['plan_sha256'], flush=True)
    print('POST_RESUME_VERIFIER_SHA256=' + verifier['environment_result_package_sha256'], flush=True)
    print('POST_RESUME_SCIENTIFICALLY_COMPLETE_PAIR_COUNT=' + str(verifier['scientifically_complete_pair_count']), flush=True)
    print('POST_RESUME_INPUT_AUTHORITY_MODE=PLAN_RUNTIME_PATH_ANCHORED_CAPTURE_ROOT', flush=True)
    if not args.execute_post:
        print('STATUS=VERIFIED_POST_CONTINUATION_PREPARED_NO_PROVIDER_CALL', flush=True)
        return 0

    result = resume(args.recovery_root)
    print('STATUS=' + result['status'], flush=True)
    print('POST_CONTINUATION_TERMINAL=' + str(args.recovery_root.resolve() / 'ROUND_EXECUTION_CONTINUATION_TERMINAL.json'), flush=True)
    post = result.get('post_terminal') or {}
    print('TRAINING_RECOMMENDATION=' + str(post.get('training_recommendation')), flush=True)
    print('PROVIDER_CALLS_THIS_RESUME=' + str(post.get('provider_calls', 0)), flush=True)
    print('TRAINING_EXECUTION_COUNT=0', flush=True)
    print('FULL_MAX10_AUTONOMOUS_CAMPAIGN_RELEASED=false', flush=True)
    return 0 if post.get('training_recommendation') in ('TRAIN', 'NO_TRAIN') else 20


if __name__ == '__main__':
    raise SystemExit(main())

from __future__ import annotations

from contextlib import ExitStack
import copy
import fcntl
import json
from pathlib import Path
from unittest.mock import patch

from io_utils import canonical, digest_file, put_json, read_json, sha
from post_resume import _validate_hash_record
from strong_post import _resolve_scientific_input_root, _terminal, route_accepted_post_artifact

SAFE_PRE_SEND = ('SAFE_PRE_SEND', 'NOT_SENT', 'PRE_SEND_INFRASTRUCTURE_UNAVAILABLE')
SAFE_PROVIDER_REJECTION = ('SAFE_PROVIDER_REJECTION', 'CONFIRMED_SENT', 'PROVIDER_TRANSIENT_UNAVAILABLE')


def _single_call_dir(root: Path) -> Path:
    if not root.is_dir():
        raise FileNotFoundError('POST_SETTLEMENT_CALL_ROOT_MISSING:' + str(root))
    rows = sorted(p for p in root.iterdir() if p.is_dir() and not p.is_symlink())
    if len(rows) != 1:
        raise ValueError('POST_SETTLEMENT_INITIAL_CALL_COUNT_NOT_ONE:' + str(len(rows)))
    return rows[0]


def _validate_base(run_root: Path) -> tuple[dict, dict, dict, dict]:
    plan = read_json(run_root / 'EXECUTION_PLAN.json')
    verifier = read_json(run_root / 'verifier' / 'ENVIRONMENT_RESULT_PACKAGE.json')
    continuation = read_json(run_root / 'ROUND_EXECUTION_CONTINUATION_TERMINAL.json')
    if continuation.get('schema_id') != 'CURRENT_CAUSAL_POST_CONTINUATION_TERMINAL_V1':
        raise ValueError('SETTLEMENT_CONTINUATION_SCHEMA_MISMATCH')
    _validate_hash_record(continuation, 'continuation_terminal_sha256')
    if continuation.get('status') != 'CURRENT_CAUSAL_POST_CONTINUATION_NOT_TERMINAL_NO_RESEND':
        raise ValueError('SETTLEMENT_CONTINUATION_NOT_EXPECTED_NONTERMINAL')
    if continuation.get('plan_sha256') != plan.get('plan_sha256'):
        raise ValueError('SETTLEMENT_PLAN_MISMATCH')
    if continuation.get('verifier_status') != 'VERIFIED_COMPLETE' or verifier.get('status') != 'VERIFIED_COMPLETE':
        raise ValueError('SETTLEMENT_VERIFIER_NOT_COMPLETE')
    if continuation.get('environment_result_package_sha256') != verifier.get('environment_result_package_sha256'):
        raise ValueError('SETTLEMENT_VERIFIER_SHA_MISMATCH')
    if continuation.get('training_execution_count') not in (None, 0):
        raise ValueError('SETTLEMENT_PRIOR_TRAINING_EXECUTED')
    if continuation.get('full_round_closed') is True or continuation.get('next_round_launched') is True:
        raise ValueError('SETTLEMENT_ROUND_ALREADY_ADVANCED')
    post = continuation.get('post_terminal')
    if not isinstance(post, dict) or post.get('provider_calls') != 1:
        raise ValueError('SETTLEMENT_PRIOR_PROVIDER_CALL_COUNT_NOT_ONE')
    if post.get('training_recommendation') in ('TRAIN', 'NO_TRAIN'):
        raise ValueError('SETTLEMENT_ALREADY_HAS_TYPED_TRAINING_ROUTE')
    return plan, verifier, continuation, post


def _load_call_evidence(call: Path) -> dict:
    logical_path = call / 'logical_call.json'
    if not logical_path.is_file():
        return {
            'call_dir': str(call),
            'logical_call_terminal': False,
            'disposition': 'PARTIAL_OR_UNKNOWN_NO_RESEND',
            'provider_resend_same_logical_call_authorized': False,
            'new_remediation_logical_call_authorized': False,
        }
    logical = read_json(logical_path)
    attempt = read_json(call / 'attempt_000.json')
    method_path = call / 'method_result.json'
    validation_path = call / 'validation_error.json'
    method = read_json(method_path) if method_path.is_file() else None
    validation = read_json(validation_path) if validation_path.is_file() else None
    rendered = read_json(call / 'rendered_request.json')
    if logical.get('logical_call_id') != call.name:
        raise ValueError('SETTLEMENT_CALL_DIRECTORY_ID_MISMATCH')
    if logical.get('request_body_sha256') != rendered.get('request_body_sha256'):
        raise ValueError('SETTLEMENT_RENDERED_REQUEST_HASH_MISMATCH')
    if attempt.get('logical_call_id') != call.name:
        raise ValueError('SETTLEMENT_ATTEMPT_LOGICAL_ID_MISMATCH')
    if attempt.get('raw_request_sha256') != digest_file(call / 'raw_request.json'):
        raise ValueError('SETTLEMENT_RAW_REQUEST_HASH_MISMATCH')
    if method is not None and method.get('status') != logical.get('terminal_method_status'):
        raise ValueError('SETTLEMENT_METHOD_LOGICAL_STATUS_MISMATCH')
    if method is None and logical.get('terminal_method_status') == 'INFRASTRUCTURE_UNAVAILABLE':
        raise ValueError('SETTLEMENT_INFRASTRUCTURE_TERMINAL_MISSING_METHOD_RESULT')
    from pchsi.reference_loop.canonical import domain_hash
    if logical.get('logical_call_sha256') != domain_hash('LOGICAL_CALL_RECORD_V1', logical, excluded_field='logical_call_sha256'):
        raise ValueError('SETTLEMENT_LOGICAL_CALL_HASH_MISMATCH')
    if attempt.get('attempt_sha256') != domain_hash('TRANSPORT_ATTEMPT_RECORD_V1', attempt, excluded_field='attempt_sha256'):
        raise ValueError('SETTLEMENT_ATTEMPT_HASH_MISMATCH')

    status = logical['terminal_method_status']
    failure_class = (
        method.get('failure_class') if method is not None
        else validation.get('failure_class') if validation is not None
        else None
    )
    counts_as_method_failure = method.get('counts_as_method_failure') if method is not None else (
        validation.get('counts_as_method_failure') if validation is not None else None
    )
    hard_stop = method.get('hard_stop') if method is not None else None
    key = (attempt.get('retry_class'), attempt.get('bytes_transmission_state'), failure_class)
    eligible = (
        status == 'INFRASTRUCTURE_UNAVAILABLE'
        and counts_as_method_failure is False
        and hard_stop is False
        and key in (SAFE_PRE_SEND, SAFE_PROVIDER_REJECTION)
    )
    disposition = (
        'ADOPT_ACCEPTED_NO_RESEND' if status == 'ACCEPTED'
        else 'ONE_AUTONOMOUS_INFRASTRUCTURE_REMEDIATION_ELIGIBLE' if eligible
        else 'POST_METHOD_TERMINAL_NO_RESEND'
    )
    return {
        'call_dir': str(call),
        'logical_call_terminal': True,
        'logical_call_id': call.name,
        'terminal_method_status': status,
        'failure_class': failure_class,
        'retry_class': attempt.get('retry_class'),
        'bytes_transmission_state': attempt.get('bytes_transmission_state'),
        'request_body_sha256': logical.get('request_body_sha256'),
        'attempt_sha256': attempt.get('attempt_sha256'),
        'disposition': disposition,
        'provider_resend_same_logical_call_authorized': False,
        'new_remediation_logical_call_authorized': bool(eligible),
    }


def classify_existing_post(run_root: Path) -> dict:
    run_root = Path(run_root).resolve()
    plan, verifier, continuation, post = _validate_base(run_root)
    call = _single_call_dir(run_root / 'post' / 'calls')
    evidence = _load_call_evidence(call)
    value = {
        'schema_id': 'CURRENT_POST_AUTONOMOUS_SETTLEMENT_CLASSIFICATION_V1',
        'plan_sha256': plan['plan_sha256'],
        'environment_result_package_sha256': verifier['environment_result_package_sha256'],
        'scientifically_complete_pair_count': verifier['scientifically_complete_pair_count'],
        'prior_continuation_terminal_sha256': continuation['continuation_terminal_sha256'],
        **evidence,
        'human_scientific_decision_required': False,
        'same_logical_call_resend_count_authorized': 0,
        'max_new_remediation_logical_calls_authorized': 1 if evidence.get('new_remediation_logical_call_authorized') else 0,
    }
    value['classification_sha256'] = sha(canonical(value))
    return value


def _runtime_context(run_root: Path, plan: dict):
    import jsonschema
    from pchsi.cognitive_runtime import request_renderer, orchestrator
    from pchsi.cognitive_runtime.researcher_primary import finalize_api_post_primary_v1

    postdir = run_root / 'post'
    projection = read_json(postdir / 'projection.json')
    manifest = read_json(postdir / 'runtime_manifest.json')
    schema = read_json(postdir / 'provider_schema.json')
    original_unit = read_json(postdir / 'unit.json')
    input_root = _resolve_scientific_input_root(run_root, plan)
    access = read_json(input_root / 'pre_root' / 'V1232V_PRE_TASK_ACCESS_V1.json')

    def validate_output(*, stage_id, text, raw_response_sha256, projection):
        if stage_id != 'R-POST-PRIMARY-V1':
            raise ValueError('POST_STAGE_ONLY')
        value = json.loads(text)
        jsonschema.Draft202012Validator(schema).validate(value)
        return finalize_api_post_primary_v1(value, projection=projection)

    return request_renderer, orchestrator, projection, manifest, schema, original_unit, access, validate_output


def _build_remediation_unit(original_unit: dict, classification: dict) -> dict:
    from pchsi.cognitive_runtime.identity import build_scientific_unit_identity
    from pchsi.reference_loop.canonical import domain_hash
    raw = {k: v for k, v in original_unit.items() if k not in ('schema_id', 'schema_version', 'identity_sha256')}
    raw['scientific_unit_id'] = domain_hash(
        'CURRENT_ROUND_POST_INFRASTRUCTURE_REMEDIATION_UNIT_V1',
        {
            'original_scientific_unit_identity_sha256': original_unit['identity_sha256'],
            'original_logical_call_id': classification['logical_call_id'],
            'original_attempt_sha256': classification['attempt_sha256'],
            'failure_class': classification['failure_class'],
            'request_body_sha256': classification['request_body_sha256'],
            'policy': 'SAFE_PRE_SEND_OR_PROVIDER_REJECTION_ONE_SHOT_V1',
        },
    )
    return build_scientific_unit_identity(**raw)


def _execute_or_adopt_remediation(run_root: Path, plan: dict, verifier: dict, classification: dict) -> dict:
    from pchsi.reference_loop.canonical import domain_hash
    request_renderer, orchestrator, projection, manifest, schema, original_unit, access, validate_output = _runtime_context(run_root, plan)
    unit = _build_remediation_unit(original_unit, classification)
    postdir = run_root / 'post'
    put_json(postdir / 'autonomous_infrastructure_disposition.json', {
        'schema_id':'CURRENT_POST_AUTONOMOUS_INFRASTRUCTURE_DISPOSITION_V1',
        'policy':'SAFE_PRE_SEND_OR_PROVIDER_REJECTION_ONE_SHOT_V1',
        'classification_sha256':classification['classification_sha256'],
        'original_logical_call_id':classification['logical_call_id'],
        'original_attempt_sha256':classification['attempt_sha256'],
        'failure_class':classification['failure_class'],
        'retry_class':classification['retry_class'],
        'bytes_transmission_state':classification['bytes_transmission_state'],
        'same_logical_call_resend_authorized':False,
        'new_remediation_logical_call_max_count':1,
        'human_scientific_decision_required':False,
    })
    with ExitStack() as stack:
        stack.enter_context(patch.object(request_renderer, 'load_runtime_manifest', lambda: manifest))
        stack.enter_context(patch.object(orchestrator, 'load_runtime_manifest', lambda: manifest))
        stack.enter_context(patch.object(orchestrator, 'validate_stage_output', validate_output))
        bundle = request_renderer.render_stage_request(stage_id='R-POST-PRIMARY-V1', projection=projection)
        if bundle['request_body_sha256'] != classification['request_body_sha256']:
            raise ValueError('POST_REMEDIATION_REQUEST_BODY_DRIFT')
        logical_key = {
            'scientific_unit_identity_sha256': unit['identity_sha256'],
            'stage_id':'R-POST-PRIMARY-V1',
            'condition_id':None,
            'round_id':plan['round_id'],
            'policy_version':plan['source_request']['parent_policy_id'],
            'request_body_sha256':bundle['request_body_sha256'],
        }
        logical_id = domain_hash('COGNITIVE_LOGICAL_CALL_ID_V1', logical_key)
        root = postdir / 'remediation_calls'
        call = root / logical_id
        calls = 0
        if not call.exists():
            orchestrator.execute_one(
                output_root=root,
                unit_identity=unit,
                stage_id='R-POST-PRIMARY-V1',
                condition_id=None,
                round_id=plan['round_id'],
                policy_version=plan['source_request']['parent_policy_id'],
                projection=projection,
                task_access=access,
            )
            calls = 1
        evidence = _load_call_evidence(call)
        if not evidence.get('logical_call_terminal'):
            return {
                'status':'POST_REMEDIATION_PARTIAL_NO_SECOND_RETRY',
                'training_recommendation':None,
                'provider_calls_this_settlement':calls,
                'remediation_logical_call_id':logical_id,
            }
        artifact, status = _terminal(call, expected={'logical_call_id':logical_id, **logical_key}, projection=projection)
        if artifact is None:
            return {
                'status':'POST_REMEDIATION_TERMINAL_NO_SECOND_RETRY',
                'training_recommendation':None,
                'method_status':status,
                'failure_class':evidence.get('failure_class'),
                'provider_calls_this_settlement':calls,
                'remediation_logical_call_id':logical_id,
            }
        routed = route_accepted_post_artifact(
            run_root=run_root,
            plan=plan,
            verifier=verifier,
            artifact=artifact,
            logical_call_id=logical_id,
            provider_calls=calls,
        )
        routed['provider_calls_this_settlement'] = calls
        routed['remediation_logical_call_id'] = logical_id
        return routed


def settle_existing_post(run_root: Path, *, execute_remediation: bool) -> dict:
    run_root = Path(run_root).resolve()
    terminal_path = run_root / 'ROUND_EXECUTION_POST_SETTLEMENT_TERMINAL.json'
    if terminal_path.is_file():
        return read_json(terminal_path)
    lock_path = run_root / 'POST_SETTLEMENT.lock'
    with lock_path.open('a+b') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('POST_SETTLEMENT_ALREADY_ACTIVE')
        if terminal_path.is_file():
            return read_json(terminal_path)
        plan, verifier, continuation, post = _validate_base(run_root)
        classification = classify_existing_post(run_root)
        put_json(run_root / 'post' / 'POST_SETTLEMENT_CLASSIFICATION_V1.json', classification)
        disposition = classification['disposition']
        if disposition == 'ADOPT_ACCEPTED_NO_RESEND':
            call = Path(classification['call_dir'])
            projection = read_json(run_root / 'post' / 'projection.json')
            logical = read_json(call / 'logical_call.json')
            artifact, status = _terminal(call, expected={
                'logical_call_id':logical['logical_call_id'],
                'scientific_unit_identity_sha256':logical['scientific_unit_identity_sha256'],
                'stage_id':'R-POST-PRIMARY-V1','condition_id':None,
                'round_id':plan['round_id'],'policy_version':plan['source_request']['parent_policy_id'],
                'request_body_sha256':logical['request_body_sha256'],
            }, projection=projection)
            if artifact is None:
                raise ValueError('POST_SETTLEMENT_ACCEPTED_CLASSIFICATION_DRIFT')
            result = route_accepted_post_artifact(
                run_root=run_root, plan=plan, verifier=verifier, artifact=artifact,
                logical_call_id=logical['logical_call_id'], provider_calls=0,
            )
            result['provider_calls_this_settlement'] = 0
        elif disposition == 'ONE_AUTONOMOUS_INFRASTRUCTURE_REMEDIATION_ELIGIBLE':
            if not execute_remediation:
                return {
                    'status':'POST_AUTONOMOUS_REMEDIATION_PREPARED_NO_PROVIDER_CALL',
                    'training_recommendation':None,
                    'provider_calls_this_settlement':0,
                    'classification_sha256':classification['classification_sha256'],
                }
            result = _execute_or_adopt_remediation(run_root, plan, verifier, classification)
        elif disposition == 'PARTIAL_OR_UNKNOWN_NO_RESEND':
            result = {
                'status':'POST_PARTIAL_OR_UNKNOWN_NO_RESEND',
                'training_recommendation':None,
                'provider_calls_this_settlement':0,
                'initial_logical_call_id':classification.get('logical_call_id'),
            }
        else:
            result = {
                'status':'POST_METHOD_TERMINAL_NO_RESEND',
                'training_recommendation':None,
                'provider_calls_this_settlement':0,
                'initial_logical_call_id':classification.get('logical_call_id'),
                'method_status':classification.get('terminal_method_status'),
                'failure_class':classification.get('failure_class'),
            }
        terminal = {
            'schema_id':'CURRENT_CAUSAL_POST_SETTLEMENT_TERMINAL_V1',
            'plan_sha256':plan['plan_sha256'],
            'environment_result_package_sha256':verifier['environment_result_package_sha256'],
            'scientifically_complete_pair_count':verifier['scientifically_complete_pair_count'],
            'prior_continuation_terminal_sha256':continuation['continuation_terminal_sha256'],
            'classification_sha256':classification['classification_sha256'],
            **result,
            'training_execution_count':0,
            'full_round_closed':False,
            'next_round_launched':False,
            'max10_released':False,
            'human_scientific_decision_count':0,
            'same_logical_call_resend_count':0,
        }
        terminal['settlement_terminal_sha256'] = sha(canonical(terminal))
        put_json(terminal_path, terminal)
        return terminal


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--recovery-root', type=Path, required=True)
    ap.add_argument('--execute-remediation', action='store_true')
    args = ap.parse_args()

    classification = classify_existing_post(args.recovery_root)
    print('POST_SETTLEMENT_CLASSIFICATION=PASS', flush=True)
    print('POST_INITIAL_LOGICAL_CALL_ID=' + str(classification.get('logical_call_id')), flush=True)
    print('POST_INITIAL_METHOD_STATUS=' + str(classification.get('terminal_method_status')), flush=True)
    print('POST_INITIAL_FAILURE_CLASS=' + str(classification.get('failure_class')), flush=True)
    print('POST_INITIAL_RETRY_CLASS=' + str(classification.get('retry_class')), flush=True)
    print('POST_INITIAL_BYTES_TRANSMISSION_STATE=' + str(classification.get('bytes_transmission_state')), flush=True)
    print('POST_SETTLEMENT_DISPOSITION=' + classification['disposition'], flush=True)
    print('SAME_LOGICAL_CALL_RESEND_AUTHORIZED=false', flush=True)
    print('HUMAN_SCIENTIFIC_DECISION_REQUIRED=false', flush=True)

    if not args.execute_remediation and classification['disposition'] == 'ONE_AUTONOMOUS_INFRASTRUCTURE_REMEDIATION_ELIGIBLE':
        print('STATUS=POST_AUTONOMOUS_REMEDIATION_PREPARED_NO_PROVIDER_CALL', flush=True)
        print('PROVIDER_CALLS_THIS_SETTLEMENT=0', flush=True)
        return 0

    result = settle_existing_post(args.recovery_root, execute_remediation=args.execute_remediation)
    print('STATUS=' + str(result.get('status')), flush=True)
    print('TRAINING_RECOMMENDATION=' + str(result.get('training_recommendation')), flush=True)
    print('PROVIDER_CALLS_THIS_SETTLEMENT=' + str(result.get('provider_calls_this_settlement', 0)), flush=True)
    print('SAME_LOGICAL_CALL_RESEND_COUNT=' + str(result.get('same_logical_call_resend_count', 0)), flush=True)
    print('TRAINING_EXECUTION_COUNT=0', flush=True)
    print('FULL_MAX10_AUTONOMOUS_CAMPAIGN_RELEASED=false', flush=True)
    rec = result.get('training_recommendation')
    if rec in ('TRAIN', 'NO_TRAIN'):
        return 0
    if result.get('status') in ('POST_METHOD_TERMINAL_NO_RESEND', 'POST_PARTIAL_OR_UNKNOWN_NO_RESEND', 'POST_REMEDIATION_TERMINAL_NO_SECOND_RETRY', 'POST_REMEDIATION_PARTIAL_NO_SECOND_RETRY'):
        return 20
    return 20


if __name__ == '__main__':
    raise SystemExit(main())

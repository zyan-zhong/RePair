from __future__ import annotations

from contextlib import ExitStack
import copy
import fcntl
import json
from pathlib import Path
from unittest.mock import patch

from io_utils import canonical, digest_file, put_json, read_json, sha
from post_settlement import _load_call_evidence, classify_existing_post
from strong_post import _resolve_scientific_input_root, _terminal, route_accepted_post_artifact

ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / 'assets' / 'POST_CONTEXT_BUDGET_POLICY_V1.json'
PROMPT_PATH = ROOT / 'assets' / 'RESEARCHER_POST_PRIMARY_CONTEXT_BOUNDED_V1.txt'


def _hash_record(value: dict, field: str, label: str) -> None:
    expected = sha(canonical({k: v for k, v in value.items() if k != field}))
    if value.get(field) != expected:
        raise ValueError(label + '_HASH_MISMATCH')


def _single_initial_call(run_root: Path) -> Path:
    root = run_root / 'post' / 'calls'
    rows = sorted(p for p in root.iterdir() if p.is_dir() and not p.is_symlink())
    if len(rows) != 1:
        raise ValueError('CONTEXT_RECOVERY_INITIAL_CALL_COUNT_NOT_ONE:' + str(len(rows)))
    return rows[0]


def validate_context_overflow_recovery(run_root: Path) -> dict:
    run_root = Path(run_root).resolve()
    plan = read_json(run_root / 'EXECUTION_PLAN.json')
    if plan.get('plan_sha256') != sha(canonical({k: v for k, v in plan.items() if k != 'plan_sha256'})):
        raise ValueError('CONTEXT_RECOVERY_PLAN_HASH_MISMATCH')
    verifier = read_json(run_root / 'verifier' / 'ENVIRONMENT_RESULT_PACKAGE.json')
    if verifier.get('environment_result_package_sha256') != sha(canonical({k: v for k, v in verifier.items() if k != 'environment_result_package_sha256'})):
        raise ValueError('CONTEXT_RECOVERY_VERIFIER_HASH_MISMATCH')
    if verifier.get('status') != 'VERIFIED_COMPLETE':
        raise ValueError('CONTEXT_RECOVERY_VERIFIER_NOT_COMPLETE')
    if verifier.get('plan_sha256') != plan.get('plan_sha256'):
        raise ValueError('CONTEXT_RECOVERY_VERIFIER_PLAN_MISMATCH')
    if not isinstance(verifier.get('scientifically_complete_pair_count'), int) or verifier['scientifically_complete_pair_count'] <= 0:
        raise ValueError('CONTEXT_RECOVERY_NO_COMPLETE_PAIRS')

    continuation = read_json(run_root / 'ROUND_EXECUTION_CONTINUATION_TERMINAL.json')
    _hash_record(continuation, 'continuation_terminal_sha256', 'CONTEXT_RECOVERY_CONTINUATION')
    if continuation.get('status') != 'CURRENT_CAUSAL_POST_CONTINUATION_NOT_TERMINAL_NO_RESEND':
        raise ValueError('CONTEXT_RECOVERY_CONTINUATION_STATUS_CHANGED')
    if continuation.get('training_execution_count') not in (None, 0):
        raise ValueError('CONTEXT_RECOVERY_PRIOR_TRAINING_EXECUTED')

    settlement = read_json(run_root / 'ROUND_EXECUTION_POST_SETTLEMENT_TERMINAL.json')
    _hash_record(settlement, 'settlement_terminal_sha256', 'CONTEXT_RECOVERY_SETTLEMENT')
    if settlement.get('status') != 'POST_METHOD_TERMINAL_NO_RESEND':
        raise ValueError('CONTEXT_RECOVERY_SETTLEMENT_NOT_METHOD_TERMINAL')
    if settlement.get('method_status') != 'SEMANTIC_INVALID' or settlement.get('failure_class') != 'METHOD_CONTEXT_OVERFLOW':
        raise ValueError('CONTEXT_RECOVERY_SETTLEMENT_NOT_CONTEXT_OVERFLOW')
    if settlement.get('same_logical_call_resend_count') != 0:
        raise ValueError('CONTEXT_RECOVERY_PRIOR_SAME_LOGICAL_RESEND_PRESENT')
    if settlement.get('provider_calls_this_settlement') != 0:
        raise ValueError('CONTEXT_RECOVERY_SETTLEMENT_UNEXPECTED_PROVIDER_CALL')
    if settlement.get('training_execution_count') != 0 or settlement.get('full_round_closed') is True or settlement.get('next_round_launched') is True:
        raise ValueError('CONTEXT_RECOVERY_ROUND_ALREADY_ADVANCED')
    if settlement.get('plan_sha256') != plan['plan_sha256'] or settlement.get('environment_result_package_sha256') != verifier['environment_result_package_sha256']:
        raise ValueError('CONTEXT_RECOVERY_SETTLEMENT_LINEAGE_MISMATCH')

    classification = classify_existing_post(run_root)
    if classification.get('terminal_method_status') != 'SEMANTIC_INVALID' or classification.get('failure_class') != 'METHOD_CONTEXT_OVERFLOW':
        raise ValueError('CONTEXT_RECOVERY_CLASSIFICATION_NOT_EXACT_OVERFLOW')
    if classification.get('retry_class') != 'NO_RETRY' or classification.get('bytes_transmission_state') != 'CONFIRMED_SENT':
        raise ValueError('CONTEXT_RECOVERY_ORIGINAL_TRANSPORT_STATE_CHANGED')
    if classification.get('disposition') != 'POST_METHOD_TERMINAL_NO_RESEND':
        raise ValueError('CONTEXT_RECOVERY_ORIGINAL_DISPOSITION_CHANGED')

    call = _single_initial_call(run_root)
    evidence = _load_call_evidence(call)
    if evidence.get('logical_call_id') != classification.get('logical_call_id'):
        raise ValueError('CONTEXT_RECOVERY_INITIAL_CALL_ID_MISMATCH')
    return {
        'plan': plan,
        'verifier': verifier,
        'continuation': continuation,
        'settlement': settlement,
        'classification': classification,
        'original_call_dir': call,
    }


def _branch_index_row(row: dict) -> dict:
    replay = row.get('source_replay_report')
    replay_sha = replay.get('report_sha256') if isinstance(replay, dict) else None
    keys = (
        'branch_key_sha256', 'binding_sha256', 'source_state_sha256',
        'native_source_fingerprint_sha256', 'source_candidate_sha256', 'arm',
        'continuation_seed', 'replicate_index', 'evidence_complete',
        'scientific_outcome_produced', 'terminal_success', 'terminal_reason',
        'option_environment_step_count', 'policy_call_count_from_source',
        'environment_step_count_from_source', 'automatic_retry_count',
        'service_lease_sha256', 'journal_event_count', 'evidence_sha256',
        'typed_option_stop_reason', 'final_budget',
    )
    out = {key: row.get(key) for key in keys if key in row}
    out['source_replay_report_sha256'] = replay_sha
    return out


def _compact_environment(verifier: dict) -> dict:
    branches = verifier.get('branch_records')
    if not isinstance(branches, list):
        raise ValueError('CONTEXT_RECOVERY_BRANCH_RECORDS_NOT_ARRAY')
    state_results = verifier.get('state_results')
    pair_results = verifier.get('pair_results')
    if not isinstance(state_results, list) or not isinstance(pair_results, list):
        raise ValueError('CONTEXT_RECOVERY_EFFECT_ROWS_NOT_ARRAYS')
    branch_index = [_branch_index_row(row) for row in branches if isinstance(row, dict)]
    if len(branch_index) != len(branches):
        raise ValueError('CONTEXT_RECOVERY_BRANCH_RECORD_NOT_OBJECT')
    omitted = sorted({
        key for row in branches if isinstance(row, dict) for key in row
        if key not in branch_index[0] and key != 'source_replay_report'
    }) if branch_index else []
    value = {
        'schema_id': 'CURRENT_ROUND_POST_ENVIRONMENT_RESULT_PROJECTION_V1',
        'schema_version': 1,
        'source_environment_result_package_sha256': verifier['environment_result_package_sha256'],
        'plan_sha256': verifier['plan_sha256'],
        'round_id': verifier['round_id'],
        'verifier_status': verifier['status'],
        'scientifically_complete_pair_count': verifier['scientifically_complete_pair_count'],
        'frozen_pair_count': verifier['frozen_pair_count'],
        'selected_state_count': verifier['selected_state_count'],
        'planned_branch_count': verifier['planned_branch_count'],
        'stable_effect_counts': verifier['stable_effect_counts'],
        'state_results': state_results,
        'pair_results': pair_results,
        'branch_evidence_index': branch_index,
        'diagnostics': verifier.get('diagnostics', []),
        'hypothesis_scope_notice': verifier.get('hypothesis_scope_notice'),
        'comparison': verifier.get('comparison'),
        'automatic_environment_effect_assignment': verifier.get('automatic_environment_effect_assignment'),
        'human_decision_count': verifier.get('human_decision_count'),
        'training_authorized_by_this_verifier': verifier.get('training_authorized_by_this_verifier'),
        'projection_semantics': {
            'effect_labels_are_copied_from_independent_verifier': True,
            'all_state_results_included': True,
            'all_pair_results_included': True,
            'all_branch_evidence_identities_included': True,
            'raw_policy_call_payloads_included': False,
            'raw_environment_transition_payloads_included': False,
            'omitted_branch_fields': omitted,
            'omitted_payloads_remain_bound_by_branch_evidence_sha256': True,
            'planner_must_not_infer_omitted_raw_details': True,
        },
    }
    value['projection_sha256'] = sha(canonical(value))
    return value


def build_context_bounded_projection(run_root: Path, plan: dict, verifier: dict) -> dict:
    run_root = Path(run_root).resolve()
    original = read_json(run_root / 'post' / 'projection.json')
    if original.get('environment_result_package_sha256') != verifier.get('environment_result_package_sha256'):
        raise ValueError('CONTEXT_RECOVERY_ORIGINAL_PROJECTION_VERIFIER_MISMATCH')
    if original.get('round_id') != plan.get('round_id'):
        raise ValueError('CONTEXT_RECOVERY_ORIGINAL_PROJECTION_ROUND_MISMATCH')
    compact_env = _compact_environment(verifier)
    projection = {
        'round_id': plan['round_id'],
        'environment_result_package_sha256': verifier['environment_result_package_sha256'],
        'environment_result_package_projection': compact_env,
        'primary_pre_record_sha256': original['primary_pre_record_sha256'],
        'primary_pre_record': original['primary_pre_record'],
        'memory_pack_sha256': original['memory_pack_sha256'],
        'researcher_memory_view': original['researcher_memory_view'],
        'protocol_audit': original['protocol_audit'],
        'machine_output_contract': original['machine_output_contract'],
        'context_overflow_recovery': {
            'schema_id': 'CURRENT_POST_CONTEXT_OVERFLOW_RECOVERY_INPUT_V1',
            'original_logical_call_id': read_json(_single_initial_call(run_root) / 'logical_call.json')['logical_call_id'],
            'original_method_failure': 'METHOD_CONTEXT_OVERFLOW',
            'original_method_failure_preserved': True,
            'same_logical_call_resend': False,
            'full_environment_result_package_sha256': verifier['environment_result_package_sha256'],
            'compact_environment_projection_sha256': compact_env['projection_sha256'],
        },
    }
    return projection


def provider_request_size_bytes(bundle: dict) -> int:
    request = bundle.get('provider_request')
    if not isinstance(request, dict):
        raise ValueError('CONTEXT_RECOVERY_PROVIDER_REQUEST_NOT_OBJECT')
    return len(canonical(request))


def _validate_context_policy(policy: dict, manifest: dict) -> None:
    if policy.get('schema_id') != 'POST_CONTEXT_BUDGET_POLICY_V1':
        raise ValueError('CONTEXT_RECOVERY_POLICY_SCHEMA_CHANGED')
    if policy.get('provider_truncation_policy') != 'DISABLED':
        raise ValueError('CONTEXT_RECOVERY_POLICY_TRUNCATION_CHANGED')
    if manifest.get('truncation') != 'disabled':
        raise ValueError('CONTEXT_RECOVERY_PROVIDER_TRUNCATION_NOT_DISABLED')
    if policy.get('max_new_context_bounded_logical_calls_after_full_projection_overflow') != 1:
        raise ValueError('CONTEXT_RECOVERY_MAX_NEW_LOGICAL_CALLS_NOT_ONE')
    if policy.get('same_logical_call_resend_allowed') is not False:
        raise ValueError('CONTEXT_RECOVERY_SAME_LOGICAL_RESEND_NOT_FORBIDDEN')
    if policy.get('raw_branch_policy_calls_in_planner_projection') is not False:
        raise ValueError('CONTEXT_RECOVERY_RAW_POLICY_CALLS_NOT_FORBIDDEN')
    if policy.get('raw_branch_environment_transitions_in_planner_projection') is not False:
        raise ValueError('CONTEXT_RECOVERY_RAW_ENV_TRANSITIONS_NOT_FORBIDDEN')
    if policy.get('current_round_cardinality_constants_allowed') is not False:
        raise ValueError('CONTEXT_RECOVERY_CARDINALITY_CONSTANTS_NOT_FORBIDDEN')
    max_bytes = policy.get('max_provider_request_body_bytes')
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError('CONTEXT_RECOVERY_PROVIDER_BODY_BUDGET_INVALID')
    min_context = policy.get('min_model_context_window_tokens')
    if not isinstance(min_context, int) or min_context <= 0:
        raise ValueError('CONTEXT_RECOVERY_MODEL_CONTEXT_AUTHORITY_INVALID')
    if not isinstance(manifest.get('requested_model'), str) or not manifest['requested_model']:
        raise ValueError('CONTEXT_RECOVERY_REQUESTED_MODEL_AUTHORITY_MISSING')


def _build_runtime_context(run_root: Path, plan: dict, projection: dict):
    import jsonschema
    from pchsi.cognitive_runtime import request_renderer, orchestrator
    from pchsi.cognitive_runtime.researcher_primary import finalize_api_post_primary_v1
    from pchsi.reference_loop.canonical import domain_hash

    postdir = run_root / 'post'
    ctxdir = postdir / 'context_bounded_recovery'
    ctxdir.mkdir(exist_ok=True)
    manifest = copy.deepcopy(read_json(postdir / 'runtime_manifest.json'))
    schema = read_json(postdir / 'provider_schema.json')
    original_unit = read_json(postdir / 'unit.json')
    policy = read_json(POLICY_PATH)
    _validate_context_policy(policy, manifest)
    spec = copy.deepcopy(next(row for row in manifest['stage_rows'] if row['stage_id'] == 'R-POST-PRIMARY-V1'))
    spec['prompt_relative_path'] = str(PROMPT_PATH)
    spec['prompt_sha256'] = digest_file(PROMPT_PATH)
    spec['prompt_template_id'] = 'RESEARCHER_POST_PRIMARY_CONTEXT_BOUNDED_V1'
    spec['required_projection_identity_fields'] = [
        'round_id', 'environment_result_package_sha256',
        'environment_result_package_projection', 'primary_pre_record_sha256',
        'primary_pre_record', 'memory_pack_sha256', 'researcher_memory_view',
        'protocol_audit', 'machine_output_contract', 'context_overflow_recovery',
    ]
    manifest['stage_rows'] = [spec if row['stage_id'] == spec['stage_id'] else row for row in manifest['stage_rows']]
    manifest['runtime_manifest_sha256'] = domain_hash('UNIFIED_COGNITIVE_RUNTIME_MANIFEST_V1', manifest, excluded_field='runtime_manifest_sha256')

    input_root = _resolve_scientific_input_root(run_root, plan)
    access = read_json(input_root / 'pre_root' / 'V1232V_PRE_TASK_ACCESS_V1.json')

    def validate_output(*, stage_id, text, raw_response_sha256, projection):
        if stage_id != 'R-POST-PRIMARY-V1':
            raise ValueError('POST_CONTEXT_RECOVERY_STAGE_ONLY')
        value = json.loads(text)
        jsonschema.Draft202012Validator(schema).validate(value)
        return finalize_api_post_primary_v1(value, projection=projection)

    put_json(ctxdir / 'POST_CONTEXT_BUDGET_POLICY_V1.json', policy)
    put_json(ctxdir / 'projection.json', projection)
    put_json(ctxdir / 'runtime_manifest.json', manifest)
    put_json(ctxdir / 'provider_schema.json', schema)
    return request_renderer, orchestrator, manifest, schema, original_unit, access, validate_output, policy, ctxdir


def _context_unit(original_unit: dict, *, validation: dict, projection: dict, policy: dict) -> dict:
    from pchsi.cognitive_runtime.identity import build_scientific_unit_identity
    from pchsi.reference_loop.canonical import domain_hash
    raw = {k: v for k, v in original_unit.items() if k not in ('schema_id', 'schema_version', 'identity_sha256')}
    raw['scientific_unit_id'] = domain_hash(
        'CURRENT_ROUND_POST_CONTEXT_BOUNDED_RECOVERY_UNIT_V1',
        {
            'original_scientific_unit_identity_sha256': original_unit['identity_sha256'],
            'original_logical_call_id': validation['classification']['logical_call_id'],
            'original_attempt_sha256': validation['classification']['attempt_sha256'],
            'original_request_body_sha256': validation['classification']['request_body_sha256'],
            'original_failure_class': 'METHOD_CONTEXT_OVERFLOW',
            'environment_result_package_sha256': validation['verifier']['environment_result_package_sha256'],
            'compact_projection_sha256': sha(canonical(projection)),
            'context_budget_policy_sha256': digest_file(POLICY_PATH),
        },
    )
    return build_scientific_unit_identity(**raw)


def recover_context_overflow_post(run_root: Path, *, execute_call: bool) -> dict:
    run_root = Path(run_root).resolve()
    terminal_path = run_root / 'ROUND_EXECUTION_CONTEXT_RECOVERY_TERMINAL.json'
    if terminal_path.is_file():
        return read_json(terminal_path)
    validation = validate_context_overflow_recovery(run_root)
    plan, verifier = validation['plan'], validation['verifier']
    projection = build_context_bounded_projection(run_root, plan, verifier)
    request_renderer, orchestrator, manifest, schema, original_unit, access, validate_output, policy, ctxdir = _build_runtime_context(run_root, plan, projection)
    unit = _context_unit(original_unit, validation=validation, projection=projection, policy=policy)
    put_json(ctxdir / 'unit.json', unit)

    with (ctxdir / 'POST_CONTEXT_RECOVERY.lock').open('a+b') as lock, ExitStack() as stack:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        if terminal_path.is_file():
            return read_json(terminal_path)
        stack.enter_context(patch.object(request_renderer, 'load_runtime_manifest', lambda: manifest))
        stack.enter_context(patch.object(orchestrator, 'load_runtime_manifest', lambda: manifest))
        stack.enter_context(patch.object(orchestrator, 'validate_stage_output', validate_output))
        bundle = request_renderer.render_stage_request(stage_id='R-POST-PRIMARY-V1', projection=projection)
        body_bytes = provider_request_size_bytes(bundle)
        full_env_bytes = len(canonical(verifier))
        compact_env_bytes = len(canonical(projection['environment_result_package_projection']))
        preflight = {
            'schema_id': 'CURRENT_POST_CONTEXT_BOUNDED_REQUEST_PREFLIGHT_V1',
            'provider_request_body_bytes': body_bytes,
            'max_provider_request_body_bytes': policy['max_provider_request_body_bytes'],
            'full_environment_package_bytes': full_env_bytes,
            'compact_environment_projection_bytes': compact_env_bytes,
            'compact_projection_bytes': len(canonical(projection)),
            'full_environment_result_package_sha256': verifier['environment_result_package_sha256'],
            'compact_environment_projection_sha256': projection['environment_result_package_projection']['projection_sha256'],
            'original_method_failure_preserved': True,
            'same_logical_call_resend_authorized': False,
        }
        preflight['preflight_sha256'] = sha(canonical(preflight))
        put_json(ctxdir / 'request_preflight.json', preflight)
        if body_bytes > policy['max_provider_request_body_bytes']:
            result = {
                'status': 'POST_CONTEXT_BOUNDED_PROJECTION_STILL_TOO_LARGE_NO_PROVIDER_CALL',
                'training_recommendation': None,
                'provider_calls_this_context_recovery': 0,
                'original_logical_call_id': validation['classification']['logical_call_id'],
                'context_recovery_logical_call_id': None,
                'same_logical_call_resend_count': 0,
                'original_method_failure_preserved': True,
            }
        elif not execute_call:
            return {
                'status': 'POST_CONTEXT_BOUNDED_RECOVERY_PREFLIGHT_PASS_NO_PROVIDER_CALL',
                'training_recommendation': None,
                'provider_calls_this_context_recovery': 0,
                'provider_request_body_bytes': body_bytes,
                'max_provider_request_body_bytes': policy['max_provider_request_body_bytes'],
            }
        else:
            from pchsi.reference_loop.canonical import domain_hash
            logical_key = {
                'scientific_unit_identity_sha256': unit['identity_sha256'],
                'stage_id': 'R-POST-PRIMARY-V1',
                'condition_id': None,
                'round_id': plan['round_id'],
                'policy_version': plan['source_request']['parent_policy_id'],
                'request_body_sha256': bundle['request_body_sha256'],
            }
            logical_id = domain_hash('COGNITIVE_LOGICAL_CALL_ID_V1', logical_key)
            if logical_id == validation['classification']['logical_call_id']:
                raise ValueError('CONTEXT_RECOVERY_LOGICAL_CALL_COLLISION')
            calls_root = ctxdir / 'calls'
            call = calls_root / logical_id
            provider_calls = 0
            if not call.exists():
                orchestrator.execute_one(
                    output_root=calls_root,
                    unit_identity=unit,
                    stage_id='R-POST-PRIMARY-V1',
                    condition_id=None,
                    round_id=plan['round_id'],
                    policy_version=plan['source_request']['parent_policy_id'],
                    projection=projection,
                    task_access=access,
                )
                provider_calls = 1
            evidence = _load_call_evidence(call)
            artifact, method_status = _terminal(call, expected={'logical_call_id': logical_id, **logical_key}, projection=projection)
            if artifact is None:
                result = {
                    'status': 'POST_CONTEXT_BOUNDED_RECOVERY_TERMINAL_NO_SECOND_CALL',
                    'training_recommendation': None,
                    'method_status': method_status,
                    'failure_class': evidence.get('failure_class'),
                    'provider_calls_this_context_recovery': provider_calls,
                    'original_logical_call_id': validation['classification']['logical_call_id'],
                    'context_recovery_logical_call_id': logical_id,
                    'same_logical_call_resend_count': 0,
                    'original_method_failure_preserved': True,
                }
            else:
                routed = route_accepted_post_artifact(
                    run_root=run_root,
                    plan=plan,
                    verifier=verifier,
                    artifact=artifact,
                    logical_call_id=logical_id,
                    provider_calls=provider_calls,
                )
                result = {
                    **routed,
                    'status': routed['status'],
                    'provider_calls_this_context_recovery': provider_calls,
                    'original_logical_call_id': validation['classification']['logical_call_id'],
                    'context_recovery_logical_call_id': logical_id,
                    'same_logical_call_resend_count': 0,
                    'original_method_failure_preserved': True,
                }
        terminal = {
            'schema_id': 'CURRENT_CAUSAL_POST_CONTEXT_RECOVERY_TERMINAL_V1',
            'plan_sha256': plan['plan_sha256'],
            'environment_result_package_sha256': verifier['environment_result_package_sha256'],
            'scientifically_complete_pair_count': verifier['scientifically_complete_pair_count'],
            'prior_settlement_terminal_sha256': validation['settlement']['settlement_terminal_sha256'],
            **result,
            'training_execution_count': 0,
            'full_round_closed': False,
            'next_round_launched': False,
            'max10_released': False,
            'human_scientific_decision_count': 0,
        }
        terminal['context_recovery_terminal_sha256'] = sha(canonical(terminal))
        put_json(terminal_path, terminal)
        return terminal


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--recovery-root', type=Path, required=True)
    ap.add_argument('--execute-context-bounded-call', action='store_true')
    args = ap.parse_args()
    validated = validate_context_overflow_recovery(args.recovery_root)
    print('CONTEXT_OVERFLOW_RECOVERY_VALIDATION=PASS', flush=True)
    print('ORIGINAL_POST_LOGICAL_CALL_ID=' + str(validated['classification']['logical_call_id']), flush=True)
    print('ORIGINAL_POST_FAILURE_CLASS=' + str(validated['classification']['failure_class']), flush=True)
    print('ORIGINAL_METHOD_FAILURE_PRESERVED=true', flush=True)
    print('SAME_LOGICAL_CALL_RESEND_AUTHORIZED=false', flush=True)
    result = recover_context_overflow_post(args.recovery_root, execute_call=args.execute_context_bounded_call)
    print('STATUS=' + str(result.get('status')), flush=True)
    print('CONTEXT_RECOVERY_LOGICAL_CALL_ID=' + str(result.get('context_recovery_logical_call_id')), flush=True)
    print('TRAINING_RECOMMENDATION=' + str(result.get('training_recommendation')), flush=True)
    print('PROVIDER_CALLS_THIS_CONTEXT_RECOVERY=' + str(result.get('provider_calls_this_context_recovery',0)), flush=True)
    print('SAME_LOGICAL_CALL_RESEND_COUNT=' + str(result.get('same_logical_call_resend_count',0)), flush=True)
    print('TRAINING_EXECUTION_COUNT=' + str(result.get('training_execution_count',0)), flush=True)
    print('FULL_MAX10_AUTONOMOUS_CAMPAIGN_RELEASED=false', flush=True)
    return 0 if result.get('training_recommendation') in ('TRAIN','NO_TRAIN') else 20


if __name__ == '__main__':
    raise SystemExit(main())

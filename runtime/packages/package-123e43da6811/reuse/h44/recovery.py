from __future__ import annotations
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from io_utils import canonical, digest_file, put_json, read_json, sha, write_new_or_equal

ROOT = Path(__file__).resolve().parent

_TRANSIENT_ERROR_TYPES = {
    'PolicyTransportError', 'WorkerTimeoutError', 'WorkerExitedError',
    'TimeoutError', 'ConnectionError', 'ConnectionResetError',
    'BrokenPipeError', 'OSError',
}
_NONRETRYABLE_MESSAGE_FRAGMENTS = (
    'branch binding hash mismatch',
    'file identity mismatch',
    'native source fingerprint differs',
    'current exact gamefile hash mismatch',
    'source replay did not pass',
    'Memory snapshot differs',
    'typed contract/original candidate namespace mismatch',
    'policy service lease model/runtime mismatch',
    'exact gamefile missing or hash mismatch',
    'runtime file changed',
    'binding file changed',
)
_F1_PROMPT_MISMATCH = 'current Memory adapter does not reproduce exact source prompt'
_KNOWN_REPLAY_REPORT_FIELD_DRIFT = (
    "'SourceStateReplayReportV1' object has no attribute 'exact_match'"
)


def _branch_events(branch_dir: Path) -> list[dict[str, Any]]:
    root = branch_dir / 'events'
    rows = []
    if not root.is_dir():
        return rows
    for path in sorted(root.glob('*.json')):
        if path.is_file() and not path.is_symlink():
            try:
                rows.append(read_json(path))
            except Exception:
                rows.append({'type': 'UNREADABLE_EVENT', 'path': str(path)})
    return rows


def _validate_hash_record(value: dict, field: str) -> None:
    if value.get(field) != sha(canonical({k: v for k, v in value.items() if k != field})):
        raise ValueError('record identity mismatch:' + field)


def diagnose(prior_root: Path) -> dict[str, Any]:
    prior_root = prior_root.resolve()
    plan_path = prior_root / 'EXECUTION_PLAN.json'
    terminal_path = prior_root / 'ROUND_EXECUTION_TERMINAL.json'
    verifier_path = prior_root / 'verifier/ENVIRONMENT_RESULT_PACKAGE.json'
    gpu_path = prior_root / 'GPU_JOB_TERMINAL.json'
    for path in (plan_path, terminal_path, verifier_path, gpu_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError('required prior receipt missing:' + str(path))
    plan = read_json(plan_path)
    if plan.get('plan_sha256') != sha(canonical({k: v for k, v in plan.items() if k != 'plan_sha256'})):
        raise ValueError('prior execution plan identity mismatch')
    terminal = read_json(terminal_path)
    verifier = read_json(verifier_path)
    gpu = read_json(gpu_path)
    if terminal.get('status') != 'NATIVE_INFRA_OR_PROTOCOL_INVALID_NO_SCIENTIFIC_NO_TRAIN':
        raise ValueError('prior terminal is not the zero-scientific-pair recovery class')
    if verifier.get('status') != 'NO_SCIENTIFICALLY_COMPLETE_PAIRS' or verifier.get('scientifically_complete_pair_count') != 0:
        raise ValueError('prior verifier is not zero scientifically complete pairs')
    if terminal.get('environment_result_package_sha256') != verifier.get('environment_result_package_sha256'):
        raise ValueError('terminal/verifier result identity mismatch')
    if verifier.get('environment_result_package_sha256') != sha(canonical({k: v for k, v in verifier.items() if k != 'environment_result_package_sha256'})):
        raise ValueError('prior verifier package identity mismatch')
    if terminal.get('training_execution_count') not in (None, 0):
        raise ValueError('prior attempt performed training')
    if terminal.get('full_round_closed') is True or terminal.get('next_round_launched') is True:
        raise ValueError('prior round is already closed or advanced')

    binding_rows = {row['binding']['branch_key_sha256']: row for row in plan['branch_bindings']}
    handoff_rows = {row['branch_key_sha256']: row for row in plan['handoff']['branch_plan']}
    if set(binding_rows) != set(handoff_rows):
        raise ValueError('prior executable branch set differs from frozen handoff')

    branches = []
    missing_terminals = []
    pair_map: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for key, frozen in sorted(handoff_rows.items()):
        bdir = prior_root / 'branches' / key
        terminal_file = bdir / 'BRANCH_TERMINAL.json'
        intent_file = bdir / 'BRANCH_INTENT.json'
        row = {
            'branch_key_sha256': key,
            'source_state_sha256': frozen['source_state_sha256'],
            'replicate_index': frozen['replicate_index'],
            'arm': frozen['arm'],
            'terminal_present': terminal_file.is_file(),
            'intent_present': intent_file.is_file(),
        }
        if terminal_file.is_file():
            value = read_json(terminal_file)
            _validate_hash_record(value, 'evidence_sha256')
            events = _branch_events(bdir)
            row.update({
                'status': value.get('status'),
                'error_type': value.get('error_type'),
                'error_message': value.get('error_message'),
                'evidence_complete': value.get('evidence_complete') is True,
                'scientific_outcome_produced': value.get('scientific_outcome_produced') is True,
                'terminal_success': value.get('terminal_success'),
                'option_environment_step_count': value.get('option_environment_step_count'),
                'journal_event_count': value.get('journal_event_count'),
                'event_types': [e.get('type') for e in events],
                'scientific_environment_action_result_count': sum(e.get('type') == 'ENVIRONMENT_ACTION_RESULT' for e in events),
                'policy_call_result_count': sum(e.get('type') == 'POLICY_CALL_RESULT' for e in events),
            })
        else:
            row.update(status='MISSING_TERMINAL', error_type=None, error_message=None,
                       evidence_complete=False, scientific_outcome_produced=False,
                       terminal_success=None, option_environment_step_count=None,
                       journal_event_count=None, event_types=[],
                       scientific_environment_action_result_count=0,
                       policy_call_result_count=0)
            missing_terminals.append(key)
        branches.append(row)
        pair_map[(row['source_state_sha256'], row['replicate_index'])][row['arm']] = row

    pair_rows = []
    all_retryable = True
    retry_reasons = []
    for group, arms in sorted(pair_map.items()):
        if set(arms) != {'F0', 'F1'}:
            raise ValueError('frozen pair arm set changed')
        f0, f1 = arms['F0'], arms['F1']
        pair_complete = bool(
            f0['scientific_outcome_produced'] and f0['evidence_complete'] and
            f1['scientific_outcome_produced'] and f1['evidence_complete'] and
            (f1.get('option_environment_step_count') or 0) > 0
        )
        reasons = []
        retryable = not pair_complete
        if pair_complete:
            retryable = False
            reasons.append('PAIR_ALREADY_SCIENTIFICALLY_COMPLETE')
        if not f0['terminal_present'] or not f1['terminal_present']:
            retryable = False
            reasons.append('MISSING_BRANCH_TERMINAL_AMBIGUOUS_NO_RETRY')
        # A zero-intervention scientific F1 is protocol missingness, not an infra retry target.
        if (f0['scientific_outcome_produced'] and f1['scientific_outcome_produced'] and
                (f1.get('option_environment_step_count') or 0) == 0):
            retryable = False
            reasons.append('SCIENTIFIC_ZERO_INTERVENTION_PROTOCOL_MISSINGNESS')
        for arm_name, branch in (('F0', f0), ('F1', f1)):
            if branch['scientific_outcome_produced']:
                continue
            msg = str(branch.get('error_message') or '')
            etype = branch.get('error_type')
            if any(fragment in msg for fragment in _NONRETRYABLE_MESSAGE_FRAGMENTS):
                # One narrow H3 correction: F1 source-prompt parity was checked before any F1 policy call.
                if arm_name == 'F1' and _F1_PROMPT_MISMATCH in msg:
                    reasons.append('H3_FIX_F1_PREINTERVENTION_SOURCE_PROMPT_PARITY')
                else:
                    retryable = False
                    reasons.append('NONRETRYABLE_IDENTITY_OR_REPLAY_DEFECT:' + arm_name)
            elif _F1_PROMPT_MISMATCH in msg:
                if arm_name == 'F1':
                    reasons.append('H3_FIX_F1_PREINTERVENTION_SOURCE_PROMPT_PARITY')
                else:
                    retryable = False
                    reasons.append('F0_SOURCE_PROMPT_EQUIVALENCE_FAILED')
            elif (
                etype == 'AttributeError'
                and msg == _KNOWN_REPLAY_REPORT_FIELD_DRIFT
            ):
                # Known package-local field drift. The exception is raised after
                # exact source replay but before run_branch_core. Pair retry is
                # legal only when journal evidence proves no scientific action or
                # policy call was executed.
                if (
                    branch.get('scientific_environment_action_result_count', 0) == 0
                    and branch.get('policy_call_result_count', 0) == 0
                    and branch.get('option_environment_step_count') in (None, 0)
                ):
                    reasons.append(
                        'H4_FIX_REPLAY_REPORT_STATUS_FIELD_DRIFT:' + arm_name
                    )
                else:
                    retryable = False
                    reasons.append(
                        'KNOWN_REPLAY_REPORT_DEFECT_AFTER_SCIENTIFIC_EFFECT_NO_RETRY:'
                        + arm_name
                    )
            elif etype in _TRANSIENT_ERROR_TYPES or 'HTTP transport failed' in msg:
                reasons.append('TRANSIENT_RUNTIME_OR_TRANSPORT:' + arm_name)
            elif branch.get('status') in ('BRANCH_INFRASTRUCTURE_OR_PROTOCOL_INVALID', 'BRANCH_CLEANUP_INVALID'):
                # Unknown deterministic package/protocol failures are not blindly retried.
                retryable = False
                reasons.append('UNKNOWN_PROTOCOL_DEFECT_NO_BLIND_RETRY:' + arm_name + ':' + str(etype))
            else:
                retryable = False
                reasons.append('UNCLASSIFIED_BRANCH_STATE:' + arm_name)
        if not retryable:
            all_retryable = False
        pair_rows.append({
            'source_state_sha256': group[0], 'replicate_index': group[1],
            'retryable_as_full_pair': retryable, 'reasons': reasons,
            'f0': f0, 'f1': f1,
        })
        retry_reasons.extend(reasons)

    zero_branch_effects = not any((prior_root / 'branches').glob('*/BRANCH_INTENT.json'))
    allocation_retryable = False
    allocation_reason = None
    if zero_branch_effects and gpu.get('status') == 'NATIVE_EXECUTION_INVALID':
        etype = gpu.get('error_type')
        msg = str(gpu.get('error_message') or '')
        if etype in _TRANSIENT_ERROR_TYPES or any(x in msg.lower() for x in ('readiness', 'terminated before readiness', 'tcp', 'http')):
            allocation_retryable = True
            allocation_reason = 'ZERO_BRANCH_EFFECT_TRANSIENT_ALLOCATION_FAILURE'

    retry_mode = None
    if allocation_retryable:
        retry_mode = 'WHOLE_ALLOCATION_ZERO_BRANCH_EFFECT_RETRY'
    elif all_retryable and pair_rows:
        retry_mode = 'ALL_INCOMPLETE_PAIRS_PAIRED_OPERATIONAL_RETRY'

    census = {
        'schema_id': 'CURRENT_CAUSAL_ZERO_PAIR_FAILURE_CENSUS_V1',
        'prior_run_root': str(prior_root),
        'prior_plan_sha256': plan['plan_sha256'],
        'prior_terminal_sha256': digest_file(terminal_path),
        'prior_verifier_sha256': verifier['environment_result_package_sha256'],
        'prior_gpu_terminal_sha256': digest_file(gpu_path),
        'selected_state_count': len(plan['states']),
        'planned_branch_count': len(plan['handoff']['branch_plan']),
        'prior_scientifically_complete_pair_count': 0,
        'missing_branch_terminal_count': len(missing_terminals),
        'branch_rows': branches,
        'pair_rows': pair_rows,
        'retry_mode': retry_mode,
        'automatic_pair_retry_authorized': retry_mode is not None,
        'scientific_candidate_reselection': False,
        'replacement_state_count': 0,
        'top_up_state_count': 0,
        'human_scientific_decision_count': 0,
        'prior_results_preserved_as_provenance': True,
    }
    census['census_sha256'] = sha(canonical(census))
    return census


def materialize_recovery(prior_root: Path, census: dict[str, Any]) -> Path:
    if not census.get('automatic_pair_retry_authorized'):
        raise RuntimeError('CURRENT_ZERO_PAIR_ATTEMPT_NOT_AUTOMATICALLY_RECOVERABLE')
    identity = read_json(ROOT / 'PACKAGE_IDENTITY.json')
    attempt_material = {
        'package_identity': identity,
        'prior_plan_sha256': census['prior_plan_sha256'],
        'prior_terminal_sha256': census['prior_terminal_sha256'],
        'prior_verifier_sha256': census['prior_verifier_sha256'],
        'retry_mode': census['retry_mode'],
    }
    attempt_id = sha(canonical(attempt_material))[:32]
    recovery_root = prior_root / 'paired_operational_recovery_attempts' / attempt_id
    recovery_root.mkdir(parents=True, exist_ok=True)
    authority = {
        'schema_id': 'CURRENT_CAUSAL_PAIRED_OPERATIONAL_RECOVERY_AUTHORITY_V1',
        'attempt_id': attempt_id,
        'retry_mode': census['retry_mode'],
        'prior_run_root': str(prior_root),
        'prior_terminal_sha256': census['prior_terminal_sha256'],
        'prior_verifier_sha256': census['prior_verifier_sha256'],
        'scientific_handoff_unchanged': True,
        'pair_level_retry_not_single_arm_retry': True,
        'candidate_reselection_performed': False,
        'replacement_state_count': 0,
        'top_up_state_count': 0,
        'human_scientific_decision_count': 0,
        'automatic_retry_ordinal': 1,
        'second_automatic_pair_retry_authorized': False,
    }
    authority['authority_sha256'] = sha(canonical(authority))
    put_json(recovery_root / 'PAIR_RECOVERY_AUTHORITY.json', authority)
    put_json(recovery_root / 'PRIOR_FAILURE_CENSUS.json', census)
    # Preserve the exact scientific plan bytes. Branch binding paths deliberately
    # continue to point at the immutable original plan materialization.
    plan_bytes = (prior_root / 'EXECUTION_PLAN.json').read_bytes()
    write_new_or_equal(recovery_root / 'EXECUTION_PLAN.json', plan_bytes)
    return recovery_root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--prior-run-root', type=Path, required=True)
    ap.add_argument('--execute-recovery', action='store_true')
    args = ap.parse_args()
    prior = args.prior_run_root.resolve()
    lock_path = prior / 'H4_RECOVERY.lock'
    with lock_path.open('a+b') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('STATUS=H4_RECOVERY_ALREADY_ACTIVE', flush=True)
            return 17
        census = diagnose(prior)
        audit_root = prior / 'recovery_audit'
        audit_root.mkdir(parents=True, exist_ok=True)
        census_path = audit_root / (census['census_sha256'] + '.json')
        if census_path.exists():
            existing = read_json(census_path)
            if existing != census:
                raise RuntimeError('existing recovery census identity mismatch')
        else:
            put_json(census_path, census)
        print('H4_FAILURE_CENSUS=' + str(census_path), flush=True)
        print('H4_AUTOMATIC_PAIR_RECOVERY_ELIGIBLE=' + str(bool(census['automatic_pair_retry_authorized'])).lower(), flush=True)
        print('H4_RETRY_MODE=' + str(census['retry_mode']), flush=True)
        if not census['automatic_pair_retry_authorized']:
            print('STATUS=CURRENT_ZERO_PAIR_ATTEMPT_DIAGNOSED_NO_BLIND_RETRY', flush=True)
            return 20
        recovery_root = materialize_recovery(prior, census)
        print('CURRENT_ROUND_RECOVERY_ROOT=' + str(recovery_root), flush=True)
        if not args.execute_recovery:
            print('STATUS=PAIRED_OPERATIONAL_RECOVERY_PREPARED_NO_EXECUTION', flush=True)
            return 0
        log_path = recovery_root / 'controller.log'
        with log_path.open('ab', buffering=0) as log:
            child = subprocess.Popen(
                [sys.executable, '-B', str(ROOT / 'controller.py'), '--resident-root', str(recovery_root)],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        print('STATUS=PAIRED_OPERATIONAL_RECOVERY_CONTROLLER_DETACHED', flush=True)
        print('CONTROLLER_PID=' + str(child.pid), flush=True)
        print('CONTROLLER_LOG=' + str(log_path), flush=True)
        print('MAX10_RELEASED=false', flush=True)
        return 0


if __name__ == '__main__':
    raise SystemExit(main())

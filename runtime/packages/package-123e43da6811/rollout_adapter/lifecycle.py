"""One nonblocking full-round gate tick; caller owns durable polling/deadline."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from .materializer import AuthorityError, canonical, checked, digest, obj, put, ref, native_contracts, no_symlink_ancestors


def run_command(argv, *, timeout=600):
    try:
        cp = subprocess.Popen(argv, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except (FileNotFoundError, PermissionError) as exc:
        return {'returncode': 127 if isinstance(exc, FileNotFoundError) else 126,
                'stdout': '', 'stderr': str(exc), 'send_attempted': False, 'error_type': type(exc).__name__}
    # Once construction succeeds, communication and wait errors cannot prove no send.
    try:
        with cp:
            try:
                stdout, stderr = cp.communicate(timeout=timeout)
            except BaseException:
                try:
                    cp.kill()
                except OSError:
                    pass
                raise
        return {'returncode': cp.returncode, 'stdout': stdout, 'stderr': stderr}
    except subprocess.TimeoutExpired:
        return {'returncode': 124, 'stdout': '', 'stderr': 'TIMEOUT', 'send_attempted': True, 'error_type': 'TimeoutExpired'}
    except Exception as exc:
        return {'returncode': 125, 'stdout': '', 'stderr': str(exc), 'send_attempted': True, 'error_type': type(exc).__name__}


def _claim(path, value):
    if Path(path).exists():
        return False
    return put(path, canonical(value))


def _result(status, **extra):
    return {'schema_id': 'REGISTERED_FRESH_ROLLOUT_GATE_STATUS_V1', 'status': status,
            'scientific_rollout_valid': False, 'full_campaign_released': False, **extra}


def verify_materialization(manifest):
    root = Path(manifest['root']).resolve()
    for pkey, hkey in [('request_path', 'request_file_sha256'), ('capsule_path', 'capsule_sha256'), ('shard_plan_path', 'shard_plan_sha256'), ('runner_path', 'runner_sha256')]:
        path = Path(manifest[pkey])
        if not path.resolve().is_relative_to(root):
            raise AuthorityError('MATERIALIZED_FILE_OUTSIDE_CURRENT_ROOT')
        checked({'path': path, 'sha256': manifest[hkey]})
    for name, expected in manifest['source_files'].items():
        path = Path(manifest['source_root']) / name
        if not path.resolve().is_relative_to(root):
            raise AuthorityError('SOURCE_OUTSIDE_CURRENT_ROOT')
        checked({'path': path, 'sha256': expected})
    for name, expected in manifest['capsule_member_sha256'].items():
        path = root / 'input_capsule' / name
        if not path.resolve().is_relative_to(root):
            raise AuthorityError('CAPSULE_MEMBER_OUTSIDE_CURRENT_ROOT')
        checked({'path': path, 'sha256': expected})
    return root


def validate_handoff(manifest):
    root = verify_materialization(manifest)
    hp = root / 'round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json'
    gp = root / 'round_evidence/PCHSI_V1232K_GLOBAL_TERMINAL_V1.json'
    if not hp.is_file() or not gp.is_file():
        raise AuthorityError('GLOBAL_TERMINAL_AND_HANDOFF_REQUIRED')
    handoff = obj(ref(hp)); terminal = obj(ref(gp))
    if terminal.get('scientific_rollout_valid') is not True or terminal.get('handoff_path') != str(hp) or terminal.get('handoff_sha256') != digest(hp.read_bytes()):
        raise AuthorityError('GLOBAL_TERMINAL_HANDOFF_MISMATCH')
    if handoff.get('round_id') != manifest['round_id'] or handoff.get('rollout_request_sha256') != manifest['request_file_sha256'] or handoff.get('scientific_rollout_valid') is not True:
        raise AuthorityError('HANDOFF_CURRENT_FORMAL_REQUEST_MISMATCH')
    for pkey, hkey in [('rollout_request_path', 'rollout_request_sha256'), ('rollout_execution_binding_path', 'rollout_execution_binding_sha256'),
                       ('rollout_universe_path', 'rollout_universe_sha256'), ('failure_cohort_path', 'failure_cohort_sha256'), ('attempt_bundle_index_path', 'attempt_bundle_index_sha256')]:
        path = Path(handoff[pkey])
        if not path.resolve().is_relative_to(root):
            raise AuthorityError('HANDOFF_CONTAINS_FOREIGN_ROOT')
        checked({'path': path, 'sha256': handoff[hkey]})
    binding = json.loads(Path(handoff['rollout_execution_binding_path']).read_bytes())
    if binding != manifest['formal_execution_binding']:
        raise AuthorityError('HANDOFF_FORMAL_EXECUTION_BINDING_MISMATCH')
    if handoff.get('infrastructure_invalid_count') != 0 or handoff.get('protocol_invalid_count') != 0:
        raise AuthorityError('HANDOFF_INVALID_ROWS')
    universe = json.loads(Path(handoff['rollout_universe_path']).read_bytes())
    if universe.get('request_sha256') != manifest['request_sha256']:
        raise AuthorityError('HANDOFF_UNIVERSE_REQUEST_MISMATCH')
    try:
        native_path = Path(manifest['implementation_worktree']) / 'src/pchsi/round_control/rollout_collection.py'
        checked({'path':native_path, 'sha256':manifest['formal_execution_binding']['rollout_control_source_sha256']})
        native = native_contracts(Path(manifest['implementation_worktree']))
        rows = tuple(native.RoundEpisodeTerminalV1(**r) for r in universe['terminal_rows'])
        sealed = native.seal_rollout_universe(request_sha256=manifest['request_sha256'], terminals=rows)
        if sealed.to_dict() != universe:
            raise AuthorityError('HANDOFF_NATIVE_UNIVERSE_CENSUS_OR_DOMAIN_MISMATCH')
        plan = obj({'path':manifest['shard_plan_path'],'sha256':manifest['shard_plan_sha256']})
        if sealed.scheduled_count != plan['total_schedule_count']:
            raise AuthorityError('HANDOFF_FROZEN_SCHEDULE_COUNT_MISMATCH')
        for key in ('scheduled_count','success_count','failure_count','infrastructure_invalid_count','protocol_invalid_count','scientific_rollout_valid'):
            if handoff.get(key) != getattr(sealed,key) or terminal.get(key) != getattr(sealed,key):
                raise AuthorityError('HANDOFF_TERMINAL_CENSUS_MISMATCH:' + key)
        cohort = json.loads(Path(handoff['failure_cohort_path']).read_bytes())
        if native.build_failure_cohort(sealed).to_dict() != cohort:
            raise AuthorityError('HANDOFF_NATIVE_FAILURE_COHORT_MISMATCH')
        index = json.loads(Path(handoff['attempt_bundle_index_path']).read_bytes())
        entries = index['rows']
        if index.get('schema_id')!='ROUND_SHARDED_ATTEMPT_BUNDLE_INDEX_V1' or index.get('request_sha256')!=manifest['request_sha256'] or index.get('row_count')!=len(rows) or len(entries)!=len(rows) or index.get('fatal_shards')!=[] or index.get('human_selection_performed') is not False:
            raise AuthorityError('HANDOFF_CURRENT_ATTEMPT_INDEX_MISMATCH')
        intent = obj(ref(root/'SUBMISSION_INTENT.json'))
        if intent.get('manifest_sha256') != digest(Path(manifest['manifest_path']).read_bytes()):
            raise AuthorityError('HANDOFF_SUBMISSION_MANIFEST_MISMATCH')
        preflight = obj(intent['preflight'])
        schedule = preflight['schedule_rows']
        if preflight.get('request_file_sha256')!=manifest['request_file_sha256'] or len(schedule)!=len(rows):
            raise AuthorityError('HANDOFF_NATIVE_PREFLIGHT_SCHEDULE_MISMATCH')
        for ordinal, (row, entry, expected) in enumerate(zip(rows,entries,schedule)):
            if any(getattr(row,key)!=expected[key] for key in ('scientific_cell_id','execution_attempt_id','task_id','task_index')):
                raise AuthorityError('HANDOFF_NATIVE_SCHEDULE_IDENTITY_MISMATCH')
            shard_id = ordinal % plan['shard_count']
            shard_root = root/'shards'/f'{shard_id:04d}'
            bundle = shard_root/'rollout_run/attempts'/row.execution_attempt_id
            attempt_terminal = shard_root/'rollout_run/attempt_ledger'/(row.execution_attempt_id+'.terminal.json')
            if entry.get('global_ordinal')!=ordinal or entry.get('shard_id')!=shard_id or entry.get('scientific_cell_id')!=row.scientific_cell_id or entry.get('attempt_bundle_path')!=str(bundle) or entry.get('attempt_terminal_path')!=str(attempt_terminal):
                raise AuthorityError('HANDOFF_ATTEMPT_INDEX_IDENTITY_MISMATCH')
            no_symlink_ancestors(bundle); no_symlink_ancestors(attempt_terminal)
            if not bundle.is_dir() or not attempt_terminal.is_file():
                raise AuthorityError('HANDOFF_NATIVE_ATTEMPT_ARTIFACT_MISSING')
            sidecar = obj({'path':shard_root/'cell_terminals'/f'{ordinal:05d}.json','sha256':row.terminal_receipt_sha256})
            if any(sidecar.get(key)!=getattr(row,key) for key in ('scientific_cell_id','execution_attempt_id','task_id','task_index','status','success')):
                raise AuthorityError('HANDOFF_CELL_TERMINAL_IDENTITY_MISMATCH')
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc,AuthorityError):
            raise
        raise AuthorityError('HANDOFF_NATIVE_ARTIFACT_INVALID:'+str(exc)) from exc
    return {'path': str(hp), 'sha256': digest(hp.read_bytes()), 'handoff': handoff}


def advance(manifest_path, *, execute=False, preflight_timeout_seconds=600):
    """Materialize is separate; True explicitly authorizes preflight/scheduler.

    No blocking monitor and no Analyzer call. The owning full-round driver calls
    this repeatedly, owns deadline/containment, and consumes only a valid handoff.
    """
    manifest_path = Path(manifest_path)
    m = obj(ref(manifest_path)); root = verify_materialization(m)
    mh = digest(manifest_path.read_bytes())
    intent = root / 'SUBMISSION_INTENT.json'; receipt = root / 'SUBMISSION_RECEIPT.json'
    if intent.exists() and not receipt.exists():
        attempt = root / 'SUBMISSION_ATTEMPT.json'
        if attempt.is_file() and obj(ref(attempt)).get('send_attempted') is False:
            return _result('SUBMISSION_NOT_SENT_EXECUTABLE_MISSING')
        return _result('SUBMISSION_AMBIGUOUS_NO_RESEND')
    for relative in ['PCHSI_V1232K_GATE_FAILURE_V1.json', 'round_evidence/PCHSI_V1232K_GLOBAL_FINALIZE_FAILURE_V1.json']:
        p = root / relative
        if p.is_file():
            return _result('ROLLOUT_FAILED_NO_RESEND', failure=ref(p))
    terminal = root / 'round_evidence/PCHSI_V1232K_GLOBAL_TERMINAL_V1.json'
    if terminal.is_file():
        if obj(ref(terminal)).get('scientific_rollout_valid') is not True:
            return _result('SCIENTIFIC_ROLLOUT_INVALID', terminal=ref(terminal))
        h = validate_handoff(m)
        return _result('VALID_CURRENT_ROUND_HANDOFF', scientific_rollout_valid=True, handoff=h)
    if not receipt.is_file():
        if not execute:
            return _result('MATERIALIZED_NATIVE_PREFLIGHT_REQUIRED')
        preflight = root / 'NATIVE_CPU_PREFLIGHT.json'
        if not preflight.is_file():
            argv = [sys.executable, '-B', str(Path(m['source_root']) / 'native_preflight.py'), '--capsule-root', str(root / 'input_capsule'),
                    '--worktree', m['implementation_worktree'], '--request', m['request_path'], '--plan', m['shard_plan_path'], '--output', str(preflight)]
            result = run_command(argv, timeout=preflight_timeout_seconds)
            if result['returncode'] != 0:
                return _result('NATIVE_PREFLIGHT_FAILED', preflight=result)
        check = obj(ref(preflight))
        if check.get('status') != 'PASS' or check.get('request_file_sha256') != m['request_file_sha256'] or check.get('current_round_id') != m['round_id']:
            raise AuthorityError('NATIVE_PREFLIGHT_CURRENT_REQUEST_MISMATCH')
        # Recheck bytes immediately before reserving the irreversible boundary.
        verify_materialization(m)
        if not _claim(intent, {'manifest_sha256': mh, 'argv': m['sbatch_argv'], 'preflight': ref(preflight)}):
            return _result('SUBMISSION_AMBIGUOUS_NO_RESEND')
        result = run_command(m['sbatch_argv'], timeout=120)
        put(root / 'SUBMISSION_ATTEMPT.json', canonical(result))
        job = result['stdout'].strip().split(';', 1)[0]
        if result['returncode'] != 0 or not job.isdigit():
            return _result('SUBMISSION_NOT_SENT_EXECUTABLE_MISSING' if result.get('send_attempted') is False else 'SUBMISSION_FAILED_NO_RESEND', submission=result)
        put(receipt, canonical({'manifest_sha256': mh, 'array_job_id': job, 'submitted_held': True}))
    sub = obj(ref(receipt))
    if sub.get('manifest_sha256') != mh:
        raise AuthorityError('SUBMISSION_DIFFERENT_MANIFEST')
    job = sub['array_job_id']
    release = root / 'GATE_RELEASE_RECEIPT.json'
    if not release.is_file():
        if not execute:
            return _result('SUBMITTED_HELD_GATE_RELEASE_REQUIRED', array_job_id=job)
        target = job + '_' + str(m['gate_shard_id'])
        if not _claim(root / 'GATE_RELEASE_INTENT.json', {'manifest_sha256': mh, 'target': target}):
            return _result('GATE_RELEASE_AMBIGUOUS_NO_RESEND', array_job_id=job)
        result = run_command(['scontrol', 'release', target], timeout=120)
        put(release, canonical({'manifest_sha256': mh, 'target': target, **result}))
    released = obj(ref(release))
    if released.get('manifest_sha256') != mh or released.get('returncode') != 0:
        return _result('GATE_RELEASE_FAILED_NO_RESEND', array_job_id=job)
    queue = run_command(['squeue', '--noheader', '--jobs', job, '--format', '%i|%T'], timeout=120)
    inactive = not queue['stdout'].strip() and (queue['returncode'] == 0 or 'Invalid job id' in queue['stderr'])
    return _result('WAITING_FOR_CURRENT_HANDOFF' if not inactive else 'ARRAY_INACTIVE_AWAITING_PUBLICATION', array_job_id=job, queue=queue)

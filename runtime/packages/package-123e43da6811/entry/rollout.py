"""Resident polling of the registered native rollout owner."""
from __future__ import annotations

from pathlib import Path
import time

from rollout_adapter.materializer import canonical, checked, obj, put, ref, AuthorityError
from rollout_adapter.lifecycle import advance, run_command, validate_handoff


def await_rollout(manifest_path, *, settings, clock=time.time, sleep=time.sleep,
                 tick=advance, command=run_command):
    """Keep the original held-array lifecycle and its explicit registered budgets."""
    for key in ('watch_timeout_seconds', 'poll_seconds', 'publication_grace_seconds',
                'native_preflight_timeout_seconds'):
        if type(settings.get(key)) not in (int, float) or settings[key] <= 0:
            raise AuthorityError('REGISTERED_ROLLOUT_OPERATIONAL_LIMIT_REQUIRED:' + key)
    manifest_path = Path(manifest_path).absolute()
    materialized = obj(ref(manifest_path))
    root = Path(materialized['root'])
    start_path = root / 'RESIDENT_ROLLOUT_WATCH_START.json'
    if not start_path.exists():
        put(start_path, canonical({'manifest': ref(manifest_path), 'start_epoch': clock(),
                                   'settings': settings}))
    watch = obj(ref(start_path))
    checked(watch['manifest'])
    if watch['manifest'] != ref(manifest_path) or watch['settings'] != settings:
        raise AuthorityError('ROLLOUT_WATCH_AUTHORITY_DRIFT')
    inactive_path = root / 'RESIDENT_ARRAY_FIRST_INACTIVE.json'
    while True:
        status = tick(manifest_path, execute=True,
                      preflight_timeout_seconds=settings['native_preflight_timeout_seconds'])
        route = status['status']
        print('FORMAL_ROLLOUT_STATUS=' + route, flush=True)
        if route == 'SCIENTIFIC_ROLLOUT_INVALID':
            put(root / 'RESIDENT_ROLLOUT_OPERATIONAL_STOP.json', canonical(status))
            return status
        if route == 'VALID_CURRENT_ROUND_HANDOFF':
            # The tick validates native indexed shards/cells/bundles before this route.
            return status
        if route not in ('WAITING_FOR_CURRENT_HANDOFF', 'ARRAY_INACTIVE_AWAITING_PUBLICATION'):
            put(root / 'RESIDENT_ROLLOUT_OPERATIONAL_STOP.json', canonical(status))
            raise AuthorityError('CURRENT_ROLLOUT_STOP:' + route)
        now = clock()
        if route == 'ARRAY_INACTIVE_AWAITING_PUBLICATION' and not inactive_path.exists():
            put(inactive_path, canonical({'array_job_id': status['array_job_id'], 'epoch': now}))
        expired = now - watch['start_epoch'] >= settings['watch_timeout_seconds']
        reason = 'REGISTERED_ROLLOUT_WATCH_TIMEOUT' if expired else None
        if route == 'ARRAY_INACTIVE_AWAITING_PUBLICATION':
            inactive = obj(ref(inactive_path))
            if inactive['array_job_id'] != status['array_job_id']:
                raise AuthorityError('INACTIVE_ARRAY_JOB_IDENTITY_DRIFT')
            if now - inactive['epoch'] >= settings['publication_grace_seconds']:
                reason = 'NATIVE_HANDOFF_NOT_PUBLISHED_WITHIN_REGISTERED_GRACE'
        if reason:
            # Submission receipt, rather than a process-name search, owns this job.
            submission = obj(ref(root / 'SUBMISSION_RECEIPT.json'))
            job = submission['array_job_id']
            if (submission['manifest_sha256'] != ref(manifest_path)['sha256']
                    or job != status['array_job_id'] or not str(job).isdigit()):
                raise AuthorityError('ROLLOUT_CONTAINMENT_JOB_AUTHORITY_MISMATCH')
            result = command(['scancel', str(job)], timeout=settings['native_preflight_timeout_seconds'])
            put(root / 'RESIDENT_ROLLOUT_CONTAINMENT.json', canonical({
                'reason': reason, 'submission_receipt': ref(root / 'SUBMISSION_RECEIPT.json'),
                'command_result': result, 'scientific_outcome_claimed': False,
                'scientific_round_consumed': False}))
            raise AuthorityError(reason)
        sleep(settings['poll_seconds'])

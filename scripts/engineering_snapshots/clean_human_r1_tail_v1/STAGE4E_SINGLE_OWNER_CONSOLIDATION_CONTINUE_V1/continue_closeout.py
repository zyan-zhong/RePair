"""Continue the completed, registered array 156934 without reacquiring its native lock.

This is an operational entry point, not another evaluator or round controller.
The original Stage4D function remains the sole owner of the execution lock.
No scheduler write, model inference, ALFWorld call, or scientific rerun exists here.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import os
from pathlib import Path
import fcntl
import sys

ROOT = Path(__file__).resolve().parent
SCRIPTS = Path('/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts')
OLD_NAME = 'STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX'
FULL_NAME = 'STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING'
RECOVERY_NAME = 'STAGE4E_NODE_EXCLUDED_ARRAY_RECOVERY_V1'
RECOVERY_SOURCE_SHA = '95e950452b576982f9dbacfa025eb1560412e0660c92c75fe3c1c3bdd98d773a'
RECOVERY_MANIFEST_SHA = 'c09e03b2b761f2d8954fdce90fbafba2659f950c62ee618ef6baaf34b2eeeac2'
ARRAY_ID = '156934'
PLAN_SHA = 'cea91dcfb65a6ddd7b1fd719cfaffedb9cfaa950287b19b776ac373260f9564a'
AUTH_SHA = '978ab39389d447b74b1a1acf653619ff437c0d341c9fe76b72236dd8f5fd865b'


class ContinuationError(ValueError):
    """Known completion evidence or original code was not available as registered."""


def load_dependencies(scripts: Path = SCRIPTS):
    """Load exact existing code; the optional root is for synthetic local tests only."""
    old_recovery = scripts / RECOVERY_NAME
    for name, expected in (('recover.py', RECOVERY_SOURCE_SHA),
                           ('PACKAGE_FILES.sha256', RECOVERY_MANIFEST_SHA)):
        path = old_recovery / name
        if path.is_symlink() or not path.is_file():
            raise ContinuationError('ORIGINAL_RECOVERY_FILE_UNAVAILABLE:' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ContinuationError('ORIGINAL_RECOVERY_FILE_CHANGED:' + name)
    spec = importlib.util.spec_from_file_location('_stage4e_frozen_recovery', old_recovery/'recover.py')
    if spec is None or spec.loader is None:
        raise ContinuationError('RECOVERY_MODULE_UNAVAILABLE')
    recovery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recovery)
    core, ad, jobs, driver = recovery.load_original(scripts / OLD_NAME)
    core.verify_inventory(old_recovery)
    return recovery, core, ad, jobs, driver


@contextmanager
def driver_mutex(path: Path):
    """Use the existing controller mutex. Never remove or replace its inode."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ContinuationError('EXISTING_STAGE4E_DRIVER_ACTIVE_DO_NOT_DELETE_LOCK') from exc
        yield
    finally:
        os.close(fd)


def verify_completed_recovery(core, ad, jobs, recovery, cfg: dict,
                              state: Path, plan: dict, recovery_root: Path) -> dict:
    """Check exact recorded submission and all four original status artifacts."""
    if plan.get('plan_sha256') != PLAN_SHA or cfg.get('authorization_sha256') != AUTH_SHA:
        raise ContinuationError('REGISTERED_SCIENTIFIC_IDENTITY_CHANGED')
    allowed = {'SUBMISSION_0.json', 'SUBMISSION_0.intent.json',
               'SUBMISSION_2.json', 'SUBMISSION_2.intent.json'}
    if any(p.name not in allowed for p in state.glob('SUBMISSION_*.json')):
        raise ContinuationError('UNEXPECTED_SUBMISSION_NO_CONCURRENT_RECOVERY')
    expected = {'generation': 2, 'shards': [0, 1, 2, 3], 'job_id': ARRAY_ID, 'plan_sha256': PLAN_SHA}
    if core.read_json(state/'SUBMISSION_2.json') != expected:
        raise ContinuationError('SUBMISSION_IDENTITY_CHANGED')
    root = Path(cfg['execution_root'])
    if core.regular(root/'LAST_JOB_ID.txt').read_text().strip() != ARRAY_ID:
        raise ContinuationError('JOB_POINTER_CHANGED')
    command = recovery.with_exclusion(jobs.submission_command(
        recovery.OLD_ROOT, root, PLAN_SHA, (0, 1, 2, 3), Path(cfg['execution_log_root'])))
    intent = {'generation': 2, 'shards': [0, 1, 2, 3], 'plan_sha256': PLAN_SHA,
        'command': command, 'authorization_sha256': AUTH_SHA,
        'recovery_authorization_file_sha256': core.file_sha(recovery_root/'RECOVERY_AUTHORIZATION.json'),
        'predecessor_array_job_id': recovery.FAILED_ARRAY, 'excluded_nodes': ['d1n41a18g03']}
    if core.read_json(state/'SUBMISSION_2.intent.json') != intent:
        raise ContinuationError('SUBMISSION_INTENT_CHANGED')
    status, text = jobs.query_array(ARRAY_ID, (0, 1, 2, 3))
    print('STAGE4E_COMPLETED_ARRAY_RECHECK=' + ARRAY_ID + '\n' + text.strip(), flush=True)
    if status != 'COMPLETE':
        raise ContinuationError('ARRAY_NOT_COMPLETED_NO_EXECUTION_OR_RETRY:' + status)
    statuses = {i: ad.load_worker_status(cfg, state, plan, ARRAY_ID, i) for i in range(4)}
    if jobs.incomplete_shards(statuses):
        raise ContinuationError('SHARDS_NOT_FULLY_COMPLETE_NO_AUTOMATIC_SUBMISSION')
    return {'array_job_id': ARRAY_ID, 'plan_sha256': PLAN_SHA,
            'submission_file_sha256': core.file_sha(state/'SUBMISSION_2.json'),
            'recovery_authorization_file_sha256': intent['recovery_authorization_file_sha256'],
            'native_shard_statuses_verified': 4}


def consolidate_single_owner(ad, cfg: dict, state: Path, plan: dict) -> None:
    """Do not lock full_select_execution.lock here: native consolidate_shards owns it."""
    ad.consolidate(cfg, state, plan)


def archive_adapter(core, repo: Path, inventory: dict) -> None:
    """Append this exact operational source using existing Git publication utilities."""
    from stage4e import source
    if source.git(repo, 'status', '--porcelain'):
        raise ContinuationError('INTEGRATION_CHECKOUT_DIRTY')
    names = []; entries = []
    for name in [*inventory, 'PACKAGE_FILES.sha256']:
        raw = core.regular(ROOT/name).read_bytes()
        source.reject_secret(raw, name)
        target = f'{source.SNAPSHOT_PREFIX}/{ROOT.name}/{name}'
        core.write_bytes_exact(core.safe_child(repo, target), raw)
        names.append(target)
        entries.append({'path': target, 'file_sha256': hashlib.sha256(raw).hexdigest()})
    target = source.DOC_PREFIX + '/SINGLE_OWNER_CONSOLIDATION_SOURCE.json'
    core.write_exact(repo/target, {
        'schema_id': 'SINGLE_OWNER_CONSOLIDATION_SOURCE_V1',
        'files': entries, 'supersedes': 'recover.main outer execution-lock acquisition only',
        'code_chain': 'driver_mutex -> original completion/status validation -> original array_driver.consolidate -> original live.consolidate_shards (sole execution-lock owner) -> original driver.finalize',
        'original_recovery_file_sha256': RECOVERY_SOURCE_SHA,
        'scientific_authorization_sha256': AUTH_SHA,
        'new_scientific_cells_executed': 0,
        'stage5_code_changed': False,
    })
    names.append(target)
    source.stage_explicit(repo, names)
    source.commit_staged(repo, 'fix: use native single-owner SELECT consolidation locking')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', help='Validate input/status only; do not consolidate or publish.')
    args = parser.parse_args(argv)
    recovery, core, ad, jobs, driver = load_dependencies()
    inventory = core.verify_inventory(ROOT)
    cfg = core.read_json(SCRIPTS/OLD_NAME/'config.json')
    control = Path(cfg['control_root']); root = Path(cfg['execution_root'])
    state = root/ad.STATE_REL; recovery_root = state/recovery.RECOVERY_REL
    # Existing preparation and recovery proof are mandatory. Never start a new recovery.
    for path in (control/'SOURCE_PREPARATION.json', state/'PLAN.json',
                 recovery_root/'RECOVERY_AUTHORIZATION.json'):
        core.regular(path)
    with driver_mutex(control/'driver.lock'):
        driver.base_gate(cfg)
        plan = ad.freeze_plan(cfg, state, '156834')
        recovery.preflight(core, ad, cfg, state, plan, recovery_root)
        proof = verify_completed_recovery(core, ad, jobs, recovery, cfg, state, plan, recovery_root)
        if args.check_only:
            print('STAGE4E_SINGLE_OWNER_CONTINUATION_PREFLIGHT_PASS\nNEW_SCIENTIFIC_CELL_COUNT=0\nREMOTE_PUBLICATION_PERFORMED=false', flush=True)
            return 0
        active, repo = driver.prepare(cfg, control)
        if (control/'FINAL_PUBLICATION_RECEIPT.json').exists():
            # The original finalizer rechecks both actual remote refs. Do not add commits.
            driver.finalize(cfg, control, repo, active)
            return 0
        # Keep the controller lock, but let the original function acquire the execution lock.
        consolidate_single_owner(ad, cfg, state, plan)
        from stage4e.audit import completion_gate
        completion_gate(root, cfg)
        core.write_exact(control/'SINGLE_OWNER_CONTINUATION.json', {
            'schema_id': 'STAGE4E_SINGLE_OWNER_CONTINUATION_V1',
            **proof,
            'adapter_manifest_sha256': core.file_sha(ROOT/'PACKAGE_FILES.sha256'),
            'completion_file_sha256': core.file_sha(root/driver.COMPLETE),
            'native_execution_lock_retained': True,
            'new_scientific_cells_executed': 0,
            'strong_execution_authorized': False,
        })
        archive_adapter(core, repo, inventory)
        driver.finalize(cfg, control, repo, active)
        return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print('STOP=' + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(70)

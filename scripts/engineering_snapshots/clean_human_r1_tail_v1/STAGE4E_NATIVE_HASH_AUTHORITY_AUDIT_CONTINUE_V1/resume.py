"""Resume only the existing completed SELECT audit and publication.

The original packages are immutable. Two hash-contract call sites are adapted
in an exact-source, ephemeral audit module. The original finalizer, validators,
statistics, disposition and Git publisher are reused. No science is rerun.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import types

ROOT=Path(__file__).resolve().parent
SCRIPTS=Path('/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts')
OLD_NAME='STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX'
CONT_NAME='STAGE4E_SINGLE_OWNER_CONSOLIDATION_CONTINUE_V1'
AUTH_SHA='978ab39389d447b74b1a1acf653619ff437c0d341c9fe76b72236dd8f5fd865b'
BINDING_SHA='4ab7942b2c66238cb3833bdb04eb7f7ca23b52d10c388575aaf1bd272dfc100d'
ARRAY_ID='156934'
AUDIT_COMMAND_OLD="[cfg['python'],'-m','stage4e.driver','audit-once','--control',str(control),"
AUDIT_COMMAND_NEW="[cfg['python'],str(_HASH_BRIDGE_ROOT/'resume.py'),'audit-once','--control',str(control),"
from native_hash_bridge import PINS, load_corrected_audit, build_bridge_report, verify_native_sources


def _pinned_file(path: Path, digest: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError('PINNED_FILE_NOT_REGULAR:'+str(path))
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:
        raise ValueError('PINNED_FILE_CHANGED:'+str(path))
    return raw


def load_dependencies():
    """Reuse the exact previous continuation's dependency and package validation."""
    old=SCRIPTS/CONT_NAME
    _pinned_file(old/'continue_closeout.py',PINS['continuation_sha256'])
    _pinned_file(old/'PACKAGE_FILES.sha256',PINS['continuation_manifest_sha256'])
    spec=importlib.util.spec_from_file_location('_stage4e_hash_bridge_predecessor',old/'continue_closeout.py')
    if spec is None or spec.loader is None:raise ValueError('CONTINUATION_LOADER_MISSING')
    continuation=importlib.util.module_from_spec(spec)
    # File was verified before import; no script main() is executed.
    spec.loader.exec_module(continuation)
    recovery,core,ad,jobs,old_driver=continuation.load_dependencies(SCRIPTS)
    core.verify_inventory(old)
    core.verify_inventory(ROOT)
    audit=load_corrected_audit(SCRIPTS/OLD_NAME)
    driver=load_corrected_driver(SCRIPTS/OLD_NAME,audit)
    return core,audit,driver


def corrected_driver_source(raw: bytes) -> str:
    from stage4e import GateError
    if hashlib.sha256(raw).hexdigest()!=PINS['old_driver_sha256']:
        raise GateError('ORIGINAL_DRIVER_CHANGED')
    text=raw.decode('utf-8')
    if text.count(AUDIT_COMMAND_OLD)!=1:raise GateError('AUDIT_CHILD_ENTRY_CHANGED')
    return text.replace(AUDIT_COMMAND_OLD,AUDIT_COMMAND_NEW,1)


def load_corrected_driver(old_root: Path, audit):
    from stage4e import regular
    path=old_root/'stage4e/driver.py'
    text=corrected_driver_source(regular(path).read_bytes())
    name='stage4e._native_hash_resume_driver'
    module=types.ModuleType(name)
    module.__file__=str(path)
    module.__package__='stage4e'
    module._HASH_BRIDGE_ROOT=ROOT
    sys.modules[name]=module
    exec(compile(text,str(path),'exec'),module.__dict__)
    module.execute_audit=audit.execute_audit
    return module


def validate_requested_paths(cfg,control,repo):
    from stage4e import GateError
    c=Path(control or cfg['control_root']);r=Path(repo or cfg['integration_repo'])
    if c!=Path(cfg['control_root']) or r!=Path(cfg['integration_repo']):
        raise GateError('AUDIT_ROOT_CHANGED')
    return c,r


@contextmanager
def driver_mutex(path: Path):
    from stage4e import GateError
    fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:raise GateError('EXISTING_STAGE4E_DRIVER_ACTIVE_DO_NOT_DELETE_LOCK') from exc
        yield
    finally:os.close(fd)


def verify_completed_handoff(core,audit,cfg,control):
    root=Path(cfg['execution_root'])
    if cfg['authorization_sha256']!=AUTH_SHA or cfg['binding_sha256']!=BINDING_SHA:
        raise core.GateError('REGISTERED_EXPERIMENT_CHANGED')
    completion=audit.completion_gate(root,cfg)
    previous=core.read_json(control/'SINGLE_OWNER_CONTINUATION.json')
    if (previous.get('array_job_id')!=ARRAY_ID or previous.get('native_shard_statuses_verified')!=4
        or previous.get('completion_file_sha256')!=core.file_sha(root/audit.COMPLETE)):
        raise core.GateError('COMPLETED_CONTINUATION_HANDOFF_CHANGED')
    consolidated=core.read_json(root/'parallel_v1/independent_jobs_v1/ARRAY_CONSOLIDATION_RECEIPT.json')
    if consolidated.get('canonical_completion_file_sha256')!=core.file_sha(root/audit.COMPLETE):
        raise core.GateError('CONSOLIDATED_COMPLETION_CHANGED')
    # Bind the canonical receipt files to the completed consolidation before audit.
    ledger_shas=consolidated.get('canonical_ledger_file_sha256s')
    if not isinstance(ledger_shas,dict):raise core.GateError('CONSOLIDATION_LEDGER_INDEX_MISSING')
    from stage4e.array_driver import ledger_shas as original_ledger_shas
    if ledger_shas!=original_ledger_shas(root):
        raise core.GateError('CANONICAL_LEDGERS_CHANGED_AFTER_CONSOLIDATION')
    return completion


def archive_adapter(core,repo: Path,report: dict):
    from stage4e import source
    if source.git(repo,'status','--porcelain'):
        raise core.GateError('INTEGRATION_CHECKOUT_DIRTY')
    names=[];entries=[]
    inventory=core.verify_inventory(ROOT)
    for name in [*inventory,'PACKAGE_FILES.sha256']:
        data=core.regular(ROOT/name).read_bytes();source.reject_secret(data,name)
        target=f'{source.SNAPSHOT_PREFIX}/{ROOT.name}/{name}'
        core.write_bytes_exact(core.safe_child(repo,target),data)
        names.append(target);entries.append({'path':target,'file_sha256':hashlib.sha256(data).hexdigest()})
    target=source.DOC_PREFIX+'/NATIVE_HASH_AUTHORITY_AUDIT_CONTINUATION.json'
    core.write_exact(repo/target,{'schema_id':'STAGE4E_NATIVE_HASH_ADAPTER_SOURCE_V1',
        'files':entries,'code_chain':'original completion -> original base_gate/raw inventory -> bound native hash bridge -> original SELECT audit -> original statistics/disposition -> original atomic publication',
        'two_audit_call_sites_only':True,'original_validator_modified':False,
        'completed_scientific_universe_unchanged':True,'stage5_code_changed':False,
        'binding_hash_report':report})
    names.append(target)
    source.stage_explicit(repo,names)
    source.commit_staged(repo,'fix: bridge frozen binding hashes to native SELECT audit identities')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('resume','audit-once'),nargs='?',default='resume')
    p.add_argument('--control');p.add_argument('--repo')
    p.add_argument('--check-only',action='store_true')
    args=p.parse_args(argv)
    core,audit,driver=load_dependencies()
    cfg=core.read_json(SCRIPTS/OLD_NAME/'config.json')
    control,repo=validate_requested_paths(cfg,args.control,args.repo)
    root=Path(cfg['execution_root']);binding=Path(cfg['binding_root'])
    if args.mode=='audit-once':
        # Fresh interpreter: exactly the finalizer's original audit isolation boundary.
        driver.base_gate(cfg)
        verify_completed_handoff(core,audit,cfg,control)
        verify_native_sources(repo)
        driver.execute_audit(cfg=cfg,output=control/'results',repo=repo,binding=binding,root=root)
        return 0
    with driver_mutex(control/'driver.lock'):
        active,repo=driver.prepare(cfg,control)
        verify_completed_handoff(core,audit,cfg,control)
        if (control/'FINAL_PUBLICATION_RECEIPT.json').exists():
            driver.finalize(cfg,control,repo,active)
            return 0
        report=build_bridge_report(cfg,repo,binding)
        print('STAGE4E_FROZEN_BINDING_TO_NATIVE_HASH_BRIDGE_PASS',flush=True)
        for e in report['entries']:
            print('HASH_AUTHORITY '+e['path']+' binding='+e['frozen_binding_artifact_sha256']+' native='+e['native_model_sha256'],flush=True)
        print('NATIVE_EXPECTED_CONDITION_CELLS='+str(report['native_expected_condition_cells']),flush=True)
        if args.check_only:
            print('NEW_SCIENTIFIC_CELL_COUNT=0\nREMOTE_PUBLICATION_PERFORMED=false',flush=True)
            return 0
        core.write_exact(control/'verification/NATIVE_HASH_AUTHORITY_BRIDGE_V1.json',report)
        archive_adapter(core,repo,report)
        # Original finalizer; its only command adaptation is the fresh audit child.
        driver.finalize(cfg,control,repo,active)
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print('STOP='+str(exc),file=sys.stderr,flush=True)
        raise SystemExit(70)

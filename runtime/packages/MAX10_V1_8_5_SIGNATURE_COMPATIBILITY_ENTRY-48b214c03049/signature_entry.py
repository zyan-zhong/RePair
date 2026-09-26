"""Restore inspected native signature without changing runtime or call identity."""
from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from functools import update_wrapper
from unittest.mock import patch
import json,hashlib,sys,inspect
ROOT=Path(__file__).resolve().parent
def verify():
    raw=(ROOT/'PACKAGE_FILES.sha256').read_bytes();seen=set()
    for line in raw.decode().splitlines():
        digest,name=line.split(maxsplit=1);p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or name in seen or '\\' in name:raise ValueError('ENTRY_MEMBER_INVALID')
        seen.add(name)
        path=ROOT/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('ENTRY_SOURCE_CHANGED')
    return hashlib.sha256(raw).hexdigest()
def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());base=Path(a['base_source_root'])
    if hashlib.sha256((base/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['base_manifest_sha256']:raise ValueError('BASE_CHANGED')
    sys.path.insert(0,str(base));import continuation
    continuation.verify_package();stop=continuation.read_ref(a['startup_stop_ref'])
    if stop['message']!='FIXED_HEAD_CALLABLE_SIGNATURE_DRIFT:execute_one':raise ValueError('EXACT_NO_SEND_STOP_REQUIRED')
    return a,continuation,identity
@contextmanager
def signature_compatibility():
    import repair
    native_install=repair.install_repair
    @contextmanager
    def compatible(*args,**kwargs):
        from pchsi.cognitive_runtime import orchestrator,registry_runner
        native=orchestrator.execute_one
        with native_install(*args,**kwargs):
            update_wrapper(orchestrator.execute_one,native)
            if registry_runner.execute_one is not orchestrator.execute_one or inspect.signature(orchestrator.execute_one)!=inspect.signature(native):
                raise ValueError('SIGNATURE_COMPATIBILITY_FAILED')
            yield
    with patch.object(repair,'install_repair',compatible):yield
def run(invocation):
    a,base,identity=load();prepared=base.prepare()
    if str(prepared[4])!=a['preserved_runtime_root']:raise ValueError('RUNTIME_GENERATION_CHANGED')
    from entry.progress import update as native_update
    import entry.progress as progress
    def update(root,**fields):
        return native_update(root,**{**fields,'entry_signature_overlay_sha256':identity,'entry_signature_overlay_root':str(ROOT)})
    with signature_compatibility(),patch.object(progress,'update',update):return base.run(invocation)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))
    a,base,identity=load();print(json.dumps({'overlay_manifest_sha256':identity,'preflight':base.preflight()}))

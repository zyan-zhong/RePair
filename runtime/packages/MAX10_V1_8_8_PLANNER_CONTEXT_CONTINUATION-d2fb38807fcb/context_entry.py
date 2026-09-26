from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from unittest.mock import patch
import json,hashlib,sys
ROOT=Path(__file__).resolve().parent

def verify():
    raw=(ROOT/'PACKAGE_FILES.sha256').read_bytes();seen=set()
    for line in raw.decode().splitlines():
        sha,name=line.split(maxsplit=1);p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_INVALID')
        seen.add(name);path=ROOT/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('PACKAGE_SHA_MISMATCH:'+name)
    return hashlib.sha256(raw).hexdigest()

def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());prior=Path(a['predecessor_source_root'])
    if hashlib.sha256((prior/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['predecessor_manifest_sha256']:
        raise ValueError('REGISTERED_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(prior));import condition_entry
    prepared=condition_entry.load()
    from continuation import read_ref
    for ref in a['preserved_refs'].values():read_ref(ref)
    return a,condition_entry,identity,prepared

@contextmanager
def install(a,prior,identity):
    import adapter
    from pre_overlay import install as pre_install
    from exact_bindings import file_ref,read_json,read_ref
    # Install after the predecessor's existing source/transport adapters.
    native=adapter.run_h44
    original_worker=native.__globals__['_transport_worker']
    native.__globals__['_transport_worker']=ROOT/'post_worker.py'
    def h44(binding,capture,out,*,execute):
        result=native(binding,capture,out,execute=execute)
        if execute and binding['round_id']==a['excluded_round_id']:
            terminal=Path(out)/'run'/a['continuation_terminal_name']
            value=read_json(terminal)
            plan=read_json(Path(out)/'run/EXECUTION_PLAN.json')
            if value['plan_sha256']!=plan['plan_sha256'] or value['source_extension_manifest_sha256']!=identity:
                raise ValueError('POST_CONTINUATION_TERMINAL_IDENTITY')
            if value.get('post_terminal',{}).get('training_recommendation') not in ('TRAIN','NO_TRAIN'):
                raise ValueError('POST_CONTINUATION_NOT_ACCEPTED_NO_RESEND')
            return file_ref(terminal)
        return result
    try:
        with pre_install(a,file_ref(ROOT/'PACKAGE_FILES.sha256')),patch.object(adapter,'run_h44',h44):yield
    finally:native.__globals__['_transport_worker']=original_worker

def run(invocation):
    a,prior,identity,prepared=load()
    import entry.progress as progress
    from entry.campaign_owner import _write_once
    from continuation import file_ref
    root=Path(a['owner_root'])/'runtime_extensions'/identity
    _write_once(root/'PLANNER_CONTEXT_ENTRY.json',{'authority':file_ref(ROOT/'AUTHORITY.json'),
        'manifest':file_ref(ROOT/'PACKAGE_FILES.sha256'),'excluded_pre_round_id':a['excluded_round_id'],
        'pre_activation':'NEXT_REGISTERED_SCIENTIFIC_ROUND','post_compaction':'CURRENT_RECOVERY_AND_FUTURE'})
    native_install=prior.install;native_update=progress.update
    @contextmanager
    def combined(*args,**kwargs):
        with native_install(*args,**kwargs),install(a,prior,identity):yield
    def update(owner,**fields):
        return native_update(owner,**{**fields,'planner_context_entry_root':str(ROOT),
            'planner_context_entry_manifest_sha256':identity,'pre_context_excluded_round_id':a['excluded_round_id']})
    with patch.object(prior,'install',combined),patch.object(progress,'update',update):return prior.run(invocation)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))
    print(json.dumps({'manifest_sha256':verify()}))

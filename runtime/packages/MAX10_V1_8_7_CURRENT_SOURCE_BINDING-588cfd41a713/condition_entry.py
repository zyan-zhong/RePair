from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from unittest.mock import patch
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent

def verify():
    raw=(ROOT/'PACKAGE_FILES.sha256').read_bytes();seen=set()
    for line in raw.decode().splitlines():
        digest,name=line.split(maxsplit=1);part=PurePosixPath(name)
        if part.is_absolute() or '..' in part.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_INVALID')
        seen.add(name);path=ROOT/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('PACKAGE_SOURCE_CHANGED:'+name)
    return hashlib.sha256(raw).hexdigest()

def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());prior=Path(a['predecessor_source_root'])
    if hashlib.sha256((prior/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['predecessor_manifest_sha256']:raise ValueError('PREDECESSOR_CHANGED')
    sys.path.insert(0,str(prior));import resume_entry
    prepared=resume_entry.load()
    from continuation import read_ref
    for ref in a['immutable_refs'].values():read_ref(ref)
    stop=read_ref(a['stop_ref'])
    if stop['message']!='REGISTERED_SOURCE_POLICY_CONDITION_MISSING':raise ValueError('EXACT_SOURCE_CONDITION_STOP_REQUIRED')
    return a,resume_entry,identity,prepared

def h44_function(a,prior,old_authority):
    from continuation import file_ref
    fn=prior.h44_function(old_authority);native_request=fn.__globals__['_transport_request']
    def request(value,binding):
        return {**native_request(value,binding),'registered_condition_entry':file_ref(ROOT/'AUTHORITY.json'),
                'registered_condition_manifest':file_ref(ROOT/'PACKAGE_FILES.sha256')}
    fn.__globals__['_transport_request']=request;fn.__globals__['_transport_worker']=ROOT/'condition_child.py'
    return fn

@contextmanager
def install(a,prior,old_authority):
    import adapter
    from source_condition import capture_function
    with patch.object(adapter,'materialize_capture',capture_function(old_authority['h44_input_ref'])),patch.object(adapter,'run_h44',h44_function(a,prior,old_authority)):
        yield

def run(invocation):
    a,prior,identity,prepared=load()
    import entry.progress as progress
    from entry.campaign_owner import _write_once
    from continuation import file_ref
    _write_once(Path(a['owner_root'])/'runtime_extensions'/identity/'SOURCE_CONDITION_ENTRY.json',{
        'authority':file_ref(ROOT/'AUTHORITY.json'),'manifest':file_ref(ROOT/'PACKAGE_FILES.sha256'),'preserved':a['immutable_refs']})
    native=progress.update;native_install=prior.install
    def update(owner,**fields):
        return native(owner,**{**fields,'source_condition_entry_root':str(ROOT),'source_condition_entry_manifest_sha256':identity})
    @contextmanager
    def combined(old_a):
        with native_install(old_a),install(a,prior,old_a):yield
    with patch.object(prior,'install',combined),patch.object(progress,'update',update):return prior.run(invocation)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))
    print(json.dumps({'manifest_sha256':verify()}))

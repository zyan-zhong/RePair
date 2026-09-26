from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from unittest.mock import patch
import hashlib,json,sys,importlib
ROOT=Path(__file__).resolve().parent
def verify():
    raw=(ROOT/'PACKAGE_FILES.sha256').read_bytes();seen=set()
    for line in raw.decode().splitlines():
        expected,name=line.split(maxsplit=1);p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_PATH')
        seen.add(name);path=ROOT/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('PACKAGE_MEMBER_SHA:'+name)
    return hashlib.sha256(raw).hexdigest()
def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());root=Path(a['budget_predecessor_root'])
    if hashlib.sha256((root/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['budget_predecessor_manifest_sha256']:raise ValueError('REGISTERED_BUDGET_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(root));prior=importlib.import_module('exception_entry');old_a,old_prior,old_identity,prepared=prior.load()
    return a,prior,identity,prepared
def run(invocation):
    a,prior,identity,prepared=load()
    import research_memory,entry.progress as progress
    from budget_bridge import installed
    native=research_memory.installed;old_update=progress.update
    @contextmanager
    def combined(*args,**kwargs):
        with native(*args,**kwargs),installed(a):yield
    def update(owner,**fields):return old_update(owner,**{**fields,'memory_budget_entry_root':str(ROOT),'memory_budget_entry_manifest_sha256':identity})
    with patch.object(research_memory,'installed',combined),patch.object(progress,'update',update):return prior.run(invocation)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))

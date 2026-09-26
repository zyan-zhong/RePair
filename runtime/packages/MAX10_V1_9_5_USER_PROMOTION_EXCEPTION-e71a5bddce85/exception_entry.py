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
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());root=Path(a['promotion_source_root'])
    if hashlib.sha256((root/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['promotion_manifest_sha256']:raise ValueError('REGISTERED_PROMOTION_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(root));prior=importlib.import_module('promotion_entry');prepared=prior.load()
    return a,prior,identity,prepared

def run(invocation):
    a,prior,identity,prepared=load();native=prior.install
    from promotion_exception import installed
    from research_memory import installed as research_installed
    @contextmanager
    def combined(*args,**kwargs):
        with native(*args,**kwargs),installed(a),research_installed(a):yield
    import entry.progress as progress
    old=progress.update
    def update(owner,**fields):return old(owner,**{**fields,'promotion_exception_entry_root':str(ROOT),'promotion_exception_entry_manifest_sha256':identity,'campaign_user_exception_ref':a['authorization_ref']})
    with patch.object(prior,'install',combined),patch.object(progress,'update',update):return prior.run(invocation)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');parser.add_argument('--invocation');args=parser.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))

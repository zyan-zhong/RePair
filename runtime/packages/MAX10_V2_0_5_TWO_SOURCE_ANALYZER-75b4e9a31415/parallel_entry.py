from pathlib import Path,PurePosixPath
from unittest.mock import patch
import hashlib,json,sys,importlib
ROOT=Path(__file__).resolve().parent
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def verify():
    seen=set()
    for line in (ROOT/'PACKAGE_FILES.sha256').read_text().splitlines():
        expected,name=line.split(maxsplit=1);p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or name in seen or '\\' in name:raise ValueError('PACKAGE_MEMBER_INVALID')
        seen.add(name)
        if (ROOT/name).is_symlink() or digest(ROOT/name)!=expected:raise ValueError('PARALLEL_PACKAGE_CHANGED:'+name)
    return digest(ROOT/'PACKAGE_FILES.sha256')
def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());prior=a['parallel_predecessor']
    if digest(Path(prior['root'])/'PACKAGE_FILES.sha256')!=prior['manifest_sha256']:raise ValueError('PARALLEL_PREDECESSOR_CHANGED')
    for ref in a['parallel_source_refs']:
        if digest(ref['path'])!=ref['sha256']:raise ValueError('PARALLEL_NATIVE_SOURCE_CHANGED')
    sys.path.insert(0,prior['root']);previous=importlib.import_module('closure_entry');prepared=previous.load()
    sys.path.insert(0,str(ROOT))
    return a,identity,previous,prepared
def run(invocation):
    a,identity,prior,prepared=load()
    from parallel_install import installed
    import entry.progress as progress
    original=progress.update
    def update(owner,**fields):
        return original(owner,**{**fields,'parallel_entry_root':str(ROOT),'parallel_manifest_sha256':identity,
            'parallel_progress_path':str(Path(a['owner_root'])/'ANALYZER_PARALLEL_PROGRESS.json'),
            'parallel_policy':a['parallel_policy']})
    def prepared_load():
        if prior.verify()!=a['parallel_predecessor']['manifest_sha256']:raise ValueError('PREPARED_PREDECESSOR_CHANGED')
        return prepared
    with installed(a,identity,ROOT),patch.object(prior,'load',prepared_load),patch.object(progress,'update',update):
        return prior.run(invocation)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation',required=True);args=p.parse_args()
    raise SystemExit(run(args.invocation))

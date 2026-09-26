from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from unittest.mock import patch
import json,hashlib,importlib.util,sys
ROOT=Path(__file__).resolve().parent
def verify():
    raw=(ROOT/'PACKAGE_FILES.sha256').read_bytes();seen=set()
    for row in raw.decode().splitlines():
        sha,name=row.split(maxsplit=1);p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_INVALID')
        seen.add(name);target=ROOT/name
        if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=sha:raise ValueError('PACKAGE_MEMBER_SHA')
    return hashlib.sha256(raw).hexdigest()
def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());root=Path(a['context_source_root'])
    if hashlib.sha256((root/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['context_manifest_sha256']:raise ValueError('MEMORY_CONTEXT_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(root));spec=importlib.util.spec_from_file_location('_previous_context_entry',root/'context_entry.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    old,_,_,prepared=prior.load()
    from exact_bindings import read_ref
    for ref in a['memory_preserved_refs'].values():read_ref(ref,as_bytes=True)
    return a,prior,identity,prepared
def run(invocation):
    a,prior,identity,prepared=load()
    import entry.progress as progress
    from exact_bindings import file_ref,immutable_json
    from memory_index import install
    immutable_json(Path(a['owner_root'])/'runtime_extensions'/identity/'MEMORY_INDEX_ENTRY.json',{
        'authority':file_ref(ROOT/'AUTHORITY.json'),'manifest':file_ref(ROOT/'PACKAGE_FILES.sha256'),
        'source_manifest':a['memory_api_ref'],'scientific_results_recomputed':False})
    native=prior.install;native_update=progress.update
    @contextmanager
    def combined(*args,**kwargs):
        with native(*args,**kwargs),install(a,file_ref(ROOT/'PACKAGE_FILES.sha256')):yield
    def update(owner,**fields):
        return native_update(owner,**{**fields,'memory_index_entry_root':str(ROOT),'memory_index_entry_manifest_sha256':identity})
    with patch.object(prior,'install',combined),patch.object(progress,'update',update):return prior.run(invocation)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))

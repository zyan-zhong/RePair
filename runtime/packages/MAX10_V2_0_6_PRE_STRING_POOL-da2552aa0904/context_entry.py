from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from unittest.mock import patch
import json,hashlib,sys,importlib
ROOT=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def verify():
    seen=set()
    for line in (ROOT/'PACKAGE_FILES.sha256').read_text().splitlines():
        h,n=line.split(maxsplit=1);p=PurePosixPath(n)
        if p.is_absolute() or '..' in p.parts or '\\' in n or n in seen:raise ValueError('PACKAGE_MEMBER_INVALID')
        seen.add(n)
        if (ROOT/n).is_symlink() or digest(ROOT/n)!=h:raise ValueError('PACKAGE_SOURCE_CHANGED:'+n)
    return digest(ROOT/'PACKAGE_FILES.sha256')

def checked(ref):
    if digest(ref['path'])!=ref.get('sha256',ref.get('file_sha256')):raise ValueError('CONTEXT_AUTHORITY_SHA')
    return json.loads(Path(ref['path']).read_bytes())

def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    for key in ('context_pool_predecessor','parallel_runtime_ref'):
        r=a[key]
        if digest(Path(r['root'])/'PACKAGE_FILES.sha256')!=r['manifest_sha256']:raise ValueError('CONTEXT_PREDECESSOR_CHANGED')
    source=checked(a['pre_context_source_authority_ref'])
    if source['planner_context_policy']['min_model_context_window_tokens']!=a['registered_context_window_tokens']:raise ValueError('CONTEXT_BUDGET_AUTHORITY_DRIFT')
    sys.path.insert(0,a['parallel_runtime_ref']['root']);prior=importlib.import_module('parallel_entry')
    prepared=prior.load()
    # Native module must come from the existing exact V204 root.
    pc=importlib.import_module('pre_context')
    if Path(pc.__file__).parent!=Path(a['context_pool_predecessor']['root']):raise ValueError('NATIVE_PRE_MODULE_IDENTITY')
    return a,identity,prior,prepared,pc

@contextmanager
def installed(a,identity,pc):
    import pool_context
    authority={'path':str(ROOT/'AUTHORITY.json'),'sha256':digest(ROOT/'AUTHORITY.json')}
    def amend(bundle,*,policy,authority_ref,hash_request):
        result=pool_context.amend(bundle,policy={**policy,'string_pool_context_window_tokens':a['registered_context_window_tokens']},
            authority_ref=authority_ref,hash_request=hash_request)
        receipt=result.get('registered_pre_context_encoding',{})
        if receipt.get('string_pool_applied'):receipt['string_pool_authority_ref']=authority
        return result
    with patch.object(pc,'amend',amend):yield

def run(invocation):
    a,identity,prior,prepared,pc=load()
    import entry.progress as progress
    old=progress.update
    def update(owner,**fields):return old(owner,**{**fields,'pre_pool_entry_root':str(ROOT),'pre_pool_manifest_sha256':identity})
    def ready():
        if prior.verify()!=a['parallel_runtime_ref']['manifest_sha256']:raise ValueError('PREPARED_PARALLEL_CHANGED')
        return prepared
    with installed(a,identity,pc),patch.object(prior,'load',ready),patch.object(progress,'update',update):return prior.run(invocation)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--invocation',required=True);args=p.parse_args()
    raise SystemExit(run(args.invocation))

from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from unittest.mock import patch
import importlib.util,inspect,json,hashlib,sys
ROOT=Path(__file__).resolve().parent

def verify():
    raw=(ROOT/'PACKAGE_FILES.sha256').read_bytes();seen=set()
    for line in raw.decode().splitlines():
        sha,name=line.split(maxsplit=1);part=PurePosixPath(name)
        if part.is_absolute() or '..' in part.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_PATH')
        seen.add(name);path=ROOT/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('PACKAGE_MEMBER_SHA:'+name)
    return hashlib.sha256(raw).hexdigest()

def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());root=Path(a['memory_source_root'])
    if hashlib.sha256((root/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['memory_manifest_sha256']:raise ValueError('REGISTERED_MEMORY_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(root));spec=importlib.util.spec_from_file_location('_prior_memory_index_entry',root/'context_entry.py')
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    _,_,_,prepared=prior.load()
    from exact_bindings import read_ref
    for ref in a['preserved_current_refs'].values():read_ref(ref,as_bytes=True)
    return a,prior,identity,prepared

@contextmanager
def install(a,identity):
    import adapter,entry.driver as driver,entry.training_job as training_job
    from exact_bindings import file_ref,read_json
    from execution_index import register,resolve_run
    from pre_typed import install as pre_install
    native=adapter.run_h44
    transport=inspect.getclosurevars(native).nonlocals['native']
    if '_transport_worker' not in transport.__globals__:raise ValueError('TYPED_TRANSPORT_SOURCE_ANCHOR')
    original_worker=transport.__globals__['_transport_worker'];original_request=transport.__globals__['_transport_request']
    def h44(binding,capture,out,*,execute):
        index=register(binding,capture,out,a,file_ref(ROOT/'AUTHORITY.json'))
        def request(value,current):
            return {**original_request(value,current),'registered_option_registry':index['option_registry_ref'],'registered_option_source':file_ref(ROOT/'AUTHORITY.json')}
        transport.__globals__['_transport_worker']=ROOT/'worker.py';transport.__globals__['_transport_request']=request
        try:return native(binding,capture,Path(index['execution_run_root']).parent,execute=execute)
        finally:transport.__globals__['_transport_worker']=original_worker;transport.__globals__['_transport_request']=original_request
    native_evidence=driver.current_h44_evidence;native_train=training_job.execute_current_training_job
    def evidence(analyzer_output):
        run=resolve_run(Path(analyzer_output)/'h44/run')
        return native_evidence(run.parent.parent)
    def train(**kwargs):
        kwargs['h44_run_root']=resolve_run(kwargs['h44_run_root']);return native_train(**kwargs)
    with pre_install(a),patch.object(adapter,'run_h44',h44),patch.object(driver,'current_h44_evidence',evidence),patch.object(training_job,'execute_current_training_job',train):yield

def run(invocation):
    a,prior,identity,prepared=load()
    import memory_index,entry.progress as progress
    from exact_bindings import file_ref,immutable_json
    immutable_json(Path(a['owner_root'])/'runtime_extensions'/identity/'TYPED_OPTION_ENTRY.json',{'source_authority':file_ref(ROOT/'AUTHORITY.json'),
        'source_manifest':file_ref(ROOT/'PACKAGE_FILES.sha256'),'current_round_id':a['materialization_round_id'],
        'pre_candidate_reselection':False,'existing_artifacts_overwritten':False})
    native=memory_index.install;old_update=progress.update
    @contextmanager
    def combined(*args,**kwargs):
        with native(*args,**kwargs),install(a,identity):yield
    def update(owner,**fields):return old_update(owner,**{**fields,'typed_option_entry_root':str(ROOT),'typed_option_entry_manifest_sha256':identity})
    with patch.object(memory_index,'install',combined),patch.object(progress,'update',update):return prior.run(invocation)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))

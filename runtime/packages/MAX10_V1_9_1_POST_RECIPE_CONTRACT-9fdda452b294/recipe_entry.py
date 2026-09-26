from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import sys,importlib.util,json,hashlib,inspect
ROOT=Path(__file__).resolve().parent

def verify():
    from pathlib import PurePosixPath
    raw=(ROOT/'PACKAGE_FILES.sha256').read_bytes();seen=set()
    for line in raw.decode().splitlines():
        sha,name=line.split(maxsplit=1);p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_PATH')
        seen.add(name);path=ROOT/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('PACKAGE_MEMBER_SHA:'+name)
    return hashlib.sha256(raw).hexdigest()

def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());root=Path(a['typed_source_root'])
    if hashlib.sha256((root/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['typed_manifest_sha256']:raise ValueError('REGISTERED_TYPED_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(root));spec=importlib.util.spec_from_file_location('_prior_typed_entry',root/'registered_entry.py')
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    _,_,_,prepared=prior.load()
    from post_recovery import check_original
    check_original(a)
    return a,prior,identity,prepared

@contextmanager
def install(a,identity,prior):
    import adapter,entry.driver as driver,entry.training_job as training_job
    from exact_bindings import file_ref
    from execution_index import register,resolve_run
    from post_recovery import materialize,resolve
    wrapper=adapter.run_h44;inside=inspect.getclosurevars(wrapper).nonlocals
    native=inside['native'];transport=inside['transport']
    old_worker=transport.__globals__['_transport_worker'];old_request=transport.__globals__['_transport_request']
    a190=json.loads((Path(a['typed_source_root'])/'AUTHORITY.json').read_bytes())
    source190=file_ref(Path(a['typed_source_root'])/'AUTHORITY.json')
    def h44(binding,capture,out,*,execute):
        index=register(binding,capture,out,a190,source190);run=Path(index['execution_run_root'])
        if binding['round_id']==a['post_recovery_round_id']:
            if str(run)!=a['post_original_run_root']:raise ValueError('POST_RECOVERY_CURRENT_RUN_DRIFT')
            recovery=materialize(a,identity,ROOT,publish=execute);run=Path(recovery['execution_run_root'])
        def request(value,current):
            return {**old_request(value,current),'registered_option_registry':index['option_registry_ref'],
                'registered_option_source':source190,'registered_recipe_source':file_ref(ROOT/'AUTHORITY.json')}
        transport.__globals__['_transport_worker']=ROOT/'recipe_worker.py';transport.__globals__['_transport_request']=request
        try:return native(binding,capture,run.parent,execute=execute)
        finally:transport.__globals__['_transport_worker']=old_worker;transport.__globals__['_transport_request']=old_request
    old_evidence=driver.current_h44_evidence;old_train=training_job.execute_current_training_job
    def evidence(analyzer_output):
        run=resolve(resolve_run(Path(analyzer_output)/'h44/run'))
        return old_evidence(run.parent.parent)
    def train(**kwargs):
        kwargs['h44_run_root']=resolve(resolve_run(kwargs['h44_run_root']));return old_train(**kwargs)
    with patch.object(adapter,'run_h44',h44),patch.object(driver,'current_h44_evidence',evidence),patch.object(training_job,'execute_current_training_job',train):yield

def run(invocation):
    a,prior,identity,prepared=load()
    import entry.progress as progress
    native=prior.install;old_update=progress.update
    @contextmanager
    def combined(*args,**kwargs):
        with native(*args,**kwargs),install(a,identity,prior):yield
    def update(owner,**fields):return old_update(owner,**{**fields,'recipe_contract_entry_root':str(ROOT),'recipe_contract_entry_manifest_sha256':identity})
    with patch.object(prior,'install',combined),patch.object(progress,'update',update):return prior.run(invocation)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))

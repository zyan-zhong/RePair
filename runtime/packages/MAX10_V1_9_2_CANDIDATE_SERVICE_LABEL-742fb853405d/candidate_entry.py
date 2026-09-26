from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import sys,importlib.util,json,hashlib
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
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());root=Path(a['recipe_source_root'])
    if hashlib.sha256((root/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['recipe_manifest_sha256']:raise ValueError('REGISTERED_RECIPE_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(root));spec=importlib.util.spec_from_file_location('_prior_recipe_entry',root/'recipe_entry.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    _,_,_,prepared=prior.load()
    from exact_bindings import read_ref
    for ref in a['preserved_training_select_refs'].values():read_ref(ref,as_bytes=True)
    return a,prior,identity,prepared

@contextmanager
def install(a,identity):
    import entry.offoff_job as job,entry.candidate_runtime as candidate
    import offoff_binding.registered_inputs as inputs
    from candidate_labels import load_publisher,load_registered_inputs
    from select_index import register
    native=job.execute_current_offoff_job;publisher=load_publisher(a['candidate_publisher_ref'])
    def execute(**kwargs):
        if kwargs['start']['round_id']==a['label_recovery_round_id']:
            kwargs['output_root']=register(kwargs['output_root'],a,identity,ROOT)
        return native(**kwargs)
    with patch.object(candidate,'publish_candidate',publisher),patch.object(inputs,'materialize_registered_inputs',load_registered_inputs(a['registered_inputs_source_ref'])),patch.object(job,'execute_current_offoff_job',execute):yield

def run(invocation):
    a,prior,identity,prepared=load()
    import entry.progress as progress
    native=prior.install;old_update=progress.update
    @contextmanager
    def combined(*args,**kwargs):
        with native(*args,**kwargs),install(a,identity):yield
    def update(owner,**fields):return old_update(owner,**{**fields,'candidate_label_entry_root':str(ROOT),'candidate_label_entry_manifest_sha256':identity})
    with patch.object(prior,'install',combined),patch.object(progress,'update',update):return prior.run(invocation)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))

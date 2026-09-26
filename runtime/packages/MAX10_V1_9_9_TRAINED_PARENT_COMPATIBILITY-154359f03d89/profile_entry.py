from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from unittest.mock import patch
import json,hashlib,sys,importlib
ROOT=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'sha256':digest(p)}
def verify():
    raw=(ROOT/'PACKAGE_FILES.sha256').read_bytes();seen=set()
    for line in raw.decode().splitlines():
        expected,name=line.split(maxsplit=1);p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_PATH')
        seen.add(name);file=ROOT/name
        if file.is_symlink() or digest(file)!=expected:raise ValueError('PACKAGE_SOURCE_CHANGED:'+name)
    return hashlib.sha256(raw).hexdigest()
def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());prior_root=Path(a['profile_predecessor_root'])
    if digest(prior_root/'PACKAGE_FILES.sha256')!=a['profile_predecessor_manifest_sha256']:raise ValueError('PROFILE_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(prior_root));prior=importlib.import_module('transport_entry');prior_prepared=prior.load()
    from runtime_overlay import checked
    for source in a['native_refs'].values():checked(source)
    return a,prior,identity,prior_prepared[3]

def check_binding(binding):
    from exact_bindings import read_ref
    from condition_contract import resolve_condition
    request=read_ref(binding['refs']['request']);runtime_ref=binding['refs']['actor_runtime']
    if runtime_ref['file_sha256']!=request['policy_runtime_binding_sha256']:raise ValueError('SOURCE_CONDITION_RUNTIME_REQUEST_BINDING_MISMATCH')
    profile_ref={'path':str(Path(binding['state_root'])/'round_evidence/ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1.json'),'file_sha256':request['execution_profile_sha256']}
    profile=read_ref(profile_ref)
    from pchsi.research_intelligence.human_f0f1_runtime import load_continuation_runtime_binding_v2
    runtime=load_continuation_runtime_binding_v2(runtime_ref['path'],expected_file_sha256=runtime_ref['file_sha256'],expected_model=profile['served_model_name'])
    # This preflight does not assert PRE acceptance. The real PRE object is
    # independently checked by the original bound_condition after PRE closes.
    condition=resolve_condition(binding,request,runtime,profile,binding,None)
    return {'schema_id':'REGISTERED_CURRENT_PARENT_PROFILE_PREFLIGHT_V1','round_id':binding['round_id'],
        'parent_policy_id':binding['parent_policy_id'],'source_policy_condition':condition,
        'runtime_ref':runtime_ref,'profile_ref':profile_ref,'runtime_schema_id':runtime['schema_id'],
        'scientific_execution_authority_conferred':False}

@contextmanager
def installed(a,identity):
    import source_condition,adapter,execution_index
    from runtime_overlay import configure
    from condition_contract import resolve_condition
    expected=a['native_refs']['source_condition.py'];
    if Path(source_condition.__file__)!=Path(expected['path']) or digest(expected['path'])!=expected['sha256']:raise ValueError('SOURCE_CONDITION_IMPLEMENTATION_DRIFT')
    configure(a,ROOT,identity);native=adapter.run_bound_round
    def bound(value,*args,**kwargs):
        binding=value if isinstance(value,dict) else json.loads(Path(value).read_bytes())
        proof=check_binding(binding)
        from exact_bindings import immutable_json
        out=Path(args[0]) if args and args[0] is not None else Path(kwargs.get('output_root') or binding['output_root'])
        immutable_json(out/'registered_profile_updates'/identity/'PROFILE_PREFLIGHT.json',{**proof,'authority_ref':ref(ROOT/'AUTHORITY.json')})
        return native(value,*args,**kwargs)
    from strategy_reference import registered_index_function
    register=registered_index_function(a['native_refs']['execution_index.py'])
    with patch.object(source_condition,'resolve_condition',resolve_condition),patch.object(adapter,'run_bound_round',bound),patch.object(execution_index,'register',register):yield

def run(invocation):
    a,prior,identity,prepared=load()
    import entry.progress as progress
    native=progress.update
    def update(owner,**fields):return native(owner,**{**fields,'trained_parent_entry_root':str(ROOT),'trained_parent_manifest_sha256':identity})
    with installed(a,identity),patch.object(progress,'update',update):return prior.run(invocation)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))

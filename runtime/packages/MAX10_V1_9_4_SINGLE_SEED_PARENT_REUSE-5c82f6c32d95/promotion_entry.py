from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import sys,json,hashlib,importlib.util,copy
ROOT=Path(__file__).resolve().parent

def verify():
    from pathlib import PurePosixPath
    raw=(ROOT/'PACKAGE_FILES.sha256').read_bytes();seen=set()
    for line in raw.decode().splitlines():
        expected,name=line.split(maxsplit=1);p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_PATH')
        seen.add(name);path=ROOT/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('PACKAGE_MEMBER_SHA:'+name)
    return hashlib.sha256(raw).hexdigest()

def load():
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());root=Path(a['candidate_source_root'])
    if hashlib.sha256((root/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['candidate_manifest_sha256']:raise ValueError('REGISTERED_CANDIDATE_PREDECESSOR_CHANGED')
    sys.path.insert(0,str(root));spec=importlib.util.spec_from_file_location('_prior_candidate_entry',root/'candidate_entry.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    _,_,_,prepared=prior.load();return a,prior,identity,prepared

def source_refs():
    return [{'path':str(ROOT/name),'sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest()} for name in ('goal_metric.py','goal_capture.py','goal_runtime.py','promotion_v2.py')]

def future_deployment(deployment,a):
    from continuity_binding.api import read_ref,write_once
    from promotion_v2 import validate_rule
    old=read_ref(deployment['promotion_rule_ref']);refs=source_refs()
    producer=old['decision_producer'];integrity=next(r for r in deployment['offoff_source_registration']['source_refs'] if r['sha256']==producer['sha256'])
    rule={**old,'schema_id':'FROZEN_TRAIN_SELECT_PROMOTION_RULE_V2','decision_rule_id':'SUCCESS_THEN_TERMINAL_GOAL_FRACTION_V1',
        'comparison':'success_then_terminal_goal_fraction','secondary_metrics_role':'goal_fraction_tie_break_only',
        'goal_metric_id':'terminal_dynamic_goal_condition_fraction_v1','memory_state':'OFF','harness_state':'OFF','benchmark_feedback_used':False,
        'effective_after_round_index':a['promotion_activation_after_round_index'],'excluded_request_ref':a['promotion_excluded_request_ref'],
        'integrity_producer_ref':integrity,'goal_source_refs':refs,'environment_source_refs':a['goal_environment_source_refs'],
        'decision_producer':{'source_ref':refs[-1],'entrypoint':'decide'}}
    seeds=a.get('future_select_replicate_seeds',old['replicate_seeds'])
    if not seeds or seeds!=old['replicate_seeds'][:len(seeds)]:raise ValueError('FUTURE_SELECT_SEEDS_MUST_USE_REGISTERED_PREFIX')
    rule['replicate_seeds']=seeds
    rule['previous_promotion_rule_ref']=deployment['promotion_rule_ref']
    rule['select_parallel_resource_ref']=a['select_parallel_resource_ref']
    validate_rule(rule);ref=write_once(ROOT/'runtime/FROZEN_PROMOTION_RULE_V2.json',rule)
    result=copy.deepcopy(deployment);result['promotion_rule_ref']=ref;result['offoff_source_registration']['promotion_rule_ref']=ref
    result['offoff_source_registration']['source_refs'].extend(refs)
    result['offoff_source_registration']['source_refs'].extend({'path':str(ROOT/name),'sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest()} for name in ('parent_cache.py','parent_replay.py','reuse_runtime.py'))
    return result

def seed_inputs(materializer):
    """Retain historical grid validation; emit only the prospectively frozen subset."""
    from continuity_binding.api import read_ref
    import types
    def execute(**kwargs):
        rule=read_ref(kwargs['registration']['promotion_rule_ref'])
        if rule.get('schema_id')!='FROZEN_TRAIN_SELECT_PROMOTION_RULE_V2':return materializer(**kwargs)
        from promotion_v2 import validate_rule
        validate_rule(rule)
        globals_=dict(materializer.__globals__);native_write=globals_['write_once']
        def write(path,value):
            if value.get('schema_id')=='CURRENT_REGISTERED_OFFOFF_PROTOCOL_V1':
                original=value['replicate_seeds'];selected=rule['replicate_seeds']
                if selected!=original[:len(selected)]:raise ValueError('SELECT_GRID_AMENDMENT_NOT_REGISTERED_PREFIX')
                value={**value,'replicate_seeds':selected}
                if 'parent_select_cache_ref' in kwargs['registration']:
                    value['parent_select_cache_ref']=kwargs['registration']['parent_select_cache_ref']
            return native_write(path,value)
        globals_['write_once']=write
        bound=types.FunctionType(materializer.__code__,globals_,materializer.__name__,materializer.__defaults__,materializer.__closure__)
        bound.__kwdefaults__=materializer.__kwdefaults__
        return bound(**kwargs)
    return execute

@contextmanager
def install(a,identity):
    from entry.driver import ExistingComponentRoundDriver as Driver
    import entry.offoff_job as job
    import offoff_binding.registered_inputs as inputs
    from continuity_binding.api import read_ref,write_once
    from goal_runtime import installed,rule_from_binding
    native=Driver.execute_round;native_jobs=job.execute_current_offoff_jobs;native_next=Driver.build_next
    def execute(driver,start,attempt_root):
        current=driver._binding(start)
        if current['round_index']<=a['promotion_activation_after_round_index']:return native(driver,start,attempt_root)
        amendment=Path(attempt_root)/'FROZEN_ACCEPTANCE_AMENDMENT.json'
        if not amendment.exists() and any((Path(attempt_root)/name).exists() for name in ('rollout','analyzer','training','offoff','DRIVER_ROUND_RESULT.json')):
            write_once(Path(attempt_root)/'ACCEPTANCE_AMENDMENT_DEFERRED.json',{'schema_id':'REGISTERED_ACCEPTANCE_AMENDMENT_DEFERRED_V1',
                'request_sha256':start['request_sha256'],'reason':'EXISTING_ROUND_STARTED_BEFORE_AMENDMENT','existing_rule_retained':True})
            return native(driver,start,attempt_root)
        prior=driver.deployment;deployment=future_deployment(prior,a)
        from parent_cache import index_path,ref
        cache_path=index_path(driver,start)
        if not cache_path.exists():raise ValueError('REGISTERED_PARENT_SELECT_CACHE_AUTHORITY_MISSING:'+str(cache_path))
        deployment['offoff_source_registration']['parent_select_cache_ref']=ref(cache_path)
        write_once(amendment,{'schema_id':'REGISTERED_FUTURE_ROUND_ACCEPTANCE_AMENDMENT_V1',
            'request_sha256':start['request_sha256'],'round_id':start['round_id'],'round_index':current['round_index'],
            'promotion_rule_ref':deployment['promotion_rule_ref'],'entry_manifest_sha256':identity,'frozen_before_round_execution':True})
        driver.deployment=deployment
        try:return native(driver,start,attempt_root)
        finally:driver.deployment=prior
    def jobs(**kwargs):
        binding=read_ref(read_ref(kwargs['parallel_ref'])['binding_ref'])
        if rule_from_binding(binding) is None:return native_jobs(**kwargs)
        with patch.object(job,'__file__',str(ROOT/'goal_worker_entry.py')):return native_jobs(**kwargs)
    def build_next(driver,start,result,governance):
        next_request=native_next(driver,start,result,governance)
        if result['outcome']!='PROTOCOL_INFRA_INVALID' and driver._binding(start)['round_index']>=a['promotion_activation_after_round_index']:
            from parent_cache import next_cache
            next_cache(driver,start,result,next_request)
        elif result['outcome']=='PROTOCOL_INFRA_INVALID':
            from parent_cache import index_path,ref
            previous=index_path(driver,start)
            if previous.exists():
                value=read_ref(ref(previous))
                write_once(index_path(driver,next_request),{**value,'request_sha256':next_request['request_sha256']})
        return next_request
    from reuse_runtime import installed as reuse_installed
    from current_cutover import installed as cutover_installed
    with installed(),reuse_installed(),patch.object(Driver,'execute_round',execute),patch.object(Driver,'build_next',build_next),patch.object(job,'execute_current_offoff_jobs',jobs),patch.object(inputs,'materialize_registered_inputs',seed_inputs(inputs.materialize_registered_inputs)),cutover_installed(a):yield

def run(invocation):
    a,prior,identity,prepared=load()
    native=prior.install
    @contextmanager
    def combined(*args,**kwargs):
        with native(*args,**kwargs),install(a,identity):yield
    import entry.progress as progress
    old=progress.update
    def update(owner,**fields):return old(owner,**{**fields,'promotion_entry_root':str(ROOT),'promotion_entry_manifest_sha256':identity,'promotion_rule_effective_after_round_index':a['promotion_activation_after_round_index']})
    with patch.object(prior,'install',combined),patch.object(progress,'update',update):return prior.run(invocation)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))

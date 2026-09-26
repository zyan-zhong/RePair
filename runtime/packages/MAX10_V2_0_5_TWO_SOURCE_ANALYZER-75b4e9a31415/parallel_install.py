"""Install before the sealed entry composes its existing scientific wrappers."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
from functools import wraps
import json,hashlib,os,time
import source_parallel
from parallel_registry import run_registry

def checked(ref):
    raw=Path(ref['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref.get('sha256',ref.get('file_sha256')):raise ValueError('PARALLEL_AUTHORITY_SHA')
    return json.loads(raw)

def round_index(a,binding):
    req=checked(binding['refs']['request'])
    index=json.loads((Path(a['owner_root'])/'request_bindings'/(req['request_sha256']+'.json')).read_bytes())
    if checked(index['request'])!=req or req['round_id']!=binding['round_id']:raise ValueError('PARALLEL_ROUND_INDEX_BINDING')
    return index['round_index']

def publisher(a,binding,identity,phase):
    from repair import progress_write
    path=Path(a['owner_root'])/'ANALYZER_PARALLEL_PROGRESS.json'
    def publish(fields):
        progress_write(path,{'schema_id':'ANALYZER_SOURCE_PARALLEL_PROGRESS_V1','round_id':binding['round_id'],
            'phase':phase,'policy_manifest_sha256':identity,**fields})
    return publish

@contextmanager
def installed(a,identity,root):
    from parallel_group_stage import run_group_tail
    import adapter,resume_entry
    from pchsi.cognitive_runtime import registry_runner as rr
    from exact_bindings import immutable_json
    native_bound=adapter.run_bound_round;native_group=adapter.run_group_tail;native_registry=rr.run_registry
    native_observer=resume_entry.progress_observer;current={}
    policy=a['parallel_policy'];workers=policy['max_concurrent_sources']
    def enabled(binding):return round_index(a,binding)>=policy['activation_round_index']
    @wraps(native_bound)
    def bound(binding_path,*args,**kwargs):
        binding=binding_path if isinstance(binding_path,dict) else json.loads(Path(binding_path).read_bytes())
        prior=dict(current);current.clear();current.update(binding=binding,enabled=enabled(binding))
        try:return native_bound(binding_path,*args,**kwargs)
        finally:current.clear();current.update(prior)
    @wraps(native_registry)
    def registry(**kwargs):
        if not current.get('enabled'):return native_registry(**kwargs)
        return run_registry(rr,native_registry,workers=workers,
            observe=publisher(a,current['binding'],identity,'L'),**kwargs)
    @wraps(native_group)
    def group(binding,values,core,prepared,accesses,out):
        if not enabled(binding):return native_group(binding,values,core,prepared,accesses,out)
        def mapping(items,fn,*,key,phase):
            return source_parallel.map_sources(items,fn,key=key,workers=workers,
                observe=publisher(a,binding,identity,phase))
        return run_group_tail(binding,values,core,prepared,accesses,out,parallel_map=mapping)
    def observer(authority,scope):
        original=native_observer(authority,scope)
        def observe(kwargs,result):
            if source_parallel._channel is None:return original(kwargs,result)
            if result is None:source_parallel.check_admission()
            source_parallel.emit({'round_id':scope['round_id'],'stage_id':kwargs['stage_id'],
                'state':'WAITING_PROVIDER' if result is None else result['status'],
                'logical_call_id':None if result is None else result['logical_call_id'],
                'scientific_unit_id':kwargs.get('unit_identity',{}).get('scientific_unit_id')})
        return observe
    immutable_json(Path(a['owner_root'])/'runtime_extensions'/identity/'PARALLEL_INSTALLED.json',{
        'policy':policy,'authority_ref':{'path':str(root/'AUTHORITY.json'),'sha256':hashlib.sha256((root/'AUTHORITY.json').read_bytes()).hexdigest()},
        'provider_use_claimed':False})
    with patch.object(adapter,'run_bound_round',bound),patch.object(adapter,'run_group_tail',group),\
         patch.object(rr,'run_registry',registry),patch.object(resume_entry,'progress_observer',observer):yield

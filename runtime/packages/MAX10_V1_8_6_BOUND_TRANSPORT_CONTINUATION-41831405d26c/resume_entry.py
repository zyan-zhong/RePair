"""Small campaign-bound overlay over the sealed, already deployed execution entry."""
from pathlib import Path,PurePosixPath
from contextlib import contextmanager
from unittest.mock import patch
import hashlib,json,sys,types
ROOT=Path(__file__).resolve().parent

def verify():
    raw=(ROOT/'PACKAGE_FILES.sha256').read_bytes();seen=set()
    for line in raw.decode().splitlines():
        digest,name=line.split(maxsplit=1);part=PurePosixPath(name)
        if part.is_absolute() or '..' in part.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_INVALID')
        seen.add(name);path=ROOT/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('PACKAGE_SOURCE_CHANGED:'+name)
    return hashlib.sha256(raw).hexdigest()

def load():
    identity=verify();raw=(ROOT/'AUTHORITY.json').read_bytes();a=json.loads(raw);a['_authority_sha256']=hashlib.sha256(raw).hexdigest()
    prior=Path(a['predecessor_source_root'])
    if hashlib.sha256((prior/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['predecessor_manifest_sha256']:raise ValueError('PREDECESSOR_CHANGED')
    sys.path.insert(0,str(prior));import signature_entry
    _,base,_=signature_entry.load()
    for ref in a['immutable_refs'].values():base.read_ref(ref)
    stop=base.read_ref(a['stop_ref'])
    if stop['message']!='GROUP_GLOBAL_HARD_STOP:G-A2:INFRASTRUCTURE_UNAVAILABLE':raise ValueError('EXACT_GROUP_STOP_REQUIRED')
    prepared=base.prepare()
    from transport_scope import bound_scope
    from group_recovery import validate_old
    scope=bound_scope(prepared[1]['analyzer_binding'],a['campaign_authority_ref']);validate_old(a)
    return a,base,signature_entry,identity,prepared,scope

def recovery_root(a):
    return Path(a['repair']['call_dir']).parent/'registered_transport_continuations'/a['_authority_sha256']

def progress_observer(a,scope):
    from repair import progress_write
    path=Path(a['owner_root'])/'CHAIN_PROGRESS.json'
    def observe(kwargs,result):
        fields={'round_id':scope['round_id'],'stage_id':kwargs['stage_id'],'state':'WAITING_PROVIDER' if result is None else result['status'],
            'logical_call_id':None if result is None else result['logical_call_id'],
            'scientific_unit_id':kwargs.get('unit_identity',{}).get('scientific_unit_id'),
            'transport_budget_ref':scope['campaign_authority_ref']}
        progress_write(path,fields)
    return observe

def worker_request(request,binding,a):
    from continuation import file_ref
    from exact_bindings import file_ref as typed_file_ref
    return {**request,'registered_transport_binding':typed_file_ref(Path(binding['output_root'])/'EXACT_ANALYZER_OPERATION_INPUT.json'),
        'registered_transport_entry':file_ref(ROOT/'AUTHORITY.json'),'registered_transport_manifest':file_ref(ROOT/'PACKAGE_FILES.sha256')}

def h44_function(a):
    from continuation import regular
    source=regular(a['h44_input_ref']['path']).read_bytes()
    if hashlib.sha256(source).hexdigest()!=a['h44_input_ref']['sha256']:raise ValueError('H44_INPUT_SOURCE_CHANGED')
    text=source.decode();needle="request_path = out / 'H44_ADAPTER_REQUEST.json'; immutable_json(request_path, request)"
    worker="str(Path(__file__).with_name('h44_worker.py'))"
    if text.count(needle)!=1 or text.count(worker)!=1:raise ValueError('H44_INPUT_OVERLAY_SOURCE_DRIFT')
    text=text.replace(needle,"request = _transport_request(request, binding)\n    "+needle).replace(worker,"str(_transport_worker)")
    module=types.ModuleType('_registered_h44_transport');module.__file__=a['h44_input_ref']['path']
    module._transport_request=lambda request,binding:worker_request(request,binding,a);module._transport_worker=ROOT/'child_entry.py'
    exec(compile(text,module.__file__,'exec'),module.__dict__)
    return module.run_h44

@contextmanager
def install(a):
    import adapter,pacing
    from transport_scope import bound_scope,install_executor,retry_pacing
    from group_recovery import group_wrapper
    native=adapter.run_bound_round;native_load=adapter.load_cores
    def bound(binding_path,*args,**kwargs):
        binding=binding_path if isinstance(binding_path,dict) else json.loads(Path(binding_path).read_bytes())
        if args and args[0] is not None:binding={**binding,'output_root':str(Path(args[0]).absolute())}
        elif kwargs.get('output_root') is not None:binding={**binding,'output_root':str(Path(kwargs['output_root']).absolute())}
        scope=bound_scope(binding,a['campaign_authority_ref']);observe=progress_observer(a,scope)
        def cores(current):
            core=native_load(current)
            # Later rounds use the same policy but cannot match the old call identity.
            core.u.execute_or_reuse=group_wrapper(core.u.execute_or_reuse,core,a,scope,recovery_root(a),observe)
            return core
        with install_executor(scope,observe),patch.object(adapter,'load_cores',cores):return native(binding_path,*args,**kwargs)
    @contextmanager
    def paced(orch,transport,**kwargs):
        with retry_pacing(orch,transport,offset_root=recovery_root(a)/'calls',consumed=a['repair']['consumed_attempts'],**kwargs):yield
    with patch.object(adapter,'run_bound_round',bound),patch.object(adapter,'run_h44',h44_function(a)),patch.object(pacing,'native_retry_pacing',paced):yield

def run(invocation):
    a,base,prior,identity,prepared,scope=load()
    from entry.campaign_owner import _write_once
    from continuation import file_ref
    root=Path(a['owner_root'])/'runtime_extensions'/identity
    _write_once(root/'TRANSPORT_ENTRY.json',{'authority':file_ref(ROOT/'AUTHORITY.json'),'manifest':file_ref(ROOT/'PACKAGE_FILES.sha256'),
        'campaign_authority':a['campaign_authority_ref'],'preserved_local_execution':a['immutable_refs']['local_execution']})
    import entry.progress as progress
    native=progress.update
    def update(owner,**fields):
        return native(owner,**{**fields,'transport_entry_manifest_sha256':identity,'transport_entry_root':str(ROOT),'chain_progress_path':str(Path(a['owner_root'])/'CHAIN_PROGRESS.json')})
    with install(a),patch.object(progress,'update',update):return prior.run(invocation)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--invocation');args=p.parse_args()
    if args.run:raise SystemExit(run(args.invocation or ''))
    print(json.dumps({'manifest_sha256':verify()}))

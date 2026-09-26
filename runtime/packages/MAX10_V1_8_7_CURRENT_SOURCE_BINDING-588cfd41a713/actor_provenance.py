"""Reconcile captured H44 actor sources with the registered current checkout."""
from pathlib import Path,PurePosixPath
import hashlib,subprocess,sys,types

def sha(raw): return hashlib.sha256(raw).hexdigest()

def reconcile(binding, authority):
    from exact_bindings import read_ref
    manifest=read_ref(binding['packages']['h44']['manifest'],as_bytes=True)
    repo=Path(binding['scientific_repo_root']);head=binding['source_registration']['scientific_repo_head']
    if head!=authority['current_scientific_commit']:raise ValueError('ACTOR_REGISTERED_COMMIT_CHANGED')
    rows=[]
    for line in manifest.decode().splitlines():
        digest,name=line.split(maxsplit=1);p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts:raise ValueError('ACTOR_MANIFEST_PATH_INVALID')
        if name.startswith('native_repo/src/') and name.endswith('.py'):
            relative=name[len('native_repo/'):];raw=(repo/relative).read_bytes()
            captured=Path(binding['packages']['h44']['root'])/name
            if sha(captured.read_bytes())!=digest:raise ValueError('CAPTURED_ACTOR_SOURCE_CHANGED:'+name)
            expected=authority['native_source_deltas'].get(relative,digest)
            if sha(raw)!=expected:raise ValueError('REGISTERED_ACTOR_SOURCE_CHANGED:'+relative)
            rows.append({'path':relative,'captured_sha256':digest,'current_sha256':sha(raw),'bytes':raw})
    if not rows or set(authority['native_source_deltas'])!={r['path'] for r in rows if r['current_sha256']!=r['captured_sha256']}:
        raise ValueError('ACTOR_RECONCILIATION_DELTA_MISMATCH')
    query=''.join(head+':'+r['path']+'\n' for r in rows).encode()
    result=subprocess.run(['git','-C',str(repo),'cat-file','--batch'],input=query,capture_output=True,check=True)
    payload=result.stdout;offset=0
    for row in rows:
        end=payload.index(b'\n',offset);header=payload[offset:end].split()
        if len(header)!=3 or header[1]!=b'blob':raise ValueError('REGISTERED_ACTOR_GIT_BLOB_MISSING')
        length=int(header[2]);blob=payload[end+1:end+1+length];offset=end+2+length
        if blob!=row.pop('bytes'):raise ValueError('ACTOR_CHECKOUT_DIFFERS_FROM_REGISTERED_COMMIT:'+row['path'])
    if offset!=len(payload):raise ValueError('ACTOR_GIT_BATCH_OUTPUT_MISMATCH')
    import pchsi
    if list(pchsi.__path__)!=[str(repo/'src/pchsi')]:raise ValueError('ACTOR_WORKER_NATIVE_NAMESPACE_MISMATCH')
    for name,module in tuple(sys.modules.items()):
        if name.startswith('pchsi.') and getattr(module,'__file__',None):
            if not Path(module.__file__).resolve().is_relative_to((repo/'src').resolve()):
                raise ValueError('ACTOR_WORKER_FOREIGN_IMPORTED_MODULE:'+name)
    return {'schema_id':'CURRENT_ACTOR_SOURCE_RECONCILIATION_V1','actor_commit':head,
        'source_registration':binding['source_registration'],'h44_manifest':binding['packages']['h44']['manifest'],
        'native_python_files_verified':len(rows),'byte_identical_actor_source_count':sum(r['captured_sha256']==r['current_sha256'] for r in rows),
        'registered_non_actor_source_deltas':authority['native_source_deltas'],'files':rows,
        'native_namespace':str(repo/'src/pchsi'),'production_git_mutation_count':0}

def install_round_plan(request,binding,authority):
    from memory_binding.worker_bootstrap import bootstrap_current_and_children
    bootstrap_current_and_children(binding['scientific_repo_root'])
    root=Path(binding['packages']['h44']['root'])
    if Path(request['h44_root'])!=root:raise ValueError('ACTOR_H44_ROOT_CHANGED')
    from exact_bindings import read_ref
    expected=dict((name,digest) for digest,name in (line.split(maxsplit=1) for line in read_ref(binding['packages']['h44']['manifest'],as_bytes=True).decode().splitlines()))
    path=root/'round_plan.py';raw=path.read_bytes()
    if sha(raw)!=expected['round_plan.py']:raise ValueError('ACTOR_ROUND_PLAN_SOURCE_CHANGED')
    proof=reconcile(binding,authority)
    source=raw.decode();needle="provenance=read_json(ROOT/'assets/source_revision.json')"
    if source.count(needle)!=1:raise ValueError('ACTOR_ROUND_PLAN_OVERLAY_DRIFT')
    source=source.replace(needle,"provenance=_current_actor_provenance\n    put_json(run_root/'authority/CURRENT_ACTOR_SOURCE_RECONCILIATION_V1.json', provenance)")
    module=types.ModuleType('round_plan');module.__file__=str(path);module._current_actor_provenance=proof
    sys.path.insert(0,str(root))
    from exact_action import install_dispatch
    dispatch=install_dispatch(root,expected)
    exec(compile(source,str(path),'exec'),module.__dict__)
    original_prepare=module.prepare_plan
    def prepare(**kwargs):
        plan=original_prepare(**kwargs)
        from portfolio_guard import require_complete_portfolio
        require_complete_portfolio(plan)
        return plan
    module.prepare_plan=prepare
    sys.modules['round_plan']=module
    controller_path=root/'controller.py';raw=controller_path.read_bytes()
    if sha(raw)!=expected['controller.py']:raise ValueError('CURRENT_CONTROLLER_SOURCE_CHANGED')
    text=raw.decode();needle="str(ROOT/'gpu_job.py')"
    if text.count(needle)!=1:raise ValueError('CURRENT_CONTROLLER_GPU_ENTRY_SOURCE_DRIFT')
    text=text.replace(needle,'str(_registered_gpu_entry)')
    controller=types.ModuleType('controller');controller.__file__=str(controller_path)
    controller._registered_gpu_entry=Path(__file__).with_name('gpu_entry.py')
    exec(compile(text,str(controller_path),'exec'),controller.__dict__)
    from portfolio_guard import guard_controller
    controller.run_controller=guard_controller(controller.run_controller)
    sys.modules['controller']=controller
    return proof

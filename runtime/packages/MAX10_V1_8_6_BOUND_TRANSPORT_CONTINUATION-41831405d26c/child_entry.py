"""Run the original isolated worker with explicit, verified transport authority."""
from pathlib import Path
from contextlib import ExitStack
import sys,json,hashlib,importlib.util
ROOT=Path(__file__).resolve().parent

def main():
    from resume_entry import verify
    verify();request_path=Path(sys.argv[sys.argv.index('--request')+1]);request=json.loads(request_path.read_bytes())
    a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    if request['registered_transport_entry']!={'path':str(ROOT/'AUTHORITY.json'),'sha256':hashlib.sha256((ROOT/'AUTHORITY.json').read_bytes()).hexdigest()}:raise ValueError('WORKER_ENTRY_BINDING_CHANGED')
    if request['registered_transport_manifest']!={'path':str(ROOT/'PACKAGE_FILES.sha256'),'sha256':verify()}:raise ValueError('WORKER_SOURCE_BINDING_CHANGED')
    base=Path(a['base_package_root']);sys.path.insert(0,str(base/'live_adapter'));sys.path.insert(0,str(base))
    sys.path.insert(0,a['v185_source_root'])
    from exact_bindings import read_ref
    binding=read_ref(request['registered_transport_binding'])
    if request['scientific_repo_root']!=binding['scientific_repo_root'] or not Path(request['run_root']).is_relative_to(Path(binding['output_root'])):raise ValueError('WORKER_ROUND_BINDING_CHANGED')
    path=Path(a['h44_worker_ref']['path']);raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=a['h44_worker_ref']['sha256']:raise ValueError('WORKER_SOURCE_CHANGED')
    spec=importlib.util.spec_from_file_location('_registered_original_h44_worker',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=module.load_current_post_module
    with ExitStack() as stack:
        def load_post(req,root):
            from transport_scope import bound_scope,install_executor,retry_pacing
            from pacing import registered_transport
            from pchsi.cognitive_runtime import orchestrator
            from resume_entry import progress_observer
            scope=bound_scope(binding,a['campaign_authority_ref'])
            if not Path(orchestrator.__file__).resolve().is_relative_to(Path(binding['scientific_repo_root']).resolve()):raise ValueError('WORKER_NATIVE_EXECUTOR_SOURCE_CHANGED')
            stack.enter_context(install_executor(scope,progress_observer(a,scope)))
            stack.enter_context(retry_pacing(orchestrator,registered_transport()))
            return original(req,root)
        module.load_current_post_module=load_post
        return module.main()

if __name__=='__main__':raise SystemExit(main())

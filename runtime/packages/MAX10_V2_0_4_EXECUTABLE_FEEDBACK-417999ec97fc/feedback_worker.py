"""Keep the registered recipe/typed worker; add public facts to its POST view."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import json,sys,hashlib,importlib
ROOT=Path(__file__).resolve().parent

@contextmanager
def facts_scope(a,identity):
    import post_context
    import post_binding.runtime as runtime
    from exact_bindings import immutable_json
    from trajectory_facts import project,researcher_summary
    from repair_guidance import POST_GUIDANCE
    from repair_feedback import checked,eligible,sha
    request_path=Path(sys.argv[sys.argv.index('--request')+1]);request=json.loads(request_path.read_bytes())
    binding=checked(request['registered_transport_binding'])
    if not eligible(a,binding):raise ValueError('TRAJECTORY_WORKER_NOT_ACTIVATED')
    native_compact=post_context.compact_projection;native_prompt=runtime.extend_prompt
    def compact(projection,source):
        value=native_compact(projection,source);facts=project(projection['environment_result_package'])
        value['registered_trajectory_facts']=researcher_summary(facts)
        immutable_json(Path(request['run_root'])/'post/REGISTERED_PUBLIC_TRAJECTORY_FACTS.json',{
            'source_environment_result_package_sha256':projection['environment_result_package_sha256'],
            'facts':facts,'authority_ref':{'path':str(ROOT/'AUTHORITY.json'),'sha256':sha(ROOT/'AUTHORITY.json')},
            'scientific_effects_changed':False,'source_request_ref':{'path':str(request_path),'sha256':sha(request_path)}})
        return value
    with patch.object(post_context,'compact_projection',compact),patch.object(runtime,'extend_prompt',lambda text:native_prompt(text)+POST_GUIDANCE):yield

def main():
    from closure_entry import verify
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    for key in ('recipe_contract','planner_context','durable_transport'):
        source=a['repair_sources'][key];root=Path(source['root'])
        if hashlib.sha256((root/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=source['manifest_sha256']:raise ValueError('REGISTERED_FEEDBACK_PREDECESSOR_CHANGED')
        sys.path.insert(0,str(root))
    # Import exact registered modules before they are used by the existing chain.
    import recipe_contract,post_context,transport_worker
    original=recipe_contract.install
    @contextmanager
    def installed():
        with original(),facts_scope(a,identity):yield
    # The V198 worker retains response IDs, retrieval-only recovery and queue budget.
    # It loads the original V191 recipe worker itself; this hook survives that import.
    with patch.object(recipe_contract,'install',installed):return transport_worker.main()

if __name__=='__main__':raise SystemExit(main())

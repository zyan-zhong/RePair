from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
import sys,json,importlib.util
ROOT=Path(__file__).resolve().parent

class Verified(Exception):pass

def main():
    from recipe_entry import verify
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    checking='--verify' in sys.argv
    if checking:sys.argv.remove('--verify')
    request=json.loads(Path(sys.argv[sys.argv.index('--request')+1]).read_bytes())
    from post_recovery import read_ref,target
    if read_ref(request['registered_recipe_source'])!=a:raise ValueError('RECIPE_WORKER_SOURCE_AUTHORITY')
    root=Path(a['typed_source_root']);sys.path.insert(0,str(root))
    spec=importlib.util.spec_from_file_location('_existing_typed_worker',root/'worker.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=module.install_worker
    with ExitStack() as stack:
        def install(*args):
            original(*args)
            worker,req,binding,_,_=args
            from recipe_contract import install as recipe_install
            stack.enter_context(recipe_install())
            current=binding['round_id']==a['post_recovery_round_id']
            if current:
                if Path(req['run_root'])!=target(a,identity):raise ValueError('POST_RECOVERY_REQUEST_TARGET')
                import post_binding.context as context
                def reuse_context(*,run_root,plan,verifier,**kwargs):
                    record=read_ref(a['post_recovery_refs']['post/CURRENT_NATIVE_DATASET_CONTEXT.json'])
                    context.check_current_verifier(plan,verifier)
                    if (record['round_id']!=plan['round_id'] or record['plan_sha256']!=plan['plan_sha256']
                        or record['verifier_sha256']!=verifier['environment_result_package_sha256']):raise ValueError('POST_REUSED_DATASET_IDENTITY')
                    from exact_bindings import read_ref as checked,immutable_json
                    for field in ('dataset_ref','dataset_manifest_ref'):checked({'path':record['dataset'][field]['path'],'file_sha256':record['dataset'][field]['sha256']},as_bytes=True)
                    immutable_json(Path(run_root)/'post/CURRENT_NATIVE_DATASET_CONTEXT.json',record)
                    return record
                stack.enter_context(patch.object(context,'materialize_post_context',reuse_context))
            if checking:
                import controller
                def preflight(run_root):
                    from independent_verifier import verify_plan
                    from strong_post import execute_post
                    from pchsi.cognitive_runtime import orchestrator
                    plan=json.loads((Path(run_root)/'EXECUTION_PLAN.json').read_bytes())
                    verifier=verify_plan(Path(run_root)/'EXECUTION_PLAN.json',Path(run_root))
                    expected=read_ref(a['post_recovery_refs']['verifier/ENVIRONMENT_RESULT_PACKAGE.json'])
                    if verifier!=expected:raise ValueError('POST_PREFLIGHT_SCIENTIFIC_VERIFIER_CHANGED')
                    def no_send(**kw):
                        from recipe_contract import CONTRACT
                        post=Path(run_root)/'post';mapping=json.loads((post/'REGISTERED_CONTEXT_PROJECTION_BINDING.json').read_bytes())
                        old=read_ref(a['post_recovery_refs']['call/logical_call.json'])
                        if mapping['logical_call_id']==old['logical_call_id']:raise ValueError('POST_SAME_LOGICAL_CALL_RESEND')
                        if CONTRACT not in (post/'POST_MATERIALIZATION_PROMPT.txt').read_text():raise ValueError('NATIVE_CONTRACT_NOT_EXPOSED')
                        print(json.dumps({'status':'ACTUAL_POST_RECIPE_CONTRACT_NO_SEND_PASS','new_logical_call_id':mapping['logical_call_id'],
                            'old_logical_call_id':old['logical_call_id'],'original_effect_counts':verifier['stable_effect_counts'],
                            'registered_request_bytes':mapping['provider_request_body_bytes'],'provider_calls':0,'scientific_branch_reexecutions':0}),flush=True)
                        raise Verified()
                    with patch.object(orchestrator,'execute_one',no_send):execute_post(run_root,plan,verifier)
                controller.run_controller=preflight
        stack.enter_context(patch.object(module,'install_worker',install))
        try:return module.main()
        except Verified:return 0

if __name__=='__main__':raise SystemExit(main())

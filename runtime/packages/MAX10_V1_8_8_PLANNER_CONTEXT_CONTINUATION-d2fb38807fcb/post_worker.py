from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import sys,json,hashlib,types
ROOT=Path(__file__).resolve().parent

def install_projection(worker,request,binding,authority,identity):
    from exact_bindings import file_ref,read_ref,read_json,immutable_json,canonical
    from post_context import renderer,validate_rejection
    source_ref=authority['post_compactor_ref'];source={'source':read_ref(source_ref,as_bytes=True).decode(),'sha256':source_ref['file_sha256']}
    policy=read_ref(authority['post_context_policy_ref']);original_loader=worker.load_current_post_module
    current=binding['round_id']==authority['excluded_round_id'];run=Path(request['run_root'])
    if current:
        if str(run)!=authority['current_h44_run_root']:raise ValueError('POST_RECOVERY_RUN_ROOT_CHANGED')
        evidence={k:read_ref(v) for k,v in authority['post_rejection_refs'].items()}
        validate_rejection(evidence)
        from pchsi.reference_loop.canonical import domain_hash
        for key,field,schema in [('logical','logical_call_sha256','LOGICAL_CALL_RECORD_V1'),('attempt','attempt_sha256','TRANSPORT_ATTEMPT_RECORD_V1')]:
            if domain_hash(schema,evidence[key],excluded_field=field)!=evidence[key][field]:raise ValueError('POST_REJECTION_CONTENT_HASH')
        if hashlib.sha256(read_ref(authority['post_original_request_ref'],as_bytes=True)).hexdigest()!=evidence['attempt']['raw_request_sha256']:
            raise ValueError('POST_ORIGINAL_REQUEST_ATTEMPT_MISMATCH')
        if authority['post_rejection_refs']['response']['file_sha256']!=evidence['attempt']['raw_response_sha256']:
            raise ValueError('POST_ORIGINAL_RESPONSE_ATTEMPT_MISMATCH')
    def load_post(req,root):
        module=original_loader(req,root);native=module.execute_post
        def post(run_root,plan,verifier):
            from pchsi.cognitive_runtime import request_renderer,orchestrator
            from pchsi.reference_loop.canonical import domain_hash
            original_render=request_renderer.render_stage_request
            def record(bundle,view,body_bytes):
                unit=read_json(Path(run_root)/'post/unit.json')
                key={'scientific_unit_identity_sha256':unit['identity_sha256'],'stage_id':'R-POST-PRIMARY-V1',
                    'condition_id':None,'round_id':plan['round_id'],'policy_version':plan['source_request']['parent_policy_id'],
                    'request_body_sha256':bundle['request_body_sha256']}
                cid=domain_hash('COGNITIVE_LOGICAL_CALL_ID_V1',key)
                if current and cid==evidence['logical']['logical_call_id']:raise ValueError('POST_SAME_LOGICAL_RESEND_FORBIDDEN')
                registration={'schema_id':'REGISTERED_POST_CONTEXT_PROJECTION_BINDING_V1',
                    'source_extension_manifest_sha256':identity,'logical_call_id':cid,'request_body_sha256':bundle['request_body_sha256'],
                    'model_view_sha256':hashlib.sha256(canonical(view)).hexdigest(),'provider_request_body_bytes':body_bytes,
                    'source_environment_result_package_sha256':verifier['environment_result_package_sha256'],
                    'compact_environment_projection_sha256':view['environment_result_package']['projection_sha256'],
                    'original_rejected_logical_call_id':evidence['logical']['logical_call_id'] if current else None,
                    'same_logical_call_resend_authorized':False,'native_full_projection_preserved':True,
                    'max_provider_request_body_bytes':policy['max_provider_request_body_bytes']}
                if authority.get('verification_no_send'):
                    raise VerificationComplete(registration)
                immutable_json(Path(run_root)/'post/REGISTERED_CONTEXT_PROJECTION_BINDING.json',registration)
                immutable_json(Path(run_root)/'post/REGISTERED_CONTEXT_MODEL_VIEW.json',view)
                if current:
                    immutable_json(Path(authority['post_original_call_root'])/'REGISTERED_CONTEXT_SUCCESSOR.json',registration)
            wrapped=renderer(original_render,source=source,policy=policy,record=record)
            native_execute=orchestrator.execute_one
            def execute(**kw):
                if current:
                    remaining=1+authority['campaign_transport_restarts']-evidence['method']['transport_attempt_count']
                    if remaining<=0:raise ValueError('POST_TRANSPORT_BUDGET_EXHAUSTED')
                    kw={**kw,'max_infrastructure_attempt_restarts':remaining-1}
                return native_execute(**kw)
            with patch.object(request_renderer,'render_stage_request',wrapped),patch.object(orchestrator,'render_stage_request',wrapped),patch.object(orchestrator,'execute_one',execute):
                return native(run_root,plan,verifier)
        module.execute_post=post
        return module
    worker.load_current_post_module=load_post
    if current:
        import controller
        def resume(run_root):
            import fcntl
            from independent_verifier import verify_plan
            from strong_post import execute_post
            run_root=Path(run_root);terminal=run_root/authority['continuation_terminal_name']
            with (run_root/'CONTROLLER.lock').open('a+b') as lock:
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                if terminal.exists():
                    value=read_json(terminal)
                    return 0 if value.get('post_terminal',{}).get('training_recommendation') in ('TRAIN','NO_TRAIN') else 20
                plan=read_ref(authority['preserved_refs']['execution_plan'])
                verifier=verify_plan(run_root/'EXECUTION_PLAN.json',run_root)
                if verifier!=read_ref(authority['preserved_refs']['verifier']):raise ValueError('POST_RECOVERY_VERIFIER_CHANGED')
                if read_ref(authority['preserved_refs']['failed_h44_terminal'])['status']!='POST_NOT_ACCEPTED_NO_RESEND':
                    raise ValueError('POST_RECOVERY_ORIGINAL_STOP_CHANGED')
                try:result=execute_post(run_root,plan,verifier)
                except VerificationComplete as done:
                    print(json.dumps({'status':'POST_CONTEXT_FULL_NO_SEND_PREFLIGHT_PASS',**done.record}),flush=True);return 0
                value={'schema_id':'REGISTERED_POST_CONTEXT_CONTINUATION_TERMINAL_V1',
                    'plan_sha256':plan['plan_sha256'],'environment_result_package_sha256':verifier['environment_result_package_sha256'],
                    'source_extension_manifest_sha256':identity,'post_terminal':result,'status':result['status'],
                    'training_execution_count':0,'scientific_branch_reexecution_count':0,
                    'old_failed_terminal_ref':authority['preserved_refs']['failed_h44_terminal'],'full_round_closed':False}
                immutable_json(terminal,value)
                print('REGISTERED_POST_CONTEXT '+json.dumps(result),flush=True)
                return 0 if result.get('training_recommendation') in ('TRAIN','NO_TRAIN') else 20
        controller.run_controller=resume

class VerificationComplete(Exception):
    def __init__(self,record):self.record=record

def overlay_child(source):
    old="source=source.replace(needle,'        _install_current_actor(request, binding)\\n'+needle)"
    new="source=source.replace(needle,'        _install_current_actor(request, binding)\\n        _install_projection(module, request, binding)\\n'+needle)"
    if source.count(old)!=1:raise ValueError('POST_WORKER_OVERLAY_ANCHOR')
    source=source.replace(old,new)
    old='\n    return module.main()\n'
    if source.count(old)!=1:raise ValueError('POST_WORKER_CALLBACK_ANCHOR')
    return source.replace(old,'\n    module._install_projection=_install_projection'+old)

def main():
    from context_entry import verify
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());prior=Path(a['predecessor_source_root'])
    if '--verify' in sys.argv:
        a['verification_no_send']=True;sys.argv.remove('--verify')
    if hashlib.sha256((prior/'PACKAGE_FILES.sha256').read_bytes()).hexdigest()!=a['predecessor_manifest_sha256']:
        raise ValueError('WORKER_PREDECESSOR_CHANGED')
    # The immutable previous worker verifies its complete manifest and request.
    sys.path.insert(0,str(prior));import condition_entry
    condition_entry.verify()
    source=overlay_child((prior/'condition_child.py').read_text())
    module=types.ModuleType('_registered_context_condition_child');module.__file__=str(prior/'condition_child.py')
    module._install_projection=lambda worker,req,binding:install_projection(worker,req,binding,a,identity)
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    return module.main()

if __name__=='__main__':raise SystemExit(main())

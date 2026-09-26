from pathlib import Path
import sys,json,subprocess,hashlib,types
from registered_entry import ROOT,verify

def server():
    from registered_entry import load
    a,prior,identity,prepared=load()
    from exact_bindings import read_ref,immutable_json,file_ref
    from execution_index import assert_unsubmitted
    old=read_ref(a['partial_plan_ref']);assert_unsubmitted(Path(a['partial_plan_ref']['path']).parent,old)
    binding=read_ref(a['registered_child_request_ref'])['registered_transport_binding']
    work=Path(read_ref(binding)['output_root'])/'registered_verification'/identity;work.mkdir(parents=True,exist_ok=True)
    registry={'schema_id':'REGISTERED_CURRENT_PRE_OPTION_REGISTRY_V1','round_id':a['materialization_round_id'],
        'capture_ref':read_ref(a['original_h44_request_ref'])['capture'],
        'execution_contracts':read_ref(file_ref(ROOT/a['frozen_registration_member']))['execution_contracts']}
    immutable_json(work/'OPTION_REGISTRY.json',registry)
    # Copy the already registered transport/condition request, never regenerate PRE.
    request=read_ref(a['registered_child_request_ref'])
    request={**request,'run_root':str(work/'run'),'execute':False,'registered_option_registry':file_ref(work/'OPTION_REGISTRY.json'),
        'registered_option_source':file_ref(ROOT/'AUTHORITY.json')}
    path=work/'H44_REQUEST.json';immutable_json(path,request)
    r=subprocess.run([a['registered_python'],'-B',str(ROOT/'worker.py'),'--request',str(path)],capture_output=True,text=True)
    (work/'worker.stdout').write_text(r.stdout);(work/'worker.stderr').write_text(r.stderr)
    if r.returncode:raise ValueError('REAL_H44_NO_SEND_PREFLIGHT:'+r.stderr[-10000:])
    plan=json.loads((work/'run/EXECUTION_PLAN.json').read_bytes())
    if plan['handoff']!=old['handoff'] or plan['capture_zip_sha256']!=old['capture_zip_sha256']:raise ValueError('FROZEN_PORTFOLIO_CHANGED')
    assert_unsubmitted(work/'run',plan)
    # Build the real GPU worker/dispatcher, without an allocation or environment call.
    script='import sys,json;sys.path.insert(0,'+repr(str(ROOT))+');from gpu_entry import prepare;prepare();from worker import validate_plan;validate_plan(json.load(open('+repr(str(work/'run/EXECUTION_PLAN.json'))+')));print("GPU_DISPATCH_NO_EXECUTION_PASS")'
    gpu=subprocess.run([a['registered_python'],'-B','-c',script],capture_output=True,text=True)
    if gpu.returncode:raise ValueError('GPU_DISPATCH_PREFLIGHT:'+gpu.stderr[-8000:])
    check=subprocess.run([a['registered_python'],'-B',str(ROOT/'pre_checks.py')],capture_output=True,text=True)
    if check.returncode:raise ValueError('NEXT_PRE_TYPED_RENDER_PREFLIGHT:'+check.stderr[-9000:])
    print(check.stdout,flush=True)
    chain=subprocess.run([a['registered_python'],'-B',str(ROOT/'chain_checks.py')],capture_output=True,text=True)
    if chain.returncode:raise ValueError('PARENT_CHAIN_PREFLIGHT:'+chain.stderr[-10000:])
    print(chain.stdout,flush=True)
    print(json.dumps({'status':'COMPLETE_CURRENT_PORTFOLIO_MATERIALIZATION_NO_SEND_PASS','states':len(plan['states']),
        'frozen_branches':len(plan['handoff']['branch_plan']),'bound_branches':len(plan['branch_bindings']),
        'plan_ref':file_ref(work/'run/EXECUTION_PLAN.json'),'capture_unchanged':True,'provider_calls':0,'environment_calls':0,'slurm_submissions':0,'git_mutations':0}))
    for ref in a['preserved_current_refs'].values():read_ref(ref,as_bytes=True)

if __name__=='__main__':
    identity=verify();r=subprocess.run([sys.executable,'-m','pytest','-q',str(ROOT/'test_contracts.py'),str(ROOT/'test_index.py')],cwd=ROOT)
    if r.returncode:raise SystemExit(r.returncode)
    if '--server' in sys.argv:server()
    print('PACKAGE_SHA_AND_TYPED_OPTION_VERIFY_PASS='+identity)

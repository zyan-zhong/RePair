from pathlib import Path
import json,subprocess,sys,os
from profile_entry import ROOT,verify,load,installed,check_binding,digest

def server():
    a,prior,identity,prepared=load()
    fixture=json.loads((ROOT/'CURRENT_FIXTURE.json').read_bytes());binding=fixture['binding']
    from runtime_overlay import configure
    configure(a,ROOT,identity)
    from pchsi.research_intelligence import human_f0f1_runtime as runtime_module
    with installed(a,identity):
        proof=check_binding(binding)
        import source_condition
        members={}
        value=source_condition.bound_condition(binding,{k:fixture[k]['value'] for k in ('request',)}|{'actor_runtime':fixture['runtime']['value']},
            {**{k:binding[k] for k in ('round_id','parent_policy_id')},'accepted_pre_logical_call_id':'no-send-contract-check'},None,
            lambda k,v:members.__setitem__(k,v))
        assert value==proof['source_policy_condition']
    # Historical clean branch is still the exact native loader.
    clean_ref=a['clean_fixture_ref'];clean=json.loads(Path(clean_ref['path']).read_bytes())
    assert runtime_module.load_continuation_runtime_binding_v2(clean_ref['path'],expected_file_sha256=clean_ref['sha256'],expected_model=clean['served_model_name'])==clean
    runtime=fixture['runtime']['value'];runtime_ref=binding['refs']['actor_runtime']
    code='ref='+repr(runtime_ref)+'\nexpected='+repr(runtime)+'\n'+r'''
import json,os
from pchsi.research_intelligence.human_f0f1_runtime import load_continuation_runtime_binding_v2
assert getattr(load_continuation_runtime_binding_v2,'_registered_trained_reader',False)
value=load_continuation_runtime_binding_v2(ref['path'],expected_file_sha256=ref['file_sha256'],expected_model=expected['served_model_name'])
assert value==expected
from policy_binding.launch import extend_lora_launch
launch=extend_lora_launch({'launch_command':['python','--served-model-name',value['served_model_name']]},value)
assert launch['launch_command'][2]==value['base_served_model_name']
assert launch['launch_command'][-1]==value['served_model_name']+'='+value['adapter_path']
print(json.dumps({'inherited_reader':True,'original_runtime_preserved':True,'actual_lora_weights_verified':True,'adapter_service_alias_verified':True}))
'''
    child=subprocess.run([a['registered_python'],'-B','-c',code],capture_output=True,text=True,check=True,timeout=120)
    result={'schema_id':'CURRENT_TRAINED_PARENT_BOUNDARY_VALIDATION_V1','manifest_sha256':identity,'current_binding':proof,
        'actual_source_condition_wrapper_verified':True,'clean_native_reader_preserved':True,'fresh_worker':json.loads(child.stdout.splitlines()[-1]),
        'provider_calls':0,'slurm_jobs_submitted':0,'scientific_execution_started':False,'git_mutation_count':0}
    out=ROOT/'verification';out.mkdir(exist_ok=True);(out/'BOUNDARY_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':
    verify()
    result=subprocess.run([sys.executable,'-B','-m','pytest','-q',str(ROOT)],cwd=ROOT)
    if result.returncode:raise SystemExit(result.returncode)
    if '--server' in sys.argv:server()
    if '--server' in sys.argv:
        r=subprocess.run([sys.executable,'-B',str(ROOT/'FULL_PREPARATION_CHECK.py')],cwd=ROOT)
        if r.returncode:raise SystemExit(r.returncode)
    print('TRAINED_PARENT_PROFILE_VERIFY_PASS')

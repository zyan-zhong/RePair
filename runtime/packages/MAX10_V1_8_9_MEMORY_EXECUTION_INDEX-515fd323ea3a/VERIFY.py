from pathlib import Path
import json,subprocess,sys
from context_entry import load,verify,ROOT
def main():
    identity=verify();r=subprocess.run([sys.executable,'-B',str(ROOT/'test_memory_index.py')])
    if r.returncode:return r.returncode
    if '--server' in sys.argv:
        a,prior,identity,prepared=load()
        from exact_bindings import read_ref,read_json,file_ref
        from memory_index import install,register
        import adapter
        binding=read_ref(a['current_analyzer_binding_ref']);values=adapter.validate_binding(binding);adapter.load_cores(binding)
        execution=read_ref(a['current_execution_ref']);register(binding,execution,a,file_ref(ROOT/'PACKAGE_FILES.sha256'))
        from pchsi.cognitive_runtime import orchestrator
        def no_send(*args,**kwargs):raise AssertionError('MEMORY_VERIFICATION_TRANSPORT_FORBIDDEN')
        from unittest.mock import patch
        with install(a,file_ref(ROOT/'PACKAGE_FILES.sha256')),patch.object(orchestrator,'execute_one',no_send):
            import memory_binding.api as api
            result=api.materialize_round_memory(binding=binding,analyzer_output_root=binding['output_root'],
                execution_plan_ref=a['preserved_refs']['execution_plan'],verifier_ref=a['preserved_refs']['verifier'],
                output_root=Path(a['owner_root'])/'runtime_extensions'/identity/'verification/memory')
        if len(result['results'])!=len(read_ref(a['preserved_refs']['verifier'])['state_results']):raise ValueError('MEMORY_STATE_CENSUS')
        for ref in a['memory_preserved_refs'].values():read_ref(ref,as_bytes=True)
        print(json.dumps({'status':'FULL_NATIVE_MEMORY_MATERIALIZATION_PREFLIGHT_PASS','state_count':len(result['results']),
            'event_count':len(result['event_refs']),'new_member_count':len(result['additional_member_refs']),
            'receipt_ref':result['receipt_ref'],'provider_calls':0,'same_round_active_memory_writeback':False}))
    print(json.dumps({'status':'MEMORY_REGISTERED_EXECUTION_VERIFY_PASS','manifest_sha256':identity,'provider_calls':0,'git_mutations':0}))
    return 0
if __name__=='__main__':raise SystemExit(main())

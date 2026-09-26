"""Exercise the real registered H44 chain with execute=False and no owner loop."""
from pathlib import Path
from unittest.mock import patch
import json,uuid,subprocess
import profile_entry
from profile_entry import ROOT,load

def main():
    a,prior,identity,prepared=load()
    import entry.main as native_main,adapter
    from exact_bindings import file_ref,read_ref,BindingError
    binding=json.loads((ROOT/'CURRENT_FIXTURE.json').read_bytes())['binding']
    accepted=read_ref(file_ref(Path(binding['output_root'])/'pre/ACCEPTED_PRE_REF.json'))
    receipt=read_ref(accepted['pre_strategy_receipt'])
    # Reproduce the actual dynamic-branch defect without any effects.
    try:read_ref(receipt['accepted_raw_response_ref'],as_bytes=True)
    except BindingError as error:assert 'FILE_SHA_MISMATCH' in str(error)
    else:raise AssertionError('EXPECTED_HISTORICAL_REFERENCE_DIALECT_FAILURE')
    from training_binding.materializer import _read_ref
    _read_ref(receipt['accepted_raw_response_ref'])
    capture=file_ref(Path(binding['output_root'])/'h44/CURRENT_H44_CAPTURE.zip')
    observed={};original_run=subprocess.run
    def guarded_run(argv,*args,**kwargs):
        if isinstance(argv,(list,tuple)) and Path(str(argv[0])).name in ('sbatch','srun','scancel'):raise AssertionError('SCHEDULER_MUTATION_FORBIDDEN')
        return original_run(argv,*args,**kwargs)
    def prepare_only(argv):
        output=Path(binding['output_root'])/'registered_verification'/identity/'h44'
        plan_ref=adapter.run_h44(binding,capture,output,execute=False)
        plan=read_ref(plan_ref)
        observed.update(execution_plan_ref=plan_ref,selected_states=len(plan['states']),branch_bindings=len(plan['branch_bindings']),
            accepted_pre_logical_call_id=accepted['accepted_pre_logical_call_id'])
        return 0
    with patch.object(native_main,'main',prepare_only),patch.object(subprocess,'run',guarded_run):
        rc=profile_entry.run(uuid.uuid4().hex)
    assert rc==0 and observed
    result={'schema_id':'FULL_TRAINED_PARENT_H44_PREPARATION_NO_EXECUTION_V1','manifest_sha256':identity,**observed,
        'old_reference_failure_reproduced':True,'existing_strategy_reader_verified_exact_sha':True,'provider_calls':0,'slurm_jobs_submitted':0,
        'scientific_execution_started':False,'git_mutation_count':0}
    (ROOT/'verification/FULL_PREPARATION_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()

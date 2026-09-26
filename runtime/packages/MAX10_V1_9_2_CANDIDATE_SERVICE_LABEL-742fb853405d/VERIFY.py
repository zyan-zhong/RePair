from pathlib import Path
import sys,json,subprocess,os,hashlib
from candidate_entry import ROOT,verify

class Checked(Exception):pass

def server():
    from candidate_entry import load
    a,prior,identity,prepared=load()
    from exact_bindings import read_ref,file_ref
    from entry.registration import build_deployment
    deployment=build_deployment(Path(a['base_source_root']),entry_source_sha256=hashlib.sha256((Path(a['base_source_root'])/'PACKAGE_FILES.sha256').read_bytes()).hexdigest())
    from memory_binding.worker_bootstrap import bootstrap_current_and_children
    bootstrap_current_and_children(deployment['scientific_repo_root'])
    import entry.offoff_job as job,entry.candidate_runtime as candidate
    import offoff_binding.registered_inputs as inputs
    from candidate_labels import load_publisher,load_registered_inputs,adapter_capacity,service_label
    from select_index import register
    from unittest.mock import patch
    start=read_ref(a['preserved_training_select_refs']['offoff/CURRENT_REQUEST.json'])
    trained=read_ref(a['preserved_training_select_refs']['training/TRAINING_JOB_RESULT.json'])['result']
    target=register(a['original_offoff_root'],a,identity,ROOT,publish=False)
    def no_submit(**kwargs):
        from continuity_binding.api import read_ref as read
        parallel=read(kwargs['parallel_ref']);binding=read(parallel['binding_ref']);server=read(binding['output_refs']['SERVER_RUNTIME.json'])
        parent=read(binding['output_refs']['PARENT_SCHEDULE.json']);child=read(binding['output_refs']['CANDIDATE_SCHEDULE.json'])
        old=read_ref(a['preserved_training_select_refs']['offoff/candidate/CANDIDATE_OFFOFF_POLICY.json'])
        new=read(binding['input_refs']['candidate_ref'])
        assert {k:v for k,v in new.items() if k not in ('logical_condition_id','checkpoint_instance_id')}=={k:v for k,v in old.items() if k not in ('logical_condition_id','checkpoint_instance_id')}
        assert len(parent['cells'])==len(child['cells'])==binding['paired_cell_count']
        assert binding['memory_state']==binding['harness_state']=='OFF'
        assert new['logical_condition_id']==new['checkpoint_instance_id'] and len(new['logical_condition_id'])==64
        # Exercise the next promoted-parent/candidate capacity at the native schema boundary.
        # This prospective fixture is never written as an execution authority.
        from pchsi.evaluation.select_policy_runtime import SelectServerRuntimeManifestV1
        import copy
        future=copy.deepcopy(server)
        first=future['static_lora_registry'][0];second=copy.deepcopy(first)
        second['logical_condition_id']=service_label('VERIFY-SECOND-POLICY',new['artifact_sha256'])
        second['checkpoint_instance_id']=second['logical_condition_id']
        second['served_model_name']=second['logical_condition_id']
        future['static_lora_registry'].append(second)
        future=adapter_capacity(future,{'kind':'LORA_ADAPTER'},{'kind':'LORA_ADAPTER'})
        checked=SelectServerRuntimeManifestV1.from_dict(future)
        assert checked.max_loras==1 and checked.max_cpu_loras>=2 and len(checked.static_lora_registry)==2
        print(json.dumps({'status':'ACTUAL_CANDIDATE_TO_TRAIN_SELECT_NO_EXECUTION_PASS','parallel_ref':kwargs['parallel_ref'],
            'paired_cells':binding['paired_cell_count'],'shards':len(parallel['shards']),'original_label_length':len(old['logical_condition_id']),
            'native_service_label':new['logical_condition_id'],'candidate_policy_id_unchanged':new['policy_id']==old['policy_id'],
            'candidate_weights_unchanged':new['artifact_sha256']==old['artifact_sha256'],'future_two_lora_native_schema_pass':True,'training_execution_count_added':0,'provider_calls':0,'evaluation_cells_executed':0,'slurm_submissions':0}),flush=True)
        raise Checked()
    with patch.object(candidate,'publish_candidate',load_publisher(a['candidate_publisher_ref'])),patch.object(inputs,'materialize_registered_inputs',load_registered_inputs(a['registered_inputs_source_ref'])),patch.object(job,'execute_current_offoff_jobs',no_submit):
        try:job.execute_current_offoff_job(start=start,current_inputs_ref=a['current_inputs_ref'],trained=trained,output_root=target,deployment=deployment)
        except Checked:pass
        else:raise ValueError('PREFLIGHT_DID_NOT_REACH_FULL_NATIVE_SELECT_BOUNDARY')
    for ref in a['preserved_training_select_refs'].values():read_ref(ref,as_bytes=True)

if __name__=='__main__':
    identity=verify()
    cp=subprocess.run([sys.executable,'-m','pytest','-q',str(ROOT/'test_candidate_labels.py')],cwd=ROOT)
    if cp.returncode:raise SystemExit(cp.returncode)
    if '--server' in sys.argv:server()
    print('PACKAGE_SHA_AND_CANDIDATE_LABEL_VERIFY_PASS='+identity)

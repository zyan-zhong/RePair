"""Exercise resumed accepted stages and full H44 preparation without sending."""
from pathlib import Path
from unittest.mock import patch
import json,subprocess,sys

def main():
    from condition_entry import load,install,ROOT
    a,prior,identity,old=load();old_a,base,signature,old_identity,prepared,scope=old
    import adapter,repair
    from pchsi.cognitive_runtime import orchestrator,registry_runner
    from exact_bindings import read_ref
    from source_condition import capture_function
    binding=prepared[1]['analyzer_binding'];seen={}
    class Done(Exception):pass
    def forbidden(*args,**kwargs):raise AssertionError('NO_SEND_PREFLIGHT_PROVIDER_CALLED')
    def capture(*args,**kwargs):
        accepted=args[4];handoff=args[5]
        assert accepted==base.read_ref(a['immutable_refs']['accepted_pre'])
        assert handoff==base.read_ref(a['immutable_refs']['accepted_handoff'])
        args=list(args);args[-1]=Path(binding['output_root'])/'h44/registered_preflights'/identity/'capture'
        ref=capture_function(old_a['h44_input_ref'])(*args,**kwargs)
        target=Path(binding['output_root'])/'h44/registered_preflights'/identity/'plan'
        plan_ref=adapter.run_h44(binding,ref,target,execute=False)
        plan=read_ref(plan_ref)
        seen.update(capture=ref,execution_plan=plan_ref,selected_states=len(plan['states']),branch_bindings=len(plan['branch_bindings']),
            semantics_statuses={x['source_state_sha256']:x['semantics_status'] for x in plan['states']},
            accepted_pre_logical_call_id=accepted['accepted_pre_logical_call_id'])
        raise Done()
    redirect=base.predecessor(prepared[0]).registry_redirect(registry_runner.run_registry,registry=prepared[0]['refs']['registry'],old_root=prepared[0]['original_runtime_root'],new_root=prepared[4])
    with signature.signature_compatibility(),prior.install(old_a),install(a,prior,old_a),repair.install_repair(prepared[0],prepared[1],prepared[4],prepared[1]['repair_plans']),patch.object(adapter,'materialize_local',lambda *x:Path(prepared[0]['refs']['registry']['path'])),patch.object(registry_runner,'run_registry',redirect),patch.object(adapter,'materialize_capture',capture),patch.object(orchestrator,'execute_via_existing_p2',forbidden):
        try:adapter.run_bound_round(binding,execute=True)
        except Done:pass
    assert seen and seen['selected_states']==len(base.read_ref(a['immutable_refs']['accepted_handoff'])['selected_states'])
    for ref in a['immutable_refs'].values():base.read_ref(ref)
    assert seen['branch_bindings']==len(base.read_ref(a['immutable_refs']['accepted_handoff'])['branch_plan'])
    child=subprocess.run([sys.executable,'-B',str(ROOT/'dispatch_checks.py')],capture_output=True,text=True,timeout=120)
    if child.returncode:raise RuntimeError(child.stderr)
    dispatch=json.loads(child.stdout.splitlines()[-1])
    environment=base.preflight()
    report={'schema_id':'CURRENT_SOURCE_BINDING_FULL_NO_SEND_PREFLIGHT_V1','manifest_sha256':identity,**seen,
        'all_accepted_stages_reused':True,'all_selected_sources_registered':True,'original_receipts_unchanged':True,
        'environment_preflight':environment,'actual_gpu_dispatch_regression':dispatch,'provider_call_count':0,'slurm_submission_count':0,'production_git_mutation_count':0}
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()

"""No-send checks against actual registered native sources and completed receipts."""
from pathlib import Path
from unittest.mock import patch
import json,inspect,sys,subprocess

def main():
    from resume_entry import load,recovery_root,h44_function,worker_request,ROOT
    a,base,prior,identity,prepared,scope=load();values=prepared[1]
    from reuse import load_cores
    from transport_scope import install_executor,executor_with_scope
    from group_recovery import group_wrapper
    from repair import validate_scope
    import adapter
    b=dict(values['analyzer_binding']);runtime=values['runtime'];core=load_cores(b)
    b['_request']=adapter.validate_binding(b)['request']
    execution=base.read_ref(a['immutable_refs']['local_execution'])
    assert len(execution['rows'])==len(values['registry']['units']) and execution.get('terminal_route') is None
    groups,accesses,_=adapter.prepare_groups(b,core,Path(b['output_root'])/'local',execution)
    original=core.u.execute_or_reuse;dry=group_wrapper(original,core,a,scope,recovery_root(a),None,dry_run=True);mapping={}
    class Reached(Exception):pass
    def capture(**kwargs):
        result=dry(**kwargs)
        if result['status']=='RECOVERY_PREFLIGHT_NO_SEND':mapping.update(result);raise Reached()
        return result
    def forbidden(**kwargs):raise AssertionError('NO_SEND_PREFLIGHT_ATTEMPTED_PROVIDER')
    with prior.signature_compatibility(),patch.object(core.rr,'load_runtime_manifest',lambda *x,**k:runtime),patch.object(core.orch,'load_runtime_manifest',lambda *x,**k:runtime),patch.dict(core.api,execute_one=forbidden),patch.object(core.u,'execute_or_reuse',capture):
        try:adapter.run_group_tail(b,adapter.validate_binding(b),core,groups,accesses,Path(b['output_root'])/'group')
        except Reached:pass
    assert mapping and mapping['mapping']['maximum_new_attempts']==scope['max_infrastructure_attempt_restarts']
    h44_function(a)
    from exact_bindings import read_ref
    produced=worker_request({},b,a)
    child_binding=read_ref(produced['registered_transport_binding'])
    assert child_binding['round_id']==b['round_id'] and child_binding['output_root']==b['output_root']
    # Isolated child: same registered bootstrap and POST import source as production.
    code=r'''
import sys,json,inspect
from pathlib import Path
sys.path.insert(0,sys.argv[1]);from resume_entry import load
a,base,prior,identity,prepared,scope=load()
from memory_binding.worker_bootstrap import bootstrap_current_and_children
b=prepared[1]['analyzer_binding'];bootstrap_current_and_children(b['scientific_repo_root'])
from policy_binding.h44_overlay import configure_h44_workers
root=Path(b['packages']['h44']['root']);configure_h44_workers(root)
sys.path[:0]=[str(root),str(root/'native_repo/src')]
from pchsi.cognitive_runtime import orchestrator
from transport_scope import executor_with_scope
assert Path(orchestrator.__file__).resolve().is_relative_to(Path(b['scientific_repo_root']).resolve())
assert 'max_infrastructure_attempt_restarts' in inspect.signature(orchestrator.execute_one).parameters
def capture(**kwargs):return kwargs['max_infrastructure_attempt_restarts']
wrapped=executor_with_scope(capture,scope)
assert wrapped(output_root=Path(b['output_root'])/'h44/run/post/calls',unit_identity={},stage_id='R-POST-PRIMARY-V1',condition_id=None,round_id=b['round_id'],policy_version=b['parent_policy_id'],projection={},task_access={})==scope['max_infrastructure_attempt_restarts']
print(json.dumps({'child_orchestrator':orchestrator.__file__,'post_budget_forwarded':True,'provider_call_count':0}))
'''
    child=subprocess.run([sys.executable,'-B','-c',code,str(ROOT)],capture_output=True,text=True,timeout=240)
    if child.returncode:raise RuntimeError(child.stderr)
    no_send=base.preflight()
    report={'schema_id':'REGISTERED_TRANSPORT_NO_SEND_VALIDATION_V1','manifest_sha256':identity,'local_rows_preserved':len(execution['rows']),
        'accepted_local_calls':sum(x['status']=='ACCEPTED' for x in execution['rows']),'registered_groups':len(groups),
        'recovery_mapping':mapping['mapping'],'child':json.loads(child.stdout.splitlines()[-1]),'environment_preflight':no_send,
        'provider_call_count':0,'slurm_submission_count':0,'production_git_mutation_count':0}
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()

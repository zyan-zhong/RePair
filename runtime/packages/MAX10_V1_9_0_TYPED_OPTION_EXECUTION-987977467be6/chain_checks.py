from pathlib import Path
import importlib.util,json,sys
from registered_entry import ROOT,load,install

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    a,prior,identity,prepared=load()
    a187,prior186,id187,prepared186=prepared
    a186,base,signature,id186,base_prepared,scope=prepared186
    import condition_entry,adapter,memory_index
    c188=module('_chain_context',Path(a['planner_context_source_root'])/'context_entry.py')
    a188=json.loads((Path(a['planner_context_source_root'])/'AUTHORITY.json').read_bytes())
    a189=json.loads((Path(a['memory_source_root'])/'AUTHORITY.json').read_bytes())
    from exact_bindings import read_ref,file_ref,read_json
    request=read_ref(a['registered_child_request_ref']);binding=read_ref(request['registered_transport_binding'])
    out=Path(binding['output_root'])/'registered_verification'/identity/'parent_chain/h44'
    with condition_entry.install(a187,prior186,a186),c188.install(a188,condition_entry,'verification'),memory_index.install(a189,file_ref(Path(a['memory_source_root'])/'PACKAGE_FILES.sha256')),install(a,identity):
        terminal=adapter.run_h44(binding,request['capture'],out,execute=False)
        from execution_index import resolve_run
        run=resolve_run(out/'run');plan=read_json(run/'EXECUTION_PLAN.json')
        from execution_index import assert_unsubmitted
        assert_unsubmitted(run,plan)
        assert len(plan['branch_bindings'])==len(plan['handoff']['branch_plan'])
        # Exercise the same training wrapper with a sentinel native function in unit tests;
        # this boundary proves its registered target, without starting training.
        assert run!=out/'run'
        print(json.dumps({'status':'ACTUAL_PARENT_H44_CHAIN_NO_EXECUTION_PASS','plan_ref':file_ref(run/'EXECUTION_PLAN.json'),
            'execution_index_ref':file_ref(out/'REGISTERED_H44_EXECUTION_INDEX.json'),'branches':len(plan['branch_bindings']),
            'provider_calls':0,'environment_calls':0,'slurm_submissions':0}))

if __name__=='__main__':main()

from pathlib import Path
from unittest.mock import patch
import sys,json,importlib.util
ROOT=Path(__file__).resolve().parent

def validate_plan(plan):
    from exact_bindings import read_ref
    from typed_options import SCHEMA,bind_contract,validate_annex
    selected={c['candidate']['candidate_sha256']:c['candidate'] for c in plan['handoff']['selected_states']}
    goals={s['source_candidate_sha256']:s['public_task_goal'] for s in plan['states']}
    seen=set()
    for item in plan['branch_bindings']:
        binding=item['binding']
        # The existing branch binding owns the exact contract file and SHA.
        path=binding['typed_contract_path'];sha=binding['typed_contract_file_sha256']
        contract=read_ref({'path':path,'file_sha256':sha})
        if contract.get('schema_id')!=SCHEMA:continue
        registry=read_ref(contract['registration_ref']);rows=registry['execution_contracts']
        validate_annex(rows,list(selected.values()))
        candidate=selected[binding['source_candidate_sha256']]
        row=next(r for r in rows if r['source_candidate_sha256']==candidate['candidate_sha256'])
        if contract!=bind_contract(candidate,row,contract['registration_ref']):raise ValueError('TYPED_BRANCH_REGISTRY_CONTRACT_MISMATCH')
        for p in row['stop_predicates']:
            if p['kind']=='PUBLIC_GOAL_COMPLETION' and p['arguments']!=[goals[candidate['candidate_sha256']]]:raise ValueError('PUBLIC_GOAL_STOP_NOT_EXACT_CURRENT_TASK')
        seen.add(candidate['candidate_sha256'])
    required={k for k,v in selected.items() if v['candidate_status']=='EXECUTABLE_SHORT_OPTION'}
    if seen!=required:raise ValueError('TYPED_PLAN_SHORT_OPTION_REGISTRATION_INCOMPLETE')
    from portfolio_guard import require_complete_portfolio
    require_complete_portfolio(plan)

def install_worker(worker,request,binding,authority,identity):
    from exact_bindings import read_ref
    import option_adapter,native_branch,round_plan,controller
    from typed_options import install_dispatch
    registry=read_ref(request['registered_option_registry'])
    if registry['capture_ref']!=request['capture'] or registry['round_id']!=binding['round_id']:raise ValueError('TYPED_WORKER_REQUEST_BINDING')
    install_dispatch(option_adapter,registry['execution_contracts'],request['registered_option_registry'])
    native_branch.decide=option_adapter.decide;native_branch.validate_contract=option_adapter.validate_contract
    round_plan.compile_option=option_adapter.compile_option
    original=round_plan.prepare_plan
    def prepare(**kw):
        plan=original(**kw);validate_plan(plan);return plan
    round_plan.prepare_plan=prepare
    native=controller.run_controller
    def run(root):
        validate_plan(json.loads((Path(root)/'EXECUTION_PLAN.json').read_bytes()))
        return native(root)
    controller.run_controller=run;controller._registered_gpu_entry=ROOT/'gpu_entry.py'

def main():
    from registered_entry import verify
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    request=json.loads(Path(sys.argv[sys.argv.index('--request')+1]).read_bytes())
    from execution_index import read_ref
    if read_ref(request['registered_option_source'])!=a:raise ValueError('TYPED_WORKER_SOURCE_AUTHORITY')
    prior=Path(a['planner_context_source_root']);sys.path.insert(0,str(prior))
    import post_worker
    native=post_worker.install_projection
    def install(*args):
        result=native(*args);install_worker(*args);return result
    with patch.object(post_worker,'install_projection',install):return post_worker.main()

if __name__=='__main__':raise SystemExit(main())

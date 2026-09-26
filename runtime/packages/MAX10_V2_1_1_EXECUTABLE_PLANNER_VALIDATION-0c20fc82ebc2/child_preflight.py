"""Load the actual registered GPU/worker interfaces with all sends disabled."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parent
def main():
    from entry_v208 import verify,checked,load_module,digest
    verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    from runtime_setup import child_bootstrap
    child_bootstrap(a)
    p=argparse.ArgumentParser();p.add_argument('--registry',type=Path,required=True);args=p.parse_args()
    path=Path(a['typed_gpu_entry_ref']['path']);checked(a['typed_gpu_entry_ref'],as_bytes=True)
    sys.path.insert(0,str(path.parent));gpu=load_module('_preflight_registered_gpu',path);gpu.prepare()
    from strategy_hooks import worker_scope
    ref={'path':str(args.registry),'sha256':digest(args.registry)}
    implementation={'path':str(ROOT/'IMPLEMENTATION.json'),'sha256':digest(ROOT/'IMPLEMENTATION.json')}
    registry=checked(ref);universe=json.loads((args.registry.parent/'DERIVED_STRATEGY_UNIVERSE.json').read_bytes())
    # GPU preparation does not install the login-node controller overlay.
    # Follow the exact GPU call signature used by strategy_gpu.main.
    with worker_scope(ref,implementation):
        import round_plan,option_adapter,native_branch,independent_verifier,controller
        for pair in universe['pair_table']:
            for condition in ('A2','A3'):
                candidate=pair[condition]['candidate'];compiled=round_plan.compile_option(candidate)
                contract=option_adapter.validate_contract(compiled['contract'])
                assert contract['execution_identity_sha256']==pair[condition]['selected_execution_identity_sha256']
                assert native_branch.validate_contract(contract)==contract
        assert getattr(independent_verifier.verify_plan,'_cue_verifier',False)
    # Actual private-observer protocol check, no model and no scientific result.
    from process_effect import register,read,progress_worker
    from functools import partial
    from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter
    from pchsi.memory.a0_replay_session import replay_source_decision_state_hold_open_v1
    from pchsi.memory.source_state_contracts import RegisteredReplaySourceV1
    source_plan=checked(a['compatibility_source_plan_ref'])
    registration=register(source_plan,args.registry.parent/'process_preflight',implementation)
    metric=read(registration)
    supported=[b['binding'] for b in source_plan['branch_bindings'] if metric['states'][b['binding']['source_state_sha256']]['status']=='REGISTERED']
    tested=0
    if supported:
        b=min(supported,key=lambda x:x['branch_key_sha256'])
        source=RegisteredReplaySourceV1.from_json(checked({'path':b['replay_source_path'],'sha256':b['replay_source_file_sha256']},as_bytes=True))
        capture=args.registry.parent/'process_preflight/TEST_ONLY_CAPTURE.json'
        adapter=SpawnedAlfworldAdapter.start(exact_gamefile=Path(source.exact_gamefile),registration_id=b['branch_key_sha256'],
            runtime_manifest_sha256=source.runtime_manifest_sha256,worker_target=partial(progress_worker,capture_path=str(capture),
                registration_ref=registration,source_state=b['source_state_sha256'],branch_key=b['branch_key_sha256']))
        session=replay_source_decision_state_hold_open_v1(source=source,adapter=adapter)
        assert session.report.status=='PASS'
        session.close();observed=json.loads(capture.read_bytes())
        assert observed['complete'] and observed['records'][-1]['environment_step_count']==source.budget_state.environment_step_count
        assert observed['records'][-1]['observation_sha256']==source.expected_source_fingerprint.observation_sha256
        tested=1
    from entry.training_job import _run_phase
    from entry.training import load_training_sources
    load_training_sources(checked(a['source_binding_ref']))
    print(json.dumps({'status':'PASS','compiled_contract_count':2*len(universe['pair_table']),
        'actual_registered_gpu_interface_loaded':True,'actual_shared_strategy_scope_loaded':True,
        'provider_calls':0,'environment_source_replay_test_count':tested,'training_jobs':0,
        'process_metric_registered_source_count':len(metric['states']),'training_sources_verified':True}))
    return 0
if __name__=='__main__':raise SystemExit(main())

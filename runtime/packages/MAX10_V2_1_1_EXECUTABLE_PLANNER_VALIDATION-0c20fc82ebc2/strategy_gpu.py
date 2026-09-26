from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent

def main():
    from entry_v208 import verify,checked,load_module
    verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    path=Path(a['typed_gpu_entry_ref']['path']);checked(a['typed_gpu_entry_ref'],as_bytes=True)
    sys.path.insert(0,str(path.parent));module=load_module('_v207_prior_gpu',path)
    native=module.prepare()
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);args=p.parse_args()
    plan=json.loads(args.plan.read_bytes())
    typed_worker=load_module('_v207_typed_worker',path.parent/'worker.py')
    typed_worker.validate_plan(plan)
    from strategy_hooks import worker_scope
    with worker_scope(plan['cue_strategy_registry_ref'],plan['strategy_implementation_ref']):
        import native_branch
        from process_effect import install_branch_observer
        restore=install_branch_observer(native_branch,plan['process_metric_registration_ref'])
        try:return native.run_allocation(args.plan)
        finally:restore()

if __name__=='__main__':raise SystemExit(main())

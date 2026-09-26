from pathlib import Path
import json,sys,importlib.util
ROOT=Path(__file__).resolve().parent

def prepare():
    from registered_entry import verify
    verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());prior=Path(a['condition_source_root'])
    sys.path.insert(0,str(prior))
    spec=importlib.util.spec_from_file_location('_prior_typed_gpu_entry',prior/'gpu_entry.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    module=m.prepare_gpu()
    import option_adapter,native_branch
    from typed_options import install_dispatch
    install_dispatch(option_adapter)
    native_branch.decide=option_adapter.decide;native_branch.validate_contract=option_adapter.validate_contract
    return module

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);args=p.parse_args()
    module=prepare()
    from worker import validate_plan
    validate_plan(json.loads(args.plan.read_bytes()))
    raise SystemExit(module.run_allocation(args.plan))

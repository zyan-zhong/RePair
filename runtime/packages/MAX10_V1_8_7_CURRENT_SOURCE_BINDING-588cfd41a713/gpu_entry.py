"""Registered GPU entry: original allocation with both native intervention kinds."""
from pathlib import Path
import sys,json,hashlib,types

def prepare_gpu():
    from condition_entry import ROOT,verify
    verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());prior=Path(a['predecessor_source_root'])
    sys.path.insert(0,str(prior));old=json.loads((prior/'AUTHORITY.json').read_bytes())
    sys.path.insert(0,old['base_package_root']);sys.path.insert(0,str(Path(old['base_package_root'])/'live_adapter'))
    from exact_bindings import read_ref
    root=Path(a['h44_package']['root']);manifest=dict((n,s) for s,n in (line.split(maxsplit=1) for line in read_ref(a['h44_package']['manifest'],as_bytes=True).decode().splitlines()))
    from memory_binding.worker_bootstrap import bootstrap_current_and_children
    bootstrap_current_and_children(a['scientific_repo_root'])
    from policy_binding.h44_overlay import configure_h44_workers
    configure_h44_workers(root);sys.path.insert(0,str(root))
    from exact_action import install_dispatch
    install_dispatch(root,manifest)
    path=root/'gpu_job.py';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest['gpu_job.py']:raise ValueError('CURRENT_GPU_WORKER_SOURCE_CHANGED')
    module=types.ModuleType('_registered_native_gpu_job');module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    native=module.run_allocation
    def run_allocation(plan_path):
        from portfolio_guard import require_complete_portfolio
        require_complete_portfolio(json.loads(Path(plan_path).read_bytes()))
        return native(plan_path)
    module.run_allocation=run_allocation
    return module

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);args=p.parse_args()
    raise SystemExit(prepare_gpu().run_allocation(args.plan))

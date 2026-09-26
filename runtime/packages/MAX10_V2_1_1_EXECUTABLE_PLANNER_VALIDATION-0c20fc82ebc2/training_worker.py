"""Registered worker bootstrap for the existing accepted-recipe trainer."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parent

def main():
    from entry_v208 import verify,checked,digest
    from runtime_setup import child_bootstrap
    verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes());child_bootstrap(a)
    p=argparse.ArgumentParser();p.add_argument('--worker',type=Path,required=True)
    p.add_argument('--request-sha256',required=True);p.add_argument('--phase',choices=['smoke','training'],default='training');args=p.parse_args()
    request=checked({'path':str(args.worker),'sha256':args.request_sha256})
    registry=checked(request['analyzer_binding']['refs']['cue_strategy_registry'])
    feedback=json.loads((Path(a['feedback_worker_ref']['path']).parent/'AUTHORITY.json').read_bytes())
    recipe=feedback['repair_sources']['recipe_contract'];root=Path(recipe['root'])
    if digest(root/'PACKAGE_FILES.sha256')!=recipe['manifest_sha256']:raise ValueError('TRAINING_RECIPE_SOURCE_CHANGED')
    sys.path.insert(0,str(root));import recipe_contract
    from strategy_hooks import training_scope
    from entry.training_job import worker
    with recipe_contract.install(),training_scope(registry):return worker(args.worker,args.request_sha256,args.phase)

if __name__=='__main__':raise SystemExit(main())

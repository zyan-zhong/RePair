"""One cold-start entry; all round progression belongs to the original owner."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'live_adapter')]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    from entry.preflight import verify_package, validate_deployment
    identity, count = verify_package(ROOT)
    from entry.registration import build_deployment
    deployment = build_deployment(ROOT, entry_source_sha256=identity)
    formal = Path(deployment['formal_state_root'])
    from memory_binding.worker_bootstrap import bootstrap_current_and_children
    bootstrap_current_and_children(deployment['scientific_repo_root'])
    # Native contracts are imported only after the source-bound Memory extension.
    from entry.authority_bundle import load_formal_authority
    from entry.campaign_owner import run_campaign, campaign_lock
    from entry.source_recovery import select_owner
    from entry.driver import ExistingComponentRoundDriver
    bundle = load_formal_authority(formal)
    validate_deployment(deployment, formal_root=formal, bundle_root=ROOT)
    if not args.run:
        with campaign_lock(formal / 'campaign_owner'):
            select_owner(bundle_root=ROOT,formal_root=formal,initial=bundle.initial,
                authority=bundle.campaign.to_dict(),entry_source_sha256=identity,publish=False)
    print('FORMAL_EXACT_EXECUTION_PREFLIGHT=PASS', flush=True)
    print('FORMAL_VALID_ROUND_LIMIT=' + str(bundle.campaign.requested_max_valid_rounds), flush=True)
    print('FORMAL_CANARY_DENOMINATOR_CONTRIBUTION=0', flush=True)
    print('PACKAGE_FILE_COUNT=' + str(count), flush=True)
    if not args.run:
        print('SCIENTIFIC_EXECUTION_STARTED=false', flush=True)
        return 0
    # The original lock remains the campaign-wide admission point across source
    # recovery. A successor additionally keeps its own original owner lock.
    with campaign_lock(formal / 'campaign_owner'):
        owner_root = select_owner(bundle_root=ROOT,formal_root=formal,initial=bundle.initial,
            authority=bundle.campaign.to_dict(),entry_source_sha256=identity,publish=True)
        if owner_root == formal / 'campaign_owner':
            raise ValueError('REGISTERED_PRE_SUBMIT_RECOVERY_REQUIRED_FOR_THIS_ENTRY')
        driver = ExistingComponentRoundDriver(bundle_root=ROOT, formal_root=formal,
            owner_root=owner_root, deployment=deployment, initial=bundle.initial)
        from entry.progress import update
        from rollout_adapter.materializer import canonical,put
        update(owner_root,stage='STARTING',valid_rounds=0,max_rounds=bundle.campaign.requested_max_valid_rounds)
        try:
            terminal = run_campaign(state_root=owner_root, authority=bundle.campaign,
                                    initial=bundle.initial, driver=driver)
        except Exception as exc:
            import traceback
            failure={'schema_id':'FORMAL_RESIDENT_RUNTIME_STOP_V1','error_type':type(exc).__name__,
                'message':str(exc),'traceback':traceback.format_exc(),'scientific_completion_claimed':False}
            put(owner_root/'RESIDENT_RUNTIME_STOP.json',canonical(failure))
            update(owner_root,stage='STOPPED',error=type(exc).__name__+':'+str(exc))
            raise
    print(json.dumps(terminal, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

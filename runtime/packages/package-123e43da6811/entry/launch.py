"""One invocation starts a detached resident after the whole binding passes."""
from pathlib import Path
import json
import os
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    from entry.main import main as verify_current
    verify_current([])
    from entry.preflight import verify_package
    from entry.registration import build_deployment
    identity, _ = verify_package(ROOT)
    deployment = build_deployment(ROOT, entry_source_sha256=identity)
    from entry.campaign_owner import campaign_lock, _write_once
    from entry.authority_bundle import load_formal_authority
    from entry.source_recovery import select_owner
    formal = Path(deployment['formal_state_root'])
    bundle = load_formal_authority(formal)
    # Refuse a second live resident. The child takes this same owner lock.
    with campaign_lock(formal / 'campaign_owner'):
        owner = select_owner(bundle_root=ROOT,formal_root=formal,initial=bundle.initial,
            authority=bundle.campaign.to_dict(),entry_source_sha256=identity,publish=True)
        if (owner / 'CAMPAIGN_TERMINAL.json').is_file():
            print((owner / 'CAMPAIGN_TERMINAL.json').read_text())
            return 0
        record_root = owner / 'launch_receipts' / uuid.uuid4().hex
        record_root.mkdir(parents=True)
        argv = [sys.executable, '-B', str(ROOT / 'entry/main.py'), '--run']
        _write_once(record_root / 'LAUNCH_INTENT.json', {'schema_id': 'FORMAL_RESIDENT_LAUNCH_INTENT_V1',
            'argv': argv, 'entry_source_sha256': identity, 'scientific_execution_started': False})
    # Release our preflight lock before the child obtains its lifetime writer lock.
    # Concurrent launchers remain safe: run_campaign admits exactly one writer.
    with (record_root / 'resident.log').open('ab', buffering=0) as log:
        child = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    receipt = {'schema_id': 'FORMAL_RESIDENT_PROCESS_LAUNCHED_V1', 'pid': child.pid,
        'argv': argv, 'entry_source_sha256': identity, 'log_path': str(record_root / 'resident.log'),
        'owner_root': str(owner), 'scientific_training_started_claimed': False}
    _write_once(record_root / 'LAUNCH_RECEIPT.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

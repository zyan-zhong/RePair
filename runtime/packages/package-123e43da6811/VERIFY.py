"""Offline package identity plus optional exact server preflight or fixture tests."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', action='store_true')
    parser.add_argument('--tests', action='store_true')
    args = parser.parse_args()
    from entry.preflight import verify_package
    identity, count = verify_package(ROOT)
    print('PACKAGE_SHA_AND_APPEND_ONLY_PROOF_PASS=' + str(count), flush=True)
    proof = json.loads((ROOT / 'ledger/APPEND_ONLY_PROOF.json').read_bytes())
    import hashlib
    raw = (ROOT / 'ledger' / proof['output_name']).read_bytes()
    if (hashlib.sha256(raw[:proof['previous_bytes']]).hexdigest() != proof['previous_sha256']
            or hashlib.sha256(raw).hexdigest() != proof['output_sha256']):
        raise ValueError('APPEND_ONLY_LEDGER_PROOF_FAILED')
    if args.tests:
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'TESTS.py')], check=False)
        if result.returncode:
            return result.returncode
    if args.server:
        from entry.main import main as verify_server
        return verify_server([])
    print('PRODUCTION_MATERIALIZATION_COMPLETED=false', flush=True)
    print('SCIENTIFIC_EXECUTION_STARTED=false', flush=True)
    print('EXECUTION_SOURCE_SHA256=' + identity, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

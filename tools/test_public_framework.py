#!/usr/bin/env python3
"""Run portable framework tests, reporting the two private provenance checks."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    scope = json.loads((ROOT/'runtime/PUBLIC_TEST_SCOPE.json').read_bytes())
    args = [sys.executable, '-m', 'pytest', 'tests', '-q']
    for item in scope['excluded_tests']:
        print('EXTERNAL_PROVENANCE_CHECK_NOT_RUN: '+item['nodeid']+' - '+item['reason'], flush=True)
        args.extend(['--deselect', item['nodeid']])
    return subprocess.run(args, cwd=ROOT).returncode

if __name__ == '__main__':
    raise SystemExit(main())

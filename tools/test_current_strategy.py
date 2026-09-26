#!/usr/bin/env python3
"""Run the current portable strategy suite with its registered local dependencies."""
from pathlib import Path
import json,os,subprocess,sys
from verify_registered_sources import main as verify
ROOT=Path(__file__).resolve().parents[1]
def main():
    verify()
    index=json.loads((ROOT/'runtime/REGISTERED_SOURCE_INDEX.json').read_bytes())
    packages={p['registered_root']:p for p in index['packages'] if 'registered_root' in p}
    binding=json.loads((ROOT/'runtime/REVIEW_TEST_BINDING.json').read_bytes())
    current=ROOT/binding['current_package'];authority=json.loads((current/'AUTHORITY.json').read_bytes())
    native=authority['native_h44_root'];matches=[]
    for origin,package in packages.items():
        try:relative=Path(native).relative_to(Path(origin))
        except ValueError:continue
        if any(m['path']==(relative/'option_adapter.py').as_posix() for m in package['members']):matches.append(ROOT/package['snapshot']/relative)
    if len(matches)!=1:raise ValueError('REGISTERED_TEST_NATIVE_SOURCE_NOT_UNIQUE')
    env=os.environ.copy();env['PCHSI_TEST_NATIVE_H44']=str(matches[0])
    return subprocess.run([sys.executable,'-m','pytest','tests','-q','-p','no:cacheprovider','--rootdir=.'],cwd=current,env=env).returncode
if __name__=='__main__':raise SystemExit(main())

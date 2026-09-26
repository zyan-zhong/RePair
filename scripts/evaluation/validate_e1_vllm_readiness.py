#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/"src"))
def main():
    p=argparse.ArgumentParser(); p.add_argument("--manifest",type=Path,required=True); a=p.parse_args()
    from pchsi.evaluation.policy_runtime_manifest import PolicyRuntimeManifestV1,validate_policy_runtime_manifest
    m=PolicyRuntimeManifestV1.from_json(a.manifest.read_bytes()); validate_policy_runtime_manifest(m)
    print(json.dumps({"manifest_id":m.manifest_id,"status":"E1_POLICY_RUNTIME_MANIFEST_VALID"},sort_keys=True,separators=(",",":")))
    return 0
if __name__=="__main__": raise SystemExit(main())

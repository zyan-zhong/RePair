#!/usr/bin/env python3
from pathlib import Path
import argparse,json
from pchsi.cognitive_runtime.manifest import load_runtime_manifest
from pchsi.cognitive_runtime.p2_assets import audit_p2_assets
from pchsi.cognitive_runtime.p2_bridge import inspect_bridge
from pchsi.reference_loop.canonical import write_new_json
p=argparse.ArgumentParser(); p.add_argument("--output-dir",required=True); a=p.parse_args()
out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=False)
write_new_json(out/"runtime_manifest_audit.json",load_runtime_manifest())
write_new_json(out/"p2_asset_identity.json",audit_p2_assets())
write_new_json(out/"p2_bridge_interface.json",inspect_bridge())
print("COGNITIVE_RUNTIME_ASSET_AUDIT_PASS")

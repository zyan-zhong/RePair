#!/usr/bin/env python3
from pathlib import Path
import argparse
from pchsi.cognitive_runtime.round_evidence import freeze_round_evidence_package
from pchsi.reference_loop.canonical import strict_json_loads
p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True); a=p.parse_args()
v=strict_json_loads(Path(a.input).read_bytes())
if not isinstance(v,dict): raise ValueError("input must be object")
out=freeze_round_evidence_package(v,Path(a.output))
print(f"ROUND_EVIDENCE_PACKAGE_V1_FREEZE_PASS sha={out['round_evidence_package_sha256']}")

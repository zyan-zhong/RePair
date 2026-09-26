#!/usr/bin/env python3
from pathlib import Path
import argparse,os
from pchsi.cognitive_runtime.identity import build_scientific_unit_identity
from pchsi.cognitive_runtime.request_renderer import render_stage_request
from pchsi.reference_loop.canonical import write_new_json
p=argparse.ArgumentParser(); p.add_argument("--output-dir",required=True); a=p.parse_args()
os.environ.pop("OPENAI_API_KEY",None)
out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=False)
fixtures={
 "L-A0":{"evidence_pack_sha256":"a"*64,"evidence_pack":{},"memory_pack_sha256":None},
 "L-A1":{"evidence_pack_sha256":"a"*64,"evidence_pack":{},"memory_pack_sha256":None},
 "G-A2":{"group_manifest_sha256":"b"*64,"a1_local_result_sha256":"c"*64,"group_synthesis_input":{},"memory_pack_sha256":None},
 "G-A3":{"group_manifest_sha256":"b"*64,"a1_local_result_sha256":"c"*64,"group_synthesis_input":{},"memory_pack_sha256":"d"*64},
 "C":{"group_result_sha256":"e"*64,"group_result":{},"memory_pack_sha256":None},
 "X":{"target_artifact_sha256":"f"*64,"target_artifact":{},"current_evidence_manifest_sha256":"0"*64,"memory_pack_sha256":None},
 "R-PRE-SHADOW":{"round_evidence_package_sha256":"1"*64,"round_evidence_package":{},"memory_pack_sha256":"2"*64},
 "R-POST-SHADOW":{"environment_result_package_sha256":"3"*64,"environment_result_package":{},"human_pre_record_sha256":"4"*64,"memory_pack_sha256":"2"*64},
}
for stage,projection in fixtures.items():
 bundle=render_stage_request(stage_id=stage,projection=projection)
 if "OPENAI_API_KEY" in str(bundle): raise SystemExit("secret leaked")
 write_new_json(out/f"{stage.lower()}_rendered.json",bundle)
try:
 write_new_json(out/"l-a0_rendered.json",{})
except FileExistsError:
 pass
else:
 raise SystemExit("no-clobber test failed")
print("ANALYZER_RUNTIME_ACT0_OFFLINE_PASS")

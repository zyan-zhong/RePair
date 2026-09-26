#!/usr/bin/env python3
from pathlib import Path
import argparse
from pchsi.cognitive_runtime.projections import local_projection,group_projection,component_projection,crosscheck_projection
from pchsi.reference_loop.canonical import write_new_json
p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="kind",required=True)
a=sub.add_parser("local");a.add_argument("--evidence-pack",required=True);a.add_argument("--output",required=True)
a=sub.add_parser("group");a.add_argument("--group-input",required=True);a.add_argument("--a1-local",required=True);a.add_argument("--memory-pack");a.add_argument("--output",required=True)
a=sub.add_parser("component");a.add_argument("--group-result",required=True);a.add_argument("--output",required=True)
a=sub.add_parser("crosscheck");a.add_argument("--target",required=True);a.add_argument("--current-evidence-manifest",required=True);a.add_argument("--memory-pack");a.add_argument("--output",required=True)
x=p.parse_args()
if x.kind=="local": out=local_projection(Path(x.evidence_pack))
elif x.kind=="group": out=group_projection(group_synthesis_input_path=Path(x.group_input),a1_local_result_path=Path(x.a1_local),memory_pack_path=None if x.memory_pack is None else Path(x.memory_pack))
elif x.kind=="component": out=component_projection(Path(x.group_result))
else: out=crosscheck_projection(target_path=Path(x.target),current_evidence_manifest_path=Path(x.current_evidence_manifest),memory_pack_path=None if x.memory_pack is None else Path(x.memory_pack))
write_new_json(Path(x.output),out);print(f"RUNTIME_INPUT_PROJECTION_MATERIALIZED kind={x.kind}")

#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from pchsi.analyzer.candidate_projector import project_candidate
from pchsi.reference_loop.canonical import strict_json_loads,write_new_json
def obj(p):
 x=strict_json_loads(Path(p).read_bytes())
 if not isinstance(x,dict): raise ValueError("object required")
 return x
p=argparse.ArgumentParser(); p.add_argument("--proposal"); p.add_argument("--source-state",required=True)
p.add_argument("--kind",required=True); p.add_argument("--output",required=True); a=p.parse_args()
write_new_json(Path(a.output),project_candidate(None if a.proposal is None else obj(a.proposal),obj(a.source_state),candidate_kind=a.kind))

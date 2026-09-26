#!/usr/bin/env python3
from pathlib import Path
import argparse
from pchsi.cognitive_runtime.formal_registry import validate_formal_dag
from pchsi.reference_loop.canonical import strict_json_loads
p=argparse.ArgumentParser();p.add_argument("--registry",required=True);a=p.parse_args()
v=strict_json_loads(Path(a.registry).read_bytes())
if not isinstance(v,dict): raise ValueError("formal registry must be object")
validate_formal_dag(v);print("FORMAL_ANALYZER_DAG_REGISTRY_PASS")

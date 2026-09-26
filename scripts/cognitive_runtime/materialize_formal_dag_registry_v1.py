#!/usr/bin/env python3
from pathlib import Path
import argparse
from pchsi.reference_loop.canonical import strict_json_loads,domain_hash,write_new_json
from pchsi.cognitive_runtime.formal_registry import validate_formal_dag
p=argparse.ArgumentParser();p.add_argument("--round-id",required=True);p.add_argument("--registered-universe-sha256",required=True);p.add_argument("--registered-units",required=True);p.add_argument("--condition-rows",required=True);p.add_argument("--runtime-input-registry-sha256",required=True);p.add_argument("--output",required=True);a=p.parse_args()
units=strict_json_loads(Path(a.registered_units).read_bytes());rows=strict_json_loads(Path(a.condition_rows).read_bytes())
if not isinstance(units,list) or not isinstance(rows,list): raise ValueError("units/rows must be arrays")
out={"schema_id":"FORMAL_ANALYZER_DAG_REGISTRY_V1","schema_version":1,"round_id":a.round_id,"registered_universe_sha256":a.registered_universe_sha256,"registered_unit_ids":units,"condition_rows":rows,"runtime_input_registry_sha256":a.runtime_input_registry_sha256,"formal_dag_sha256":"0"*64}
out["formal_dag_sha256"]=domain_hash("FORMAL_ANALYZER_DAG_REGISTRY_V1",out,excluded_field="formal_dag_sha256");validate_formal_dag(out);write_new_json(Path(a.output),out);print("FORMAL_ANALYZER_DAG_REGISTRY_V1_MATERIALIZED")

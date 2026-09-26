#!/usr/bin/env python3
from pathlib import Path
import argparse
from pchsi.reference_loop.canonical import strict_json_loads,sha256_file,domain_hash,write_new_json
p=argparse.ArgumentParser();p.add_argument("--role",required=True,choices=["ACT1_DEV_SMOKE","ACT2_LOCAL_PILOT","ACT3_HIERARCHY_PILOT","FORMAL_A0_A3"]);p.add_argument("--round-id",required=True);p.add_argument("--policy-version",required=True);p.add_argument("--task-access-manifest",required=True);p.add_argument("--units",required=True);p.add_argument("--output",required=True);a=p.parse_args()
units=strict_json_loads(Path(a.units).read_bytes())
if not isinstance(units,list): raise ValueError("units must be array")
out={"schema_id":"RUNTIME_INPUT_REGISTRY_V1","schema_version":1,"registry_role":a.role,"round_id":a.round_id,"policy_version":a.policy_version,"task_access_manifest_sha256":sha256_file(Path(a.task_access_manifest)),"units":units,"registry_sha256":"0"*64}
out["registry_sha256"]=domain_hash("RUNTIME_INPUT_REGISTRY_V1",out,excluded_field="registry_sha256")
write_new_json(Path(a.output),out);print(f"RUNTIME_INPUT_REGISTRY_V1_MATERIALIZED units={len(units)}")

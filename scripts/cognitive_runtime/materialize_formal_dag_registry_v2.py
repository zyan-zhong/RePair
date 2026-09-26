#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.reference_loop.canonical import (
    domain_hash,
    strict_json_loads,
    write_new_json,
)
from pchsi.cognitive_runtime.formal_registry_v2 import validate_formal_dag_v2


def _array(path: str) -> list[object]:
    value = strict_json_loads(Path(path).read_bytes())
    if not isinstance(value, list):
        raise ValueError(f"array required: {path}")
    return value


parser = argparse.ArgumentParser()
parser.add_argument("--round-id", required=True)
parser.add_argument("--registered-universe-sha256", required=True)
parser.add_argument("--registered-local-units", required=True)
parser.add_argument("--local-condition-rows", required=True)
parser.add_argument("--registered-group-manifests", required=True)
parser.add_argument("--group-condition-rows", required=True)
parser.add_argument("--local-runtime-input-registry-sha256", required=True)
parser.add_argument("--group-runtime-input-registry-sha256")
parser.add_argument("--output", required=True)
args = parser.parse_args()

out = {
    "schema_id": "FORMAL_ANALYZER_DAG_REGISTRY_V2",
    "schema_version": 2,
    "round_id": args.round_id,
    "registered_universe_sha256": args.registered_universe_sha256,
    "registered_local_unit_ids": _array(args.registered_local_units),
    "local_condition_rows": _array(args.local_condition_rows),
    "registered_group_manifest_sha256s": _array(
        args.registered_group_manifests
    ),
    "group_condition_rows": _array(args.group_condition_rows),
    "local_runtime_input_registry_sha256":
        args.local_runtime_input_registry_sha256,
    "group_runtime_input_registry_sha256":
        args.group_runtime_input_registry_sha256,
    "formal_dag_sha256": "0" * 64,
}
out["formal_dag_sha256"] = domain_hash(
    "FORMAL_ANALYZER_DAG_REGISTRY_V2",
    out,
    excluded_field="formal_dag_sha256",
)
validate_formal_dag_v2(out)
write_new_json(Path(args.output), out)
print("FORMAL_ANALYZER_DAG_REGISTRY_V2_MATERIALIZED")

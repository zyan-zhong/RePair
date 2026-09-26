from __future__ import annotations
from collections.abc import Mapping
from pchsi.reference_loop.canonical import domain_hash
from .schema_registry import validate_artifact

CONDITIONS=("A0","A1","A2","A3")

def validate_formal_dag(value:Mapping[str,object])->None:
 validate_artifact("FORMAL_ANALYZER_DAG_REGISTRY_V1",value)
 if value["formal_dag_sha256"]!=domain_hash("FORMAL_ANALYZER_DAG_REGISTRY_V1",value,excluded_field="formal_dag_sha256"):
  raise ValueError("formal DAG SHA mismatch")
 units=list(value["registered_unit_ids"])
 if len(units)!=len(set(units)): raise ValueError("duplicate registered unit")
 rows=list(value["condition_rows"]); observed=set()
 by_unit={u:{} for u in units}
 for row in rows:
  key=(row["source_unit_id"],row["condition_id"])
  if key in observed: raise ValueError("duplicate unit-condition row")
  observed.add(key)
  if row["source_unit_id"] not in by_unit: raise ValueError("row outside U_reg")
  by_unit[row["source_unit_id"]][row["condition_id"]]=row
 expected={(u,c) for u in units for c in CONDITIONS}
 if observed!=expected: raise ValueError("formal registry is not complete U_reg x A0-A3")
 for unit,conds in by_unit.items():
  evidence={conds[c]["common_evidence_pack_sha256"] for c in CONDITIONS}
  if len(evidence)!=1: raise ValueError("common evidence differs across conditions")
  a1=conds["A1"]["a1_local_result_sha256"]
  if not a1 or conds["A2"]["a1_local_result_sha256"]!=a1 or conds["A3"]["a1_local_result_sha256"]!=a1:
   raise ValueError("A2/A3 do not byte-reuse A1 local result")
  if conds["A0"]["a1_local_result_sha256"] is not None: raise ValueError("A0 cannot bind A1 result")
  for c in ("A0","A1","A2"):
   if conds[c]["memory_pack_sha256"] is not None: raise ValueError(f"{c} cannot receive Memory")
  if conds["A3"]["memory_pack_sha256"] is None: raise ValueError("A3 requires frozen Memory")

from pathlib import Path
from pchsi.cognitive_runtime.manifest import load_runtime_manifest,stage_spec
from pchsi.cognitive_runtime.projections import local_projection
from pchsi.reference_loop.canonical import write_new_json


def _pack():
 return {
  "schema_id":"ANALYZER_EVIDENCE_PACK_V1",
  "evidence_pack_sha256":"a"*64,
  "trajectory":[{"model_call_index":0}],
  "mechanical_evidence":{"nested":{"leaf":1}},
  "counterexample_inventory":[],
 }


def test_projection_exposes_machine_readable_semantic_contracts(tmp_path:Path):
 p=tmp_path/"pack.json";write_new_json(p,_pack())
 x=local_projection(p)
 assert x["evidence_reference_catalog"]["copy_policy"]=="EXACT_OBJECT_COPY_ONLY"
 assert x["evidence_reference_catalog"]["mechanical_selector_policy"]=="LEAF_ONLY_EXACT_CATALOG_MEMBER"
 c=x["local_repair_contract"]
 assert c["EXACT_ACTION"]=={
  "exact_action":"REQUIRED_EXACT_ADMISSIBLE_COMMAND_STRING",
  "option_actions":"EMPTY_ARRAY",
  "termination_condition":"NULL",
  "trainable_rule":"NULL",
 }
 assert c["TRAINABLE_RULE"]["termination_condition"]=="NULL"
 assert c["SHORT_OPTION"]["termination_condition"]=="REQUIRED_NONEMPTY_STRING"


def test_a0_a1_v3_share_same_semantic_contract_fields():
 m=load_runtime_manifest()
 a0=stage_spec("L-A0",m);a1=stage_spec("L-A1",m)
 for row in (a0,a1):
  assert row["prompt_template_id"].endswith("_V3")
  assert "evidence_reference_catalog" in row["required_projection_identity_fields"]
  assert "local_repair_contract" in row["required_projection_identity_fields"]
  assert row["memory_exposure"] is False
 assert a0["output_schema_id"]==a1["output_schema_id"]=="ANALYZER_LOCAL_RESULT_V2"


def test_v3_prompts_freeze_repair_matrix_and_leaf_copy_rule():
 root=Path(__file__).resolve().parents[2]
 required=(
  "EXACT_ACTION:",
  "SHORT_OPTION:",
  "TRAINABLE_RULE:",
  "termination_condition = null",
  "mechanical list/object/container path is NOT a valid selector",
  "audit every evidence reference for exact catalog membership",
  "audit the selected repair against this matrix",
 )
 for name in ("ANALYZER_L_A0_PROMPT_V3.txt","ANALYZER_L_A1_PROMPT_V3.txt"):
  text=(root/"prompts/cognitive_runtime"/name).read_text(encoding="utf-8")
  normalized=" ".join(text.split())
  for token in required:
   assert " ".join(token.split()) in normalized

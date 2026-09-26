from pathlib import Path

from pchsi.analyzer.local_results import EvidencePackReferenceResolver
from pchsi.cognitive_runtime.manifest import load_runtime_manifest, stage_spec
from pchsi.cognitive_runtime.projections import local_projection
from pchsi.reference_loop.canonical import write_new_json


def _pack():
 return {
  "schema_id":"ANALYZER_EVIDENCE_PACK_V1",
  "evidence_pack_sha256":"a"*64,
  "trajectory":[
   {"model_call_index":0},
   {"model_call_index":1},
   {"model_call_index":3},
  ],
  "mechanical_evidence":{
   "generic_episode_facts":{
    "inadmissible_action_count":3,
    "budget_exhaustion":True,
   },
   "nested":[{"value":"x"}],
  },
  "counterexample_inventory":[],
 }


def test_local_projection_materializes_exact_reference_catalog(tmp_path:Path):
 path=tmp_path/"pack.json"
 write_new_json(path,_pack())
 projection=local_projection(path)
 catalog=projection["evidence_reference_catalog"]
 assert catalog["schema_id"]=="ANALYZER_EVIDENCE_REFERENCE_CATALOG_V1"
 assert catalog["evidence_pack_sha256"]=="a"*64
 assert catalog["copy_policy"]=="EXACT_OBJECT_COPY_ONLY"
 assert catalog["mechanical_selector_policy"]=="LEAF_ONLY_EXACT_CATALOG_MEMBER"
 assert [x["local_selector"] for x in catalog["trajectory_calls"]]==[
  "trajectory:0","trajectory:1","trajectory:3"
 ]
 assert "mechanical:generic_episode_facts.inadmissible_action_count" in {
  x["local_selector"] for x in catalog["mechanical_facts"]
 }
 assert catalog["counterexamples"]==[]

 resolver=EvidencePackReferenceResolver.from_pack(_pack())
 for section in ("trajectory_calls","mechanical_facts","counterexamples"):
  for ref in catalog[section]:
   resolver.resolve(ref)


def test_local_stages_preserve_reference_catalog_and_add_repair_contract():
 manifest=load_runtime_manifest()
 a0=stage_spec("L-A0",manifest)
 a1=stage_spec("L-A1",manifest)
 for row in (a0,a1):
  fields=row["required_projection_identity_fields"]
  assert "evidence_reference_catalog" in fields
  assert "local_repair_contract" in fields
  assert row["prompt_template_id"].endswith("_V3")
  assert row["prompt_relative_path"].endswith("_V3.txt")
 assert a0["output_schema_id"]==a1["output_schema_id"]=="ANALYZER_LOCAL_RESULT_V2"
 assert a0["memory_exposure"] is False
 assert a1["memory_exposure"] is False


def test_v3_prompts_preserve_reference_copy_contract():
 root=Path(__file__).resolve().parents[2]
 for name in ("ANALYZER_L_A0_PROMPT_V3.txt","ANALYZER_L_A1_PROMPT_V3.txt"):
  text=(root/"prompts/cognitive_runtime"/name).read_text(encoding="utf-8")
  normalized=" ".join(text.split())
  assert "evidence_reference_catalog" in text
  assert "copy all four field values exactly from one catalog object" in normalized
  assert 'does NOT imply `evidence_kind="COUNTEREXAMPLE"`' in normalized
  assert "Never use a nested mechanical-evidence hash" in normalized
  assert "mechanical list/object/container path is NOT a valid selector" in normalized
  assert "Local-repair contract (mandatory):" in text

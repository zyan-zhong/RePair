from pchsi.cognitive_runtime.manifest import load_runtime_manifest,stage_spec
from pchsi.cognitive_runtime.identity import build_scientific_unit_identity

def test_stage_freeze_and_memory_contract():
 m=load_runtime_manifest()
 assert m["requested_model"]=="gpt-5.6-sol"
 assert m["sdk_automatic_retries"]==0
 assert stage_spec("L-A1",m)["memory_exposure"] is False
 assert stage_spec("G-A2",m)["memory_exposure"] is False
 assert stage_spec("G-A3",m)["memory_exposure"] is True
 assert stage_spec("P",m)["logical_call_budget_per_unit"]==0

def test_round_scientific_unit_can_be_non_episode():
 x=build_scientific_unit_identity(
  scientific_unit_type="ROUND",scientific_unit_id="r1",
  source_unit_manifest_sha256="a"*64,task_set_manifest_sha256="b"*64,
  task_id=None,gamefile_sha256=None,group_manifest_sha256=None,
  round_evidence_package_sha256="c"*64)
 assert len(x["identity_sha256"])==64

import pytest
from pchsi.cognitive_runtime.request_renderer import render_stage_request


def _catalog():
 return {
  "schema_id":"ANALYZER_EVIDENCE_REFERENCE_CATALOG_V1",
  "evidence_pack_sha256":"a"*64,
  "copy_policy":"EXACT_OBJECT_COPY_ONLY",
  "mechanical_selector_policy":"LEAF_ONLY_EXACT_CATALOG_MEMBER",
  "trajectory_calls":[{
   "artifact_sha256":"a"*64,
   "evidence_kind":"TRAJECTORY_CALL",
   "local_selector":"trajectory:0",
   "authority":"DETERMINISTIC_FACT",
  }],
  "mechanical_facts":[],
  "counterexamples":[],
 }


def _repair_contract():
 return {
  "schema_id":"ANALYZER_LOCAL_REPAIR_CONTRACT_V1",
  "EXACT_ACTION":{
   "exact_action":"REQUIRED_EXACT_ADMISSIBLE_COMMAND_STRING",
   "option_actions":"EMPTY_ARRAY",
   "termination_condition":"NULL",
   "trainable_rule":"NULL",
  },
  "SHORT_OPTION":{
   "exact_action":"NULL",
   "option_actions":"ARRAY_1_TO_4_FIRST_ACTION_ADMISSIBLE",
   "termination_condition":"REQUIRED_NONEMPTY_STRING",
   "trainable_rule":"NULL",
  },
  "TRAINABLE_RULE":{
   "exact_action":"NULL",
   "option_actions":"EMPTY_ARRAY",
   "termination_condition":"NULL",
   "trainable_rule":"REQUIRED_NONEMPTY_STRING",
  },
  "requires_environment_verification":True,
 }


def test_memory_exposure_and_no_tools():
 x=render_stage_request(stage_id="L-A1",projection={
  "evidence_pack_sha256":"a"*64,
  "evidence_pack":{},
  "evidence_reference_catalog":_catalog(),
  "local_repair_contract":_repair_contract(),
  "memory_pack_sha256":None})
 assert x["provider_request"]["tools"]==[]
 assert x["provider_request"]["store"] is False
 assert x["provider_request"]["truncation"]=="disabled"
 with pytest.raises(ValueError,match="Memory-blind"):
  render_stage_request(stage_id="G-A2",projection={
   "a1_local_result_sha256":"b"*64,"memory_pack_sha256":"c"*64})
 with pytest.raises(ValueError,match="requires one frozen Memory"):
  render_stage_request(stage_id="G-A3",projection={
   "a1_local_result_sha256":"b"*64,"memory_pack_sha256":None})


def test_local_request_requires_reference_catalog():
 with pytest.raises(ValueError,match="missing frozen identity fields"):
  render_stage_request(stage_id="L-A1",projection={
   "evidence_pack_sha256":"a"*64,
   "evidence_pack":{},
   "local_repair_contract":_repair_contract(),
   "memory_pack_sha256":None})


def test_local_request_requires_repair_contract():
 with pytest.raises(ValueError,match="missing frozen identity fields"):
  render_stage_request(stage_id="L-A1",projection={
   "evidence_pack_sha256":"a"*64,
   "evidence_pack":{},
   "evidence_reference_catalog":_catalog(),
   "memory_pack_sha256":None})

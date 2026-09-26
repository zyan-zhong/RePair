from __future__ import annotations
from pathlib import Path
import json
import pytest

from pchsi.analyzer.act3_registration import select_dev_source_call
from pchsi.cognitive_runtime.output_validation import validate_stage_output
from pchsi.cognitive_runtime.projections import (
    canonical_group_current_evidence_sha256s,
)


def test_dev_source_call_prefers_unique_linked_repair():
 local={
  "local_repairs":[{
   "decision_call_index":3,
   "supporting_hypothesis_ids":["h1"],
  }]
 }
 error={
  "trigger_call_index":4,
  "mechanism_hypotheses":[{"hypothesis_id":"h1"}],
 }
 out=select_dev_source_call(local_result=local,error=error)
 assert out["source_call_index"]==3
 assert out["formal_eligible"] is True


def test_dev_source_call_trigger_fallback_is_explicitly_formal_ineligible():
 out=select_dev_source_call(
  local_result={"local_repairs":[]},
  error={"trigger_call_index":5,"mechanism_hypotheses":[]},
 )
 assert out=={
  "source_call_index":5,
  "selection_rule":"DEV_TRIGGER_FALLBACK_NO_LINKED_A1_REPAIR",
  "formal_eligible":False,
 }


def _projection():
 projection={
  "group_id":"e"*64,
  "group_manifest_sha256":"a"*64,
  "a1_local_result_sha256s":["b"*64],
  "a1_local_results":[{
   "local_result_sha256":"b"*64,
   "evidence_pack_sha256":"b"*64,
   "error_instances":[],
   "local_repairs":[],
  }],
  "group_synthesis_input":{
   "group_synthesis_input_sha256":"2"*64,
  },
  "source_contexts":[{
   "local_result_sha256":"b"*64,
   "error_instance_id":"e1",
   "source_state_sha256":"c"*64,
   "menu_sha256":"d"*64,
   "source_call_index":3,
   "admissible_commands":["open fridge 1","go to cabinet 1"],
  }],
  "memory_pack_sha256":None,
 }
 projection["current_evidence_sha256s"]=(
  canonical_group_current_evidence_sha256s(
   projection
  )
 )
 return projection


def _group_output(action="open fridge 1"):
 return {
  "schema_id":"ANALYZER_GROUP_RESULT_V2",
  "schema_version":2,
  "group_id":"e"*64,
  "group_manifest_sha256":"a"*64,
  "mechanism_hypotheses":[{
    "hypothesis_id":"h","statement":"recurring failure",
    "evidence_sha256s":["b"*64],"uncertainty":"dev",
  }],
  "source_conditioned_proposals":[{
   "schema_id":"ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1",
   "schema_version":1,
   "group_manifest_sha256":"a"*64,
   "local_result_sha256":"b"*64,
   "error_instance_id":"e1",
   "source_state_sha256":"c"*64,
   "menu_sha256":"d"*64,
   "exact_action":action,
   "option_actions":[],
   "termination_condition":None,
   "supporting_evidence_sha256s":["b"*64],
   "source_proposal_sha256":"0"*64,
  }],
  "source_conditioned_repair_sha256s":[],
  "group_result_sha256":"0"*64,
 }


def test_group_v2_finalizer_binds_proposal_to_exact_menu():
 out=validate_stage_output(
  stage_id="G-A2",
  text=json.dumps(_group_output(),sort_keys=True),
  raw_response_sha256="f"*64,
  projection=_projection(),
 )
 assert out["schema_id"]=="ANALYZER_GROUP_RESULT_V2"
 assert len(out["source_conditioned_repair_sha256s"])==1
 assert out["source_conditioned_proposals"][0]["source_proposal_sha256"]==out["source_conditioned_repair_sha256s"][0]


def test_group_v2_rejects_nonmenu_exact_action():
 with pytest.raises(ValueError,match="not exact source-menu member"):
  validate_stage_output(
   stage_id="G-A2",
   text=json.dumps(_group_output("open microwave 1"),sort_keys=True),
   raw_response_sha256="f"*64,
   projection=_projection(),
  )


def test_group_signature_uses_environment_agnostic_registered_progress_facts():
 from types import SimpleNamespace
 from pchsi.analyzer.act3_registration import build_group_signature_binding

 trace=SimpleNamespace(
  attempt_outcome="ACTION_NOT_ADMISSIBLE",
  failure_code="ACTION_NOT_ADMISSIBLE",
  admissibility_status="not_admissible",
  feedback_code="INVALID_ACTION_V1",
  normalized_action="go to fridge 1",
  policy_attempt_count_before=1,
  policy_attempt_count_after=2,
  environment_step_count_before=1,
  environment_step_count_after=1,
  protocol_failure_count_before=0,
  protocol_failure_count=0,
  inadmissible_action_count_before=0,
  inadmissible_action_count=1,
  consecutive_nonexecuted_attempt_count=1,
 )
 pack={
  "task_type":"pick_and_place",
  "mechanical_evidence":{
   "generic_episode_facts":{"budget_exhaustion":False},
   "registered_domain_progress_facts":{
    "goal_object_parse_status":"PARSED",
    "goal_object_visible_events":[0],
    "goal_take_available_events":[0],
    "goal_object_acquired_events":[],
    "inventory_change_events":[],
    "required_treatment_completed_events":[],
    "placement_completed_events":[],
   },
  },
 }
 local={"local_result_sha256":"1"*64}
 error={
  "error_instance_id":"e1",
  "critical_window_start_call_index":1,
  "critical_window_end_call_index":1,
 }
 out=build_group_signature_binding(
  local_result=local,error=error,evidence_pack=pack,
  action_traces_by_call={1:trace},
 )
 assert out["task_family"]=="pick_and_place"
 assert len(out["mechanical_signature_sha256"])==64
 assert len(out["progress_signature_sha256"])==64


def test_exact_source_registration_uses_frozen_public_transition_field_names():
 from types import SimpleNamespace
 from pchsi.analyzer.act3_registration import build_exact_source_registration

 transition=SimpleNamespace(
  model_call_index=0,
  environment_step_index=0,
  submitted_action="go to fridge 1",
  pre_action_observation_sha256="1"*64,
  pre_action_admissible_commands_sha256="2"*64,
  resulting_observation_sha256="3"*64,
  resulting_admissible_commands_sha256="4"*64,
  score=0,
  done=False,
  won=False,
 )
 call=SimpleNamespace(
  budget_before=(
   ("policy_attempt_count",1),
   ("environment_step_count",1),
   ("protocol_failure_count",0),
   ("inadmissible_action_count",0),
   ("consecutive_nonexecuted_attempt_count",0),
  ),
  observation_sha256="3"*64,
  admissible_commands_sequence_sha256="4"*64,
  executed_history_sha256="5"*64,
  interface_feedback_before=None,
  prompt_sha256="6"*64,
  public_task_goal="put the object away",
  observation="at fridge",
  admissible_commands=("open fridge 1","go to cabinet 1"),
  executed_history=(("go to fridge 1","at fridge"),),
 )
 out=build_exact_source_registration(
  source_task_id="task",
  source_gamefile_sha256="7"*64,
  source_bundle_sha256="8"*64,
  policy_call=call,
  public_transitions=[transition],
  source_call_index=1,
  selection_rule="UNIQUE_LINKED_A1_REPAIR_DECISION_CALL",
  formal_eligible=True,
 )
 assert out["menu_sha256"]=="4"*64
 assert len(out["source_state_sha256"])==64
 assert out["source_context"]["admissible_commands"]==[
  "open fridge 1","go to cabinet 1"
 ]

"""Current-pilot lineage and P1 seed-17 condition/schedule builders."""
from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar

from .canonical_evidence import canonical_json_text
from .condition_run_schedule import ConditionRunPurpose,build_condition_run_schedule,ConditionRunScheduleV1
from .distillation_access import DistillationAccessClass,TaskAccessManifestV1
from .distillation_governance import canonical_model_sha256
from .policy_condition import CheckpointKind,PolicyConditionManifestV1,TrainingMethod
from .schema_contract import validate_payload_against_schema

PROHIBITED_LEGACY_DATA_CLASSES=("OLD_GPT_TRAJECTORY","OLD_CLAUDE_TRAJECTORY","OLD_GEMINI_TRAJECTORY","V7B_TRAJECTORY","OLD_PLANNER_GUARD_CONTROLLER_OUTPUT","OLD_CORRECTION_DATA","OLD_FAILURE_TAXONOMY","OLD_SUCCESS_FAILURE_LABEL","OLD_TEACHER_RATIONALE")

@dataclass(frozen=True, slots=True)
class CurrentPilotDataLineageV1:
    SCHEMA_ID:ClassVar[str]="CURRENT_PILOT_DATA_LINEAGE_V1"
    schema_id:str="CURRENT_PILOT_DATA_LINEAGE_V1"; schema_version:int=1; lineage_id:str="CURRENT_PILOT_DATA_LINEAGE_V1"; p1_dev_lineage_id:str="P1_DEV_DATA_LINEAGE_V1"; p4_select_lineage_id:str="P4_SELECT_EVALUATION_LINEAGE_V1"; p1_policy_condition_id:str="P4-R0-PI0"; p1_dev_seed:int=17; p1_dev_access_class:str="DEV_VISIBLE"; p4_select_access_class:str="SELECT_SUMMARY_ONLY"; legacy_reference_only:bool=True; prohibited_legacy_data_classes:tuple[str,...]=PROHIBITED_LEGACY_DATA_CLASSES
    def __post_init__(self):
        if self.prohibited_legacy_data_classes!=PROHIBITED_LEGACY_DATA_CLASSES:
            raise ValueError("prohibited legacy data classes must match frozen lineage")
        validate_payload_against_schema(schema_id=self.SCHEMA_ID,payload=self.to_dict())
    def to_dict(self): return {"schema_id":self.schema_id,"schema_version":self.schema_version,"lineage_id":self.lineage_id,"p1_dev_lineage_id":self.p1_dev_lineage_id,"p4_select_lineage_id":self.p4_select_lineage_id,"p1_policy_condition_id":self.p1_policy_condition_id,"p1_dev_seed":self.p1_dev_seed,"p1_dev_access_class":self.p1_dev_access_class,"p4_select_access_class":self.p4_select_access_class,"legacy_reference_only":self.legacy_reference_only,"prohibited_legacy_data_classes":list(self.prohibited_legacy_data_classes)}
    def to_json(self): return canonical_json_text(self.to_dict())

def build_p1_dev_policy_condition(*,policy_runtime_manifest_sha256:str,tokenizer_identity_manifest_sha256:str,chat_template_sha256:str,raw_protocol_sha256:str,runtime_core_commit:str,evaluator_commit:str)->PolicyConditionManifestV1:
    return PolicyConditionManifestV1("POLICY_CONDITION_MANIFEST_V1",1,"P4-R0-PI0","Qwen/Qwen2.5-3B-Instruct","aa8e72537993ba99e69dfaafa59ed015b17504d1",CheckpointKind.BASE_MODEL,None,None,TrainingMethod.NONE,None,None,policy_runtime_manifest_sha256,tokenizer_identity_manifest_sha256,chat_template_sha256,"Qwen2.5-3B-Instruct-E1","pi0","MEMORY_M0_V1",raw_protocol_sha256,runtime_core_commit,evaluator_commit)

def build_p1_dev_schedule(*,task_access_manifest:TaskAccessManifestV1,policy_condition:PolicyConditionManifestV1,output_namespace:str="p1-pi0-dev-v1")->ConditionRunScheduleV1:
    return build_condition_run_schedule(task_access_manifest=task_access_manifest,task_access_manifest_sha256=canonical_model_sha256(task_access_manifest),policy_condition=policy_condition,policy_condition_manifest_sha256=canonical_model_sha256(policy_condition),run_purpose=ConditionRunPurpose.P1_PI0_DEV_ROLLOUT,target_access_class=DistillationAccessClass.DEV_VISIBLE,replicate_seeds=(17,),output_namespace=output_namespace)

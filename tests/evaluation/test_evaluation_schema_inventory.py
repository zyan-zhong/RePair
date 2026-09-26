from __future__ import annotations
import json
from pchsi.evaluation.schema_contract import load_schema, schema_directory, validate_schema_definition

EXPECTED={
"alfworld_environment_runtime_manifest_v1.json":"ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1",
"e1_attempt_receipt_v1.json":"E1_ATTEMPT_RECEIPT_V1",
"e1_episode_artifact_v1.json":"E1_EPISODE_ARTIFACT_V1",
"e1_gamefile_sha256_preflight_v1.json":"E1_GAMEFILE_SHA256_PREFLIGHT_V1",
"e1_policy_runtime_manifest_v1.json":"E1_POLICY_RUNTIME_MANIFEST_V1",
"e1_public_transition_v1.json":"E1_PUBLIC_TRANSITION_RECORD_V1",
"e1_run_schedule_v1.json":"E1_RUN_SCHEDULE_V1",
"e1_scientific_cell_lock_v1.json":"E1_SCIENTIFIC_CELL_LOCK_V1",
"distillation_historical_access_audit_v1.json":"DISTILLATION_HISTORICAL_ACCESS_AUDIT_V1",
"distillation_task_access_manifest_v1.json":"DISTILLATION_TASK_ACCESS_MANIFEST_V1",
"policy_condition_manifest_v1.json":"POLICY_CONDITION_MANIFEST_V1",
"condition_run_schedule_v1.json":"CONDITION_RUN_SCHEDULE_V1",
"legacy_current_task_crosswalk_v1.json":"LEGACY_CURRENT_TASK_CROSSWALK_V1",
"p1_b_split_contract_v1.json":"P1_B_SPLIT_CONTRACT_V1",
"p1_b_split_proof_v1.json":"P1_B_SPLIT_PROOF_V1",
"current_pilot_data_lineage_v1.json":"CURRENT_PILOT_DATA_LINEAGE_V1",
"p1_b_evidence_completeness_report_v1.json":"P1_B_EVIDENCE_COMPLETENESS_REPORT_V1",
"policy_call_evidence_v1.json":"POLICY_CALL_EVIDENCE_V1",
"select_server_runtime_manifest_v1.json":"SELECT_SERVER_RUNTIME_MANIFEST_V1",
"select_policy_runtime_manifest_v1.json":"SELECT_POLICY_RUNTIME_MANIFEST_V1",
"evidence_visibility_matrix_v1.json":"EVIDENCE_VISIBILITY_MATRIX_V1",
}

def test_schema_inventory_is_exact_and_closed() -> None:
    root=schema_directory()
    observed={p.name:json.loads(p.read_text())["$id"] for p in root.glob("*.json")}
    assert observed==EXPECTED
    for schema_id in EXPECTED.values():
        schema=load_schema(schema_id); validate_schema_definition(schema)
        assert schema["type"]=="object" and schema["additionalProperties"] is False
        if schema_id == "E1_EPISODE_ARTIFACT_V1":
            optional={"task_access_manifest_sha256","policy_condition_manifest_sha256","condition_run_schedule_sha256","access_class","policy_condition_id","condition_cell_id","evaluation_context","logical_condition_id","checkpoint_instance_id","training_seed","select_policy_runtime_manifest_sha256"}
            assert set(schema["required"]) == set(schema["properties"]) - optional
        else:
            assert set(schema["required"])==set(schema["properties"])

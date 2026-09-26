import importlib

EXPECTED = {'ANALYZER_ANALYSIS_BUDGET_V2': 'analyzer_analysis_budget_v2.json', 'ANALYZER_CAPABILITY_PROFILE_V1': 'analyzer_capability_profile_v1.json', 'ANALYZER_COMPONENT_ATTRIBUTION_V1': 'analyzer_component_attribution_v1.json', 'ANALYZER_CROSSCHECK_RESULT_V1': 'analyzer_crosscheck_result_v1.json', 'ANALYZER_ERROR_INSTANCE_MEMBERSHIP_V1': 'analyzer_error_instance_membership_v1.json', 'ANALYZER_GROUP_MANIFEST_V1': 'analyzer_group_manifest_v1.json', 'ANALYZER_GROUP_RESULT_V1': 'analyzer_group_result_v1.json', 'ANALYZER_GROUP_RESULT_V2': 'analyzer_group_result_v2.json', 'ANALYZER_LOCAL_RESULT_V2': 'analyzer_local_result_v2.json', 'ANALYZER_MECHANICAL_CENSUS_V1': 'analyzer_mechanical_census_v1.json', 'ANALYZER_OUTCOME_ROUTE_V1': 'analyzer_outcome_route_v1.json', 'ANALYZER_POLICY_BEHAVIOR_PROFILE_V1': 'analyzer_policy_behavior_profile_v1.json', 'ANALYZER_REGRESSION_GUARD_V1': 'analyzer_regression_guard_v1.json', 'ANALYZER_REPAIR_CANDIDATE_V1': 'analyzer_repair_candidate_v1.json', 'ANALYZER_SUCCESS_OPTIMIZATION_CANDIDATE_V1': 'analyzer_success_optimization_candidate_v1.json', 'ANALYZER_SUCCESS_WORKFLOW_REFERENCE_V1': 'analyzer_success_workflow_reference_v1.json', 'COGNITIVE_ROLE_TRACE_V1': 'cognitive_role_trace_v1.json', 'REPAIR_EFFECT_DECOMPOSITION_RESULT_V1': 'repair_effect_decomposition_result_v1.json', 'REPAIR_EFFECT_DECOMPOSITION_TRACE_V1': 'repair_effect_decomposition_trace_v1.json', 'ANALYZER_GROUP_SYNTHESIS_INPUT_V1': 'analyzer_group_synthesis_input_v1.json', 'ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1': 'analyzer_source_conditioned_proposal_v1.json'}

def test_expanded_analyzer_schema_inventory_is_exact_and_closed():
    m=importlib.import_module("pchsi.analyzer.schema_contract")
    assert dict(m.EXPECTED_ANALYZER_SCHEMAS)==EXPECTED
    for sid in EXPECTED:
        schema=m.load_schema(sid)
        assert schema["$id"]==sid
        assert schema["type"]=="object"
        assert schema["additionalProperties"] is False

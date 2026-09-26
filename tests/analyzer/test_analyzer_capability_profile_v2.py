from pchsi.analyzer.component_attribution import (
    finalize_component_attribution,aggregate_capability_profile,
    build_policy_behavior_profile,
)
from pchsi.reference_loop.canonical import domain_hash

def _group():
    g={"schema_id":"ANALYZER_GROUP_RESULT_V1","schema_version":1,
       "group_id":"1"*64,"group_manifest_sha256":"2"*64,
       "mechanism_hypotheses":[],
       "source_conditioned_repair_sha256s":[],
       "group_result_sha256":"0"*64}
    g["group_result_sha256"]=domain_hash(
        "ANALYZER_GROUP_RESULT_V1",g,excluded_field="group_result_sha256")
    return g

def test_component_is_explicit_and_zero_claim_denominator_preserved():
    g=_group()
    a=finalize_component_attribution({
      "schema_id":"ANALYZER_COMPONENT_ATTRIBUTION_V1","schema_version":1,
      "group_result_sha256":g["group_result_sha256"],
      "principal_component":"RECOVERY_AND_BACKTRACKING",
      "secondary_components":[],"evidence_sha256s":[g["group_manifest_sha256"]],
      "uncertainty":"Unverified.","raw_response_sha256":"c"*64,
      "validated_result_sha256":"d"*64,"attribution_sha256":"0"*64,
    },group_result=g)
    profile=aggregate_capability_profile(
        [a],registered_group_results={
            g["group_result_sha256"]:g,
            "e"*64:{"unused":True},
        })
    assert profile["zero_claim_group_count"]==1
    policy=build_policy_behavior_profile(profile)
    assert policy["principal_bottleneck_selected"] is False
    assert policy["training_method_selected"] is False

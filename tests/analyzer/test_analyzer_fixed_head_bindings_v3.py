from __future__ import annotations
from copy import deepcopy
import pytest

import pchsi.analyzer.grouping as grouping
from pchsi.analyzer.component_attribution import (
    aggregate_capability_profile, build_policy_behavior_profile,
)
from pchsi.analyzer.crosscheck import (
    finalize_crosscheck, apply_crosscheck_disposition,
)
from pchsi.analyzer.candidate_projector import project_candidate


def test_group_synthesis_requires_exact_source_binding():
    manifest={
        "schema_id":"ANALYZER_GROUP_MANIFEST_V1","schema_version":1,
        "group_id":"a"*64,"task_family":"f",
        "mechanical_signature_sha256":"b"*64,
        "progress_signature_sha256":"c"*64,
        "lifecycle_signature":"ACTIVE",
        "terminal_footprint_class":"DIRECT_TERMINAL_IMPACT",
        "membership_sha256s":["d"*64],
        "source_local_result_sha256s":["e"*64],
        "inference_cluster_unit":"TASK_GAMEFILE",
        "membership_records":[{
            "schema_id":"ANALYZER_ERROR_INSTANCE_MEMBERSHIP_V1","schema_version":1,
            "local_result_sha256":"e"*64,"error_instance_id":"err",
            "task_id":"t","gamefile_sha256":"f"*64,"task_family":"f",
            "group_id":"a"*64,"primary_group_key_sha256":"a"*64,
            "inference_cluster_unit":"TASK_GAMEFILE","membership_sha256":"d"*64,
        }],
        "group_manifest_sha256":"0"*64,
    }
    from pchsi.reference_loop.canonical import domain_hash
    manifest["group_manifest_sha256"]=domain_hash(
        "ANALYZER_GROUP_MANIFEST_V1",manifest,
        excluded_field="group_manifest_sha256",
    )
    with pytest.raises(ValueError,match="missing source-state"):
        grouping.build_group_synthesis_inputs([manifest],source_bindings={})


def test_crosscheck_direct_apply_rejects_tampered_hash():
    original={"group_result_sha256":"a"*64}
    side=finalize_crosscheck({
        "schema_id":"ANALYZER_CROSSCHECK_RESULT_V1","schema_version":1,
        "target_artifact_sha256":"a"*64,"disposition":"ACCEPT",
        "supporting_evidence_sha256s":["b"*64],
        "contradiction_evidence_sha256s":[],
        "residual_case_ids":[],"current_evidence_sha256s":["b"*64],
        "historical_evidence_sha256s":[],"crosscheck_sha256":"0"*64,
    })
    bad=deepcopy(side); bad["disposition"]="REJECT"
    with pytest.raises(ValueError,match="mismatch"):
        apply_crosscheck_disposition(original,bad)


def test_historical_only_crosscheck_cannot_accept():
    with pytest.raises(ValueError,match="historical-only"):
        finalize_crosscheck({
            "schema_id":"ANALYZER_CROSSCHECK_RESULT_V1","schema_version":1,
            "target_artifact_sha256":"a"*64,"disposition":"ACCEPT",
            "supporting_evidence_sha256s":["b"*64],
            "contradiction_evidence_sha256s":[],
            "residual_case_ids":[],"current_evidence_sha256s":[],
            "historical_evidence_sha256s":["b"*64],
            "crosscheck_sha256":"0"*64,
        })


def test_projector_rejects_unknown_crosscheck_and_requires_live_menu_contract():
    source={"source_state_sha256":"a"*64,"menu_sha256":"b"*64,
            "admissible_commands":["look","go to fridge 1"]}
    with pytest.raises(ValueError):
        project_candidate(None,source,candidate_kind="FAILURE_REPAIR",
                          crosscheck_disposition="UNKNOWN")
    proposal=grouping.finalize_source_conditioned_proposal({
        "schema_id":"ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1","schema_version":1,
        "group_manifest_sha256":"c"*64,"local_result_sha256":"d"*64,
        "error_instance_id":"err","source_state_sha256":"a"*64,
        "menu_sha256":"b"*64,"exact_action":None,
        "option_actions":["go to fridge 1","open fridge 1"],
        "termination_condition":"stop when open","supporting_evidence_sha256s":["e"*64],
        "source_proposal_sha256":"0"*64,
    })
    out=project_candidate(proposal,source,candidate_kind="FAILURE_REPAIR")
    assert out["live_menu_revalidation_required"] is True
    assert out["all_intervention_actions_count_against_environment_budget"] is True


def test_duplicate_component_attribution_is_rejected():
    a={
        "schema_id":"ANALYZER_COMPONENT_ATTRIBUTION_V1","schema_version":1,
        "group_result_sha256":"a"*64,
        "principal_component":"RECOVERY_AND_BACKTRACKING",
        "secondary_components":[],"evidence_sha256s":["b"*64],
        "uncertainty":"u","raw_response_sha256":"c"*64,
        "validated_result_sha256":"d"*64,"attribution_sha256":"0"*64,
    }
    from pchsi.reference_loop.canonical import domain_hash
    a["attribution_sha256"]=domain_hash(
        "ANALYZER_COMPONENT_ATTRIBUTION_V1",a,
        excluded_field="attribution_sha256",
    )
    with pytest.raises(ValueError,match="duplicate"):
        aggregate_capability_profile(
            [a,a],
            registered_group_results={"a"*64:{"unused":True}},
        )

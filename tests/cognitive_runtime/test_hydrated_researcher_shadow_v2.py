from __future__ import annotations

import json

import pytest

from pchsi.cognitive_runtime.manifest import (
    load_runtime_manifest,
    stage_spec,
)
from pchsi.cognitive_runtime.output_validation import (
    validate_stage_output,
)
from pchsi.cognitive_runtime.request_renderer import (
    render_stage_request,
)


STAGE_ID = "R-PRE-SHADOW-HYDRATED-V2"


def _sha(index: int) -> str:
    return f"{index:064x}"


def _blind() -> dict[str, object]:
    pairs = []
    for index in range(30):
        source = _sha(1000 + index)
        family = f"family-{index % 6}"
        pairs.append(
            {
                "source_state_sha256": source,
                "A2": {
                    "candidate_sha256": _sha(2000 + index * 2),
                    "condition_id": "A2",
                    "source_state_sha256": source,
                    "task_family": family,
                    "formal_x_disposition": "ACCEPT",
                },
                "A3": {
                    "candidate_sha256": _sha(2001 + index * 2),
                    "condition_id": "A3",
                    "source_state_sha256": source,
                    "task_family": family,
                    "formal_x_disposition": "ACCEPT",
                },
            }
        )

    return {
        "schema_id": "STRONG_RESEARCHER_BLIND_PRE_INPUT_V2",
        "schema_version": 2,
        "round_id": "round-test",
        "parent_policy_id": "pi1",
        "blind_input_sha256": _sha(50),
        "evidence_hydration_manifest_sha256": _sha(51),
        "registered_candidate_universe": {
            "pair_table": pairs,
        },
        "required_output_contract": {
            "selected_state_budget": 12,
        },
        "verification_budget_plan": {
            "paired_repetitions_per_state": 5,
            "branch_arms_per_repetition": 2,
            "branch_runs_per_state": 10,
            "total_branch_run_budget": 120,
        },
        "visibility_boundary": {
            "human_pre_visible": False,
            "human_pre_hash_visible": False,
            "human_selection_visible": False,
            "human_rationale_visible": False,
            "current_f0f1_outcomes_visible": False,
            "future_policy_evaluation_visible": False,
            "strong_model_benchmark_per_task_results_visible": False,
            "success_trajectory_optimization_active": False,
        },
        # These registered values make evidence citation validation explicit.
        "synthetic_evidence_sha256": _sha(9000),
    }


def _projection(blind: dict[str, object]) -> dict[str, object]:
    return {
        "schema_id": "STRONG_RESEARCHER_BLIND_PRE_PROJECTION_V2",
        "blind_input_sha256": blind["blind_input_sha256"],
        "evidence_hydration_manifest_sha256": blind[
            "evidence_hydration_manifest_sha256"
        ],
        "blind_input": blind,
        "human_pre_gate_satisfied": True,
        "human_pre_content_visible": False,
        "human_pre_hash_visible": False,
    }


def _valid_output(
    blind: dict[str, object],
    *,
    selected_count: int = 12,
) -> dict[str, object]:
    pair_table = blind["registered_candidate_universe"]["pair_table"]
    reviews = []
    selected_sources = []
    selected_candidates = []
    a2_count = 0
    a3_count = 0

    for index, pair in enumerate(pair_table):
        preferred_condition = "A3" if index == 8 else "A2"
        alternative_condition = (
            "A2" if preferred_condition == "A3" else "A3"
        )
        preferred = pair[preferred_condition]
        alternative = pair[alternative_condition]
        selected = index < selected_count
        if selected:
            selected_sources.append(pair["source_state_sha256"])
            selected_candidates.append(
                preferred["candidate_sha256"]
            )
            if preferred_condition == "A2":
                a2_count += 1
            else:
                a3_count += 1

        reviews.append(
            {
                "state_index": index,
                "source_state_sha256": pair[
                    "source_state_sha256"
                ],
                "task_family": preferred["task_family"],
                "preferred_condition": preferred_condition,
                "preferred_candidate_sha256": preferred[
                    "candidate_sha256"
                ],
                "preferred_x_disposition": preferred[
                    "formal_x_disposition"
                ],
                "alternative_condition": alternative_condition,
                "alternative_candidate_sha256": alternative[
                    "candidate_sha256"
                ],
                "alternative_x_disposition": alternative[
                    "formal_x_disposition"
                ],
                "evidence_support_class": "HIGH",
                "expected_value_class": "HIGH",
                "expected_harm_risk_class": "LOW",
                "verification_cost_branch_runs": 10,
                "selected_for_verification": selected,
                "state_portfolio_disposition": (
                    "SELECTED" if selected else "DEFERRED_BUDGET"
                ),
                "evidence_summary": "Registered current evidence supports this arm.",
                "counterevidence_summary": "Mechanism remains pre-outcome uncertain.",
                "pair_adjudication_rationale": "Preferred arm is the bounded comparison.",
                "selection_rationale": (
                    "Selected for verification."
                    if selected
                    else "Deferred under the frozen state budget."
                ),
            }
        )

    return {
        "schema_id": "STRONG_RESEARCHER_PRE_SHADOW_V2",
        "schema_version": 2,
        "round_id": blind["round_id"],
        "blind_input_sha256": blind["blind_input_sha256"],
        "evidence_hydration_manifest_sha256": blind[
            "evidence_hydration_manifest_sha256"
        ],
        "observed_facts": ["The candidate universe has 30 A2/A3 pairs."],
        "uncertainties": ["Environment effects are not yet observed."],
        "candidate_bottlenecks": [
            {
                "candidate_id": "B1_TEST",
                "status": "SELECTED",
                "observed_facts": ["Repairs are unverified."],
                "uncertainties": ["Stable effects are unknown."],
                "evidence_sha256s": [
                    blind["synthetic_evidence_sha256"]
                ],
                "counterevidence_sha256s": [],
                "expected_value_class": "HIGH",
                "expected_harm_risk_class": "MEDIUM",
                "expected_verification_cost_class": "MEDIUM",
                "disposition_reason": "This is the current missing causal bridge.",
            },
            {
                "candidate_id": "B2_DEFER",
                "status": "DEFERRED",
                "observed_facts": ["Training is not yet authorized."],
                "uncertainties": ["Verified mixture is unknown."],
                "evidence_sha256s": [],
                "counterevidence_sha256s": [],
                "expected_value_class": "UNKNOWN",
                "expected_harm_risk_class": "UNKNOWN",
                "expected_verification_cost_class": "UNKNOWN",
                "disposition_reason": "Defer until F0/F1.",
            },
        ],
        "selected_bottleneck_id": "B1_TEST",
        "selected_bottleneck_statement": "Unverified repair quality is the principal bottleneck.",
        "single_falsifiable_hypothesis": "A bounded subset of repairs will show stable paired Benefit.",
        "single_principal_change_id": "PC1_TEST",
        "single_principal_change": "Verify a bounded source-conditioned repair portfolio.",
        "state_reviews": reviews,
        "selected_state_count": selected_count,
        "unused_state_budget": 12 - selected_count,
        "selected_source_state_sha256s": selected_sources,
        "selected_candidate_sha256s": selected_candidates,
        "selected_condition_counts": {
            "A2": a2_count,
            "A3": a3_count,
        },
        "abstention_reason": (
            None
            if selected_count == 12
            else "Remaining states do not add enough marginal verification value."
        ),
        "verification_plan": {
            "selected_state_budget_ceiling": 12,
            "paired_repetitions_per_state": 5,
            "branch_arms_per_repetition": 2,
            "branch_runs_per_state": 10,
            "selected_branch_run_budget": selected_count * 10,
            "total_branch_run_budget_ceiling": 120,
            "outcome_adaptive_budget_change_allowed": False,
            "unfavorable_candidate_replacement_allowed": False,
            "primary_endpoint": "Paired environment outcome under the registered repair.",
            "support_criterion": "Stable favorable paired evidence supports the hypothesis.",
            "refutation_criterion": "Stable non-benefit or harm refutes the repair hypothesis.",
            "stop_condition": "Stop at the frozen branch-run ceiling.",
        },
        "resource_plan": {
            "expected_environment_branch_runs": selected_count * 10,
            "expected_additional_model_logical_calls": 0,
            "expected_gpu_hours": 0.0,
            "expected_api_cost_usd": None,
            "resource_basis": "Same-state environment verification is the next experiment.",
        },
        "memory_usage_summary": {
            "memory_used_for_candidate_discovery": True,
            "memory_use_summary": "Historical Failure Experience is advisory.",
            "memory_helpfulness_hypothesis": "History can prioritize recurring mechanisms.",
            "memory_misleading_risk": "Historical analogies may not transfer to the current state.",
            "memory_effect_authority": False,
        },
        "training_policy_at_pre": {
            "status": "HOLD_PENDING_VERIFIED_F0F1_MANIFEST",
            "exact_training_mixture_frozen": False,
            "recommendation": "Use only independently verified effects for later training design.",
            "deferred_until": "A sealed F0/F1 verifier manifest exists.",
        },
        "automatic_environment_effect_assignment": False,
        "effect_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
        "promotion_authority": "DETERMINISTIC_INDEPENDENT_GATE_ONLY",
        "shadow_record_sha256": "0" * 64,
    }


def test_hydrated_stage_is_registered_without_replacing_legacy_stage():
    manifest = load_runtime_manifest()
    hydrated = stage_spec(STAGE_ID, manifest)
    assert hydrated["output_schema_id"] == (
        "STRONG_RESEARCHER_PRE_SHADOW_V2"
    )
    assert hydrated["max_output_tokens"] == 24576

    legacy = stage_spec("R-PRE-SHADOW", manifest)
    assert legacy["output_schema_id"] == "API_RESEARCHER_PRE_SHADOW_V1"


def test_request_renderer_uses_hydrated_blind_projection():
    blind = _blind()
    bundle = render_stage_request(
        stage_id=STAGE_ID,
        projection=_projection(blind),
    )
    request = bundle["provider_request"]
    assert request["text"]["format"]["name"] == (
        "strong_researcher_pre_shadow_v2"
    )
    user_text = request["input"][1]["content"][0]["text"]
    assert blind["blind_input_sha256"] in user_text
    assert "human_adjudication_sha256" not in user_text
    assert "human_pre_input_candidate_sha256" not in user_text


def test_valid_output_is_semantically_bound_and_content_hashed():
    blind = _blind()
    raw = _valid_output(blind)
    artifact = validate_stage_output(
        stage_id=STAGE_ID,
        text=json.dumps(raw),
        raw_response_sha256=_sha(9999),
        projection=_projection(blind),
    )
    assert artifact["schema_id"] == "STRONG_RESEARCHER_PRE_SHADOW_V2"
    assert artifact["selected_state_count"] == 12
    assert artifact["selected_condition_counts"] == {
        "A2": 11,
        "A3": 1,
    }
    assert artifact["shadow_record_sha256"] != "0" * 64


def test_output_rejects_candidate_outside_registered_pair():
    blind = _blind()
    raw = _valid_output(blind)
    raw["state_reviews"][0][
        "preferred_candidate_sha256"
    ] = _sha(55555)
    with pytest.raises(ValueError, match="outside registered pair"):
        validate_stage_output(
            stage_id=STAGE_ID,
            text=json.dumps(raw),
            raw_response_sha256=_sha(9999),
            projection=_projection(blind),
        )


def test_output_rejects_hallucinated_evidence_sha():
    blind = _blind()
    raw = _valid_output(blind)
    raw["candidate_bottlenecks"][0][
        "evidence_sha256s"
    ] = [_sha(55555)]
    with pytest.raises(ValueError, match="outside blind-input"):
        validate_stage_output(
            stage_id=STAGE_ID,
            text=json.dumps(raw),
            raw_response_sha256=_sha(9999),
            projection=_projection(blind),
        )


def test_output_rejects_budget_arithmetic_mismatch():
    blind = _blind()
    raw = _valid_output(blind)
    raw["verification_plan"]["selected_branch_run_budget"] = 110
    with pytest.raises(ValueError, match="branch-run budget mismatch"):
        validate_stage_output(
            stage_id=STAGE_ID,
            text=json.dumps(raw),
            raw_response_sha256=_sha(9999),
            projection=_projection(blind),
        )


def test_partial_budget_requires_abstention_reason():
    blind = _blind()
    raw = _valid_output(blind, selected_count=10)
    raw["abstention_reason"] = None
    with pytest.raises(ValueError, match="requires abstention reason"):
        validate_stage_output(
            stage_id=STAGE_ID,
            text=json.dumps(raw),
            raw_response_sha256=_sha(9999),
            projection=_projection(blind),
        )

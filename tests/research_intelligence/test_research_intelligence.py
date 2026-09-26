from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _module(name: str):
    return importlib.import_module(f"pchsi.research_intelligence.{name}")


def _round_record(round_id: str, status: str = "GO") -> dict[str, object]:
    return {
        "schema_id": "RESEARCH_PLANNER_REFERENCE_ROUND_MANIFEST_V1",
        "schema_version": 1,
        "round_id": round_id,
        "policy_lineage_sha256": "1" * 64,
        "round_evidence_package_sha256": "2" * 64,
        "human_pre_record_sha256": "3" * 64,
        "strong_pre_shadow_sha256": "4" * 64,
        "pre_adjudication_sha256": "5" * 64,
        "environment_result_package_sha256": "6" * 64,
        "human_post_record_sha256": "7" * 64,
        "strong_post_shadow_sha256": "8" * 64,
        "post_adjudication_sha256": "9" * 64,
        "verified_training_evidence_sha256": "a" * 64,
        "policy_evaluation_result_sha256": "b" * 64,
        "promotion_result": "PROMOTE" if status == "GO" else "ROLLBACK",
        "go_nogo_status": status,
        "access_class": "TRAIN_REFERENCE_ROUND",
        "reference_round_manifest_sha256": "c" * 64,
    }


def test_paradigm_reuses_six_layer_human_reference_framework() -> None:
    paradigm = _module("paradigm").load_research_planner_paradigm()
    layer_ids = [row["layer_id"] for row in paradigm["human_reference_layers"]]
    assert layer_ids == [
        "L0_EVIDENCE_INTEGRITY",
        "L1_POLICY_FAILURE_PROFILE",
        "L2_CANDIDATE_RESEARCH_PORTFOLIO",
        "L3_CAUSAL_EXPERIMENT_DESIGN",
        "L4_TRAINING_SIGNAL_AND_OBJECTIVE",
        "L5_EVALUATION_AND_PROMOTION",
    ]
    assert paradigm["human_role"] == (
        "BOOTSTRAP_REFERENCE_PRIMARY_FOR_PI1_TO_PI2"
    )
    assert paradigm["final_cognitive_model_target"][
        "same_checkpoint_required_at_target_stage"
    ] is True


def test_strong_pre_projection_is_blind_to_current_human_answer() -> None:
    visibility = _module("visibility")
    round_evidence = {
        "round_id": "r1",
        "round_evidence_package_sha256": "1" * 64,
        "researcher_memory_pack_sha256": None,
        "forbidden_future_outcomes_absent": True,
        "sealed_test_details_absent": True,
    }
    projection = visibility.build_strong_pre_projection(
        round_evidence_package=round_evidence,
        researcher_memory_pack=None,
    )
    encoded = json.dumps(projection, sort_keys=True)
    assert "human_pre_record" not in encoded
    assert "environment_result_package" not in encoded
    assert projection["round_evidence_package_sha256"] == "1" * 64


def test_strong_pre_projection_rejects_hindsight_leakage() -> None:
    visibility = _module("visibility")
    with pytest.raises(ValueError, match="forbidden"):
        visibility.build_strong_pre_projection(
            round_evidence_package={
                "round_evidence_package_sha256": "1" * 64,
                "researcher_memory_pack_sha256": None,
                "current_f0f1_outcomes": {},
            },
            researcher_memory_pack=None,
        )


def test_reference_round_manifest_preserves_full_supervision_chain(
    tmp_path: Path,
) -> None:
    reference = _module("reference_round")
    value = _round_record("round-1")
    value.pop("schema_id")
    value.pop("schema_version")
    value.pop("reference_round_manifest_sha256")
    output = tmp_path / "round.json"
    result = reference.freeze_reference_round_manifest(value, output)
    assert output.is_file()
    for field in (
        "human_pre_record_sha256",
        "strong_pre_shadow_sha256",
        "pre_adjudication_sha256",
        "environment_result_package_sha256",
        "human_post_record_sha256",
        "strong_post_shadow_sha256",
        "post_adjudication_sha256",
        "verified_training_evidence_sha256",
        "policy_evaluation_result_sha256",
    ):
        assert field in result


def test_demonstration_pack_excludes_current_round_and_sealed_details(
    tmp_path: Path,
) -> None:
    demo = _module("demonstrations")
    prior = tmp_path / "prior.json"
    prior.write_text(json.dumps(_round_record("round-0")), encoding="utf-8")
    output = tmp_path / "pack.json"
    result = demo.build_demonstration_pack(
        reference_round_paths=[prior],
        current_round_id="round-1",
        output=output,
    )
    assert result["current_round_human_answer_absent"] is True
    assert result["sealed_test_details_absent"] is True
    assert result["records"][0]["round_id"] == "round-0"

    current = tmp_path / "current.json"
    current.write_text(json.dumps(_round_record("round-1")), encoding="utf-8")
    with pytest.raises(ValueError, match="current-round"):
        demo.build_demonstration_pack(
            reference_round_paths=[current],
            current_round_id="round-1",
            output=tmp_path / "bad.json",
        )


def test_distillation_dataset_keeps_go_and_nogo_and_requires_no_cot(
    tmp_path: Path,
) -> None:
    distillation = _module("distillation")
    paths = []
    for index, status in enumerate(("GO", "NO_GO")):
        path = tmp_path / f"r{index}.json"
        path.write_text(
            json.dumps(_round_record(f"round-{index}", status)),
            encoding="utf-8",
        )
        paths.append(path)
    result = distillation.build_local_role_supervision_dataset(
        reference_round_paths=paths,
        output=tmp_path / "dataset.json",
    )
    statuses = {example["go_nogo_status"] for example in result["examples"]}
    assert statuses == {"GO", "NO_GO"}
    assert result["provider_reasoning_artifact_required"] is False
    assert result["local_training_executed"] is False
    assert result["local_primary_authorized"] is False
    assert result["split_unit"] == "ROUND_ID_PLUS_POLICY_LINEAGE_PLUS_TASK_SET"


def test_takeover_gate_does_not_confuse_shadow_with_primary_control(
    tmp_path: Path,
) -> None:
    takeover = _module("takeover")
    metrics = {
        "completed_reference_round_count": 1,
        "full_round_go_count": 0,
        "strong_pre_shadow_round_count": 1,
        "strong_post_shadow_round_count": 1,
        "future_outcome_leakage_count": 0,
        "single_change_compliance_rate": 1.0,
        "budget_compliance_rate": 1.0,
        "evidence_validity_rate": 1.0,
        "human_field_revision_rate": 0.2,
        "repeated_nogo_avoidance_rate": 1.0,
        "downstream_benefits_per_budget_ratio_vs_human": 1.0,
    }
    result = takeover.evaluate_takeover_gate(
        metrics=metrics,
        output=tmp_path / "gate.json",
    )
    assert result["strong_research_planner_primary_eligible"] is True
    assert result["local_training_and_shadow_eligible"] is True
    assert result["local_research_planner_primary_eligible"] is False
    assert result["fresh_autonomous_round_claim_supported"] is False
    assert result["unified_checkpoint_claim_supported"] is False

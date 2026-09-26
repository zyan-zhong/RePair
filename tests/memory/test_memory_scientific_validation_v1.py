from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from pchsi.memory.scientific_validation import (
    A0ArmBindingV1,
    A0SourceBindingV1,
    AmendmentTriggerV1,
    C2FrozenHistoricalSupportBindingV1,
    DIRECT_RETRIEVAL_MODE,
    EffectLabelV1,
    EffectScopeV1,
    InfrastructureDispositionV1,
    MechanismEffectV1,
    PolicyInternalizationPrefreezeV1,
    TerminalRelationV1,
    build_a0_scientific_manifest_v1,
    classify_local_paired_effect_v1,
    require_registered_amendment_trigger_v1,
    validate_c_query_isolation_v1,
    validate_task_group_disjointness_v1,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _arms(prefix: str) -> tuple[A0ArmBindingV1, ...]:
    return (
        A0ArmBindingV1(
            arm_id="M0",
            representation_class="M0",
            availability="AVAILABLE",
            artifact_sha256=None,
            policy_payload_sha256=None,
            token_count=0,
            retrieval_mode=DIRECT_RETRIEVAL_MODE,
        ),
        A0ArmBindingV1(
            arm_id="M1",
            representation_class="FM1",
            availability="AVAILABLE",
            artifact_sha256=_sha(prefix + ":m1:artifact"),
            policy_payload_sha256=_sha(prefix + ":m1:payload"),
            token_count=409,
            retrieval_mode=DIRECT_RETRIEVAL_MODE,
        ),
        A0ArmBindingV1(
            arm_id="M2",
            representation_class="SINGLE_CUE",
            availability="AVAILABLE",
            artifact_sha256=_sha(prefix + ":m2:artifact"),
            policy_payload_sha256=_sha(prefix + ":m2:payload"),
            token_count=31,
            retrieval_mode=DIRECT_RETRIEVAL_MODE,
        ),
        A0ArmBindingV1(
            arm_id="M3",
            representation_class="FM2",
            availability="AVAILABLE",
            artifact_sha256=_sha(prefix + ":m3:artifact"),
            policy_payload_sha256=_sha(prefix + ":m3:payload"),
            token_count=142,
            retrieval_mode=DIRECT_RETRIEVAL_MODE,
        ),
    )


def _source(index: int, seed: int = 17) -> A0SourceBindingV1:
    prefix = f"source-{index}"
    return A0SourceBindingV1(
        source_state_id=_sha(prefix + ":state"),
        source_task_id=f"task-{index}",
        task_gamefile_group_id=f"gamefile-group-{index}",
        source_fingerprint_sha256=_sha(prefix + ":fingerprint"),
        source_bundle_sha256=_sha(prefix + ":bundle"),
        memory_lineage_id=_sha(prefix + ":lineage"),
        record_version=2,
        snapshot_sha256=_sha("snapshot"),
        representation_template_sha256=_sha(prefix + ":template"),
        continuation_seed=seed,
        arms=_arms(prefix),
    )


def test_a0_manifest_is_exactly_three_by_four_local_cells() -> None:
    sources = tuple(_source(index) for index in range(3))
    manifest = build_a0_scientific_manifest_v1(
        engineering_base_head="112ba5d3ccc0a3f3c3a9fdd143ec4c69fa525229",
        sources=sources,
    )

    assert len(manifest.sources) == 3
    assert len(manifest.cells) == 12
    assert manifest.scientific_execution_authorized is False
    assert manifest.to_dict()["authority"] == (
        "LOCAL_MECHANISM_REPRESENTATION_PROBE_ONLY"
    )
    assert manifest.to_dict()["paper_main_representation_claim_authorized"] is False
    assert manifest.to_dict()["a1_status"] == "OPTIONAL_CONDITIONAL"

    for source in sources:
        cells = [
            cell for cell in manifest.cells
            if cell.source_state_id == source.source_state_id
        ]
        assert [cell.arm.arm_id for cell in cells] == ["M0", "M1", "M2", "M3"]
        assert {cell.continuation_seed for cell in cells} == {source.continuation_seed}
        assert {cell.source_fingerprint_sha256 for cell in cells} == {
            source.source_fingerprint_sha256
        }
        assert {cell.memory_lineage_id for cell in cells} == {
            source.memory_lineage_id
        }


def test_a0_m0_is_empty_and_m3_is_descriptive_fm2() -> None:
    source = _source(0)
    m0, _, _, m3 = source.arms
    assert m0.arm_id == "M0"
    assert m0.artifact_sha256 is None
    assert m0.policy_payload_sha256 is None
    assert m0.token_count == 0
    assert m3.arm_id == "M3"
    assert m3.representation_class == "FM2"

    with pytest.raises(ValueError, match="structured descriptive FM2"):
        A0ArmBindingV1(
            arm_id="M3",
            representation_class="PRESCRIPTIVE_FM3",
            availability="AVAILABLE",
            artifact_sha256=_sha("x"),
            policy_payload_sha256=_sha("y"),
            token_count=1,
            retrieval_mode=DIRECT_RETRIEVAL_MODE,
        )


def test_effect_vocabulary_retains_common_labels_and_local_scope() -> None:
    assert [item.value for item in EffectLabelV1] == [
        "Benefit", "Harm", "Neutral", "Uncertain"
    ]
    result = classify_local_paired_effect_v1(
        f0_success=False,
        f1_success=True,
        scientific_execution_started=True,
        pre_result_infrastructure_failure=False,
        identity_resolved=True,
        evidence_complete=True,
    )
    assert result.effect_label is EffectLabelV1.BENEFIT
    assert result.effect_scope is EffectScopeV1.SOURCE_STATE_LOCAL_PAIRED
    assert result.terminal_relation is TerminalRelationV1.FAIL_TO_SUCCESS
    assert result.mechanism_effect is MechanismEffectV1.NOT_EVALUATED
    assert result.scientific_denominator_eligible is True


def test_terminal_neutral_does_not_claim_mechanism_neutrality() -> None:
    result = classify_local_paired_effect_v1(
        f0_success=False,
        f1_success=False,
        scientific_execution_started=True,
        pre_result_infrastructure_failure=False,
        identity_resolved=True,
        evidence_complete=True,
    )
    assert result.effect_label is EffectLabelV1.NEUTRAL
    assert result.terminal_relation is TerminalRelationV1.SAME_TERMINAL
    assert result.mechanism_effect is MechanismEffectV1.NOT_EVALUATED


def test_pre_result_infrastructure_failure_retries_exact_cell_without_outcome() -> None:
    result = classify_local_paired_effect_v1(
        f0_success=None,
        f1_success=None,
        scientific_execution_started=False,
        pre_result_infrastructure_failure=True,
        identity_resolved=True,
        evidence_complete=False,
    )
    assert result.effect_label is None
    assert result.terminal_relation is TerminalRelationV1.NO_SCIENTIFIC_OUTCOME
    assert result.infrastructure_disposition is (
        InfrastructureDispositionV1.RETRY_EXACT_SAME_FROZEN_CELL
    )
    assert result.retry_exact_same_frozen_cell is True
    assert result.scientific_denominator_eligible is False


def test_post_execution_identity_ambiguity_is_not_auto_retry() -> None:
    result = classify_local_paired_effect_v1(
        f0_success=None,
        f1_success=None,
        scientific_execution_started=True,
        pre_result_infrastructure_failure=False,
        identity_resolved=False,
        evidence_complete=False,
    )
    assert result.effect_label is EffectLabelV1.UNCERTAIN
    assert result.infrastructure_disposition is (
        InfrastructureDispositionV1.SCIENTIFIC_UNCERTAIN_OR_HARD_STOP
    )
    assert result.retry_exact_same_frozen_cell is False
    assert result.scientific_denominator_eligible is False


def test_b_retrieval_pools_are_task_gamefile_group_disjoint() -> None:
    validate_task_group_disjointness_v1(
        {
            "CALIBRATION": ("g1", "g2"),
            "SELECTION": ("g3",),
            "SAFETY_STRESS": ("g4", "g5"),
        }
    )
    with pytest.raises(ValueError, match="overlap"):
        validate_task_group_disjointness_v1(
            {
                "CALIBRATION": ("g1",),
                "SELECTION": ("g1",),
            }
        )


def test_c_query_isolation_excludes_every_registered_exact_group_source() -> None:
    validate_c_query_isolation_v1(
        c_query_groups=("c1", "c2"),
        a0_source_groups=("a1", "a2", "a3"),
        token_calibration_groups=("t1", "t2"),
        active_memory_source_groups=("a1", "m2"),
        b_development_groups=("b1", "b2", "b3"),
    )
    with pytest.raises(ValueError, match="overlap"):
        validate_c_query_isolation_v1(
            c_query_groups=("c1", "m2"),
            a0_source_groups=("a1",),
            token_calibration_groups=("t1",),
            active_memory_source_groups=("m1", "m2"),
            b_development_groups=("b1",),
        )


def test_c2_requires_frozen_package_b_historical_support_binding() -> None:
    binding = C2FrozenHistoricalSupportBindingV1(
        retriever_config_sha256=_sha("retriever"),
        threshold_config_sha256=_sha("threshold"),
        active_snapshot_sha256=_sha("snapshot"),
        applicability_gate_sha256=_sha("gate"),
        selection_validation_report_sha256=_sha("selection"),
    )
    assert binding.retrieval_mode == "PACKAGE_B_FROZEN_RETRIEVER"
    assert binding.human_memory_selection_allowed is False

    with pytest.raises(ValueError, match="human-picked"):
        C2FrozenHistoricalSupportBindingV1(
            retriever_config_sha256=_sha("retriever"),
            threshold_config_sha256=_sha("threshold"),
            active_snapshot_sha256=_sha("snapshot"),
            applicability_gate_sha256=_sha("gate"),
            selection_validation_report_sha256=_sha("selection"),
            human_memory_selection_allowed=True,
        )


def test_outcome_guided_redesign_requires_registered_amendment_trigger() -> None:
    assert require_registered_amendment_trigger_v1("PROTOCOL_DEFECT") is (
        AmendmentTriggerV1.PROTOCOL_DEFECT
    )
    with pytest.raises(ValueError, match="outcome-guided redesign is forbidden"):
        require_registered_amendment_trigger_v1("A_RESULT_WAS_NULL")


def test_internalization_prefreeze_requires_all_frozen_authorities() -> None:
    value = PolicyInternalizationPrefreezeV1(
        training_eligibility_rule_sha256=_sha("eligibility"),
        training_arms_sha256=_sha("arms"),
        model_initialization_sha256=_sha("init"),
        data_deduplication_rule_sha256=_sha("dedup"),
        hyperparameter_selection_authority_sha256=_sha("hp"),
        off_off_evaluation_panel_sha256=_sha("panel"),
        primary_metric_sha256=_sha("metric"),
        promotion_rollback_rule_sha256=_sha("promotion"),
    )
    assert value.actual_training_execution_authorized is False


def test_manifest_materializer_is_explicit_write_once(tmp_path: Path) -> None:
    module_path = Path("scripts/memory/materialize_a0_scientific_manifest_v1.py")
    spec = importlib.util.spec_from_file_location("_a0_materializer", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    source_paths = []
    for index in range(3):
        path = tmp_path / f"source{index}.json"
        path.write_text(
            json.dumps(_source(index).to_dict(), sort_keys=True),
            encoding="utf-8",
        )
        source_paths.append(path)

    output = tmp_path / "a0_manifest.json"
    digest = module.materialize(
        source_binding_paths=tuple(source_paths),
        output_path=output,
        engineering_base_head="112ba5d3ccc0a3f3c3a9fdd143ec4c69fa525229",
    )
    assert output.is_file()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["manifest_sha256"] == digest
    assert len(payload["cells"]) == 12
    assert payload["scientific_execution_authorized"] is False

    with pytest.raises(FileExistsError):
        module.materialize(
            source_binding_paths=tuple(source_paths),
            output_path=output,
            engineering_base_head="112ba5d3ccc0a3f3c3a9fdd143ec4c69fa525229",
        )

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from pchsi.evaluation.canonical_evidence import canonical_json_bytes
from pchsi.memory.a0_formal_execution import (
    A0CellResultV1,
    A0ContinuationTransitionV1,
    validate_cell_result_against_frozen_cell_v1,
    validate_runtime_representation_binding_v1,
)


def _sha(ch: str) -> str:
    return ch * 64


def _frozen():
    payload = {"failure": "wrong branch"}
    payload_sha = hashlib.sha256(
        canonical_json_bytes(payload)
    ).hexdigest()
    template_sha = _sha("7")
    cell = {
        "cell_id": _sha("1"),
        "source_state_id": _sha("2"),
        "source_task_id": "task",
        "task_gamefile_group_id": _sha("3"),
        "source_fingerprint_sha256": _sha("2"),
        "source_bundle_sha256": _sha("4"),
        "memory_lineage_id": _sha("5"),
        "record_version": 1,
        "snapshot_sha256": _sha("6"),
        "representation_template_sha256": template_sha,
        "continuation_seed": 17,
        "arm": {
            "arm_id": "M3",
            "representation_class": "FM2",
            "availability": "AVAILABLE",
            "artifact_sha256": _sha("8"),
            "policy_payload_sha256": payload_sha,
            "token_count": 23,
            "retrieval_mode": "DIRECT_FIXED_RECORD_NO_RETRIEVAL",
        },
        "effect_scope": "SOURCE_STATE_LOCAL_PAIRED",
        "scientific_execution_authorized": False,
    }
    row = {
        "source_state_id": _sha("2"),
        "source_task_id": "task",
        "source_gamefile_sha256": _sha("3"),
        "source_bundle_sha256": _sha("4"),
        "memory_lineage_id": _sha("5"),
        "record_version": 1,
        "representation_template_sha256": template_sha,
        "continuation_seed": 17,
    }
    template = {
        "snapshot_sha256": _sha("6"),
        "memory_lineage_id": _sha("5"),
        "record_version": 1,
        "template_sha256": template_sha,
        "arms": [
            {
                "arm_id": "M3",
                "availability": "AVAILABLE",
                "representation_class": "FM2",
                "artifact_sha256": _sha("8"),
                "policy_visible_payload": payload,
                "token_count": 23,
                "retrieval_mode": "DIRECT_FIXED_RECORD_NO_RETRIEVAL",
            }
        ],
    }
    return cell, row, template


def test_runtime_representation_binding_locks_actual_template_arm_payload():
    cell, row, template = _frozen()
    actual = validate_runtime_representation_binding_v1(
        cell=cell,
        binding_row=row,
        representation_template=template,
    )
    assert actual["policy_visible_payload"] == {"failure": "wrong branch"}

    mutations = []
    x = copy.deepcopy(template)
    x["template_sha256"] = _sha("9")
    mutations.append(x)
    x = copy.deepcopy(template)
    x["arms"][0]["artifact_sha256"] = _sha("9")
    mutations.append(x)
    x = copy.deepcopy(template)
    x["arms"][0]["policy_visible_payload"] = {"failure": "different"}
    mutations.append(x)
    x = copy.deepcopy(template)
    x["arms"][0]["token_count"] = 24
    mutations.append(x)
    x = copy.deepcopy(template)
    x["arms"][0]["retrieval_mode"] = "SOME_OTHER_MODE"
    mutations.append(x)

    for altered in mutations:
        with pytest.raises(ValueError):
            validate_runtime_representation_binding_v1(
                cell=cell,
                binding_row=row,
                representation_template=altered,
            )


def test_cell_result_from_dict_recomputes_hash_and_rebinds_manifest_identity():
    cell, _, _ = _frozen()
    result = A0CellResultV1(
        cell_id=cell["cell_id"],
        source_state_id=cell["source_state_id"],
        arm_id="M3",
        continuation_seed=17,
        execution_identity_sha256=_sha("a"),
        scientific_outcome_produced=True,
        terminal_success=False,
        evidence_complete=True,
        pre_result_infrastructure_failure=False,
        final_budget_sha256=_sha("b"),
        prompt_census_count=2,
        policy_call_count=2,
        environment_step_count_from_source=1,
    )
    parsed = A0CellResultV1.from_dict(result.to_dict())
    validate_cell_result_against_frozen_cell_v1(
        result=parsed,
        cell=cell,
    )

    tampered = result.to_dict()
    tampered["terminal_success"] = True
    with pytest.raises(ValueError, match="result SHA"):
        A0CellResultV1.from_dict(tampered)

    wrong = result.to_dict()
    wrong["result_sha256"] = None
    wrong["continuation_seed"] = 18
    rebuilt = A0CellResultV1.from_dict(wrong)
    with pytest.raises(ValueError, match="continuation seed"):
        validate_cell_result_against_frozen_cell_v1(
            result=rebuilt,
            cell=cell,
        )


def test_continuation_transition_is_content_addressed():
    transition = A0ContinuationTransitionV1(
        environment_step_from_source_index=0,
        policy_call_index=4,
        action="take mug 1 from table 1",
        pre_observation_sha256=_sha("1"),
        pre_menu_sequence_sha256=_sha("2"),
        resulting_observation_sha256=_sha("3"),
        resulting_menu_sequence_sha256=_sha("4"),
        score=0,
        done=False,
        won=False,
        budget_before_policy_attempt_sha256=_sha("5"),
        budget_after_environment_finalization_sha256=_sha("6"),
    )
    assert len(transition.transition_sha256) == 64
    tampered = transition.to_dict()
    tampered["action"] = "look"
    with pytest.raises(ValueError, match="transition SHA"):
        A0ContinuationTransitionV1(**tampered)


def test_cell_runner_hardens_no_exposure_ambiguity_and_transition_evidence():
    source = Path("scripts/memory/run_formal_a0_cell_v1.py").read_text(
        encoding="utf-8"
    )
    assert "validate_runtime_representation_binding_v1" in source
    assert "validate_a0_manifest_binding_top_level_v1" in source
    assert "FORMAL_A0_NO_POLICY_EXPOSURE_V1" in source
    assert "return 77" in source
    assert "PromptTokenMismatchError" in source
    assert "PolicyResponseError" in source
    assert "continuation_transitions" in source
    assert "A0ContinuationTransitionV1" in source


def test_aggregator_revalidates_result_selected_attempt_and_evidence():
    source = Path(
        "scripts/memory/aggregate_formal_a0_results_v1.py"
    ).read_text(encoding="utf-8")
    assert "A0CellResultV1.from_dict" in source
    assert "validate_cell_result_against_frozen_cell_v1" in source
    assert "resolved_attempt.json" in source
    assert "RESOLVED_ATTEMPT_EVIDENCE_BINDING_MISMATCH" in source
    assert "continuation_transitions" in source
    assert "NOT_EVALUATED_PENDING_REGISTERED_RULE" in source


def test_execution_candidate_binds_src_layout_and_resolved_attempt():
    source = Path(
        "scripts/memory/RUN_FORMAL_A0_EXECUTION_CANDIDATE.sh"
    ).read_text(encoding="utf-8")
    assert 'export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"' in source
    assert "resolved_attempt.json" in source
    assert "FORMAL_A0_RESOLVED_ATTEMPT_V1" in source
    assert "set -e" not in source
    assert "set -u" not in source
    assert "set -o pipefail" not in source

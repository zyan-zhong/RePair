from pathlib import Path
import copy

import pytest

from pchsi.analyzer.candidate_projector import project_candidate
from pchsi.analyzer.schema_contract import validate_payload_against_schema
from pchsi.evaluation.budget import BudgetState
from pchsi.memory.source_state_contracts import (
    SourceDecisionStateFingerprintV1,
    build_source_decision_state_fingerprint_v1,
)
from pchsi.reference_loop.canonical import domain_hash
from pchsi.research_intelligence.human_f0f1_runtime import (
    validate_candidate_source_provenance_v1,
)


def fingerprint(condition="TEST_SOURCE::PROFILE_A"):
    return build_source_decision_state_fingerprint_v1(
        source_task_id="schema-compatibility-test",
        source_gamefile_sha256="1" * 64,
        source_bundle_sha256="2" * 64,
        source_policy_condition=condition,
        executed_prefix_sha256="3" * 64,
        observation_sha256="4" * 64,
        menu_sequence_sha256="5" * 64,
        memory_m0_sha256="6" * 64,
        interface_feedback_code=None,
        budget_state=BudgetState(
            policy_attempt_count=0, environment_step_count=0,
            protocol_failure_count=0, inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        ),
        model_call_index=0,
        base_policy_input_sha256="7" * 64,
    )


def candidate_for(fp):
    # Use the existing producer, not a new candidate schema.
    candidate = project_candidate(
        None,
        {"source_state_sha256": fp.fingerprint_sha256,
         "menu_sha256": fp.menu_sequence_sha256},
        candidate_kind="FAILURE_REPAIR",
    )
    candidate["candidate_status"] = "EXECUTABLE_EXACT_ACTION"
    candidate["exact_action"] = "look"
    candidate["candidate_sha256"] = domain_hash(
        candidate["schema_id"], candidate, excluded_field="candidate_sha256"
    )
    return candidate


def validate(candidate, fp):
    return validate_candidate_source_provenance_v1(
        candidate,
        expected_source_state_sha256=fp.fingerprint_sha256,
        expected_source_policy_condition=fp.source_policy_condition,
    )


def test_candidate_source_provenance_accepts_exact_replay_authority():
    fp = fingerprint()
    candidate = candidate_for(fp)
    original = copy.deepcopy(candidate)
    validate_payload_against_schema(
        schema_id="ANALYZER_REPAIR_CANDIDATE_V1", payload=candidate
    )
    assert "source_policy_condition" not in candidate
    assert validate(candidate, fp) == original
    assert candidate == original


def test_candidate_source_provenance_rejects_condition_mismatch():
    # A different source condition creates a different source-state identity.
    original, different = fingerprint(), fingerprint("TEST_SOURCE::PROFILE_B")
    assert original.fingerprint_sha256 != different.fingerprint_sha256
    with pytest.raises(ValueError, match="source state differs"):
        validate(candidate_for(original), different)


def test_fingerprint_rejects_condition_relabeling_without_rehash():
    payload = fingerprint().to_dict()
    payload["source_policy_condition"] = "WRONG"
    with pytest.raises(ValueError, match="fingerprint_sha256 mismatch"):
        SourceDecisionStateFingerprintV1.from_dict(payload)


def test_candidate_rejects_injected_condition_even_if_it_matches():
    fp = fingerprint()
    candidate = candidate_for(fp)
    candidate["source_policy_condition"] = fp.source_policy_condition
    candidate["candidate_sha256"] = domain_hash(
        candidate["schema_id"], candidate, excluded_field="candidate_sha256"
    )
    with pytest.raises(ValueError, match="unknown fields"):
        validate(candidate, fp)


def test_candidate_rejects_changed_action_without_rehash():
    fp = fingerprint()
    candidate = candidate_for(fp)
    candidate["exact_action"] = "inventory"
    with pytest.raises(ValueError, match="hash|SHA"):
        validate(candidate, fp)


def test_candidate_rejects_missing_existing_schema_field():
    fp = fingerprint()
    candidate = candidate_for(fp)
    del candidate["menu_sha256"]
    with pytest.raises(ValueError, match="missing required fields"):
        validate(candidate, fp)


def test_candidate_rejects_minimal_non_schema_fixture():
    fp = fingerprint()
    with pytest.raises(ValueError):
        validate({"source_state_sha256": fp.fingerprint_sha256,
                  "source_policy_condition": fp.source_policy_condition}, fp)


@pytest.mark.parametrize("condition", [None, "", "bad\x00label"])
def test_expected_replay_condition_must_be_valid_text(condition):
    fp = fingerprint()
    with pytest.raises(ValueError, match="expected_source_policy_condition"):
        validate_candidate_source_provenance_v1(
            candidate_for(fp),
            expected_source_state_sha256=fp.fingerprint_sha256,
            expected_source_policy_condition=condition,
        )


def test_live_runner_has_no_source_condition_vs_served_model_comparison():
    root = Path(__file__).resolve().parents[2]
    source = (root / "scripts/research_intelligence/"
              "run_human_reference_f0f1_branch_v2.py").read_text(encoding="utf-8")
    assert 'source.source_policy_condition != binding["policy_model"]' not in source
    assert "validate_candidate_source_provenance_v1(" in source
    assert 'expected_model=str(binding["policy_model"])' in source

from pathlib import Path
import pytest
from pchsi.evaluation.budget import BudgetState
from pchsi.memory.source_state_contracts import (
    SourceDecisionStateFingerprintV1,
    build_source_decision_state_fingerprint_v1,
)

def test_source_fingerprint_roundtrip_and_tamper():
    value = build_source_decision_state_fingerprint_v1(
        source_task_id="task",
        source_gamefile_sha256="a"*64,
        source_bundle_sha256="b"*64,
        source_policy_condition="P4-R1-Q2-BAD-TRAIN17",
        executed_prefix_sha256="c"*64,
        observation_sha256="d"*64,
        menu_sequence_sha256="e"*64,
        memory_m0_sha256="f"*64,
        interface_feedback_code=None,
        budget_state=BudgetState(policy_attempt_count=1, environment_step_count=1),
        model_call_index=1,
        base_policy_input_sha256="1"*64,
    )
    assert SourceDecisionStateFingerprintV1.from_json(value.canonical_bytes()) == value
    payload = value.to_dict()
    payload["observation_sha256"] = "2"*64
    with pytest.raises(ValueError, match="fingerprint_sha256"):
        SourceDecisionStateFingerprintV1.from_dict(payload)

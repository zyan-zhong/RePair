from __future__ import annotations

from pathlib import Path


def test_final_result_audit_candidate_script_keeps_human_result_gate() -> None:
    script = (
        Path(__file__).parents[2]
        / "scripts/memory/audit_memory_final_result_candidate_v1.py"
    ).read_text(encoding="utf-8")
    assert "result_audit_approved" in script
    assert '"result_audit_approved": False' in script
    assert (
        "RESULT_AUDIT_APPROVED_FAILURE_MEMORY_V1_"
        "MEMORY_OWNED_CLOSURE_V2"
    ) in script
    assert "policy_training_performed" in script
    assert '"policy_training_performed": False' in script

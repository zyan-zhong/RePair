from __future__ import annotations

from pathlib import Path


def test_formal_a_execution_candidate_is_gated_and_never_submits():
    source = Path(
        "scripts/memory/RUN_FORMAL_A0_EXECUTION_CANDIDATE.sh"
    ).read_text(encoding="utf-8")
    assert "PACKAGE_A0_LOCAL_MECHANISM_EXECUTION_APPROVED" in source
    assert "run_formal_a0_cell_v1.py" in source
    assert 'while [ "$index" -lt 12 ]' in source
    assert "sbatch " not in source
    assert "set -e" not in source
    assert "set -u" not in source
    assert "set -o pipefail" not in source
    assert "FORMAL_A0_EXACT_CELL_INFRA_RETRY" in source


def test_cell_runner_has_execution_gate_token_census_and_infra_split():
    source = Path(
        "scripts/memory/run_formal_a0_cell_v1.py"
    ).read_text(encoding="utf-8")
    assert "PACKAGE_A0_LOCAL_MECHANISM_EXECUTION_APPROVED" in source
    assert "DIRECT_FIXED_RECORD_NO_RETRIEVAL" in source
    assert "FORMAL_A0_LOCAL_REPRESENTATION_PROBE" in source
    assert "A0PromptCensusRecordV1" in source
    assert "truncation_applied=False" in source
    assert "FORMAL_A0_PRE_RESULT_INFRASTRUCTURE_FAILURE_V1" in source
    assert "FORMAL_A0_POST_EXECUTION_INFRASTRUCTURE_AMBIGUITY_V1" in source
    assert "return 75" in source
    assert "return 76" in source


def test_aggregator_forbids_general_representation_claim():
    source = Path(
        "scripts/memory/aggregate_formal_a0_results_v1.py"
    ).read_text(encoding="utf-8")
    assert '"paper_main_representation_claim_authorized": False' in source
    assert '"effect_scope": "SOURCE_STATE_LOCAL_PAIRED"' in source
    assert "A0_EFFECT_LEDGER_V1.jsonl" in source

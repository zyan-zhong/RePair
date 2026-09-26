from __future__ import annotations

from pathlib import Path


def test_token_budget_analyzer_is_calibration_only_and_strict():
    text = Path(
        "scripts/memory/run_token_budget_calibration_analyzer_v1.py"
    ).read_text(encoding="utf-8")

    assert "CALIBRATION_ONLY_ANALYZER_PROPOSAL" in text
    assert '"type": "json_schema"' in text
    assert '"strict": True' in text
    assert "store=False" in text
    assert "gpt-5.6-sol" in text
    assert "ABSTAIN" in text
    assert "NO_PERFORMANCE_ESTIMAND" in text
    assert "AMBIGUOUS_POST_REQUEST_NO_AUTOMATIC_RETRY" in text

    for forbidden in (
        "valid_seen",
        "valid_unseen",
    ):
        assert forbidden not in text

    assert '"memory_on_execution_used": False' in text


def test_token_budget_contract_builder_has_fixed_candidates_and_no_replacement():
    text = Path(
        "scripts/memory/build_token_budget_contract_v1.py"
    ).read_text(encoding="utf-8")

    assert "MIN_VALID_CALIBRATION_RECORDS_V1" in text
    assert "SINGLE_RECORD_CANDIDATES_V1" in text
    assert "LIBRARY_TOTAL_CANDIDATES_V1" in text
    assert "choose_smallest_ceiling_v1" in text
    assert "NO_PERFORMANCE_ESTIMAND" in text
    assert "for ordinal, failure in enumerate(failures)" in text
    assert "backfill" not in text.casefold()
    assert "random.choice" not in text
    assert "random.sample" not in text

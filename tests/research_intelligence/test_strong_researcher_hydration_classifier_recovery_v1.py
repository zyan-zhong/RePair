from __future__ import annotations

import json
from pathlib import Path

from pchsi.research_intelligence.strong_researcher_evidence_hydration import (
    build_hydration_manifest_v1,
)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )


def _blind(target: str) -> dict[str, object]:
    return {
        "schema_id": "STRONG_RESEARCHER_BLIND_PRE_INPUT_V1",
        "schema_version": 1,
        "policy_scorecard": {
            "policy_lineage_sha256": None,
            "policy_checkpoint_sha256": None,
            "policy_config_sha256": None,
            "task_set_manifest_sha256": None,
            "rollout_census_sha256": target,
            "mechanical_failure_census_sha256": None,
        },
        "analyzer_evidence": {
            "formal_result_manifest_sha256": None,
            "metric_report_sha256": None,
        },
        "experiment_history": {
            "historical_f0f1_summary_sha256": None,
            "historical_go_nogo_ledger_sha256": None,
            "previous_researcher_decisions_sha256": None,
            "training_history_sha256": None,
            "code_config_diff_manifest_sha256": None,
        },
        "resource_and_cost": {
            "resource_budget_manifest_sha256": None,
        },
        "blind_input_sha256": "f" * 64,
    }


def _slot(manifest: dict[str, object], slot_id: str) -> dict[str, object]:
    return next(
        row
        for row in manifest["slots"]
        if row["slot_id"] == slot_id
    )


def test_malformed_non_authority_sha_value_does_not_abort_reference_classification(
    tmp_path: Path,
) -> None:
    target = "a" * 64
    _write(
        tmp_path / "schema_less_reference_map.json",
        {
            "rollout_census_sha256": target,
            "formal_result_manifest_sha256": "NOT_BOUND",
            "metric_report_sha256": None,
        },
    )

    manifest = build_hydration_manifest_v1(
        blind_input_v1=_blind(target),
        roots=[tmp_path],
    )

    slot = _slot(
        manifest,
        "policy_scorecard.rollout_census_sha256",
    )
    assert slot["status"] == "QUERY_REQUIRED_MISSING"
    assert manifest["hydration_ready"] is False


def test_malformed_reference_map_never_becomes_readable_evidence_when_leaf_exists(
    tmp_path: Path,
) -> None:
    target = "a" * 64
    _write(
        tmp_path / "schema_less_reference_map.json",
        {
            "rollout_census_sha256": target,
            "formal_result_manifest_sha256": "MISSING",
        },
    )
    _write(
        tmp_path
        / "formal_state"
        / "05_round_evidence_seal"
        / "support"
        / "FORMAL_PI1_ROLLOUT_CENSUS_V1.json",
        {
            "schema_id": "FORMAL_PI1_ROLLOUT_CENSUS_V1",
            "rollout_census_sha256": target,
            "success_count": 10,
            "failure_count": 124,
        },
    )

    manifest = build_hydration_manifest_v1(
        blind_input_v1=_blind(target),
        roots=[tmp_path],
    )
    slot = _slot(
        manifest,
        "policy_scorecard.rollout_census_sha256",
    )
    assert slot["status"] == "RESOLVED_READABLE"
    assert slot["selected_match"]["schema_id"] == (
        "FORMAL_PI1_ROLLOUT_CENSUS_V1"
    )
    assert slot["readable_view"]["content"]["failure_count"] == 124

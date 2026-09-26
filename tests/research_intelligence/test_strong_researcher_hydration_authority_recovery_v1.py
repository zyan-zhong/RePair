from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pchsi.research_intelligence.strong_researcher_evidence_hydration import (
    build_hydration_manifest_v1,
)


def _write(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _blind(
    *,
    lane: str,
    field: str,
    target_sha256: str,
) -> dict[str, object]:
    policy = {
        "policy_lineage_sha256": None,
        "policy_checkpoint_sha256": None,
        "policy_config_sha256": None,
        "task_set_manifest_sha256": None,
        "rollout_census_sha256": None,
        "mechanical_failure_census_sha256": None,
    }
    analyzer = {
        "formal_result_manifest_sha256": None,
        "metric_report_sha256": None,
    }
    history = {
        "historical_f0f1_summary_sha256": None,
        "historical_go_nogo_ledger_sha256": None,
        "previous_researcher_decisions_sha256": None,
        "training_history_sha256": None,
        "code_config_diff_manifest_sha256": None,
    }
    resources = {
        "resource_budget_manifest_sha256": None,
    }
    lanes = {
        "policy_scorecard": policy,
        "analyzer_evidence": analyzer,
        "experiment_history": history,
        "resource_and_cost": resources,
    }
    lanes[lane][field] = target_sha256
    return {
        "schema_id": "STRONG_RESEARCHER_BLIND_PRE_INPUT_V1",
        "schema_version": 1,
        **lanes,
        "blind_input_sha256": "f" * 64,
    }


def _slot(manifest: dict[str, object], slot_id: str) -> dict[str, object]:
    return next(
        row
        for row in manifest["slots"]
        if row["slot_id"] == slot_id
    )


def test_schema_bearing_round_evidence_leaf_beats_reference_only_map(
    tmp_path: Path,
) -> None:
    target = "a" * 64
    _write(
        tmp_path / "reference_map.json",
        {
            "policy_lineage_sha256": target,
            "policy_checkpoint_sha256": "b" * 64,
            "policy_config_sha256": "c" * 64,
            "task_set_manifest_sha256": "d" * 64,
            "rollout_census_sha256": "e" * 64,
            "mechanical_failure_census_sha256": "1" * 64,
        },
    )
    leaf = {
        "schema_id": "FORMAL_PI1_POLICY_LINEAGE_BINDING_V1",
        "policy_lineage_sha256": target,
        "policy_version": "pi1",
        "parent_policy_id": "pi0",
    }
    _write(
        tmp_path
        / "formal_analyzer_to_human_researcher_pre_boundary_v1_1_state"
        / "05_round_evidence_seal"
        / "support"
        / "FORMAL_PI1_POLICY_LINEAGE_BINDING_V1.json",
        leaf,
    )

    manifest = build_hydration_manifest_v1(
        blind_input_v1=_blind(
            lane="policy_scorecard",
            field="policy_lineage_sha256",
            target_sha256=target,
        ),
        roots=[tmp_path],
    )

    slot = _slot(
        manifest,
        "policy_scorecard.policy_lineage_sha256",
    )
    assert slot["status"] == "RESOLVED_READABLE"
    assert slot["selected_match"]["schema_id"] == (
        "FORMAL_PI1_POLICY_LINEAGE_BINDING_V1"
    )
    assert slot["readable_view"]["content"]["policy_version"] == "pi1"


def test_reference_only_hash_map_is_not_readable_evidence(
    tmp_path: Path,
) -> None:
    target = "a" * 64
    _write(
        tmp_path / "reference_map.json",
        {
            "rollout_census_sha256": target,
            "mechanical_failure_census_sha256": "b" * 64,
            "policy_lineage_sha256": "c" * 64,
        },
    )

    manifest = build_hydration_manifest_v1(
        blind_input_v1=_blind(
            lane="policy_scorecard",
            field="rollout_census_sha256",
            target_sha256=target,
        ),
        roots=[tmp_path],
    )
    slot = _slot(
        manifest,
        "policy_scorecard.rollout_census_sha256",
    )
    assert slot["status"] == "QUERY_REQUIRED_MISSING"
    assert slot["readable_view"] is None


def test_scientific_unit_identity_is_not_task_set_manifest_content(
    tmp_path: Path,
) -> None:
    target = "a" * 64
    _write(
        tmp_path / "scientific_unit_identity.json",
        {
            "schema_id": "SCIENTIFIC_UNIT_IDENTITY_V1",
            "identity_sha256": "b" * 64,
            "scientific_unit_id": "unit-1",
            "scientific_unit_type": "GROUP",
            "task_set_manifest_sha256": target,
        },
    )

    manifest = build_hydration_manifest_v1(
        blind_input_v1=_blind(
            lane="policy_scorecard",
            field="task_set_manifest_sha256",
            target_sha256=target,
        ),
        roots=[tmp_path],
    )
    slot = _slot(
        manifest,
        "policy_scorecard.task_set_manifest_sha256",
    )
    assert slot["status"] == "QUERY_REQUIRED_MISSING"


def test_task_set_leaf_beats_many_scientific_unit_identity_carriers(
    tmp_path: Path,
) -> None:
    target = "a" * 64
    for index in range(20):
        _write(
            tmp_path / "units" / f"unit-{index}.json",
            {
                "schema_id": "SCIENTIFIC_UNIT_IDENTITY_V1",
                "identity_sha256": f"{index + 1:064x}",
                "scientific_unit_id": f"unit-{index}",
                "scientific_unit_type": "GROUP",
                "task_set_manifest_sha256": target,
            },
        )

    leaf = {
        "schema_id": "FORMAL_PI1_TASK_SET_MANIFEST_V1",
        "task_set_manifest_sha256": target,
        "split": "valid_unseen",
        "task_count": 134,
    }
    _write(
        tmp_path
        / "formal_state"
        / "05_round_evidence_seal"
        / "support"
        / "FORMAL_PI1_TASK_SET_MANIFEST_V1.json",
        leaf,
    )

    manifest = build_hydration_manifest_v1(
        blind_input_v1=_blind(
            lane="policy_scorecard",
            field="task_set_manifest_sha256",
            target_sha256=target,
        ),
        roots=[tmp_path],
    )
    slot = _slot(
        manifest,
        "policy_scorecard.task_set_manifest_sha256",
    )
    assert slot["status"] == "RESOLVED_READABLE"
    assert slot["selected_match"]["schema_id"] == (
        "FORMAL_PI1_TASK_SET_MANIFEST_V1"
    )
    assert slot["readable_view"]["content"]["task_count"] == 134


def test_schema_bearing_formal_result_leaf_beats_analyzer_hash_map(
    tmp_path: Path,
) -> None:
    target = "a" * 64
    _write(
        tmp_path / "analyzer_refs.json",
        {
            "formal_result_manifest_sha256": target,
            "metric_report_sha256": "b" * 64,
            "repair_effect_authority": False,
        },
    )
    leaf = {
        "schema_id": "FORMAL_ANALYZER_RESULT_MANIFEST_V1",
        "formal_result_manifest_sha256": target,
        "selected_candidate_count": 60,
        "source_state_count": 30,
    }
    _write(
        tmp_path
        / "formal_state"
        / "05_round_evidence_seal"
        / "support"
        / "FORMAL_ANALYZER_RESULT_MANIFEST_V1.json",
        leaf,
    )

    manifest = build_hydration_manifest_v1(
        blind_input_v1=_blind(
            lane="analyzer_evidence",
            field="formal_result_manifest_sha256",
            target_sha256=target,
        ),
        roots=[tmp_path],
    )
    slot = _slot(
        manifest,
        "analyzer_evidence.formal_result_manifest_sha256",
    )
    assert slot["status"] == "RESOLVED_READABLE"
    assert slot["selected_match"]["schema_id"] == (
        "FORMAL_ANALYZER_RESULT_MANIFEST_V1"
    )
    assert slot["readable_view"]["content"][
        "selected_candidate_count"
    ] == 60



def test_exact_text_file_sha_can_be_hydrated_as_readable_text(
    tmp_path: Path,
) -> None:
    config = tmp_path / "policy_config.yaml"
    data = b"model: qwen\nmax_steps: 50\n"
    config.write_bytes(data)
    target = hashlib.sha256(data).hexdigest()

    manifest = build_hydration_manifest_v1(
        blind_input_v1=_blind(
            lane="policy_scorecard",
            field="policy_config_sha256",
            target_sha256=target,
        ),
        roots=[tmp_path],
    )
    slot = _slot(
        manifest,
        "policy_scorecard.policy_config_sha256",
    )
    assert slot["status"] == "RESOLVED_READABLE"
    assert slot["readable_view"]["projection_kind"] == "FULL_TEXT"
    assert "max_steps: 50" in slot["readable_view"]["content"]

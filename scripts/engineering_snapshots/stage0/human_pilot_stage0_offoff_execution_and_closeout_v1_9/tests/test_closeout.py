from stage0.closeout import build_closeout


def test_closeout_is_engineering_only_and_forbids_clean_run_reuse() -> None:
    result = build_closeout(
        result_sha256="a" * 64,
        artifact_index_sha256="b" * 64,
        package_inventory_sha256="c" * 64,
    )
    assert result["round_role"] == "PILOT_ENGINEERING_ROUND_V1"
    assert result["paper_efficacy_evidence"] is False
    assert result["promotion_eligible"] is False
    assert result["contaminated_valid_unseen_development_task_count"] == 117
    assert result["heldout_select_task_count"] == 17
    assert "CURRENT_PILOT_POLICY_ADAPTERS" in result[
        "forbidden_clean_experiment_inputs"
    ]
    assert result["next_gate"] == (
        "GENERIC_ROUND_ORCHESTRATOR_AND_ROLE_HANDOFF_AUTOMATION"
    )

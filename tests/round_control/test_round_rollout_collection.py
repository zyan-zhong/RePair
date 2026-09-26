import pytest

from pchsi.round_control.rollout_collection import (
    RoundEpisodeTerminalV1,
    RoundRolloutCollectionRequestV1,
    RoundRolloutExecutionBindingV1,
    build_failure_cohort,
    execute_generic_rollout_control,
    seal_rollout_universe,
)


def _request():
    return RoundRolloutCollectionRequestV1(
        round_id="formal-r1",
        execution_attempt_id="formal-r1-attempt-0",
        parent_policy_id="PI0_CLEAN",
        parent_policy_artifact_sha256="a" * 64,
        policy_runtime_binding_sha256="b" * 64,
        execution_profile_sha256="c" * 64,
        train_update_manifest_sha256="d" * 64,
        round_memory_runtime_authority_sha256="e" * 64,
        round_start_memory_snapshot_sha256="f" * 64,
        token_budget_contract_sha256="1" * 64,
        execution_namespace="formal-max10-r1",
        rollout_seed=17,
    )


def _terminal(i, status, success):
    return RoundEpisodeTerminalV1(
        scientific_cell_id=f"cell-{i}",
        execution_attempt_id=f"attempt-{i}",
        task_id=f"task-{i}",
        task_index=i,
        status=status,
        success=success,
        terminal_receipt_sha256=f"{i+2:064x}",
    )


def test_request_hash_is_domain_separated_and_stable():
    a = _request()
    b = _request()
    assert a.request_sha256 == b.request_sha256
    assert len(a.request_sha256) == 64
    assert a.to_dict()["selection_rule"] == "FULL_FROZEN_TRAIN_UPDATE_UNIVERSE"


def test_benchmark_feedback_and_invalid_attempt_reuse_are_forbidden():
    with pytest.raises(ValueError):
        RoundRolloutCollectionRequestV1(
            round_id="formal-r1",
            execution_attempt_id="formal-r1-attempt-0",
            parent_policy_id="PI0_CLEAN",
            parent_policy_artifact_sha256="a" * 64,
            policy_runtime_binding_sha256="b" * 64,
            execution_profile_sha256="c" * 64,
            train_update_manifest_sha256="d" * 64,
            round_memory_runtime_authority_sha256="e" * 64,
            round_start_memory_snapshot_sha256="f" * 64,
            token_budget_contract_sha256="1" * 64,
            execution_namespace="formal-max10-r1",
            rollout_seed=17,
            benchmark_feedback_authorized=True,
        )


def test_invalid_rollout_cannot_publish_failure_cohort():
    universe = seal_rollout_universe(
        request_sha256=_request().request_sha256,
        terminals=(
            _terminal(0, "SCIENTIFIC_FAILURE", False),
            _terminal(1, "INFRASTRUCTURE_INVALID", None),
        ),
    )
    assert universe.scientific_rollout_valid is False
    with pytest.raises(ValueError):
        build_failure_cohort(universe)


def test_failure_cohort_is_all_failures_in_frozen_order():
    universe = seal_rollout_universe(
        request_sha256=_request().request_sha256,
        terminals=(
            _terminal(0, "SCIENTIFIC_SUCCESS", True),
            _terminal(1, "SCIENTIFIC_FAILURE", False),
            _terminal(2, "SCIENTIFIC_FAILURE", False),
        ),
    )
    cohort = build_failure_cohort(universe)
    assert cohort.failure_scientific_cell_ids == ("cell-1", "cell-2")
    assert (
        cohort.to_dict()["selection_rule"]
        == "ALL_SCIENTIFIC_FAILURES_IN_FROZEN_ROLLOUT_ORDER"
    )
    assert cohort.to_dict()["human_selection_performed"] is False


def test_generic_control_injects_existing_runner_only():
    request = _request()
    seen = []

    def run_one(item):
        seen.append(item)
        return _terminal(item, "SCIENTIFIC_FAILURE", False)

    universe, cohort = execute_generic_rollout_control(
        request=request,
        scheduled_items=(0, 1, 2),
        run_one=run_one,
    )
    assert seen == [0, 1, 2]
    assert universe.scheduled_count == 3
    assert cohort.failure_scientific_cell_ids == (
        "cell-0",
        "cell-1",
        "cell-2",
    )


def test_execution_binding_must_explicitly_authorize_science():
    binding = RoundRolloutExecutionBindingV1(
        request_sha256=_request().request_sha256,
        rollout_control_source_sha256="2" * 64,
        clean_execution_binding_source_sha256="3" * 64,
        episode_evaluator_source_sha256="4" * 64,
        attempt_receipts_source_sha256="5" * 64,
        policy_runtime_adapter_sha256="6" * 64,
        scientific_execution_authorized=False,
    )
    assert binding.scientific_execution_authorized is False

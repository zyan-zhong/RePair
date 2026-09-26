from pathlib import Path

from pchsi.round_control.clean_data_gate import (
    CleanConsumerV1,
)
from pchsi.round_control.concrete_bindings import (
    binding_map,
    build_concrete_component_bindings,
)
from pchsi.round_control.execution_plan import (
    build_component_execution_plans,
)
from pchsi.round_control.lifecycle import (
    RoundLifecycleV1,
    RoundStageV1,
)
from pchsi.round_control.round_manifest import (
    CleanRoundDataPlaneV1,
    freeze_generic_round_manifest,
)
from pchsi.round_control.role_authority import (
    AuthorityPhaseV1,
)


def test_round_manifest_is_train_only_and_execution_closed() -> None:
    lifecycle = RoundLifecycleV1.new(
        round_id="clean-r001",
        parent_policy_id="pi-clean-0",
    )
    data_plane = CleanRoundDataPlaneV1(
        train_update_manifest_sha256="1" * 64,
        train_select_manifest_sha256="2" * 64,
        train_audit_manifest_sha256="3" * 64,
    )
    manifest = freeze_generic_round_manifest(
        round_id="clean-r001",
        parent_policy_id="pi-clean-0",
        parent_policy_artifact_sha256="4" * 64,
        authority_phase=(
            AuthorityPhaseV1.HUMAN_PRIMARY_STRONG_SHADOW
        ),
        data_plane=data_plane,
        concrete_binding_registry_sha256="5" * 64,
        lifecycle_sha256=lifecycle.lifecycle_sha256,
    )
    assert manifest.benchmark_feedback_authorized is False
    assert manifest.scientific_execution_authorized is False
    assert manifest.trace_capture_required is True


def test_execution_plan_routes_adaptive_work_to_train_update() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    bindings = binding_map(
        build_concrete_component_bindings(repo_root)
    )
    lifecycle = RoundLifecycleV1.new(
        round_id="clean-r001",
        parent_policy_id="pi-clean-0",
    ).advance(
        RoundStageV1.EVIDENCE_READY,
        evidence_sha256="a" * 64,
    )

    plans = build_component_execution_plans(
        lifecycle=lifecycle,
        bindings=bindings,
    )

    assert {
        plan.component_id
        for plan in plans
    } == {
        "HIERARCHICAL_ANALYZER",
        "PERSISTENT_FAILURE_EXPERIENCE",
    }
    assert all(
        plan.train_pool == "TRAIN_UPDATE"
        for plan in plans
    )
    assert all(
        plan.scientific_execution_authorized is False
        for plan in plans
    )


def test_internal_evaluation_uses_train_select_only() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    bindings = binding_map(
        build_concrete_component_bindings(repo_root)
    )
    lifecycle = RoundLifecycleV1.new(
        round_id="clean-r001",
        parent_policy_id="pi-clean-0",
    )
    for stage in (
        RoundStageV1.EVIDENCE_READY,
        RoundStageV1.ANALYSIS_READY,
        RoundStageV1.PRE_PLAN_FROZEN,
        RoundStageV1.EXPERIMENTS_COMPLETED,
        RoundStageV1.POST_PLAN_FROZEN,
        RoundStageV1.TRAINING_DATA_READY,
        RoundStageV1.TRAINING_COMPLETED,
    ):
        lifecycle = lifecycle.advance(
            stage,
            evidence_sha256="b" * 64,
        )

    plans = build_component_execution_plans(
        lifecycle=lifecycle,
        bindings=bindings,
    )

    assert {
        plan.component_id
        for plan in plans
    } == {
        "SELECT_EVALUATOR",
        "GENERIC_SELECT_POLICY_BINDING",
    }
    assert all(
        plan.train_pool == "TRAIN_SELECT"
        for plan in plans
    )
    assert all(
        plan.consumer
        == CleanConsumerV1.PROMOTION_GATE.value
        for plan in plans
    )


def test_execution_plan_covers_complete_orchestrator_route() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    bindings = binding_map(
        build_concrete_component_bindings(repo_root)
    )

    lifecycle = RoundLifecycleV1.new(
        round_id="clean-r001",
        parent_policy_id="pi-clean-0",
    )

    transitions = (
        RoundStageV1.EVIDENCE_READY,
        RoundStageV1.ANALYSIS_READY,
        RoundStageV1.PRE_PLAN_FROZEN,
        RoundStageV1.EXPERIMENTS_COMPLETED,
        RoundStageV1.POST_PLAN_FROZEN,
        RoundStageV1.TRAINING_DATA_READY,
        RoundStageV1.TRAINING_COMPLETED,
        RoundStageV1.INTERNAL_EVALUATION_COMPLETED,
        RoundStageV1.PROMOTED,
        RoundStageV1.ROUND_CLOSED,
    )

    for next_stage in transitions:
        plans = build_component_execution_plans(
            lifecycle=lifecycle,
            bindings=bindings,
        )
        assert all(
            plan.scientific_execution_authorized is False
            for plan in plans
        )
        lifecycle = lifecycle.advance(
            next_stage,
            evidence_sha256="c" * 64,
        )

    assert build_component_execution_plans(
        lifecycle=lifecycle,
        bindings=bindings,
    ) == ()

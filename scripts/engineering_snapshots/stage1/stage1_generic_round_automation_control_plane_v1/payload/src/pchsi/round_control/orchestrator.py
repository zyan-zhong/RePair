from __future__ import annotations

from dataclasses import dataclass

from .lifecycle import RoundLifecycleV1, RoundStageV1


@dataclass(frozen=True)
class NextActionV1:
    current_stage: RoundStageV1
    component_ids: tuple[str, ...]
    expected_output_stage: RoundStageV1 | None
    model_execution_authorized: bool
    environment_execution_authorized: bool
    training_execution_authorized: bool


_ROUTING: dict[RoundStageV1, tuple[tuple[str, ...], RoundStageV1 | None]] = {
    RoundStageV1.ROUND_CREATED: (
        ("EVIDENCE_PACKAGE",),
        RoundStageV1.EVIDENCE_READY,
    ),
    RoundStageV1.EVIDENCE_READY: (
        ("HIERARCHICAL_ANALYZER", "PERSISTENT_FAILURE_EXPERIENCE"),
        RoundStageV1.ANALYSIS_READY,
    ),
    RoundStageV1.ANALYSIS_READY: (
        ("RESEARCH_PLANNER_PRE_POST",),
        RoundStageV1.PRE_PLAN_FROZEN,
    ),
    RoundStageV1.PRE_PLAN_FROZEN: (
        ("SAME_STATE_F0F1",),
        RoundStageV1.EXPERIMENTS_COMPLETED,
    ),
    RoundStageV1.EXPERIMENTS_COMPLETED: (
        ("RESEARCH_PLANNER_PRE_POST",),
        RoundStageV1.POST_PLAN_FROZEN,
    ),
    RoundStageV1.POST_PLAN_FROZEN: (
        ("TRAINING_DATA_PLAN", "DETERMINISTIC_DATA_BUILDER"),
        RoundStageV1.TRAINING_DATA_READY,
    ),
    RoundStageV1.TRAINING_DATA_READY: (
        ("SCHEMA_AWARE_RENDERER", "GENERIC_TRAINING_STAGE_V2_1"),
        RoundStageV1.TRAINING_COMPLETED,
    ),
    RoundStageV1.TRAINING_COMPLETED: (
        ("SELECT_EVALUATOR", "GENERIC_SELECT_POLICY_BINDING"),
        RoundStageV1.INTERNAL_EVALUATION_COMPLETED,
    ),
    RoundStageV1.INTERNAL_EVALUATION_COMPLETED: (
        ("PROMOTION_ROLLBACK_CONTRACTS",),
        None,
    ),
    RoundStageV1.PROMOTED: (
        ("AUTOMATIC_ROLLBACK_AND_NEXT_ROUND_CREATION",),
        RoundStageV1.ROUND_CLOSED,
    ),
    RoundStageV1.ROLLED_BACK: (
        ("AUTOMATIC_ROLLBACK_AND_NEXT_ROUND_CREATION",),
        RoundStageV1.ROUND_CLOSED,
    ),
    RoundStageV1.ROUND_CLOSED: ((), None),
}


def next_action_for(state: RoundLifecycleV1) -> NextActionV1:
    if not isinstance(state, RoundLifecycleV1):
        raise TypeError("state must be RoundLifecycleV1")
    components, next_stage = _ROUTING[state.current_stage]
    return NextActionV1(
        current_stage=state.current_stage,
        component_ids=components,
        expected_output_stage=next_stage,
        model_execution_authorized=False,
        environment_execution_authorized=False,
        training_execution_authorized=False,
    )

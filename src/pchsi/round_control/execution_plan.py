from __future__ import annotations

from dataclasses import dataclass

from .clean_data_gate import (
    CleanConsumerV1,
    CleanSplitV1,
    TrainPoolV1,
    authorize_clean_access,
)
from .concrete_bindings import ConcreteComponentBindingV1
from .lifecycle import RoundLifecycleV1
from .orchestrator import next_action_for


_COMPONENT_ACCESS: dict[
    str,
    tuple[
        CleanSplitV1,
        TrainPoolV1,
        CleanConsumerV1,
    ],
] = {
    "EVIDENCE_PACKAGE": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_UPDATE,
        CleanConsumerV1.EVIDENCE_PACKAGE,
    ),
    "HIERARCHICAL_ANALYZER": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_UPDATE,
        CleanConsumerV1.HIERARCHICAL_ANALYZER,
    ),
    "PERSISTENT_FAILURE_EXPERIENCE": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_UPDATE,
        CleanConsumerV1.FAILURE_MEMORY,
    ),
    "RESEARCH_PLANNER_PRE_POST": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_UPDATE,
        CleanConsumerV1.RESEARCH_PLANNER,
    ),
    "SAME_STATE_F0F1": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_UPDATE,
        CleanConsumerV1.SAME_STATE_F0F1,
    ),
    "TRAINING_DATA_PLAN": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_UPDATE,
        CleanConsumerV1.POLICY_TRAINING,
    ),
    "DETERMINISTIC_DATA_BUILDER": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_UPDATE,
        CleanConsumerV1.POLICY_TRAINING,
    ),
    "SCHEMA_AWARE_RENDERER": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_UPDATE,
        CleanConsumerV1.POLICY_TRAINING,
    ),
    "GENERIC_TRAINING_STAGE_V2_1": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_UPDATE,
        CleanConsumerV1.POLICY_TRAINING,
    ),
    "SELECT_EVALUATOR": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_SELECT,
        CleanConsumerV1.PROMOTION_GATE,
    ),
    "GENERIC_SELECT_POLICY_BINDING": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_SELECT,
        CleanConsumerV1.PROMOTION_GATE,
    ),
    "PROMOTION_ROLLBACK_CONTRACTS": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_SELECT,
        CleanConsumerV1.PROMOTION_GATE,
    ),
    "AUTOMATIC_ROLLBACK_AND_NEXT_ROUND_CREATION": (
        CleanSplitV1.ALFWORLD_TRAIN,
        TrainPoolV1.TRAIN_SELECT,
        CleanConsumerV1.PROMOTION_GATE,
    ),
}


@dataclass(frozen=True)
class ComponentExecutionPlanV1:
    round_id: str
    lifecycle_stage: str
    component_id: str
    binding_sha256: str
    split: str
    train_pool: str
    consumer: str
    scientific_execution_authorized: bool


def build_component_execution_plans(
    *,
    lifecycle: RoundLifecycleV1,
    bindings: dict[str, ConcreteComponentBindingV1],
) -> tuple[ComponentExecutionPlanV1, ...]:
    action = next_action_for(lifecycle)
    plans: list[ComponentExecutionPlanV1] = []

    for component_id in action.component_ids:
        if component_id not in bindings:
            raise ValueError(f"missing concrete binding for {component_id}")
        if component_id not in _COMPONENT_ACCESS:
            raise ValueError(f"missing clean-data access rule for {component_id}")
        split, train_pool, consumer = _COMPONENT_ACCESS[component_id]
        authorize_clean_access(
            split=split,
            train_pool=train_pool,
            consumer=consumer,
        )
        binding = bindings[component_id]
        if binding.scientific_execution_authorized:
            raise ValueError("Stage 1 binding registry must not authorize execution")
        plans.append(
            ComponentExecutionPlanV1(
                round_id=lifecycle.round_id,
                lifecycle_stage=lifecycle.current_stage.value,
                component_id=component_id,
                binding_sha256=binding.binding_sha256,
                split=split.value,
                train_pool=train_pool.value,
                consumer=consumer.value,
                scientific_execution_authorized=False,
            )
        )
    return tuple(plans)

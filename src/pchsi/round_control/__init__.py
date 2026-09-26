"""Generic clean-round control-plane contracts.

This package coordinates existing project components without reimplementing
their scientific semantics or executing models, environments, or training.
"""

from .benchmark_sealing import BenchmarkResultSealV1, BenchmarkSplitV1
from .clean_data_gate import (
    CleanAccessGrantV1,
    CleanConsumerV1,
    CleanSplitV1,
    TrainPoolV1,
    authorize_clean_access,
)
from .lifecycle import RoundLifecycleV1, RoundStageV1
from .orchestrator import NextActionV1, next_action_for
from .promotion import PromotionDecisionV1, freeze_promotion_decision
from .role_authority import AuthorityPhaseV1, ResearchRoleV1, resolve_authority_plan
from .trace_handoff import RoundTraceLedgerV1, RoleTraceRecordV1

__all__ = [
    "AuthorityPhaseV1",
    "BenchmarkResultSealV1",
    "BenchmarkSplitV1",
    "CleanAccessGrantV1",
    "CleanConsumerV1",
    "CleanSplitV1",
    "NextActionV1",
    "PromotionDecisionV1",
    "ResearchRoleV1",
    "RoleTraceRecordV1",
    "RoundLifecycleV1",
    "RoundStageV1",
    "RoundTraceLedgerV1",
    "TrainPoolV1",
    "authorize_clean_access",
    "freeze_promotion_decision",
    "next_action_for",
    "resolve_authority_plan",
]

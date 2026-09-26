"""Human-bootstrap, strong-teacher, and local-distillation research intelligence."""

from .paradigm import load_research_planner_paradigm, render_human_pre_worksheet
from .records import (
    finalize_human_post,
    freeze_human_pre,
    freeze_human_post,
    freeze_field_adjudication,
)
from .visibility import build_strong_pre_projection, build_strong_post_projection
from .demonstrations import build_demonstration_pack
from .distillation import build_local_role_supervision_dataset
from .takeover import evaluate_takeover_gate

__all__ = [
    "load_research_planner_paradigm",
    "render_human_pre_worksheet",
    "finalize_human_post",
    "freeze_human_pre",
    "freeze_human_post",
    "freeze_field_adjudication",
    "build_strong_pre_projection",
    "build_strong_post_projection",
    "build_demonstration_pack",
    "build_local_role_supervision_dataset",
    "evaluate_takeover_gate",
]


# Research Planner Reference Round V2 exports
from .repair_portfolio import (
    ResearchRepairPortfolioV1,
    ResearchRepairProgramV1,
    ResearchRepairCandidateV1,
)
from .benchmark_registry import (
    BenchmarkLineageRegistryV1,
    BenchmarkEntryV1,
    ProtocolFingerprintV1,
)
from .role_neutral import (
    ResearcherPreDecisionV1,
    ResearcherPostInterpretationV1,
    UnifiedQwenRoleTargetV1,
    AutonomyAttestationV1,
)


# Shared benchmark protocol V2 exports
from .benchmark_registry import (
    SharedEvaluationProtocolV1,
    ModelExecutionProfileV1,
)

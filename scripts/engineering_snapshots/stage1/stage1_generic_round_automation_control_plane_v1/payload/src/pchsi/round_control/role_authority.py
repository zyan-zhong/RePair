from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pchsi.research_intelligence.role_neutral import ResearcherRoleModeV1


class AuthorityPhaseV1(str, Enum):
    HUMAN_PRIMARY_STRONG_SHADOW = "HUMAN_PRIMARY_STRONG_SHADOW"
    STRONG_PRIMARY_LOCAL_SHADOW = "STRONG_PRIMARY_LOCAL_SHADOW"
    LOCAL_PRIMARY_STRONG_AUDIT = "LOCAL_PRIMARY_STRONG_AUDIT"


class ResearchRoleV1(str, Enum):
    ANALYZER = "ANALYZER"
    RESEARCH_PLANNER_PRE = "RESEARCH_PLANNER_PRE"
    RESEARCH_PLANNER_POST = "RESEARCH_PLANNER_POST"


@dataclass(frozen=True)
class AuthorityPlanV1:
    phase: AuthorityPhaseV1
    primary_by_role: dict[ResearchRoleV1, str]
    shadow_by_role: dict[ResearchRoleV1, tuple[str, ...]]
    auditor_by_role: dict[ResearchRoleV1, tuple[str, ...]]
    role_modes: dict[str, ResearcherRoleModeV1]
    strong_trace_capture_required: bool
    local_trace_capture_required: bool

    def primary_actor(self, role: ResearchRoleV1) -> str:
        return self.primary_by_role[role]

    def shadow_actors(self, role: ResearchRoleV1) -> tuple[str, ...]:
        return self.shadow_by_role.get(role, ())


def _all_roles(actor: str) -> dict[ResearchRoleV1, str]:
    return {role: actor for role in ResearchRoleV1}


def resolve_authority_plan(
    *,
    phase: AuthorityPhaseV1,
    takeover_evaluation: dict[str, object] | None,
) -> AuthorityPlanV1:
    if phase is AuthorityPhaseV1.HUMAN_PRIMARY_STRONG_SHADOW:
        return AuthorityPlanV1(
            phase=phase,
            primary_by_role=_all_roles("HUMAN"),
            shadow_by_role={role: ("STRONG",) for role in ResearchRoleV1},
            auditor_by_role={role: () for role in ResearchRoleV1},
            role_modes={
                "HUMAN": ResearcherRoleModeV1.HUMAN_REFERENCE,
                "STRONG": ResearcherRoleModeV1.STRONG_API_SHADOW,
            },
            strong_trace_capture_required=True,
            local_trace_capture_required=False,
        )

    if takeover_evaluation is None:
        raise ValueError("takeover evaluation is required for non-human primary")

    if takeover_evaluation.get("schema_id") != (
        "RESEARCH_PLANNER_TAKEOVER_EVALUATION_V1"
    ):
        raise ValueError("unexpected takeover evaluation schema")

    if phase is AuthorityPhaseV1.STRONG_PRIMARY_LOCAL_SHADOW:
        if takeover_evaluation.get(
            "strong_research_planner_primary_eligible"
        ) is not True:
            raise ValueError("strong primary is not takeover-eligible")
        if takeover_evaluation.get(
            "local_training_and_shadow_eligible"
        ) is not True:
            raise ValueError("local shadow is not takeover-eligible")
        return AuthorityPlanV1(
            phase=phase,
            primary_by_role=_all_roles("STRONG"),
            shadow_by_role={role: ("LOCAL",) for role in ResearchRoleV1},
            auditor_by_role={role: ("HUMAN",) for role in ResearchRoleV1},
            role_modes={
                "STRONG": ResearcherRoleModeV1.STRONG_API_PRIMARY,
                "LOCAL": ResearcherRoleModeV1.LOCAL_SHADOW,
            },
            strong_trace_capture_required=True,
            local_trace_capture_required=True,
        )

    if phase is AuthorityPhaseV1.LOCAL_PRIMARY_STRONG_AUDIT:
        if takeover_evaluation.get(
            "local_research_planner_primary_eligible"
        ) is not True:
            raise ValueError("local primary is not takeover-eligible")
        return AuthorityPlanV1(
            phase=phase,
            primary_by_role=_all_roles("LOCAL"),
            shadow_by_role={role: () for role in ResearchRoleV1},
            auditor_by_role={role: ("STRONG", "HUMAN") for role in ResearchRoleV1},
            role_modes={
                "LOCAL": ResearcherRoleModeV1.LOCAL_PRIMARY,
                "STRONG": ResearcherRoleModeV1.STRONG_API_SHADOW,
            },
            strong_trace_capture_required=True,
            local_trace_capture_required=True,
        )

    raise ValueError(f"unsupported authority phase: {phase}")

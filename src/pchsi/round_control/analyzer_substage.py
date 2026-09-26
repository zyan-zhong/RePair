"""Analyzer-internal substage handoff over the existing round lifecycle.

This module does not create a second round orchestrator. The outer lifecycle
remains `RoundLifecycleV1`; this only decomposes the existing
HIERARCHICAL_ANALYZER component into receipt-driven substages.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .common import hashed_payload, require_sha256, require_text
from .role_authority import (
    AuthorityPhaseV1,
    ResearchRoleV1,
    resolve_authority_plan,
)


class AnalyzerSubstageV1(str, Enum):
    LOCAL_A0_A1 = "LOCAL_A0_A1"
    DETERMINISTIC_GROUPING = "DETERMINISTIC_GROUPING"
    GROUP_A2_A3 = "GROUP_A2_A3"
    COMPONENT_C = "COMPONENT_C"
    DETERMINISTIC_P = "DETERMINISTIC_P"
    CROSSCHECK_X = "CROSSCHECK_X"
    ANALYZER_CLOSED = "ANALYZER_CLOSED"


_ALLOWED_NEXT = {
    AnalyzerSubstageV1.LOCAL_A0_A1:
        AnalyzerSubstageV1.DETERMINISTIC_GROUPING,
    AnalyzerSubstageV1.DETERMINISTIC_GROUPING:
        AnalyzerSubstageV1.GROUP_A2_A3,
    AnalyzerSubstageV1.GROUP_A2_A3:
        AnalyzerSubstageV1.COMPONENT_C,
    AnalyzerSubstageV1.COMPONENT_C:
        AnalyzerSubstageV1.DETERMINISTIC_P,
    AnalyzerSubstageV1.DETERMINISTIC_P:
        AnalyzerSubstageV1.CROSSCHECK_X,
    AnalyzerSubstageV1.CROSSCHECK_X:
        AnalyzerSubstageV1.ANALYZER_CLOSED,
    AnalyzerSubstageV1.ANALYZER_CLOSED:
        None,
}


_STAGE_IDS = {
    AnalyzerSubstageV1.LOCAL_A0_A1: ("L-A0", "L-A1"),
    AnalyzerSubstageV1.DETERMINISTIC_GROUPING: (),
    AnalyzerSubstageV1.GROUP_A2_A3: ("G-A2", "G-A3"),
    AnalyzerSubstageV1.COMPONENT_C: ("C",),
    AnalyzerSubstageV1.DETERMINISTIC_P: ("P",),
    AnalyzerSubstageV1.CROSSCHECK_X: ("X",),
    AnalyzerSubstageV1.ANALYZER_CLOSED: (),
}


@dataclass(frozen=True)
class AnalyzerPipelineStateV1:
    round_id: str
    authority_phase: AuthorityPhaseV1
    current_substage: AnalyzerSubstageV1
    transition_index: int
    last_receipt_sha256: str
    pipeline_sha256: str

    @classmethod
    def from_frozen_receipt(
        cls,
        *,
        round_id: str,
        authority_phase: AuthorityPhaseV1,
        current_substage: AnalyzerSubstageV1,
        receipt_sha256: str,
        transition_index: int,
    ) -> "AnalyzerPipelineStateV1":
        require_text("round_id", round_id)
        require_sha256("receipt_sha256", receipt_sha256)
        if type(transition_index) is not int or transition_index < 0:
            raise ValueError("transition_index must be non-negative int")
        payload = {
            "schema_id": "ANALYZER_PIPELINE_STATE_V1",
            "schema_version": 1,
            "round_id": round_id,
            "authority_phase": authority_phase.value,
            "current_substage": current_substage.value,
            "transition_index": transition_index,
            "last_receipt_sha256": receipt_sha256,
        }
        hashed = hashed_payload(
            domain="ANALYZER_PIPELINE_STATE_V1",
            hash_field="pipeline_sha256",
            payload=payload,
        )
        return cls(
            round_id=round_id,
            authority_phase=authority_phase,
            current_substage=current_substage,
            transition_index=transition_index,
            last_receipt_sha256=receipt_sha256,
            pipeline_sha256=hashed["pipeline_sha256"],
        )

    def advance(
        self,
        *,
        next_substage: AnalyzerSubstageV1,
        receipt_sha256: str,
    ) -> "AnalyzerPipelineStateV1":
        require_sha256("receipt_sha256", receipt_sha256)
        expected = _ALLOWED_NEXT[self.current_substage]
        if next_substage is not expected:
            raise ValueError(
                "invalid Analyzer substage transition: "
                f"{self.current_substage.value} -> {next_substage.value}"
            )
        return self.from_frozen_receipt(
            round_id=self.round_id,
            authority_phase=self.authority_phase,
            current_substage=next_substage,
            receipt_sha256=receipt_sha256,
            transition_index=self.transition_index + 1,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "ANALYZER_PIPELINE_STATE_V1",
            "schema_version": 1,
            "round_id": self.round_id,
            "authority_phase": self.authority_phase.value,
            "current_substage": self.current_substage.value,
            "transition_index": self.transition_index,
            "last_receipt_sha256": self.last_receipt_sha256,
            "pipeline_sha256": self.pipeline_sha256,
        }


@dataclass(frozen=True)
class AnalyzerSubstageActionV1:
    substage: AnalyzerSubstageV1
    stage_ids: tuple[str, ...]
    deterministic: bool
    primary_actor: str | None
    shadow_actors: tuple[str, ...]
    auditor_actors: tuple[str, ...]
    routine_human_scientific_action_required: bool
    automatic_handoff_after_terminal_receipt: bool


def next_analyzer_substage_action(
    *,
    state: AnalyzerPipelineStateV1,
    takeover_evaluation: dict[str, object] | None,
) -> AnalyzerSubstageActionV1:
    stages = _STAGE_IDS[state.current_substage]
    deterministic = state.current_substage in {
        AnalyzerSubstageV1.DETERMINISTIC_GROUPING,
        AnalyzerSubstageV1.DETERMINISTIC_P,
        AnalyzerSubstageV1.ANALYZER_CLOSED,
    }

    if deterministic:
        return AnalyzerSubstageActionV1(
            substage=state.current_substage,
            stage_ids=stages,
            deterministic=True,
            primary_actor=None,
            shadow_actors=(),
            auditor_actors=(),
            routine_human_scientific_action_required=False,
            automatic_handoff_after_terminal_receipt=True,
        )

    plan = resolve_authority_plan(
        phase=state.authority_phase,
        takeover_evaluation=takeover_evaluation,
    )
    primary = plan.primary_actor(ResearchRoleV1.ANALYZER)
    shadows = plan.shadow_actors(ResearchRoleV1.ANALYZER)
    auditors = plan.auditor_by_role.get(ResearchRoleV1.ANALYZER, ())

    human_primary = (
        state.authority_phase
        is AuthorityPhaseV1.HUMAN_PRIMARY_STRONG_SHADOW
    )
    return AnalyzerSubstageActionV1(
        substage=state.current_substage,
        stage_ids=stages,
        deterministic=False,
        primary_actor=primary,
        shadow_actors=shadows,
        auditor_actors=auditors,
        routine_human_scientific_action_required=human_primary,
        automatic_handoff_after_terminal_receipt=not human_primary,
    )


def future_nonhuman_phases_are_automatic(
    takeover_evaluation: dict[str, object],
) -> None:
    for phase in (
        AuthorityPhaseV1.STRONG_PRIMARY_LOCAL_SHADOW,
        AuthorityPhaseV1.LOCAL_PRIMARY_STRONG_AUDIT,
    ):
        for substage in (
            AnalyzerSubstageV1.LOCAL_A0_A1,
            AnalyzerSubstageV1.GROUP_A2_A3,
            AnalyzerSubstageV1.COMPONENT_C,
            AnalyzerSubstageV1.CROSSCHECK_X,
        ):
            state = AnalyzerPipelineStateV1.from_frozen_receipt(
                round_id="AUTOMATION-CHECK",
                authority_phase=phase,
                current_substage=substage,
                receipt_sha256="0" * 64,
                transition_index=0,
            )
            action = next_analyzer_substage_action(
                state=state,
                takeover_evaluation=takeover_evaluation,
            )
            if action.routine_human_scientific_action_required:
                raise ValueError(
                    "future non-human primary phase unexpectedly "
                    "requires routine Human scientific action"
                )
            if not action.automatic_handoff_after_terminal_receipt:
                raise ValueError(
                    "future non-human primary phase does not auto-handoff"
                )

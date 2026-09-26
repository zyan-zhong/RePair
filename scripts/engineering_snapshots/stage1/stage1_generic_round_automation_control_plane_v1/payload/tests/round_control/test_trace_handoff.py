from pchsi.round_control.trace_handoff import (
    ActorV1,
    AuthorityModeV1,
    ResearchRoleV1,
    RoleTraceRecordV1,
    RoundTraceLedgerV1,
)


def _trace(role, actor, mode, suffix):
    return RoleTraceRecordV1(
        round_id="clean-r001",
        role=role,
        actor=actor,
        authority_mode=mode,
        input_artifact_sha256=("a" + suffix) * 32,
        output_artifact_sha256=("b" + suffix) * 32,
        access_class="TRAIN_REFERENCE_ROUND",
        structured_output_only=True,
        provider_reasoning_artifact_required=False,
    )


def test_strong_outputs_are_retained_for_localization() -> None:
    ledger = RoundTraceLedgerV1(
        round_id="clean-r001",
        records=(
            _trace(
                ResearchRoleV1.RESEARCH_PLANNER_PRE,
                ActorV1.HUMAN,
                AuthorityModeV1.PRIMARY,
                "1",
            ),
            _trace(
                ResearchRoleV1.RESEARCH_PLANNER_PRE,
                ActorV1.STRONG,
                AuthorityModeV1.SHADOW,
                "2",
            ),
            _trace(
                ResearchRoleV1.RESEARCH_PLANNER_POST,
                ActorV1.HUMAN,
                AuthorityModeV1.PRIMARY,
                "3",
            ),
            _trace(
                ResearchRoleV1.RESEARCH_PLANNER_POST,
                ActorV1.STRONG,
                AuthorityModeV1.SHADOW,
                "4",
            ),
        ),
    )
    ledger.validate(
        require_strong_pre=True,
        require_strong_post=True,
    )
    assert len(ledger.localization_teacher_records()) == 2

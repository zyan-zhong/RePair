from __future__ import annotations

from pchsi.evaluation.budget import (
    BudgetState,
)
from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
)
from pchsi.memory.memory_runtime_bridge import (
    prepare_memory_policy_attempt_v1,
    process_memory_policy_generation_v1,
)


def _prepare(
    *,
    memory_payloads=(),
    representation_class="M0",
    lineage=None,
    version=None,
    artifact_sha=None,
    packed_token_count=0,
    policy_menu=("look", "open cabinet 1"),
    harness_menu=("look", "open cabinet 1"),
    env_menu=("look", "open cabinet 1"),
):
    return prepare_memory_policy_attempt_v1(
        public_task_goal="goal",
        observation="observation",
        executed_transitions=(
            ExecutedTransition(
                action="go to desk 1",
                resulting_observation="at desk",
            ),
        ),
        memory_payloads=memory_payloads,
        policy_visible_commands=policy_menu,
        harness_visible_commands=harness_menu,
        environment_commands=env_menu,
        interface_feedback=None,
        budget_state=BudgetState(),
        snapshot_sha256="1" * 64,
        token_budget_contract_sha256="2" * 64,
        retrieval_mode="DIRECT_FIXED_RECORD_NO_RETRIEVAL",
        branch_role="M0" if representation_class == "M0" else "M3",
        representation_class=representation_class,
        memory_lineage_id=lineage,
        record_version=version,
        projection_artifact_sha256=artifact_sha,
        packed_token_count=packed_token_count,
    )


def test_b4_bridge_uses_runtime_core_without_action_repair():
    prepared = _prepare(
        memory_payloads=(
            {"failure_cue": "visible cue"},
        ),
        representation_class="FM2",
        lineage="3" * 64,
        version=1,
        artifact_sha="4" * 64,
        packed_token_count=20,
    )

    assert prepared.precondition.should_call_policy is True
    assert prepared.prompt is not None
    assert prepared.exposure is not None
    assert prepared.exposure.final_prompt_sha256

    decision = process_memory_policy_generation_v1(
        raw_response='{"action":"look"}',
        visible_admissible_commands=(
            "look",
            "open cabinet 1",
        ),
        prepared=prepared,
    )
    assert decision.should_call_env is True
    assert decision.candidate_environment_action == "look"


def test_b4_offlist_action_remains_runtime_core_invalid():
    prepared = _prepare()
    decision = process_memory_policy_generation_v1(
        raw_response='{"action":"LOOK"}',
        visible_admissible_commands=(
            "look",
            "open cabinet 1",
        ),
        prepared=prepared,
    )
    assert decision.should_call_env is False
    assert decision.candidate_environment_action is None
    assert decision.attempt_outcome.value == "ACTION_NOT_ADMISSIBLE"


def test_b4_invalid_three_party_menu_stops_before_prompt():
    prepared = _prepare(
        harness_menu=("look",),
    )
    assert prepared.precondition.should_call_policy is False
    assert prepared.prompt is None
    assert prepared.exposure is None

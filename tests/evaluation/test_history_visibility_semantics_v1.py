from types import SimpleNamespace

from pchsi.evaluation.evidence_completeness import (
    validate_distillation_evidence_complete,
)
from pchsi.evaluation.evidence_visibility import (
    build_student_decision_projection,
)


def _full_history_before(call_index: int):
    return tuple(
        ("act", f"obs-{index + 1}")
        for index in range(call_index)
    )


def _build_complete_ten_call_episode():
    cell = "p4-P4-R0-PI0-t00000-s0000000017"

    calls = []
    traces = []
    transitions = []

    for index in range(10):
        observation = f"obs-{index}"
        resulting_observation = f"obs-{index + 1}"
        provider_request_id = f"provider-{index}"

        calls.append(
            SimpleNamespace(
                model_call_index=index,
                environment_step_count_before=index,
                prompt_text=f"prompt-{index}",
                public_task_goal="goal",
                observation=observation,
                admissible_commands=("act",),
                raw_response_text='{"action":"act"}',
                provider_request_id=provider_request_id,
                budget_before=(
                    ("policy_attempt_count", index),
                    ("environment_step_count", index),
                    ("protocol_failure_count", 0),
                    ("inadmissible_action_count", 0),
                    (
                        "consecutive_nonexecuted_attempt_count",
                        0,
                    ),
                ),
                executed_history=_full_history_before(index),
                interface_feedback_before=None,
                rendered_prompt_text=f"<user>prompt-{index}</user>",
            )
        )

        provenance = SimpleNamespace(
            provider_request_id=provider_request_id,
            task_access_manifest_sha256="a" * 64,
            policy_condition_manifest_sha256="b" * 64,
            condition_run_schedule_sha256="c" * 64,
            access_class="DEV_VISIBLE",
            policy_condition_id="P4-R0-PI0",
            condition_cell_id=cell,
        )

        traces.append(
            SimpleNamespace(
                model_call_index=index,
                prompt_text=f"prompt-{index}",
                public_task_goal="goal",
                observation=observation,
                admissible_commands=("act",),
                raw_model_response='{"action":"act"}',
                provenance=provenance,
                policy_attempt_count_before=index,
                policy_attempt_count_after=index + 1,
                environment_step_count_before=index,
                environment_step_count_after=index + 1,
                protocol_failure_count_before=0,
                protocol_failure_count=0,
                inadmissible_action_count_before=0,
                inadmissible_action_count=0,
                consecutive_nonexecuted_attempt_count_before=0,
                consecutive_nonexecuted_attempt_count=0,
                execution_status="executed",
                environment_step_index=index,
                submitted_environment_action="act",
                resulting_observation=resulting_observation,
                feedback_code=None,
            )
        )

        transitions.append(
            SimpleNamespace(
                environment_step_index=index,
                submitted_action="act",
                pre_action_observation=observation,
                pre_action_admissible_commands=("act",),
                resulting_observation=resulting_observation,
                resulting_admissible_commands=("act",),
            )
        )

    episode = SimpleNamespace(
        access_class="DEV_VISIBLE",
        policy_condition_id="P4-R0-PI0",
        task_access_manifest_sha256="a" * 64,
        policy_condition_manifest_sha256="b" * 64,
        condition_run_schedule_sha256="c" * 64,
        condition_cell_id=cell,
        scheduled_cell_id=cell,
        split_access_sha256="a" * 64,
        trace_count=10,
        public_transition_count=10,
        environment_call_trace_count=10,
        final_budget=SimpleNamespace(
            policy_attempt_count=10,
            environment_step_count=10,
            protocol_failure_count=0,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        ),
    )

    return episode, tuple(calls), tuple(traces), tuple(transitions)


def test_complete_evidence_accepts_full_raw_history_beyond_m0_window():
    episode, calls, traces, transitions = (
        _build_complete_ten_call_episode()
    )

    assert len(calls[-1].executed_history) == 9

    validate_distillation_evidence_complete(
        episode=episode,
        policy_calls=calls,
        action_traces=traces,
        public_transitions=transitions,
    )


def test_student_projection_exposes_only_memory_m0_last_eight():
    history = tuple(
        (f"action-{index}", f"observation-{index}")
        for index in range(10)
    )

    policy_call = SimpleNamespace(
        public_task_goal="goal",
        observation="current",
        admissible_commands=("look",),
        executed_history=history,
        interface_feedback_before=None,
        prompt_text="prompt",
        rendered_prompt_text="<user>prompt</user>",
    )

    projection = build_student_decision_projection(policy_call)

    assert projection["executed_history"] == [
        {
            "action": action,
            "resulting_observation": observation,
        }
        for action, observation in history[-8:]
    ]

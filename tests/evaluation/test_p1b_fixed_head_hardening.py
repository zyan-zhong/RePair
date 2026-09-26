from importlib.util import (
    module_from_spec,
    spec_from_file_location,
)
from pathlib import Path
from types import SimpleNamespace

import pytest

from pchsi.evaluation.condition_execution_binding import (
    ConditionBoundEpisodeCellV1,
)
from pchsi.evaluation.distillation_access import (
    DistillationAccessClass,
)
import pchsi.evaluation.evidence_completeness as completeness
from pchsi.evaluation.evidence_visibility import (
    build_dev_teacher_projection,
)


def _synthetic_complete():
    cell = "p4-P4-R0-PI0-t00000-s0000000017"
    provenance = SimpleNamespace(
        provider_request_id="provider-1",
        task_access_manifest_sha256="a" * 64,
        policy_condition_manifest_sha256="b" * 64,
        condition_run_schedule_sha256="c" * 64,
        access_class="DEV_VISIBLE",
        policy_condition_id="P4-R0-PI0",
        condition_cell_id=cell,
    )
    call = SimpleNamespace(
        model_call_index=0,
        environment_step_count_before=0,
        prompt_text="prompt",
        public_task_goal="goal",
        observation="before",
        admissible_commands=("look",),
        raw_response_text='{"action":"look"}',
        provider_request_id="provider-1",
        budget_before=(
            ("policy_attempt_count", 0),
            ("environment_step_count", 0),
            ("protocol_failure_count", 0),
            ("inadmissible_action_count", 0),
            (
                "consecutive_nonexecuted_attempt_count",
                0,
            ),
        ),
        executed_history=(),
        interface_feedback_before=None,
        rendered_prompt_text="<user>prompt</user>",
    )
    trace = SimpleNamespace(
        model_call_index=0,
        prompt_text="prompt",
        public_task_goal="goal",
        observation="before",
        admissible_commands=("look",),
        raw_model_response='{"action":"look"}',
        provenance=provenance,
        policy_attempt_count_before=0,
        policy_attempt_count_after=1,
        environment_step_count_before=0,
        environment_step_count_after=1,
        protocol_failure_count_before=0,
        protocol_failure_count=0,
        inadmissible_action_count_before=0,
        inadmissible_action_count=0,
        consecutive_nonexecuted_attempt_count_before=0,
        consecutive_nonexecuted_attempt_count=0,
        execution_status=SimpleNamespace(value="executed"),
        environment_step_index=0,
        submitted_environment_action="look",
        resulting_observation="after",
        feedback_code=None,
    )
    transition = SimpleNamespace(
        environment_step_index=0,
        submitted_action="look",
        pre_action_observation="before",
        pre_action_admissible_commands=("look",),
        resulting_observation="after",
        resulting_admissible_commands=("inventory",),
    )
    final_budget = SimpleNamespace(
        policy_attempt_count=1,
        environment_step_count=1,
        protocol_failure_count=0,
        inadmissible_action_count=0,
        consecutive_nonexecuted_attempt_count=0,
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
        trace_count=1,
        public_transition_count=1,
        environment_call_trace_count=1,
        final_budget=final_budget,
    )
    return episode, (call,), (trace,), (transition,)


def test_code_inventory_cannot_self_certify_with_flag():
    with pytest.raises(TypeError):
        completeness.audit_current_evidence_contract(
            upgraded=True
        )


def test_teacher_projection_rejects_spoofed_dev_argument():
    episode = {
        "access_class": "SELECT_SUMMARY_ONLY",
        "policy_condition_id": "P4-R0-PI0",
        "task_access_manifest_sha256": "a" * 64,
        "condition_cell_id": "select-cell",
    }
    with pytest.raises(PermissionError):
        build_dev_teacher_projection(
            access_class=DistillationAccessClass.DEV_VISIBLE,
            episode=episode,
            policy_calls=(),
            action_traces=(),
            public_transitions=(),
        )


def test_condition_bound_cell_rejects_noncanonical_id():
    with pytest.raises(ValueError):
        ConditionBoundEpisodeCellV1(
            scheduled_cell_id="forged-cell",
            task_index=0,
            task_id="task-0",
            seed=17,
            policy_condition_id="P4-R0-PI0",
            access_class=DistillationAccessClass.DEV_VISIBLE,
        )


def test_complete_episode_report_is_data_driven():
    builder = getattr(
        completeness,
        "build_evidence_completeness_report",
        None,
    )
    assert callable(builder)

    episode, calls, traces, transitions = (
        _synthetic_complete()
    )
    report = builder(
        episode=episode,
        policy_calls=calls,
        action_traces=traces,
        public_transitions=transitions,
    )
    assert report.critical_missing == ()


def test_orphan_transition_is_rejected():
    episode, calls, traces, transitions = (
        _synthetic_complete()
    )
    orphan = SimpleNamespace(
        environment_step_index=1,
        submitted_action="inventory",
        pre_action_observation="after",
        pre_action_admissible_commands=("inventory",),
        resulting_observation="after-2",
        resulting_admissible_commands=("look",),
    )
    episode.public_transition_count = 2

    with pytest.raises(
        ValueError,
        match=(
            completeness
            .INELIGIBLE_DISTILLATION_EVIDENCE_INCOMPLETE
        ),
    ):
        completeness.validate_distillation_evidence_complete(
            episode=episode,
            policy_calls=calls,
            action_traces=traces,
            public_transitions=(
                *transitions,
                orphan,
            ),
        )


def test_materializer_requires_frozen_manifest_identity():
    path = Path(
        "scripts/evaluation/materialize_p1b_access.py"
    )
    spec = spec_from_file_location(
        "materialize_p1b_access_hardening_test",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    validator = getattr(
        module,
        "_validate_frozen_manifest_input",
        None,
    )
    assert callable(validator)

    manifest = Path(
        "data/manifests/"
        "alfworld_strict_valid_unseen_all134_v1.jsonl"
    )
    with pytest.raises(ValueError):
        validator(
            manifest_path=manifest,
            manifest_sha256="0" * 64,
        )

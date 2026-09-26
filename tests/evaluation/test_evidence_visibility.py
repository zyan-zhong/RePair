from types import SimpleNamespace

import pytest

from pchsi.evaluation.distillation_access import (
    DistillationAccessClass,
)
from pchsi.evaluation.evidence_visibility import (
    build_dev_teacher_projection,
    build_visibility_matrix,
    validate_visibility_matrix,
)


def test_visibility_matrix_blocks_oracle_exposure():
    validate_visibility_matrix(build_visibility_matrix())


def test_teacher_projection_rejects_explicit_select():
    with pytest.raises(PermissionError):
        build_dev_teacher_projection(
            access_class=(
                DistillationAccessClass.SELECT_SUMMARY_ONLY
            ),
            episode={},
            policy_calls=(),
            action_traces=(),
            public_transitions=(),
        )


def test_teacher_projection_rejects_spoofed_dev_argument():
    episode = {
        "access_class": "SELECT_SUMMARY_ONLY",
        "policy_condition_id": "P4-R0-PI0",
        "task_access_manifest_sha256": "a" * 64,
        "policy_condition_manifest_sha256": "b" * 64,
        "condition_run_schedule_sha256": "c" * 64,
        "condition_cell_id": "select-cell",
    }

    with pytest.raises(
        PermissionError,
        match="episode is not bound to DEV_VISIBLE",
    ):
        build_dev_teacher_projection(
            access_class=DistillationAccessClass.DEV_VISIBLE,
            episode=episode,
            policy_calls=(),
            action_traces=(),
            public_transitions=(),
        )


def test_teacher_projection_accepts_bound_dev_episode():
    cell = "p4-P4-R0-PI0-t00000-s0000000017"
    episode = {
        "access_class": "DEV_VISIBLE",
        "policy_condition_id": "P4-R0-PI0",
        "task_access_manifest_sha256": "a" * 64,
        "policy_condition_manifest_sha256": "b" * 64,
        "condition_run_schedule_sha256": "c" * 64,
        "condition_cell_id": cell,
    }
    trace = SimpleNamespace(
        provenance=SimpleNamespace(
            access_class="DEV_VISIBLE",
            policy_condition_id="P4-R0-PI0",
            task_access_manifest_sha256="a" * 64,
            policy_condition_manifest_sha256="b" * 64,
            condition_run_schedule_sha256="c" * 64,
            condition_cell_id=cell,
        ),
        to_dict=lambda: {"trace": 1},
    )

    result = build_dev_teacher_projection(
        access_class=DistillationAccessClass.DEV_VISIBLE,
        episode=episode,
        policy_calls=(),
        action_traces=(trace,),
        public_transitions=(),
    )

    assert result["episode"]["access_class"] == "DEV_VISIBLE"

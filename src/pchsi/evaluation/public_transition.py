"""Non-leaking public transition evidence for accepted environment results."""

from __future__ import annotations

from .action_trace import (
    sha256_string_sequence,
    sha256_text,
)
from .alfworld_contracts import (
    MenuSnapshot,
    StepPublicState,
)
from .canonical_evidence import require_nonnegative_int
from .schema_models import PublicTransitionRecordV1


_PRE_ACTION_VISIBILITY = (
    "POLICY_VISIBLE_BEFORE_ACTION"
)
_RESULTING_VISIBILITY = (
    "POST_ACTION_PUBLIC_AUDIT_ONLY"
)


def _require_nonempty_text(
    name: str,
    value: object,
) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty")
    return value


def _validate_menu(
    name: str,
    menu: object,
) -> MenuSnapshot:
    if not isinstance(menu, MenuSnapshot):
        raise TypeError(f"{name} must be MenuSnapshot")
    expected = sha256_string_sequence(
        menu.commands
    )
    if menu.sequence_sha256 != expected:
        raise ValueError(
            f"{name}.sequence_sha256 does not match commands"
        )
    return menu


def build_public_transition(
    *,
    scheduled_cell_id: str,
    execution_attempt_id: str,
    model_call_index: int,
    environment_step_index: int,
    submitted_action: str,
    pre_observation: str,
    pre_menu: MenuSnapshot,
    result: StepPublicState,
) -> PublicTransitionRecordV1:
    cell_id = _require_nonempty_text(
        "scheduled_cell_id",
        scheduled_cell_id,
    )
    attempt_id = _require_nonempty_text(
        "execution_attempt_id",
        execution_attempt_id,
    )
    model_index = require_nonnegative_int(
        "model_call_index",
        model_call_index,
    )
    environment_index = require_nonnegative_int(
        "environment_step_index",
        environment_step_index,
    )
    action = _require_nonempty_text(
        "submitted_action",
        submitted_action,
    )
    if not isinstance(pre_observation, str):
        raise TypeError(
            "pre_observation must be str"
        )
    before_menu = _validate_menu(
        "pre_menu",
        pre_menu,
    )
    if not isinstance(result, StepPublicState):
        raise TypeError(
            "result must be StepPublicState"
        )
    after_menu = _validate_menu(
        "result.menu",
        result.menu,
    )

    return PublicTransitionRecordV1(
        schema_id="E1_PUBLIC_TRANSITION_RECORD_V1",
        schema_version=1,
        scheduled_cell_id=cell_id,
        execution_attempt_id=attempt_id,
        model_call_index=model_index,
        environment_step_index=environment_index,
        submitted_action=action,
        pre_action_observation=pre_observation,
        pre_action_observation_sha256=sha256_text(
            pre_observation
        ),
        pre_action_admissible_commands=(
            before_menu.commands
        ),
        pre_action_admissible_commands_sha256=(
            before_menu.sequence_sha256
        ),
        resulting_observation=result.observation,
        resulting_observation_sha256=sha256_text(
            result.observation
        ),
        resulting_admissible_commands=(
            after_menu.commands
        ),
        resulting_admissible_commands_sha256=(
            after_menu.sequence_sha256
        ),
        done=result.done,
        won=result.won,
        score=result.score,
        pre_action_visibility=(
            _PRE_ACTION_VISIBILITY
        ),
        resulting_visibility=(
            _RESULTING_VISIBILITY
        ),
    )

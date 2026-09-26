"""Deterministic mechanical comparison for registered comparable pairs."""
from __future__ import annotations

from pathlib import Path

from .canonical import domain_hash, write_new_json
from .types import ValidatedAttemptBundle


def _first_divergence(
    left: list[object],
    right: list[object],
) -> int | None:
    for index, (a, b) in enumerate(zip(left, right)):
        if a != b:
            return index
    if len(left) != len(right):
        return min(len(left), len(right))
    return None


def _trace_action(trace) -> object:
    return (
        trace.submitted_environment_action
        if trace.submitted_environment_action is not None
        else trace.normalized_action
        if trace.normalized_action is not None
        else trace.literal_action
    )


def extract_mechanical_paired_evidence(
    *,
    left: ValidatedAttemptBundle,
    right: ValidatedAttemptBundle,
    pair_id: str,
    pair_kind: str,
    registered_intervention_model_call_index: int | None,
    repair_registration_sha256: str | None,
) -> dict[str, object]:
    if left.task_id != right.task_id:
        raise ValueError("paired evidence requires the same task_id")
    if left.gamefile_sha256 != right.gamefile_sha256:
        raise ValueError("paired evidence requires the same gamefile")
    if left.episode.get("seed") != right.episode.get("seed"):
        raise ValueError("paired evidence requires the same continuation seed")

    left_calls = list(left.policy_calls)
    right_calls = list(right.policy_calls)
    left_traces = list(left.traces)
    right_traces = list(right.traces)
    left_transitions = list(left.transitions)
    right_transitions = list(right.transitions)

    call_identity_left = [
        (
            call.public_task_goal,
            call.observation,
            call.admissible_commands,
            call.executed_history,
            call.budget_before,
        )
        for call in left_calls
    ]
    call_identity_right = [
        (
            call.public_task_goal,
            call.observation,
            call.admissible_commands,
            call.executed_history,
            call.budget_before,
        )
        for call in right_calls
    ]

    action_left = [_trace_action(trace) for trace in left_traces]
    action_right = [_trace_action(trace) for trace in right_traces]
    executed_left = [
        transition.submitted_action for transition in left_transitions
    ]
    executed_right = [
        transition.submitted_action for transition in right_transitions
    ]
    observation_left = [
        transition.resulting_observation for transition in left_transitions
    ]
    observation_right = [
        transition.resulting_observation for transition in right_transitions
    ]
    menu_left = [
        transition.resulting_menu for transition in left_transitions
    ]
    menu_right = [
        transition.resulting_menu for transition in right_transitions
    ]
    budget_left = [trace.budget_before for trace in left_traces]
    budget_right = [trace.budget_before for trace in right_traces]

    pre_state_divergence = _first_divergence(
        call_identity_left,
        call_identity_right,
    )
    first_action_divergence = _first_divergence(
        action_left,
        action_right,
    )
    first_executed_action_divergence = _first_divergence(
        executed_left,
        executed_right,
    )
    first_observation_divergence = _first_divergence(
        observation_left,
        observation_right,
    )
    first_menu_divergence = _first_divergence(
        menu_left,
        menu_right,
    )
    first_budget_divergence = _first_divergence(
        budget_left,
        budget_right,
    )

    if pair_kind == "F0F1":
        if registered_intervention_model_call_index is None:
            raise ValueError("F0/F1 paired evidence requires intervention index")
        if repair_registration_sha256 is None:
            raise ValueError("F0/F1 paired evidence requires repair registration")
        prohibited = [
            value
            for value in (
                pre_state_divergence,
                first_action_divergence,
                first_budget_divergence,
            )
            if value is not None
            and value < registered_intervention_model_call_index
        ]
        pair_alignment_status = (
            "INVALID_DIVERGENCE_BEFORE_REGISTERED_INTERVENTION"
            if prohibited
            else "VALID_REGISTERED_INTERVENTION_ALIGNMENT"
        )
    else:
        pair_alignment_status = (
            "VALID_MATCHED_CONDITION_ALIGNMENT"
            if pre_state_divergence is None
            else "NONIDENTICAL_MATCHED_CONDITION_PREFIX"
        )

    shared_policy_calls = (
        min(len(left_calls), len(right_calls))
        if pre_state_divergence is None
        else pre_state_divergence
    )
    transition_prefix = 0
    for a, b in zip(left_transitions, right_transitions):
        if (
            a.submitted_action,
            a.pre_observation,
            a.pre_menu,
            a.resulting_observation,
            a.resulting_menu,
        ) != (
            b.submitted_action,
            b.pre_observation,
            b.pre_menu,
            b.resulting_observation,
            b.resulting_menu,
        ):
            break
        transition_prefix += 1

    artifact = {
        "schema_id": "MECHANICAL_PAIRED_EVIDENCE_V1",
        "schema_version": 1,
        "pair_id": pair_id,
        "pair_kind": pair_kind,
        "left_attempt_bundle_sha256": left.attempt_bundle_sha256,
        "right_attempt_bundle_sha256": right.attempt_bundle_sha256,
        "task_id": left.task_id,
        "gamefile_sha256": left.gamefile_sha256,
        "paired_seed": left.episode.get("seed"),
        "registered_intervention_model_call_index": (
            registered_intervention_model_call_index
        ),
        "repair_registration_sha256": repair_registration_sha256,
        "shared_prefix_policy_call_count": shared_policy_calls,
        "shared_prefix_environment_step_count": transition_prefix,
        "first_pre_state_divergence": pre_state_divergence,
        "first_action_divergence": first_action_divergence,
        "first_executed_action_divergence": (
            first_executed_action_divergence
        ),
        "first_observation_divergence": first_observation_divergence,
        "first_menu_divergence": first_menu_divergence,
        "first_budget_divergence": first_budget_divergence,
        "pair_alignment_status": pair_alignment_status,
        "authority": "DETERMINISTIC_PAIR_FACTS_ONLY",
        "outcome_authority_absent": True,
        "evidence_sha256": "0" * 64,
    }
    artifact["evidence_sha256"] = domain_hash(
        "MECHANICAL_PAIRED_EVIDENCE_V1",
        artifact,
        excluded_field="evidence_sha256",
    )
    return artifact


def extract_mechanical_paired_evidence_file(
    *,
    left: ValidatedAttemptBundle,
    right: ValidatedAttemptBundle,
    pair_id: str,
    pair_kind: str,
    registered_intervention_model_call_index: int | None,
    repair_registration_sha256: str | None,
    output_path: Path,
) -> dict[str, object]:
    artifact = extract_mechanical_paired_evidence(
        left=left,
        right=right,
        pair_id=pair_id,
        pair_kind=pair_kind,
        registered_intervention_model_call_index=(
            registered_intervention_model_call_index
        ),
        repair_registration_sha256=repair_registration_sha256,
    )
    write_new_json(output_path, artifact)
    return artifact

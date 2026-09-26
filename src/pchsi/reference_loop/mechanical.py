"""Deterministic episode-level mechanical evidence extraction."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from .alfworld_events import extract_alfworld_event_facts
from .canonical import domain_hash, write_new_json
from .types import ValidatedAttemptBundle


_NOTHING_HAPPENS = "Nothing happens."
_BUDGET_TERMINATIONS = {
    "POLICY_ATTEMPT_BUDGET_EXHAUSTED",
    "ENVIRONMENT_STEP_BUDGET_EXHAUSTED",
    "CONSECUTIVE_NONEXECUTED_ATTEMPTS_EXHAUSTED",
}


def _max_run(values: list[str]) -> int:
    best = 0
    current = 0
    prior: str | None = None
    for value in values:
        if value == prior:
            current += 1
        else:
            current = 1
            prior = value
        best = max(best, current)
    return best


def _first_and_last_true(flags: list[bool]) -> tuple[int | None, int | None]:
    positions = [index for index, flag in enumerate(flags) if flag]
    if not positions:
        return None, None
    return positions[0], positions[-1]


def extract_mechanical_episode_evidence(
    bundle: ValidatedAttemptBundle,
) -> dict[str, object]:
    traces = bundle.traces
    transitions = bundle.transitions
    executed_actions = [
        item.submitted_action for item in transitions
    ]

    frequencies = Counter(executed_actions)
    exact_repeat_count = sum(
        count - 1 for count in frequencies.values() if count > 1
    )
    consecutive_repeat_count = sum(
        executed_actions[index] == executed_actions[index - 1]
        for index in range(1, len(executed_actions))
    )
    abab_count = 0
    for index in range(3, len(executed_actions)):
        a, b, c, d = executed_actions[index - 3 : index + 1]
        if a == c and b == d and a != b:
            abab_count += 1

    observation_unchanged = [
        item.pre_observation == item.resulting_observation
        for item in transitions
    ]
    menu_unchanged = [
        item.pre_menu == item.resulting_menu
        for item in transitions
    ]
    nothing_happens = [
        item.resulting_observation == _NOTHING_HAPPENS
        for item in transitions
    ]
    no_effect = [
        exact_nothing
        or (same_observation and same_menu)
        for exact_nothing, same_observation, same_menu in zip(
            nothing_happens,
            observation_unchanged,
            menu_unchanged,
        )
    ]
    public_state_changes = [
        not same_observation or not same_menu
        for same_observation, same_menu in zip(
            observation_unchanged,
            menu_unchanged,
        )
    ]
    first_state_change, last_state_change = _first_and_last_true(
        public_state_changes
    )
    time_to_first_state_change = (
        None if first_state_change is None else first_state_change + 1
    )
    time_since_last_state_change = (
        len(transitions)
        if last_state_change is None
        else len(transitions) - last_state_change - 1
    )

    termination_reason = str(
        bundle.episode.get("termination_reason", "")
    )
    generic = {
        "policy_call_count": len(bundle.policy_calls),
        "executed_environment_step_count": len(transitions),
        "protocol_failure_count": sum(
            trace.attempt_outcome == "FORMAT_PROTOCOL_FAILURE"
            for trace in traces
        ),
        "inadmissible_action_count": sum(
            trace.attempt_outcome == "ACTION_NOT_ADMISSIBLE"
            for trace in traces
        ),
        "nonexecuted_attempt_count": sum(
            trace.execution_status == "not_executed"
            for trace in traces
        ),
        "environment_error_count": sum(
            trace.execution_status == "environment_error"
            for trace in traces
        ),
        "exact_action_repeat_count": exact_repeat_count,
        "consecutive_exact_action_repeat_count": (
            consecutive_repeat_count
        ),
        "max_consecutive_exact_action_repeat_run": (
            _max_run(executed_actions)
        ),
        "abab_action_oscillation_count": abab_count,
        "observation_unchanged_count": sum(observation_unchanged),
        "menu_unchanged_count": sum(menu_unchanged),
        "nothing_happens_count": sum(nothing_happens),
        "no_effect_transition_count": sum(no_effect),
        "no_effect_rule": (
            "EXACT_RESULT_NOTHING_HAPPENS_OR_BOTH_OBSERVATION_AND_MENU_UNCHANGED"
        ),
        "budget_exhaustion": (
            termination_reason in _BUDGET_TERMINATIONS
        ),
        "time_to_first_public_state_change": (
            time_to_first_state_change
        ),
        "time_since_last_public_state_change": (
            time_since_last_state_change
        ),
        "terminal_done": bool(bundle.episode.get("final_done")),
        "terminal_won": bool(bundle.episode.get("final_won")),
        "terminal_success": bundle.episode.get("success"),
        "termination_reason": termination_reason,
    }

    alfworld = extract_alfworld_event_facts(bundle)
    artifact = {
        "schema_id": "MECHANICAL_EPISODE_EVIDENCE_V1",
        "schema_version": 1,
        "source_attempt_bundle_sha256": (
            bundle.attempt_bundle_sha256
        ),
        "source_episode_semantic_sha256": (
            bundle.episode_semantic_sha256
        ),
        "task_id": bundle.task_id,
        "gamefile_sha256": bundle.gamefile_sha256,
        "generic_episode_facts": generic,
        "alfworld_event_facts": alfworld,
        "authority": "DETERMINISTIC_FACTS_ONLY",
        "prohibited_interpretations": [
            "FAILURE_MECHANISM",
            "CRITICAL_STEP",
            "ROOT_CAUSE",
            "REPAIR_QUALITY",
            "BENEFIT",
            "HARM",
            "NEUTRAL",
            "UNCERTAIN",
        ],
        "evidence_sha256": "0" * 64,
    }
    artifact["evidence_sha256"] = domain_hash(
        "MECHANICAL_EPISODE_EVIDENCE_V1",
        artifact,
        excluded_field="evidence_sha256",
    )
    return artifact


def extract_mechanical_episode_evidence_file(
    *,
    bundle: ValidatedAttemptBundle,
    output_path: Path,
) -> dict[str, object]:
    artifact = extract_mechanical_episode_evidence(bundle)
    write_new_json(output_path, artifact)
    return artifact

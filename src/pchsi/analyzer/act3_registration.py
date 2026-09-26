from __future__ import annotations

from collections.abc import Mapping, Sequence
from pchsi.evaluation.budget import BudgetState
from pchsi.evaluation.canonical_evidence import canonical_json_bytes, sha256_bytes
from pchsi.memory.source_state_contracts import (
    ReplayTransitionExpectationV1,
    build_source_decision_state_fingerprint_v1,
)
from pchsi.reference_loop.canonical import domain_hash


SOURCE_CONDITION = "P4-R1-Q2-BAD-TRAIN17"


def _domain_sha(domain: str, value: object) -> str:
    return sha256_bytes(domain.encode("utf-8") + b"\0" + canonical_json_bytes(value))


def _error_hypothesis_ids(error: Mapping[str, object]) -> set[str]:
    raw = error.get("mechanism_hypotheses")
    if not isinstance(raw, list):
        return set()
    return {
        str(row["hypothesis_id"])
        for row in raw
        if isinstance(row, Mapping) and isinstance(row.get("hypothesis_id"), str)
    }


def linked_repairs(
    *,
    local_result: Mapping[str, object],
    error: Mapping[str, object],
) -> list[Mapping[str, object]]:
    ids = _error_hypothesis_ids(error)
    raw = local_result.get("local_repairs")
    if not isinstance(raw, list):
        return []
    out = []
    for repair in raw:
        if not isinstance(repair, Mapping):
            continue
        supporting = repair.get("supporting_hypothesis_ids")
        if not isinstance(supporting, list):
            continue
        if ids.intersection(str(x) for x in supporting if isinstance(x, str)):
            out.append(repair)
    return out


def select_dev_source_call(
    *,
    local_result: Mapping[str, object],
    error: Mapping[str, object],
) -> dict[str, object]:
    repairs = linked_repairs(local_result=local_result, error=error)
    indices = sorted({
        int(row["decision_call_index"])
        for row in repairs
        if type(row.get("decision_call_index")) is int
    })
    if len(indices) == 1:
        return {
            "source_call_index": indices[0],
            "selection_rule": "UNIQUE_LINKED_A1_REPAIR_DECISION_CALL",
            "formal_eligible": True,
        }
    if len(indices) > 1:
        raise ValueError("multiple linked A1 repair decision calls")
    trigger = error.get("trigger_call_index")
    if type(trigger) is not int or trigger < 0:
        raise ValueError("no source-call candidate")
    return {
        "source_call_index": trigger,
        "selection_rule": "DEV_TRIGGER_FALLBACK_NO_LINKED_A1_REPAIR",
        "formal_eligible": False,
    }


def _first_seen_pattern(values: Sequence[str | None]) -> list[int]:
    ids: dict[str | None, int] = {}
    result: list[int] = []
    for value in values:
        if value not in ids:
            ids[value] = len(ids)
        result.append(ids[value])
    return result


def build_group_signature_binding(
    *,
    local_result: Mapping[str, object],
    error: Mapping[str, object],
    evidence_pack: Mapping[str, object],
    action_traces_by_call: Mapping[int, object],
) -> dict[str, object]:
    start = error.get("critical_window_start_call_index")
    end = error.get("critical_window_end_call_index")
    if type(start) is not int or type(end) is not int or not 0 <= start <= end:
        raise ValueError("invalid critical window")

    traces = []
    for index in range(start, end + 1):
        trace = action_traces_by_call.get(index)
        if trace is None:
            raise ValueError(f"missing action trace for critical-window call {index}")
        traces.append(trace)

    outcomes = [getattr(x, "attempt_outcome", None) for x in traces]
    failure_codes = [getattr(x, "failure_code", None) for x in traces]
    admissibility = [getattr(x, "admissibility_status", None) for x in traces]
    feedback = [getattr(x, "feedback_code", None) for x in traces]
    actions = [getattr(x, "normalized_action", None) for x in traces]

    def delta(after: str, before: str) -> int:
        last = getattr(traces[-1], after)
        first = getattr(traces[0], before)
        if type(last) is not int or type(first) is not int:
            raise ValueError(f"missing deterministic trace counters: {after}/{before}")
        return last - first

    mechanical_payload = {
        "schema_id": "ACT3_MECHANICAL_SIGNATURE_PAYLOAD_V1",
        "attempt_outcome_sequence": outcomes,
        "failure_code_sequence": failure_codes,
        "admissibility_sequence": admissibility,
        "feedback_code_sequence": feedback,
        "action_equality_pattern": _first_seen_pattern(actions),
        "policy_attempt_delta": delta("policy_attempt_count_after", "policy_attempt_count_before"),
        "environment_step_delta": delta("environment_step_count_after", "environment_step_count_before"),
        "protocol_failure_delta": (
            int(getattr(traces[-1], "protocol_failure_count"))
            - int(getattr(traces[0], "protocol_failure_count_before"))
        ),
        "inadmissible_action_delta": (
            int(getattr(traces[-1], "inadmissible_action_count"))
            - int(getattr(traces[0], "inadmissible_action_count_before"))
        ),
        "max_consecutive_nonexecuted_after": max(
            int(getattr(x, "consecutive_nonexecuted_attempt_count"))
            for x in traces
        ),
    }

    mech = evidence_pack.get("mechanical_evidence")
    if not isinstance(mech, Mapping):
        raise ValueError("mechanical_evidence missing")

    event_fields = (
        "goal_object_visible_events",
        "goal_take_available_events",
        "goal_object_acquired_events",
        "inventory_change_events",
        "required_treatment_completed_events",
        "placement_completed_events",
    )
    progress_required = set(event_fields) | {"goal_object_parse_status"}
    progress_sources = [
        value
        for value in mech.values()
        if isinstance(value, Mapping)
        and progress_required.issubset(set(value))
    ]
    if len(progress_sources) != 1:
        raise ValueError(
            "deterministic progress-fact source is not uniquely registered"
        )
    progress_facts = progress_sources[0]

    event_summary = {}
    for field in event_fields:
        raw = progress_facts.get(field)
        if not isinstance(raw, list) or any(type(x) is not int for x in raw):
            raise ValueError(f"invalid deterministic progress field: {field}")
        before_count = sum(x < start for x in raw)
        within_count = sum(start <= x <= end for x in raw)
        after_count = sum(x > end for x in raw)
        event_summary[field] = {
            "before_window": before_count,
            "within_window": within_count,
            "after_window": after_count,
        }

    progress_payload = {
        "schema_id": "ACT3_PROGRESS_SIGNATURE_PAYLOAD_V1",
        "goal_object_parse_status": progress_facts.get(
            "goal_object_parse_status"
        ),
        "progress_event_counts": event_summary,
        "registered_progress_before_window": any(
            row["before_window"] > 0 for row in event_summary.values()
        ),
        "registered_progress_within_window": any(
            row["within_window"] > 0 for row in event_summary.values()
        ),
    }

    task_family = evidence_pack.get("task_type")
    task_identity = evidence_pack.get("task_identity")
    nested_task_family = (
        task_identity.get("task_type")
        if isinstance(task_identity, Mapping)
        else None
    )
    if task_family is None:
        task_family = nested_task_family
    elif (
        nested_task_family is not None
        and nested_task_family != task_family
    ):
        raise ValueError("task family identity mismatch")
    if not isinstance(task_family, str) or not task_family:
        raise ValueError("task family missing")

    return {
        "local_result_sha256": local_result["local_result_sha256"],
        "error_instance_id": error["error_instance_id"],
        "task_family": task_family,
        "mechanical_signature_sha256": _domain_sha(
            "ACT3_MECHANICAL_SIGNATURE_V1", mechanical_payload
        ),
        "progress_signature_sha256": _domain_sha(
            "ACT3_PROGRESS_SIGNATURE_V1", progress_payload
        ),
        "mechanical_signature_payload": mechanical_payload,
        "progress_signature_payload": progress_payload,
    }


def build_exact_source_registration(
    *,
    source_task_id: str,
    source_gamefile_sha256: str,
    source_bundle_sha256: str,
    policy_call: object,
    public_transitions: Sequence[object],
    source_call_index: int,
    selection_rule: str,
    formal_eligible: bool,
) -> dict[str, object]:
    transitions = tuple(
        sorted(
            (
                row for row in public_transitions
                if getattr(row, "model_call_index") < source_call_index
            ),
            key=lambda row: getattr(row, "environment_step_index"),
        )
    )
    expectations = []
    for expected_index, row in enumerate(transitions):
        if getattr(row, "environment_step_index") != expected_index:
            raise ValueError("source replay prefix environment-step indices are not contiguous")
        expectations.append(
            ReplayTransitionExpectationV1(
                environment_step_index=expected_index,
                action=getattr(row, "submitted_action"),
                pre_observation_sha256=getattr(row, "pre_action_observation_sha256"),
                pre_menu_sequence_sha256=getattr(row, "pre_action_admissible_commands_sha256"),
                resulting_observation_sha256=getattr(row, "resulting_observation_sha256"),
                resulting_menu_sequence_sha256=getattr(row, "resulting_admissible_commands_sha256"),
                score=getattr(row, "score"),
                done=getattr(row, "done"),
                won=getattr(row, "won"),
            )
        )
    prefix_payload = [row.to_dict() for row in expectations]
    executed_prefix_sha256 = _domain_sha("SOURCE_EXECUTED_PREFIX_V1", prefix_payload)

    budget = BudgetState(**dict(getattr(policy_call, "budget_before")))
    fingerprint = build_source_decision_state_fingerprint_v1(
        source_task_id=source_task_id,
        source_gamefile_sha256=source_gamefile_sha256,
        source_bundle_sha256=source_bundle_sha256,
        source_policy_condition=SOURCE_CONDITION,
        executed_prefix_sha256=executed_prefix_sha256,
        observation_sha256=getattr(policy_call, "observation_sha256"),
        menu_sequence_sha256=getattr(policy_call, "admissible_commands_sequence_sha256"),
        memory_m0_sha256=getattr(policy_call, "executed_history_sha256"),
        interface_feedback_code=getattr(policy_call, "interface_feedback_before"),
        budget_state=budget,
        model_call_index=source_call_index,
        base_policy_input_sha256=getattr(policy_call, "prompt_sha256"),
    )
    return {
        "schema_id": "ACT3_EXACT_SOURCE_STATE_BINDING_V1",
        "source_state_sha256": fingerprint.fingerprint_sha256,
        "menu_sha256": getattr(policy_call, "admissible_commands_sequence_sha256"),
        "source_call_index": source_call_index,
        "source_fingerprint": fingerprint.to_dict(),
        "source_context": {
            "source_state_sha256": fingerprint.fingerprint_sha256,
            "menu_sha256": getattr(policy_call, "admissible_commands_sequence_sha256"),
            "source_call_index": source_call_index,
            "public_task_goal": getattr(policy_call, "public_task_goal"),
            "observation": getattr(policy_call, "observation"),
            "admissible_commands": list(getattr(policy_call, "admissible_commands")),
            "executed_history": [
                {"action": a, "resulting_observation": o}
                for a, o in getattr(policy_call, "executed_history")
            ],
            "interface_feedback_before": getattr(policy_call, "interface_feedback_before"),
            "budget_before": dict(getattr(policy_call, "budget_before")),
        },
        "selection_rule": selection_rule,
        "formal_eligible": formal_eligible,
    }

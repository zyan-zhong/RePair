"""State-level K<=1 Formal candidate materialization.

This module intentionally separates:
- candidate/proposal artifact identity, which preserves provenance; from
- execution identity, which captures what the environment would actually do.

No winner is selected among genuinely distinct executable interventions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pchsi.reference_loop.canonical import domain_hash

_EXECUTABLE = {
    "EXECUTABLE_EXACT_ACTION",
    "EXECUTABLE_SHORT_OPTION",
}


def _sha64(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be lowercase sha256")
    return value


def execution_semantics_payload(candidate: Mapping[str, object]) -> dict[str, object]:
    """Return provenance-free execution semantics for one executable candidate."""
    status = candidate.get("candidate_status")
    if status not in _EXECUTABLE:
        raise ValueError("execution identity requires executable candidate")

    state = _sha64("source_state_sha256", candidate.get("source_state_sha256"))
    menu = _sha64("menu_sha256", candidate.get("menu_sha256"))
    exact = candidate.get("exact_action")
    option = candidate.get("option_actions")
    termination = candidate.get("termination_condition")

    if status == "EXECUTABLE_EXACT_ACTION":
        if not isinstance(exact, str) or not exact:
            raise ValueError("executable exact-action candidate lacks exact_action")
        if option not in ([], ()):
            raise ValueError("exact-action candidate has option_actions")
        if termination is not None:
            raise ValueError("exact-action candidate has termination_condition")
        mode = "EXACT_ACTION"
        actions: list[str] = [exact]
        termination_value = None
    else:
        if exact is not None:
            raise ValueError("short-option candidate has exact_action")
        if (
            not isinstance(option, (list, tuple))
            or not 1 <= len(option) <= 4
            or any(not isinstance(x, str) or not x for x in option)
        ):
            raise ValueError("short-option candidate actions invalid")
        if not isinstance(termination, str) or not termination:
            raise ValueError("short-option termination invalid")
        mode = "SHORT_OPTION"
        actions = list(option)
        termination_value = termination

    return {
        "schema_id": "ANALYZER_EXECUTION_SEMANTICS_V1",
        "source_state_sha256": state,
        "menu_sha256": menu,
        "execution_mode": mode,
        "ordered_actions": actions,
        "termination_condition": termination_value,
    }


def execution_identity_sha256(candidate: Mapping[str, object]) -> str:
    return domain_hash(
        "ANALYZER_EXECUTION_EQUIVALENCE_V1",
        execution_semantics_payload(candidate),
    )


def deduplicate_execution_equivalent(
    candidates: Iterable[Mapping[str, object]],
) -> dict[str, list[Mapping[str, object]]]:
    buckets: dict[str, list[Mapping[str, object]]] = {}
    for candidate in candidates:
        if candidate.get("candidate_status") not in _EXECUTABLE:
            continue
        identity = execution_identity_sha256(candidate)
        buckets.setdefault(identity, []).append(candidate)
    return {key: buckets[key] for key in sorted(buckets)}


def _candidate_sha(candidate: Mapping[str, object]) -> str:
    value = candidate.get("candidate_sha256")
    return _sha64("candidate_sha256", value)


def materialize_state_condition_k1(
    *,
    condition_id: str,
    source_state_sha256: str,
    candidates: Iterable[Mapping[str, object]],
    zero_candidate_disposition: str = "NO_FORMAL_PROPOSAL",
) -> dict[str, Any]:
    """Materialize the frozen K<=1 budget for one condition x source state.

    Compatibility fields candidate_count/abstained remain, but `abstained`
    MUST NOT be interpreted as voluntary/model abstention without consulting
    `formal_disposition` / `voluntary_abstention`.
    """
    if not isinstance(condition_id, str) or not condition_id:
        raise ValueError("condition_id required")
    state = _sha64("source_state_sha256", source_state_sha256)

    rows = list(candidates)
    for row in rows:
        if row.get("source_state_sha256") != state:
            raise ValueError("candidate outside requested source state")

    buckets = deduplicate_execution_equivalent(rows)
    executable_artifact_shas = sorted(
        _candidate_sha(row)
        for rows2 in buckets.values()
        for row in rows2
    )

    if len(buckets) == 0:
        return {
            "schema_id": "FORMAL_STATE_CONDITION_K1_MATERIALIZATION_V1",
            "schema_version": 1,
            "condition_id": condition_id,
            "source_state_sha256": state,
            "candidate_count": 0,
            "abstained": True,
            "voluntary_abstention": zero_candidate_disposition == "MODEL_ABSTAIN",
            "formal_disposition": zero_candidate_disposition,
            "method_failure_reason": (
                zero_candidate_disposition
                if zero_candidate_disposition.startswith("METHOD_")
                else None
            ),
            "selected_execution_identity_sha256": None,
            "selected_candidate_sha256": None,
            "equivalent_candidate_sha256s": [],
            "all_executable_candidate_sha256s": executable_artifact_shas,
            "distinct_execution_count": 0,
            "distinct_execution_identity_sha256s": [],
        }

    if len(buckets) == 1:
        identity = next(iter(buckets))
        equivalent = sorted(_candidate_sha(row) for row in buckets[identity])
        # Representative selection is ONLY among execution-equivalent artifacts.
        # It does not change the intervention sent to the environment.
        representative = equivalent[0]
        return {
            "schema_id": "FORMAL_STATE_CONDITION_K1_MATERIALIZATION_V1",
            "schema_version": 1,
            "condition_id": condition_id,
            "source_state_sha256": state,
            "candidate_count": 1,
            "abstained": False,
            "voluntary_abstention": False,
            "formal_disposition": "FORMAL_CANDIDATE_REGISTERED",
            "method_failure_reason": None,
            "selected_execution_identity_sha256": identity,
            "selected_candidate_sha256": representative,
            "equivalent_candidate_sha256s": equivalent,
            "all_executable_candidate_sha256s": executable_artifact_shas,
            "distinct_execution_count": 1,
            "distinct_execution_identity_sha256s": [identity],
        }

    return {
        "schema_id": "FORMAL_STATE_CONDITION_K1_MATERIALIZATION_V1",
        "schema_version": 1,
        "condition_id": condition_id,
        "source_state_sha256": state,
        "candidate_count": 0,
        "abstained": True,
        "voluntary_abstention": False,
        "formal_disposition": "METHOD_INVALID_K1_STATE_BUDGET_COLLISION",
        "method_failure_reason": "METHOD_INVALID_K1_STATE_BUDGET_COLLISION",
        "selected_execution_identity_sha256": None,
        "selected_candidate_sha256": None,
        "equivalent_candidate_sha256s": [],
        "all_executable_candidate_sha256s": executable_artifact_shas,
        "distinct_execution_count": len(buckets),
        "distinct_execution_identity_sha256s": sorted(buckets),
    }

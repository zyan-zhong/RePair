"""Mechanical decision aid for Human Research Planner portfolio review.

This module is deliberately non-authoritative. It extracts structural evidence
from the canonical 60-candidate pool and produces a transparent recommendation.
The final 12-state portfolio remains a Human Researcher decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from collections.abc import Mapping
import json


_POSITIVE = {
    "ACCEPT",
    "PASS",
    "SUPPORTED",
    "NO_CONTRADICTION",
    "CONSISTENT",
}
_NEGATIVE = {
    "REJECT",
    "REJECTED",
    "FAIL",
    "FAILED",
    "CONTRADICTED",
    "ABSTAIN",
}


def _walk_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def _walk_sha(value: object):
    if isinstance(value, str):
        if (
            len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value)
        ):
            yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_sha(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_sha(child)


def _count_named_lists(value: object, token: str) -> int:
    total = 0
    if isinstance(value, dict):
        for key, child in value.items():
            if token in str(key).lower() and isinstance(child, list):
                total += len(child)
            total += _count_named_lists(child, token)
    elif isinstance(value, list):
        for child in value:
            total += _count_named_lists(child, token)
    return total


def _crosscheck_dispositions(value: object) -> tuple[str, ...]:
    rows: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            if (
                any(
                    token in lower
                    for token in ("disposition", "status", "verdict")
                )
                and isinstance(child, str)
            ):
                rows.add(child)
            rows.update(_crosscheck_dispositions(child))
    elif isinstance(value, list):
        for child in value:
            rows.update(_crosscheck_dispositions(child))
    return tuple(sorted(rows))


def _disposition_signal(dispositions: tuple[str, ...]) -> tuple[int, int, int]:
    positive = negative = unknown = 0
    for raw in dispositions:
        upper = raw.upper()
        if upper in _POSITIVE:
            positive += 1
        elif upper in _NEGATIVE or any(x in upper for x in ("REJECT", "FAIL", "CONTRADICT", "ABSTAIN")):
            negative += 1
        else:
            unknown += 1
    return positive, negative, unknown


@dataclass(frozen=True, slots=True)
class CandidateEvidenceProfileV1:
    source_state_sha256: str
    condition_id: str
    candidate_sha256: str
    task_family: str | None
    group_id: str | None
    repair_kind: str
    intervention_action_count: int
    supporting_evidence_count: int
    contradiction_evidence_count: int
    residual_case_count: int
    positive_crosscheck_count: int
    negative_crosscheck_count: int
    unknown_crosscheck_count: int
    memory_exact_sha_overlap_count: int
    crosscheck_dispositions: tuple[str, ...]
    mechanical_preference_key: tuple[object, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_state_sha256": self.source_state_sha256,
            "condition_id": self.condition_id,
            "candidate_sha256": self.candidate_sha256,
            "task_family": self.task_family,
            "group_id": self.group_id,
            "repair_kind": self.repair_kind,
            "intervention_action_count": self.intervention_action_count,
            "supporting_evidence_count": self.supporting_evidence_count,
            "contradiction_evidence_count": self.contradiction_evidence_count,
            "residual_case_count": self.residual_case_count,
            "positive_crosscheck_count": self.positive_crosscheck_count,
            "negative_crosscheck_count": self.negative_crosscheck_count,
            "unknown_crosscheck_count": self.unknown_crosscheck_count,
            "memory_exact_sha_overlap_count": self.memory_exact_sha_overlap_count,
            "crosscheck_dispositions": list(self.crosscheck_dispositions),
            "mechanical_preference_key": list(self.mechanical_preference_key),
        }


def profile_candidate_v1(
    *,
    candidate: Mapping[str, object],
    memory_sha256s: set[str],
) -> CandidateEvidenceProfileV1:
    crosschecks = candidate.get("crosschecks")
    if not isinstance(crosschecks, list):
        crosschecks = []
    dispositions = _crosscheck_dispositions(crosschecks)
    positive, negative, unknown = _disposition_signal(dispositions)

    support_shas = candidate.get("supporting_evidence_sha256s")
    if not isinstance(support_shas, list):
        support_shas = []

    contradiction_count = _count_named_lists(crosschecks, "contradiction")
    residual_count = _count_named_lists(crosschecks, "residual")

    repair_kind = str(candidate.get("repair_kind"))
    option_actions = candidate.get("option_actions")
    if not isinstance(option_actions, list):
        option_actions = []
    action_count = 1 if repair_kind == "EXACT_ACTION" else max(1, len(option_actions))

    group = candidate.get("group_manifest")
    group_id = task_family = None
    if isinstance(group, dict):
        if isinstance(group.get("group_id"), str):
            group_id = str(group["group_id"])
        if isinstance(group.get("task_family"), str):
            task_family = str(group["task_family"])

    candidate_shas = set(_walk_sha(candidate))
    memory_overlap = len(candidate_shas & memory_sha256s)

    # Lexicographic only; no arbitrary weighted scalar score.
    # Smaller tuple is mechanically preferred.
    preference = (
        1 if negative > 0 else 0,
        contradiction_count,
        residual_count,
        -len(support_shas),
        action_count,
        str(candidate.get("candidate_sha256")),
    )

    return CandidateEvidenceProfileV1(
        source_state_sha256=str(candidate["source_state_sha256"]),
        condition_id=str(candidate["condition_id"]),
        candidate_sha256=str(candidate["candidate_sha256"]),
        task_family=task_family,
        group_id=group_id,
        repair_kind=repair_kind,
        intervention_action_count=action_count,
        supporting_evidence_count=len(support_shas),
        contradiction_evidence_count=contradiction_count,
        residual_case_count=residual_count,
        positive_crosscheck_count=positive,
        negative_crosscheck_count=negative,
        unknown_crosscheck_count=unknown,
        memory_exact_sha_overlap_count=memory_overlap,
        crosscheck_dispositions=dispositions,
        mechanical_preference_key=preference,
    )


def build_select12_decision_aid_v1(
    *,
    canonical_pool: Mapping[str, object],
    researcher_memory: Mapping[str, object],
    registered_state_budget: int,
) -> dict[str, object]:
    pairs = canonical_pool.get("state_pairs")
    if not isinstance(pairs, dict) or len(pairs) != 30:
        raise ValueError("canonical pool must contain 30 state pairs")
    if registered_state_budget != 12:
        raise ValueError("current reference budget must register 12 states")

    memory_shas = set(_walk_sha(researcher_memory))
    pair_rows: list[dict[str, object]] = []

    for state, pair in sorted(pairs.items()):
        if not isinstance(pair, dict) or set(pair) != {"A2", "A3"}:
            raise ValueError("each state must contain exactly A2/A3")
        profiles = {
            condition: profile_candidate_v1(
                candidate=pair[condition],
                memory_sha256s=memory_shas,
            )
            for condition in ("A2", "A3")
        }
        preferred = min(
            profiles.values(),
            key=lambda row: row.mechanical_preference_key,
        )
        alternative = (
            profiles["A3"]
            if preferred.condition_id == "A2"
            else profiles["A2"]
        )
        pair_rows.append(
            {
                "source_state_sha256": state,
                "A2": profiles["A2"].to_dict(),
                "A3": profiles["A3"].to_dict(),
                "mechanically_preferred_candidate_sha256": (
                    preferred.candidate_sha256
                ),
                "mechanically_preferred_condition": preferred.condition_id,
                "alternative_candidate_sha256": alternative.candidate_sha256,
                "decision_aid_only": True,
                "human_selected_candidate_sha256": None,
                "human_selected_condition": None,
                "human_expected_value": None,
                "human_harm_risk": None,
                "human_selection_rationale": None,
            }
        )

    # Greedy diversity-first state recommendation. It never changes the
    # within-state mechanical preference and never sees F0/F1 outcomes.
    remaining = {row["source_state_sha256"]: row for row in pair_rows}
    chosen: list[dict[str, object]] = []
    covered_families: set[str] = set()
    covered_groups: set[str] = set()
    covered_kinds: set[str] = set()

    while len(chosen) < registered_state_budget:
        ranked = []
        for state, row in remaining.items():
            preferred_condition = row["mechanically_preferred_condition"]
            profile = row[preferred_condition]
            family = profile.get("task_family")
            group = profile.get("group_id")
            kind = profile.get("repair_kind")

            diversity_gain = sum(
                (
                    bool(family) and family not in covered_families,
                    bool(group) and group not in covered_groups,
                    bool(kind) and kind not in covered_kinds,
                )
            )
            quality = tuple(profile["mechanical_preference_key"])
            ranked.append(
                (
                    -diversity_gain,
                    quality,
                    state,
                    row,
                )
            )
        ranked.sort(key=lambda item: (item[0], item[1], item[2]))
        _, _, state, row = ranked[0]
        chosen.append(row)
        del remaining[state]

        profile = row[row["mechanically_preferred_condition"]]
        if profile.get("task_family"):
            covered_families.add(str(profile["task_family"]))
        if profile.get("group_id"):
            covered_groups.add(str(profile["group_id"]))
        if profile.get("repair_kind"):
            covered_kinds.add(str(profile["repair_kind"]))

    recommendation = [
        {
            "source_state_sha256": row["source_state_sha256"],
            "candidate_sha256": row[
                "mechanically_preferred_candidate_sha256"
            ],
            "condition_id": row["mechanically_preferred_condition"],
            "decision_aid_only": True,
        }
        for row in chosen
    ]

    return {
        "schema_id": "HUMAN_SELECT12_DECISION_AID_V1",
        "schema_version": 1,
        "registered_state_budget": registered_state_budget,
        "pair_count": len(pair_rows),
        "pair_rows": pair_rows,
        "mechanical_recommendation": recommendation,
        "recommendation_count": len(recommendation),
        "selection_method": {
            "within_state": (
                "lexicographic: explicit-negative-crosscheck, contradiction, "
                "residual, support-count-desc, intervention-action-count, SHA"
            ),
            "across_states": (
                "greedy diversity-first over task_family/group/repair_kind, "
                "then within-state mechanical quality"
            ),
            "uses_current_f0f1_outcomes": False,
            "uses_strong_model_benchmark_results": False,
            "human_authority_required": True,
        },
        "success_trajectory_optimization_active": False,
        "automatic_scientific_selection_performed": False,
        "next_gate": "HUMAN_REVIEW_RECOMMENDED_12",
    }

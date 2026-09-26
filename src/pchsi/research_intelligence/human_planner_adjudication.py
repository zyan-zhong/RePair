"""Human Research Planner scientific adjudication and blind-shadow inputs.

The Human reference decision is a typed scientific artifact, not an automatic
effect label. This module validates the 30 A2/A3 pairs, compiles one bounded
repair portfolio, and builds a role-neutral input for the blind Strong
Researcher shadow.

Authority remains separated:

- Analyzer / Formal X: diagnosis, candidate and scope evidence;
- Human/Strong/Local Researcher: research selection and budget planning;
- Environment Verifier: Benefit/Harm/Neutral/Uncertain;
- Promotion Gate: promote/rollback.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from pathlib import Path
import hashlib
import json

from pchsi.reference_loop.canonical import (
    canonical_json_bytes,
    domain_hash,
)
from pchsi.research_intelligence.repair_portfolio import (
    PortfolioDecisionV1,
    RepairCandidateOriginV1,
    RepairDispositionV1,
    RepairLineageV1,
    RepairProgramKindV1,
    ResearchRepairCandidateV1,
    ResearchRepairPortfolioV1,
    ResearchRepairProgramV1,
)
from pchsi.research_intelligence.role_neutral import (
    ResearcherPreDecisionV1,
    ResearcherRoleModeV1,
)


_FORBIDDEN_PRE_KEYS = frozenset(
    {
        "current_f0f1_outcomes",
        "current_selected_f0f1_outcomes",
        "future_pi2_evaluation",
        "strong_model_benchmark_per_task_results",
        "benchmark_per_task_results",
        "sealed_test_trajectory",
    }
)
_SCORE_CLASSES = frozenset({"LOW", "MEDIUM", "HIGH"})
_EXPECTED_FAMILIES = frozenset(
    {
        "pick_and_place_simple",
        "pick_heat_then_place_in_recep",
        "look_at_obj_in_light",
        "pick_clean_then_place_in_recep",
        "pick_two_obj_and_place",
        "pick_cool_then_place_in_recep",
    }
)


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value


def _require_sha(value: object, name: str) -> str:
    text = _require_text(value, name)
    if (
        len(text) != 64
        or any(character not in "0123456789abcdef" for character in text)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return text


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_keys(child)


def _contains_forbidden(value: object) -> set[str]:
    return _FORBIDDEN_PRE_KEYS.intersection(_walk_keys(value))


def _require_score_class(value: object, name: str) -> str:
    text = _require_text(value, name)
    if text not in _SCORE_CLASSES:
        raise ValueError(f"{name} must be LOW/MEDIUM/HIGH")
    return text


def _sha_list(values: object, name: str, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(values, list):
        raise TypeError(f"{name} must be array")
    if not allow_empty and not values:
        raise ValueError(f"{name} must be non-empty")
    rows = tuple(_require_sha(value, name) for value in values)
    if len(set(rows)) != len(rows):
        raise ValueError(f"{name} contains duplicates")
    return rows


def _string_list(
    values: object,
    name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if not isinstance(values, list):
        raise TypeError(f"{name} must be array")
    if not allow_empty and not values:
        raise ValueError(f"{name} must be non-empty")
    rows = tuple(_require_text(value, name) for value in values)
    if len(set(rows)) != len(rows):
        raise ValueError(f"{name} contains duplicates")
    return rows


def _candidate_index(
    dossier: Mapping[str, object],
) -> dict[tuple[str, str], dict[str, object]]:
    pairs = dossier.get("state_pairs")
    if not isinstance(pairs, dict) or len(pairs) != 30:
        raise ValueError("evidence-rich dossier must contain 30 state pairs")

    index: dict[tuple[str, str], dict[str, object]] = {}
    for state, raw_pair in pairs.items():
        state_sha = _require_sha(state, "source state")
        if not isinstance(raw_pair, dict) or set(raw_pair) != {"A2", "A3"}:
            raise ValueError("each state pair must contain exactly A2 and A3")
        for condition in ("A2", "A3"):
            raw_candidate = raw_pair[condition]
            if not isinstance(raw_candidate, dict):
                raise TypeError("candidate must be object")
            candidate = dict(raw_candidate)
            if candidate.get("condition_id") != condition:
                raise ValueError("candidate condition mismatch")
            if candidate.get("source_state_sha256") != state_sha:
                raise ValueError("candidate source-state mismatch")
            candidate_sha = _require_sha(
                candidate.get("candidate_sha256"),
                "candidate_sha256",
            )
            key = (state_sha, condition)
            if key in index:
                raise ValueError("duplicate state/condition candidate")
            index[key] = candidate
    if len(index) != 60:
        raise ValueError("candidate index must contain 60 candidates")
    return index


def _round_input(
    shared_input: Mapping[str, object],
) -> dict[str, object]:
    value = shared_input.get("round_input_package")
    if not isinstance(value, dict):
        raise ValueError("shared input lacks round_input_package")
    return dict(value)


def _budget_plan(
    shared_input: Mapping[str, object],
) -> dict[str, object]:
    value = shared_input.get("verification_budget_plan")
    if not isinstance(value, dict):
        raise ValueError("shared input lacks verification_budget_plan")
    return dict(value)


def _validate_global_identity(
    adjudication: Mapping[str, object],
    dossier: Mapping[str, object],
    shared_input: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    if adjudication.get("schema_id") != (
        "HUMAN_PLANNER_SCIENTIFIC_ADJUDICATION_V1"
    ):
        raise ValueError("adjudication schema mismatch")
    if adjudication.get("schema_version") != 1:
        raise ValueError("adjudication schema version mismatch")
    if dossier.get("schema_id") != (
        "EVIDENCE_RICH_A2_A3_PAIR_DOSSIER_V2"
    ):
        raise ValueError("dossier schema mismatch")
    if dossier.get("status") != "READY_FOR_HUMAN_SCIENTIFIC_REVIEW":
        raise ValueError("dossier is not ready for Human review")
    if shared_input.get("schema_id") != (
        "RESEARCH_PLANNER_SHARED_PRE_INPUT_CANDIDATE_V2"
    ):
        raise ValueError("shared PRE input schema mismatch")
    if shared_input.get("status") not in {
        "READY_FOR_HUMAN_SCIENTIFIC_REVIEW",
        "READY_FOR_HUMAN_REFERENCE_REVIEW_NOT_FROZEN",
    }:
        raise ValueError("shared PRE input is not ready")

    forbidden = (
        _contains_forbidden(adjudication)
        | _contains_forbidden(dossier)
        | _contains_forbidden(shared_input)
    )
    if forbidden:
        raise ValueError(
            "pre-outcome package contains forbidden keys: "
            + repr(sorted(forbidden))
        )

    identity_checks = {
        "evidence_rich_dossier_sha256": dossier.get("dossier_sha256"),
        "formal_x_binding_authority_sha256": dossier.get(
            "formal_x_binding_authority_sha256"
        ),
        "canonical_pool_sha256": dossier.get("canonical_pool_sha256"),
        "selection_authority_sha256": dossier.get(
            "selection_authority_sha256"
        ),
    }
    for field, expected in identity_checks.items():
        if adjudication.get(field) != expected:
            raise ValueError(f"adjudication {field} mismatch")
        _require_sha(expected, field)

    round_input = _round_input(shared_input)
    budget = _budget_plan(shared_input)
    round_checks = {
        "round_id": round_input.get("round_id"),
        "parent_policy_id": round_input.get("parent_policy_id"),
        "evidence_cutoff_sha256": round_input.get(
            "input_package_sha256"
        ),
        "round_evidence_package_sha256": round_input.get(
            "round_evidence_package_sha256"
        ),
    }
    for field, expected in round_checks.items():
        if adjudication.get(field) != expected:
            raise ValueError(f"adjudication {field} mismatch")
    _require_sha(
        adjudication.get("evidence_cutoff_sha256"),
        "evidence_cutoff_sha256",
    )
    _require_sha(
        adjudication.get("round_evidence_package_sha256"),
        "round_evidence_package_sha256",
    )

    registered_state_budget = budget.get("registered_state_budget")
    paired_repetitions = budget.get("paired_repetitions_per_state")
    branch_arms = budget.get("branch_arms_per_repetition")
    total_branch_runs = budget.get("total_branch_run_budget")
    if type(registered_state_budget) is not int or registered_state_budget <= 0:
        raise ValueError("registered state budget must be positive integer")
    if type(paired_repetitions) is not int or paired_repetitions <= 0:
        raise ValueError("paired repetitions must be positive integer")
    if branch_arms != 2:
        raise ValueError("F0/F1 requires two arms")
    if total_branch_runs != registered_state_budget * paired_repetitions * branch_arms:
        raise ValueError("total branch-run budget differs from Planner-selected state derivation")
    if budget.get("outcome_adaptive_budget_change_allowed") is not False:
        raise ValueError("outcome-adaptive budget change must be disabled")
    if budget.get("unfavorable_candidate_replacement_allowed") is not False:
        raise ValueError("unfavorable candidate replacement must be disabled")

    return round_input, budget


def validate_human_planner_adjudication_v1(
    *,
    adjudication: Mapping[str, object],
    dossier: Mapping[str, object],
    shared_input: Mapping[str, object],
) -> dict[str, object]:
    round_input, budget = _validate_global_identity(
        adjudication,
        dossier,
        shared_input,
    )
    candidate_index = _candidate_index(dossier)

    reviews = adjudication.get("state_reviews")
    if not isinstance(reviews, list) or len(reviews) != 30:
        raise ValueError("Human adjudication must review all 30 states")

    review_by_state: dict[str, dict[str, object]] = {}
    selected: list[dict[str, object]] = []

    for raw_review in reviews:
        if not isinstance(raw_review, dict):
            raise TypeError("state review must be object")
        review = dict(raw_review)
        state_sha = _require_sha(
            review.get("source_state_sha256"),
            "source_state_sha256",
        )
        if state_sha in review_by_state:
            raise ValueError("duplicate Human state review")
        review_by_state[state_sha] = review

        preferred_condition = _require_text(
            review.get("preferred_condition"),
            "preferred_condition",
        )
        if preferred_condition not in {"A2", "A3"}:
            raise ValueError("preferred condition must be A2/A3")
        alternative_condition = _require_text(
            review.get("alternative_condition"),
            "alternative_condition",
        )
        if {preferred_condition, alternative_condition} != {"A2", "A3"}:
            raise ValueError("preferred/alternative conditions must be A2/A3")

        preferred = candidate_index[(state_sha, preferred_condition)]
        alternative = candidate_index[(state_sha, alternative_condition)]

        exact_checks = {
            "preferred_candidate_sha256": preferred.get(
                "candidate_sha256"
            ),
            "preferred_repair_kind": preferred.get("repair_kind"),
            "preferred_exact_action": preferred.get("exact_action"),
            "preferred_option_actions": preferred.get("option_actions") or [],
            "preferred_x_disposition": preferred.get(
                "formal_x_disposition"
            ),
            "preferred_a3_memory_pack_sha256": preferred.get(
                "a3_analyzer_memory_pack_sha256"
            ),
            "alternative_candidate_sha256": alternative.get(
                "candidate_sha256"
            ),
            "alternative_repair_kind": alternative.get("repair_kind"),
            "alternative_exact_action": alternative.get("exact_action"),
            "alternative_option_actions": (
                alternative.get("option_actions") or []
            ),
            "alternative_x_disposition": alternative.get(
                "formal_x_disposition"
            ),
            "alternative_a3_memory_pack_sha256": alternative.get(
                "a3_analyzer_memory_pack_sha256"
            ),
            "group_manifest_sha256": preferred.get(
                "group_manifest_sha256"
            ),
        }
        for field, expected in exact_checks.items():
            if review.get(field) != expected:
                raise ValueError(
                    f"Human review {field} differs from frozen dossier"
                )

        families = preferred.get("task_family_values")
        if not isinstance(families, list) or len(families) != 1:
            raise ValueError("candidate must have one task family")
        if review.get("task_family") != families[0]:
            raise ValueError("Human review task family mismatch")

        if review.get("effect_label_authority") is not False:
            raise ValueError("Human review cannot assign effect authority")
        for field in (
            "pair_adjudication_rationale",
            "alternative_disposition",
            "state_portfolio_disposition",
            "human_evidence_summary",
            "human_counterevidence_summary",
            "human_selection_rationale",
        ):
            _require_text(review.get(field), field)
        for field in (
            "expected_value_class",
            "expected_harm_risk_class",
            "evidence_support_class",
            "portfolio_marginal_value_class",
        ):
            _require_score_class(review.get(field), field)

        supporting = _sha_list(
            review.get("formal_x_supporting_evidence_sha256s"),
            "formal_x_supporting_evidence_sha256s",
            allow_empty=False,
        )
        _sha_list(
            review.get("formal_x_contradiction_evidence_sha256s"),
            "formal_x_contradiction_evidence_sha256s",
            allow_empty=True,
        )
        _string_list(
            review.get("formal_x_residual_case_ids"),
            "formal_x_residual_case_ids",
            allow_empty=True,
        )
        for field in (
            "formal_x_crosscheck_sha256",
            "formal_group_result_sha256",
            "local_result_sha256",
            "source_proposal_sha256",
            "group_manifest_sha256",
            "preferred_candidate_sha256",
            "alternative_candidate_sha256",
        ):
            _require_sha(review.get(field), field)

        if preferred_condition == "A2":
            if review.get("preferred_a3_memory_pack_sha256") is not None:
                raise ValueError("A2 preferred candidate cannot bind A3 Memory")
        else:
            _require_sha(
                review.get("preferred_a3_memory_pack_sha256"),
                "preferred_a3_memory_pack_sha256",
            )

        selected_flag = review.get("selected_for_verification")
        if not isinstance(selected_flag, bool):
            raise TypeError("selected_for_verification must be boolean")
        state_disposition = review.get("state_portfolio_disposition")
        if selected_flag:
            if state_disposition != "SELECTED":
                raise ValueError("selected state must have SELECTED disposition")
            if review.get("preferred_x_disposition") != "ACCEPT":
                raise ValueError(
                    "selected repair must have Formal X ACCEPT"
                )
            if review.get("preferred_repair_kind") != "EXACT_ACTION":
                raise ValueError(
                    "current reference portfolio selects exact actions only"
                )
            if not isinstance(review.get("preferred_exact_action"), str):
                raise ValueError("selected exact action missing")
            if review.get("preferred_option_actions") != []:
                raise ValueError(
                    "selected exact-action repair cannot contain option actions"
                )
            if not supporting:
                raise ValueError("selected repair lacks current evidence")
            selected.append(review)
        elif state_disposition != "DEFERRED_BUDGET":
            raise ValueError(
                "non-selected state must be explicitly DEFERRED_BUDGET"
            )

    if set(review_by_state) != {
        state for state, _ in candidate_index
    }:
        raise ValueError("Human review state universe mismatch")

    registered_state_budget = int(budget["registered_state_budget"])
    paired_repetitions = int(budget["paired_repetitions_per_state"])
    total_branch_runs = int(budget["total_branch_run_budget"])
    if len(selected) != registered_state_budget:
        raise ValueError("Human portfolio differs from Planner-selected state budget")
    selected_states = {
        str(review["source_state_sha256"]) for review in selected
    }
    selected_candidates = {
        str(review["preferred_candidate_sha256"]) for review in selected
    }
    if (
        len(selected_states) != registered_state_budget
        or len(selected_candidates) != registered_state_budget
    ):
        raise ValueError("selected states/candidates must be unique")

    family_counts = Counter(
        str(review["task_family"]) for review in selected
    )
    selected_groups = [
        str(review["group_manifest_sha256"]) for review in selected
    ]
    if len(set(selected_groups)) != registered_state_budget:
        raise ValueError(
            f"current reference portfolio requires {registered_state_budget} unique groups"
        )

    if adjudication.get("selected_unique_group_count") != registered_state_budget:
        raise ValueError("adjudication selected group count mismatch")
    if adjudication.get("selected_condition_counts") != dict(
        Counter(str(review["preferred_condition"]) for review in selected)
    ):
        raise ValueError("selected condition-count mismatch")
    if adjudication.get("selected_task_family_counts") != dict(family_counts):
        raise ValueError("selected family-count mismatch")
    if adjudication.get("selected_source_state_sha256s") != [
        review["source_state_sha256"] for review in selected
    ]:
        raise ValueError("selected state list must follow review order")
    if adjudication.get("selected_candidate_sha256s") != [
        review["preferred_candidate_sha256"] for review in selected
    ]:
        raise ValueError("selected candidate list must follow review order")

    bottlenecks = adjudication.get("candidate_bottlenecks")
    if not isinstance(bottlenecks, list) or len(bottlenecks) < 2:
        raise ValueError("candidate bottlenecks must be present")
    selected_bottlenecks = [
        row
        for row in bottlenecks
        if isinstance(row, dict) and row.get("status") == "SELECTED"
    ]
    if len(selected_bottlenecks) != 1:
        raise ValueError("exactly one bottleneck must be selected")
    if selected_bottlenecks[0].get("candidate_id") != adjudication.get(
        "principal_bottleneck_id"
    ):
        raise ValueError("principal bottleneck mismatch")

    policy = adjudication.get("selection_policy")
    if not isinstance(policy, dict):
        raise ValueError("selection policy missing")
    required_policy = {
        "registered_state_budget": registered_state_budget,
        "paired_repetitions_per_state": paired_repetitions,
        "branch_arms_per_repetition": 2,
        "total_branch_run_budget": total_branch_runs,
        "selected_groups_must_be_unique": True,
        "selected_repairs_must_be_exact_action": True,
        "selected_x_disposition_must_be_accept": True,
        "no_outcome_adaptive_replacement": True,
        "no_condition_balance_quota": True,
        "a3_history_is_support_not_effect_authority": True,
        "success_trajectory_optimization_active": False,
    }
    for field, expected in required_policy.items():
        if policy.get(field) != expected:
            raise ValueError(
                f"selection policy {field} differs from frozen contract"
            )
    authority = policy.get(
        "state_budget_authority",
        "LEGACY_FIXED_REFERENCE_BUDGET"
        if registered_state_budget == 12
        else None,
    )
    if authority not in {
        "RESEARCH_PLANNER_PRE_SELECTED_UNIVERSE",
        "LEGACY_FIXED_REFERENCE_BUDGET",
    }:
        raise ValueError("selection policy state-budget authority mismatch")
    exact_two = policy.get("select_exactly_two_states_per_task_family")
    if exact_two is True:
        if registered_state_budget != 12:
            raise ValueError("legacy two-per-family rule is valid only for 12-state reference")
        if set(family_counts) != _EXPECTED_FAMILIES:
            raise ValueError("selected task-family universe mismatch")
        if any(count != 2 for count in family_counts.values()):
            raise ValueError("current reference portfolio requires two states per family")
    elif exact_two not in {False, None}:
        raise ValueError("select_exactly_two_states_per_task_family must be boolean")

    encoding = adjudication.get("ordinal_score_encoding")
    if not isinstance(encoding, dict):
        raise ValueError("ordinal score encoding missing")
    if encoding.get("not_calibrated_probability") is not True:
        raise ValueError("ordinal values must not be represented as calibrated")
    for dimension in (
        "expected_value",
        "expected_harm_risk",
        "evidence_support",
    ):
        mapping = encoding.get(dimension)
        if not isinstance(mapping, dict) or set(mapping) != _SCORE_CLASSES:
            raise ValueError(f"invalid ordinal mapping for {dimension}")
        for value in mapping.values():
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"invalid numeric encoding for {dimension}")

    if adjudication.get("automatic_environment_effect_assignment") is not False:
        raise ValueError("Human PRE cannot assign environment effects")
    if adjudication.get("human_pre_frozen") is not False:
        raise ValueError("adjudication candidate cannot be pre-frozen")
    if adjudication.get("strong_researcher_shadow_executed") is not False:
        raise ValueError("Strong shadow cannot precede Human PRE freeze")
    if adjudication.get("success_trajectory_optimization_active") is not False:
        raise ValueError("success optimization must remain inactive")

    for field in (
        "principal_bottleneck_statement",
        "single_falsifiable_hypothesis",
        "single_principal_change_id",
        "single_principal_change",
        "support_criterion",
        "refutation_criterion",
        "stop_condition",
        "primary_endpoint",
    ):
        _require_text(adjudication.get(field), field)
    _string_list(
        adjudication.get("observed_facts"),
        "observed_facts",
        allow_empty=False,
    )
    _string_list(
        adjudication.get("uncertainties"),
        "uncertainties",
        allow_empty=False,
    )
    _string_list(
        adjudication.get("secondary_diagnostics"),
        "secondary_diagnostics",
        allow_empty=False,
    )

    return {
        "round_input": round_input,
        "budget": budget,
        "candidate_index": candidate_index,
        "reviews": reviews,
        "selected": selected,
        "family_counts": dict(sorted(family_counts.items())),
    }


def _ordinal_value(
    adjudication: Mapping[str, object],
    dimension: str,
    score_class: str,
) -> float:
    encoding = adjudication["ordinal_score_encoding"]
    return float(encoding[dimension][score_class])


def build_repair_portfolio_v1(
    *,
    adjudication: Mapping[str, object],
    validation: Mapping[str, object],
) -> ResearchRepairPortfolioV1:
    principal_change_id = _require_text(
        adjudication.get("single_principal_change_id"),
        "single_principal_change_id",
    )
    candidates: list[ResearchRepairCandidateV1] = []

    for raw_review in validation["reviews"]:
        review = dict(raw_review)
        candidate_id = str(review["preferred_candidate_sha256"])
        selected = bool(review["selected_for_verification"])
        memory_ids = (
            ()
            if review["preferred_a3_memory_pack_sha256"] is None
            else (str(review["preferred_a3_memory_pack_sha256"]),)
        )
        analyzer_artifacts = tuple(
            dict.fromkeys(
                (
                    str(review["local_result_sha256"]),
                    str(review["source_proposal_sha256"]),
                    str(review["formal_group_result_sha256"]),
                    str(review["formal_x_crosscheck_sha256"]),
                )
            )
        )
        current_evidence = tuple(
            str(value)
            for value in review[
                "formal_x_supporting_evidence_sha256s"
            ]
        )

        repair_action = str(review["preferred_exact_action"])
        repair_contract = (
            "At the exact registered source state, execute exactly one "
            f"admissible action `{repair_action}`; count it against the "
            "shared environment budget; then return control to the frozen "
            "parent-policy continuation. No additional repair action, fuzzy menu "
            "matching, or outcome-adaptive replacement is permitted."
        )

        candidates.append(
            ResearchRepairCandidateV1(
                candidate_id=candidate_id,
                principal_change_id=principal_change_id,
                origin=RepairCandidateOriginV1.ANALYZER,
                repair_description=repair_action,
                repair_contract=repair_contract,
                mechanism_target=str(
                    review["human_evidence_summary"]
                ),
                task_family_scope=(str(review["task_family"]),),
                estimated_value=_ordinal_value(
                    adjudication,
                    "expected_value",
                    str(review["expected_value_class"]),
                ),
                estimated_harm_risk=_ordinal_value(
                    adjudication,
                    "expected_harm_risk",
                    str(review["expected_harm_risk_class"]),
                ),
                estimated_verification_calls=1,
                evidence_support=_ordinal_value(
                    adjudication,
                    "evidence_support",
                    str(review["evidence_support_class"]),
                ),
                novelty_or_nonduplication_reason=(
                    "Selected-group uniqueness and task-family coverage are "
                    "evaluated at portfolio level. "
                    + str(review["pair_adjudication_rationale"])
                ),
                disposition=(
                    RepairDispositionV1.SELECTED
                    if selected
                    else RepairDispositionV1.DEFERRED
                ),
                disposition_reason=str(
                    review["human_selection_rationale"]
                ),
                lineage=RepairLineageV1(
                    source_state_ids=(
                        str(review["source_state_sha256"]),
                    ),
                    source_candidate_ids=(candidate_id,),
                    source_group_ids=(
                        str(review["group_manifest_sha256"]),
                    ),
                    analyzer_artifact_sha256s=analyzer_artifacts,
                    memory_record_ids=memory_ids,
                    current_evidence_sha256s=current_evidence,
                ),
            )
        )

    selected_reviews = list(validation["selected"])
    selected_candidate_ids = tuple(
        str(review["preferred_candidate_sha256"])
        for review in selected_reviews
    )
    selected_state_ids = tuple(
        str(review["source_state_sha256"])
        for review in selected_reviews
    )
    selected_count = len(selected_state_ids)
    legacy_balanced = (
        selected_count == 12
        and adjudication["selection_policy"].get(
            "select_exactly_two_states_per_task_family"
        ) is True
    )

    program = ResearchRepairProgramV1(
        program_id=(
            "PROGRAM_VERIFY_12_EXACT_SOURCE_REPAIRS_V1"
            if legacy_balanced
            else f"PROGRAM_VERIFY_{selected_count}_PLANNER_SELECTED_SOURCE_REPAIRS_V2"
        ),
        principal_change_id=principal_change_id,
        kind=RepairProgramKindV1.DIRECT_SOURCE_REPAIR,
        candidate_ids=selected_candidate_ids,
        source_state_ids=selected_state_ids,
        falsifiable_hypothesis=str(
            adjudication["single_falsifiable_hypothesis"]
        ),
        high_value_rationale=(
            f"The Research Planner selected {selected_count} unique source "
            "states and candidates before current F0/F1 outcomes. The "
            "portfolio preserves unique-group, exact-action and Formal-X "
            "constraints without treating any historical state count as "
            "current scientific authority."
        ),
        generalization_scope=(
            "Source-conditioned repairs for the frozen parent-policy failure cohort. "
            "Any generalization beyond the registered source states must be "
            "established by later policy evaluation."
        ),
        deterministic_projector_contract=(
            "Use the exact selected candidate SHA and registered source "
            "state. F1 executes its single exact action once; F0 performs "
            "no repair. Both arms use the same task, prefix, hidden state, "
            "observation, menu, parent policy, Memory state, parser, decoding, budget, "
            "and paired continuation seed. Five pairs per state; four-of-"
            "five stability; no candidate replacement."
        ),
        verification_protocol_id=(
            "F0F1_REPAIR_VERIFICATION_V2_5_PAIRED_4_OF_5"
        ),
        estimated_verification_calls=selected_count,
    )

    portfolio = ResearchRepairPortfolioV1(
        schema_version="RESEARCH_REPAIR_PORTFOLIO_V1",
        round_id=str(adjudication["round_id"]),
        parent_policy_id=str(adjudication["parent_policy_id"]),
        evidence_cutoff_sha256=str(
            adjudication["evidence_cutoff_sha256"]
        ),
        principal_change_id=principal_change_id,
        researcher_mode="HUMAN_REFERENCE",
        decision=PortfolioDecisionV1.SELECT_ONE_PROGRAM,
        verification_call_budget=selected_count,
        candidates=tuple(candidates),
        programs=(program,),
        selected_program_id=program.program_id,
        abstention_reason=None,
    )
    portfolio.validate()
    return portfolio


def build_human_pre_input_v1(
    *,
    adjudication: Mapping[str, object],
) -> dict[str, object]:
    policy = adjudication.get("selection_policy")
    if not isinstance(policy, dict):
        raise ValueError("selection policy missing")
    state_budget = policy.get("registered_state_budget")
    repetitions = policy.get("paired_repetitions_per_state")
    arms = policy.get("branch_arms_per_repetition")
    branch_budget = policy.get("total_branch_run_budget")
    if type(state_budget) is not int or state_budget <= 0:
        raise ValueError("Planner-selected state budget must be positive")
    if type(repetitions) is not int or repetitions <= 0 or arms != 2:
        raise ValueError("invalid paired F0/F1 replication policy")
    if branch_budget != state_budget * repetitions * arms:
        raise ValueError("Planner branch budget derivation mismatch")
    return {
        "round_id": adjudication["round_id"],
        "policy_version": adjudication["parent_policy_id"],
        "evidence_cutoff": adjudication["evidence_cutoff_sha256"],
        "round_evidence_package_sha256": adjudication[
            "round_evidence_package_sha256"
        ],
        "observed_facts": list(adjudication["observed_facts"]),
        "uncertainties": list(adjudication["uncertainties"]),
        "candidate_bottlenecks": list(adjudication["candidate_bottlenecks"]),
        "selected_bottleneck_id": adjudication["principal_bottleneck_id"],
        "selection_rationale": adjudication["principal_bottleneck_statement"],
        "single_falsifiable_hypothesis": adjudication[
            "single_falsifiable_hypothesis"
        ],
        "single_principal_change": adjudication[
            "single_principal_change_id"
        ],
        "baseline": (
            "F0 reconstructs the exact registered source state and lets the "
            "frozen parent policy continue without a repair, under the "
            "frozen Memory, parser, prompt, decoding, policy-call budget, "
            "environment-step budget, and paired continuation seed."
        ),
        "intervention": (
            "F1 reconstructs the same source state, executes the one exact "
            "registered repair action, charges it to the same environment "
            "budget, and then returns control to the same frozen parent policy."
        ),
        "fixed_variables": [
            "task and gamefile identity",
            "full source prefix and hidden environment state",
            "current observation and exact admissible menu",
            "parent-policy checkpoint, config, prompt, parser, and decoding",
            "round-level Researcher Memory and policy-facing Memory state",
            "remaining policy-call and environment-step budgets",
            "paired continuation seed within each repetition",
            "success definition and artifact publication contract",
        ],
        "sample_definition": (
            f"{state_budget} unique source states selected by Research Planner "
            "PRE before current F0/F1 outcomes, exactly one candidate per "
            "state, unique Analyzer groups, exact single actions, and no "
            "outcome-adaptive replacement."
        ),
        "verification_budget": state_budget,
        "model_logical_call_budget": 0,
        "environment_budget": branch_budget,
        "gpu_budget_hours": 0.0,
        "primary_endpoint": adjudication["primary_endpoint"],
        "secondary_diagnostics": list(adjudication["secondary_diagnostics"]),
        "support_criterion": adjudication["support_criterion"],
        "refutation_criterion": adjudication["refutation_criterion"],
        "stop_condition": adjudication["stop_condition"],
    }

def _compact_memory_view(
    memory_view: Mapping[str, object],
) -> dict[str, object]:
    records = memory_view.get("train_side_records")
    compact_records = []
    if isinstance(records, list):
        for row in records:
            if not isinstance(row, dict):
                continue
            governed = row.get("governed_record")
            if not isinstance(governed, dict):
                continue
            semantic = governed.get("semantic_hypotheses")
            recoveries = governed.get("proposed_recoveries")
            applicability = governed.get("applicability")
            compact_records.append(
                {
                    "record_id": governed.get("record_id"),
                    "memory_lineage_id": governed.get(
                        "memory_lineage_id"
                    ),
                    "record_version": governed.get("record_version"),
                    "governance_state": governed.get(
                        "governance_state"
                    ),
                    "semantic_hypotheses": semantic,
                    "proposed_recoveries": recoveries,
                    "applicability": applicability,
                }
            )
    return {
        "schema_id": "COMPACT_RESEARCHER_MEMORY_VIEW_V1",
        "source_view_sha256": memory_view.get("view_sha256"),
        "snapshot_sha256": memory_view.get("snapshot_sha256"),
        "purpose": memory_view.get("purpose"),
        "train_side_record_count": len(compact_records),
        "train_side_records": compact_records,
        "heldout_aggregate_metrics": memory_view.get(
            "heldout_aggregate_metrics"
        ),
        "direct_environment_action_authority": False,
        "benefit_harm_authority": False,
    }


def _compact_candidate(
    candidate: Mapping[str, object],
) -> dict[str, object]:
    hypotheses = candidate.get("formal_group_mechanism_hypotheses")
    if not isinstance(hypotheses, list):
        hypotheses = []
    return {
        "condition_id": candidate.get("condition_id"),
        "candidate_sha256": candidate.get("candidate_sha256"),
        "source_state_sha256": candidate.get(
            "source_state_sha256"
        ),
        "task_family": (
            candidate.get("task_family_values") or [None]
        )[0],
        "group_manifest_sha256": candidate.get(
            "group_manifest_sha256"
        ),
        "local_result_sha256": candidate.get("local_result_sha256"),
        "source_proposal_sha256": candidate.get(
            "source_proposal_sha256"
        ),
        "formal_group_result_sha256": candidate.get(
            "formal_group_result_sha256"
        ),
        "repair_kind": candidate.get("repair_kind"),
        "exact_action": candidate.get("exact_action"),
        "option_actions": candidate.get("option_actions") or [],
        "termination_condition": candidate.get(
            "termination_condition"
        ),
        "top_group_hypotheses": [
            {
                "hypothesis_id": row.get("hypothesis_id"),
                "statement": row.get("statement"),
                "uncertainty": row.get("uncertainty"),
                "evidence_sha256s": row.get("evidence_sha256s") or [],
            }
            for row in hypotheses[:3]
            if isinstance(row, dict)
        ],
        "formal_x": candidate.get("formal_x_crosscheck"),
        "formal_x_disposition": candidate.get(
            "formal_x_disposition"
        ),
        "a3_analyzer_memory_pack_sha256": candidate.get(
            "a3_analyzer_memory_pack_sha256"
        ),
        "a3_analyzer_memory_summary": candidate.get(
            "a3_analyzer_memory_summary"
        ),
        "effect_label_authority": False,
    }


def build_strong_researcher_blind_pre_input_v1(
    *,
    dossier: Mapping[str, object],
    shared_input: Mapping[str, object],
) -> dict[str, object]:
    """Build the exact evidence package for the blind Strong shadow.

    This function deliberately has no adjudication/Human-PRE argument. That
    makes Human selection, rationale, hashes and portfolio IDs unavailable by
    construction.
    """

    if dossier.get("schema_id") != (
        "EVIDENCE_RICH_A2_A3_PAIR_DOSSIER_V2"
    ):
        raise ValueError("blind input dossier schema mismatch")
    if dossier.get("status") != "READY_FOR_HUMAN_SCIENTIFIC_REVIEW":
        raise ValueError("blind input dossier is not review-ready")
    if shared_input.get("schema_id") != (
        "RESEARCH_PLANNER_SHARED_PRE_INPUT_CANDIDATE_V2"
    ):
        raise ValueError("blind input shared schema mismatch")

    round_input = _round_input(shared_input)
    budget = _budget_plan(shared_input)
    memory_view = shared_input.get(
        "round_level_researcher_memory_view",
        shared_input.get("researcher_memory_view"),
    )
    if not isinstance(memory_view, dict):
        raise ValueError("shared input lacks Researcher Memory view")

    candidate_index = _candidate_index(dossier)
    pairs: list[dict[str, object]] = []
    for state in sorted(
        {
            state_sha
            for state_sha, _ in candidate_index
        }
    ):
        pair = {
            condition: _compact_candidate(
                candidate_index[(state, condition)]
            )
            for condition in ("A2", "A3")
        }
        pairs.append(
            {
                "source_state_sha256": state,
                "A2": pair["A2"],
                "A3": pair["A3"],
            }
        )

    if len(pairs) != 30:
        raise ValueError("blind input must contain 30 A2/A3 pairs")

    result = {
        "schema_id": "STRONG_RESEARCHER_BLIND_PRE_INPUT_V1",
        "schema_version": 1,
        "round_id": round_input["round_id"],
        "parent_policy_id": round_input["parent_policy_id"],
        "evidence_cutoff_sha256": round_input[
            "input_package_sha256"
        ],
        "round_evidence_package_sha256": round_input[
            "round_evidence_package_sha256"
        ],
        "policy_scorecard": round_input[
            "current_policy_scorecard"
        ],
        "analyzer_evidence": round_input["analyzer_evidence"],
        "experiment_history": round_input["experiment_history"],
        "resource_and_cost": round_input["resource_and_cost"],
        "researcher_memory_view": _compact_memory_view(
            memory_view
        ),
        "verification_budget_plan": budget,
        "registered_candidate_universe": {
            "candidate_count": 60,
            "source_state_count": 30,
            "condition_counts": {"A2": 30, "A3": 30},
            "formal_x_candidate_disposition_counts": dossier.get(
                "formal_x_candidate_disposition_counts",
                dossier.get("candidate_x_disposition_counts"),
            ),
            "a2_analyzer_memory_binding_count": dossier[
                "a2_analyzer_memory_binding_count"
            ],
            "a3_analyzer_memory_binding_count": dossier[
                "a3_analyzer_memory_binding_count"
            ],
            "unique_a3_analyzer_memory_pack_count": dossier[
                "unique_a3_analyzer_memory_pack_count"
            ],
            "pair_table": pairs,
        },
        "researcher_role_contract": {
            "role": "TRAINING_RESEARCHER",
            "stage": "PRE_DECISION_SHADOW",
            "objective": (
                "Independently identify the round's principal bottleneck, "
                "compare the 30 A2/A3 repair pairs using current evidence, "
                "counterevidence, Formal X, historical Failure Experience, "
                "expected value, Harm risk and verification cost, and select "
                "one bounded repair program under the frozen budget."
            ),
            "must_output": [
                "observed facts and uncertainties",
                "all candidate bottlenecks",
                "one selected bottleneck",
                "rejected and deferred directions",
                "evidence and counterevidence",
                "one falsifiable hypothesis",
                "one principal scientific change",
                "exact selected source states and candidate SHAs",
                "expected value, Harm risk and cost for every selected repair",
                "verification endpoint, support/refutation and stop rules",
                "training recommendation at PRE",
            ],
            "must_not_do": [
                "assign Benefit/Harm/Neutral/Uncertain",
                "execute environment actions",
                "change the frozen budget after outcomes",
                "read or infer the Human PRE decision",
                "read strong-model benchmark per-task results",
                "activate success-trajectory optimization",
                "promote a policy",
            ],
            "effect_authority": (
                "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY"
            ),
            "promotion_authority": (
                "DETERMINISTIC_INDEPENDENT_GATE_ONLY"
            ),
        },
        "required_output_contract": {
            "schema_id": "STRONG_RESEARCHER_PRE_SHADOW_V1",
            "selected_state_budget": budget["registered_state_budget"],
            "paired_repetitions_per_state": budget[
                "paired_repetitions_per_state"
            ],
            "branch_run_budget": budget["total_branch_run_budget"],
            "selected_candidates_must_come_from_input": True,
            "selected_source_states_must_be_unique": True,
            "pre_outcome_predictions_required": True,
            "abstention_allowed_with_reason": True,
        },
        "visibility_boundary": {
            "human_pre_visible": False,
            "human_pre_hash_visible": False,
            "human_selection_visible": False,
            "human_rationale_visible": False,
            "current_f0f1_outcomes_visible": False,
            "future_policy_evaluation_visible": False,
            "strong_model_benchmark_per_task_results_visible": False,
            "success_trajectory_optimization_active": False,
        },
        "blind_input_sha256": "0" * 64,
    }
    result["blind_input_sha256"] = domain_hash(
        "STRONG_RESEARCHER_BLIND_PRE_INPUT_V1",
        result,
        excluded_field="blind_input_sha256",
    )

    forbidden = _contains_forbidden(result)
    if forbidden:
        raise ValueError(
            "blind input contains forbidden keys: "
            + repr(sorted(forbidden))
        )
    decision_leak_keys = {
        "state_reviews",
        "selected_source_state_sha256s",
        "selected_candidate_sha256s",
        "selected_condition_counts",
        "selected_task_family_counts",
        "human_selection_rationale",
        "human_expected_value",
        "human_harm_risk",
        "human_approval",
    }.intersection(_walk_keys(result))
    if decision_leak_keys:
        raise ValueError(
            "blind input leaks Human decision fields: "
            + repr(sorted(decision_leak_keys))
        )
    serialized = json.dumps(
        result,
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    for forbidden_text in (
        "human_planner_scientific_adjudication",
        "human_researcher_pre",
        "selected_condition_counts",
        "selected_task_family_counts",
        "assistant_prepared_requires_user_approval",
    ):
        if forbidden_text in serialized:
            raise ValueError(
                "blind input leaks Human decision marker: "
                + forbidden_text
            )
    return result


def build_reference_trace_pre_v1(
    *,
    adjudication: Mapping[str, object],
    portfolio: ResearchRepairPortfolioV1,
    human_pre_input: Mapping[str, object],
    strong_blind_input: Mapping[str, object],
) -> dict[str, object]:
    adjudication_sha = hashlib.sha256(
        canonical_json_bytes(dict(adjudication))
    ).hexdigest()
    portfolio_sha = hashlib.sha256(
        canonical_json_bytes(portfolio.to_dict())
    ).hexdigest()
    human_pre_candidate_sha = domain_hash(
        "HUMAN_RESEARCHER_PRE_INPUT_CANDIDATE_V1",
        dict(human_pre_input),
    )
    selected = [
        row
        for row in adjudication["state_reviews"]
        if row["selected_for_verification"]
    ]

    trace = {
        "schema_id": "RESEARCH_PLANNER_REFERENCE_TRACE_V2",
        "schema_version": 2,
        "round_id": adjudication["round_id"],
        "parent_policy_id": adjudication["parent_policy_id"],
        "evidence_cutoff_sha256": adjudication[
            "evidence_cutoff_sha256"
        ],
        "pre_decision": {
            "human_adjudication_sha256": adjudication_sha,
            "human_pre_input_candidate_sha256": human_pre_candidate_sha,
            "repair_portfolio_file_sha256": portfolio_sha,
            "strong_blind_input_sha256": strong_blind_input[
                "blind_input_sha256"
            ],
            "principal_bottleneck_id": adjudication[
                "principal_bottleneck_id"
            ],
            "principal_change_id": adjudication[
                "single_principal_change_id"
            ],
            "selected_source_state_sha256s": [
                row["source_state_sha256"] for row in selected
            ],
            "selected_candidate_sha256s": [
                row["preferred_candidate_sha256"] for row in selected
            ],
            "predicted_effects": [
                {
                    "source_state_sha256": row[
                        "source_state_sha256"
                    ],
                    "candidate_sha256": row[
                        "preferred_candidate_sha256"
                    ],
                    "condition_id": row["preferred_condition"],
                    "expected_value_class": row[
                        "expected_value_class"
                    ],
                    "expected_harm_risk_class": row[
                        "expected_harm_risk_class"
                    ],
                    "evidence_support_class": row[
                        "evidence_support_class"
                    ],
                    "selection_rationale": row[
                        "human_selection_rationale"
                    ],
                }
                for row in selected
            ],
            "training_policy_status": adjudication[
                "training_policy_at_pre"
            ]["status"],
            "exact_training_mixture_frozen": False,
        },
        "strong_shadow": {
            "executed": False,
            "raw_output_sha256": None,
            "parsed_decision_sha256": None,
            "field_level_adjudication_sha256": None,
        },
        "environment_feedback": {
            "f0f1_manifest_sha256": None,
            "label_census": None,
            "benefit_per_branch_run": None,
            "environment_steps_per_benefit": None,
            "unexpected_harm_cases": [],
        },
        "post_decision": {
            "human_post_sha256": None,
            "strong_shadow_post_sha256": None,
            "hypothesis_status": None,
            "training_mixture_manifest_sha256": None,
            "training_recommendation": None,
            "memory_writeback_sha256": None,
            "next_round_implication": None,
        },
        "localization_supervision": {
            "preserve_exact_shared_input": True,
            "preserve_human_pre": True,
            "preserve_strong_shadow_pre": True,
            "preserve_field_level_adjudication": True,
            "preserve_actual_environment_outcomes": True,
            "preserve_human_post": True,
            "preserve_rejected_and_deferred_directions": True,
            "target_roles": [
                "STRONG_API_SHADOW",
                "LOCAL_SHADOW",
                "LOCAL_PRIMARY",
            ],
        },
        "authority_boundary": {
            "human_researcher_effect_authority": False,
            "strong_researcher_effect_authority": False,
            "environment_verifier_effect_authority": True,
            "promotion_gate_authority": True,
        },
        "trace_sha256": "0" * 64,
    }
    trace["trace_sha256"] = domain_hash(
        "RESEARCH_PLANNER_REFERENCE_TRACE_V2",
        trace,
        excluded_field="trace_sha256",
    )
    return trace


def build_role_neutral_human_pre_decision_v1(
    *,
    adjudication: Mapping[str, object],
    portfolio: ResearchRepairPortfolioV1,
) -> ResearcherPreDecisionV1:
    adjudication_sha = hashlib.sha256(
        canonical_json_bytes(dict(adjudication))
    ).hexdigest()
    portfolio_sha = hashlib.sha256(
        canonical_json_bytes(portfolio.to_dict())
    ).hexdigest()
    bottlenecks = adjudication["candidate_bottlenecks"]
    rejected = tuple(
        str(row["candidate_id"])
        for row in bottlenecks
        if row["status"] == "REJECTED"
    )
    deferred = tuple(
        str(row["candidate_id"])
        for row in bottlenecks
        if row["status"] == "DEFERRED"
    )
    budget_id = domain_hash(
        "HUMAN_REFERENCE_VERIFICATION_BUDGET_V1",
        adjudication["selection_policy"],
    )
    stop_rule_id = domain_hash(
        "HUMAN_REFERENCE_STOP_RULE_V1",
        {
            "support_criterion": adjudication[
                "support_criterion"
            ],
            "refutation_criterion": adjudication[
                "refutation_criterion"
            ],
            "stop_condition": adjudication["stop_condition"],
        },
    )
    decision = ResearcherPreDecisionV1(
        schema_version="RESEARCHER_PRE_DECISION_V1",
        round_id=str(adjudication["round_id"]),
        parent_policy_id=str(adjudication["parent_policy_id"]),
        researcher_role_mode=ResearcherRoleModeV1.HUMAN_REFERENCE,
        raw_artifact_sha256=adjudication_sha,
        evidence_cutoff_sha256=str(
            adjudication["evidence_cutoff_sha256"]
        ),
        candidate_bottleneck_ids=tuple(
            str(row["candidate_id"]) for row in bottlenecks
        ),
        selected_bottleneck_id=str(
            adjudication["principal_bottleneck_id"]
        ),
        selected_principal_change_id=str(
            adjudication["single_principal_change_id"]
        ),
        rejected_direction_ids=rejected,
        deferred_direction_ids=deferred,
        repair_portfolio_sha256=portfolio_sha,
        verification_budget_id=budget_id,
        training_plan_id=(
            "HOLD_PENDING_VERIFIED_F0F1_MANIFEST"
        ),
        stop_rule_id=stop_rule_id,
    )
    decision.validate()
    return decision


def compile_human_planner_artifacts_v1(
    *,
    adjudication: Mapping[str, object],
    dossier: Mapping[str, object],
    shared_input: Mapping[str, object],
) -> dict[str, object]:
    validation = validate_human_planner_adjudication_v1(
        adjudication=adjudication,
        dossier=dossier,
        shared_input=shared_input,
    )
    portfolio = build_repair_portfolio_v1(
        adjudication=adjudication,
        validation=validation,
    )
    human_pre = build_human_pre_input_v1(
        adjudication=adjudication,
    )
    strong_input = build_strong_researcher_blind_pre_input_v1(
        dossier=dossier,
        shared_input=shared_input,
    )
    trace = build_reference_trace_pre_v1(
        adjudication=adjudication,
        portfolio=portfolio,
        human_pre_input=human_pre,
        strong_blind_input=strong_input,
    )
    role_neutral = build_role_neutral_human_pre_decision_v1(
        adjudication=adjudication,
        portfolio=portfolio,
    )

    selected = list(validation["selected"])
    report = {
        "schema_id": "HUMAN_PLANNER_ADJUDICATION_BUILD_REPORT_V1",
        "schema_version": 1,
        "status": "READY_FOR_USER_SCIENTIFIC_APPROVAL",
        "round_id": adjudication["round_id"],
        "human_adjudication_sha256": role_neutral.raw_artifact_sha256,
        "human_pre_input_candidate_sha256": domain_hash(
            "HUMAN_RESEARCHER_PRE_INPUT_CANDIDATE_V1",
            human_pre,
        ),
        "repair_portfolio_file_sha256": (
            role_neutral.repair_portfolio_sha256
        ),
        "strong_blind_input_sha256": strong_input[
            "blind_input_sha256"
        ],
        "reference_trace_sha256": trace["trace_sha256"],
        "reviewed_state_count": 30,
        "selected_state_count": len(selected),
        "selected_candidate_count": len(selected),
        "selected_unique_group_count": adjudication[
            "selected_unique_group_count"
        ],
        "selected_condition_counts": adjudication[
            "selected_condition_counts"
        ],
        "selected_task_family_counts": adjudication[
            "selected_task_family_counts"
        ],
        "selected_repair_kind_counts": dict(
            Counter(
                str(row["preferred_repair_kind"])
                for row in selected
            )
        ),
        "selected_x_disposition_counts": dict(
            Counter(
                str(row["preferred_x_disposition"])
                for row in selected
            )
        ),
        "human_approval_status": adjudication[
            "human_approval"
        ]["status"],
        "human_pre_frozen": False,
        "strong_researcher_shadow_executed": False,
        "f0f1_executed": False,
        "training_executed": False,
        "success_trajectory_optimization_active": False,
        "next_gate": (
            "USER_APPROVAL_OF_HUMAN_PLANNER_SCIENTIFIC_ADJUDICATION"
        ),
    }

    return {
        "adjudication": dict(adjudication),
        "repair_portfolio": portfolio.to_dict(),
        "human_pre_input": human_pre,
        "strong_blind_input": strong_input,
        "reference_trace": trace,
        "role_neutral_pre_decision": role_neutral.to_dict(),
        "build_report": report,
    }

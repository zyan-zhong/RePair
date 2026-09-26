from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import re

from pchsi.reference_loop.canonical import domain_hash
from pchsi.cognitive_runtime.schema_registry import validate_artifact


_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and _SHA_RE.fullmatch(value) is not None


def _collect_sha_values(value: object) -> set[str]:
    out: set[str] = set()

    def walk(current: object) -> None:
        if isinstance(current, Mapping):
            for child in current.values():
                walk(child)
            return
        if isinstance(current, list):
            for child in current:
                walk(child)
            return
        if _valid_sha(current):
            out.add(str(current))

    walk(value)
    return out


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be one object")
    return value


def _require_list(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be one array")
    return value


def finalize_strong_researcher_pre_shadow_v2(
    value: Mapping[str, object],
    *,
    projection: Mapping[str, object],
) -> dict[str, object]:
    blind = _require_mapping(
        projection.get("blind_input"),
        "hydrated Strong blind input",
    )

    if blind.get("schema_id") != "STRONG_RESEARCHER_BLIND_PRE_INPUT_V2":
        raise ValueError("hydrated Strong blind input schema mismatch")

    expected_blind_sha = blind.get("blind_input_sha256")
    expected_hydration_sha = blind.get(
        "evidence_hydration_manifest_sha256"
    )
    if not _valid_sha(expected_blind_sha):
        raise ValueError("blind input identity invalid")
    if not _valid_sha(expected_hydration_sha):
        raise ValueError("hydration identity invalid")

    if projection.get("blind_input_sha256") != expected_blind_sha:
        raise ValueError("projection blind-input identity mismatch")
    if projection.get(
        "evidence_hydration_manifest_sha256"
    ) != expected_hydration_sha:
        raise ValueError("projection hydration identity mismatch")
    if projection.get("human_pre_gate_satisfied") is not True:
        raise ValueError("Human PRE gate is not satisfied")
    if projection.get("human_pre_content_visible") is not False:
        raise ValueError("Human PRE content visibility must be false")
    if projection.get("human_pre_hash_visible") is not False:
        raise ValueError("Human PRE hash visibility must be false")

    out = dict(value)
    if out.get("schema_id") != "STRONG_RESEARCHER_PRE_SHADOW_V2":
        raise ValueError("Strong PRE shadow schema mismatch")
    if out.get("schema_version") != 2:
        raise ValueError("Strong PRE shadow schema version mismatch")
    if out.get("round_id") != blind.get("round_id"):
        raise ValueError("Strong PRE shadow round binding mismatch")
    if out.get("blind_input_sha256") != expected_blind_sha:
        raise ValueError("Strong PRE shadow blind-input binding mismatch")
    if out.get(
        "evidence_hydration_manifest_sha256"
    ) != expected_hydration_sha:
        raise ValueError("Strong PRE shadow hydration binding mismatch")
    if out.get("automatic_environment_effect_assignment") is not False:
        raise ValueError("Strong PRE shadow may not assign environment effects")
    if out.get("effect_authority") != (
        "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY"
    ):
        raise ValueError("Strong PRE shadow effect authority mismatch")
    if out.get("promotion_authority") != (
        "DETERMINISTIC_INDEPENDENT_GATE_ONLY"
    ):
        raise ValueError("Strong PRE shadow promotion authority mismatch")

    # Bottleneck contract: exactly one SELECTED candidate and ID binding.
    bottlenecks = _require_list(
        out.get("candidate_bottlenecks"),
        "candidate_bottlenecks",
    )
    selected_bottlenecks = [
        row
        for row in bottlenecks
        if isinstance(row, Mapping)
        and row.get("status") == "SELECTED"
    ]
    if len(selected_bottlenecks) != 1:
        raise ValueError(
            "Strong PRE shadow must select exactly one bottleneck"
        )
    if selected_bottlenecks[0].get("candidate_id") != out.get(
        "selected_bottleneck_id"
    ):
        raise ValueError("selected bottleneck ID mismatch")

    # Evidence citations must come from the blind-input identity universe.
    allowed_sha = _collect_sha_values(blind)
    for row in bottlenecks:
        item = _require_mapping(row, "candidate bottleneck")
        for field in (
            "evidence_sha256s",
            "counterevidence_sha256s",
        ):
            refs = _require_list(item.get(field), field)
            if any(not _valid_sha(ref) for ref in refs):
                raise ValueError(f"{field} contains invalid SHA")
            if not set(refs) <= allowed_sha:
                raise ValueError(
                    f"{field} cites SHA outside blind-input evidence universe"
                )

    candidate_universe = _require_mapping(
        blind.get("registered_candidate_universe"),
        "registered_candidate_universe",
    )
    pair_table = _require_list(
        candidate_universe.get("pair_table"),
        "pair_table",
    )
    if len(pair_table) != 30:
        raise ValueError("Strong PRE shadow requires exactly 30 candidate pairs")

    reviews = _require_list(out.get("state_reviews"), "state_reviews")
    if len(reviews) != len(pair_table):
        raise ValueError("state-review count must match 30-pair universe")

    selected_rows: list[Mapping[str, object]] = []
    for index, (raw_review, raw_pair) in enumerate(
        zip(reviews, pair_table, strict=True)
    ):
        review = _require_mapping(raw_review, "state review")
        pair = _require_mapping(raw_pair, "candidate pair")

        if review.get("state_index") != index:
            raise ValueError("state reviews must preserve pair-table order")

        source_state = pair.get("source_state_sha256")
        if review.get("source_state_sha256") != source_state:
            raise ValueError("state-review source-state binding mismatch")

        a2 = _require_mapping(pair.get("A2"), "A2 pair arm")
        a3 = _require_mapping(pair.get("A3"), "A3 pair arm")
        if a2.get("source_state_sha256") != source_state:
            raise ValueError("A2 source-state binding mismatch")
        if a3.get("source_state_sha256") != source_state:
            raise ValueError("A3 source-state binding mismatch")

        preferred_condition = review.get("preferred_condition")
        alternative_condition = review.get("alternative_condition")
        if {
            preferred_condition,
            alternative_condition,
        } != {"A2", "A3"}:
            raise ValueError(
                "state review must prefer one A2/A3 arm and retain the other"
            )

        preferred = a2 if preferred_condition == "A2" else a3
        alternative = a2 if alternative_condition == "A2" else a3

        if review.get("preferred_candidate_sha256") != preferred.get(
            "candidate_sha256"
        ):
            raise ValueError("preferred candidate is outside registered pair")
        if review.get("alternative_candidate_sha256") != alternative.get(
            "candidate_sha256"
        ):
            raise ValueError("alternative candidate is outside registered pair")
        if review.get("preferred_x_disposition") != preferred.get(
            "formal_x_disposition"
        ):
            raise ValueError("preferred Formal-X disposition mismatch")
        if review.get("alternative_x_disposition") != alternative.get(
            "formal_x_disposition"
        ):
            raise ValueError("alternative Formal-X disposition mismatch")

        task_family = a2.get("task_family")
        if a3.get("task_family") != task_family:
            raise ValueError("A2/A3 task-family mismatch")
        if review.get("task_family") != task_family:
            raise ValueError("state-review task-family mismatch")

        branch_runs_per_state = blind.get(
            "verification_budget_plan", {}
        ).get("branch_runs_per_state")
        if review.get("verification_cost_branch_runs") != (
            branch_runs_per_state
        ):
            raise ValueError("state-review verification cost mismatch")

        selected = review.get("selected_for_verification")
        disposition = review.get("state_portfolio_disposition")
        if selected is True:
            if disposition != "SELECTED":
                raise ValueError(
                    "selected state must have SELECTED portfolio disposition"
                )
            selected_rows.append(review)
        else:
            if disposition == "SELECTED":
                raise ValueError(
                    "unselected state cannot have SELECTED disposition"
                )

    selected_count = len(selected_rows)
    budget_ceiling = blind.get(
        "required_output_contract", {}
    ).get("selected_state_budget")
    if type(budget_ceiling) is not int or budget_ceiling != 12:
        raise ValueError("blind selected-state budget must equal 12")
    if selected_count > budget_ceiling:
        raise ValueError("Strong PRE shadow exceeds selected-state budget")
    if out.get("selected_state_count") != selected_count:
        raise ValueError("selected_state_count mismatch")
    if out.get("unused_state_budget") != (
        budget_ceiling - selected_count
    ):
        raise ValueError("unused_state_budget mismatch")

    expected_sources = [
        str(row["source_state_sha256"])
        for row in selected_rows
    ]
    expected_candidates = [
        str(row["preferred_candidate_sha256"])
        for row in selected_rows
    ]
    if out.get("selected_source_state_sha256s") != expected_sources:
        raise ValueError("selected source-state list mismatch")
    if out.get("selected_candidate_sha256s") != expected_candidates:
        raise ValueError("selected candidate list mismatch")
    if len(expected_sources) != len(set(expected_sources)):
        raise ValueError("selected source states are not unique")
    if len(expected_candidates) != len(set(expected_candidates)):
        raise ValueError("selected candidate identities are not unique")

    condition_counts = Counter(
        str(row["preferred_condition"])
        for row in selected_rows
    )
    observed_counts = _require_mapping(
        out.get("selected_condition_counts"),
        "selected_condition_counts",
    )
    if observed_counts.get("A2") != condition_counts["A2"]:
        raise ValueError("selected A2 count mismatch")
    if observed_counts.get("A3") != condition_counts["A3"]:
        raise ValueError("selected A3 count mismatch")

    abstention_reason = out.get("abstention_reason")
    if selected_count == budget_ceiling:
        if abstention_reason is not None:
            raise ValueError(
                "full 12-state portfolio must not carry abstention reason"
            )
    else:
        if not isinstance(abstention_reason, str) or not abstention_reason:
            raise ValueError(
                "unused verification budget requires abstention reason"
            )

    plan = _require_mapping(out.get("verification_plan"), "verification_plan")
    frozen_plan = _require_mapping(
        blind.get("verification_budget_plan"),
        "blind verification_budget_plan",
    )
    expected_repetitions = frozen_plan.get(
        "paired_repetitions_per_state"
    )
    expected_arms = frozen_plan.get("branch_arms_per_repetition")
    expected_per_state = frozen_plan.get("branch_runs_per_state")
    total_ceiling = frozen_plan.get("total_branch_run_budget")

    checks = {
        "selected_state_budget_ceiling": budget_ceiling,
        "paired_repetitions_per_state": expected_repetitions,
        "branch_arms_per_repetition": expected_arms,
        "branch_runs_per_state": expected_per_state,
        "total_branch_run_budget_ceiling": total_ceiling,
        "outcome_adaptive_budget_change_allowed": False,
        "unfavorable_candidate_replacement_allowed": False,
    }
    for field, expected in checks.items():
        if plan.get(field) != expected:
            raise ValueError(
                f"verification plan frozen-field mismatch: {field}"
            )

    selected_branch_runs = selected_count * int(expected_per_state)
    if plan.get("selected_branch_run_budget") != selected_branch_runs:
        raise ValueError("selected branch-run budget mismatch")
    if selected_branch_runs > int(total_ceiling):
        raise ValueError("selected branch-run budget exceeds ceiling")

    resource = _require_mapping(out.get("resource_plan"), "resource_plan")
    if resource.get("expected_environment_branch_runs") != (
        selected_branch_runs
    ):
        raise ValueError("resource-plan environment branch-run mismatch")

    memory = _require_mapping(
        out.get("memory_usage_summary"),
        "memory_usage_summary",
    )
    if memory.get("memory_effect_authority") is not False:
        raise ValueError("Memory cannot have effect authority")

    training = _require_mapping(
        out.get("training_policy_at_pre"),
        "training_policy_at_pre",
    )
    if training.get("status") != (
        "HOLD_PENDING_VERIFIED_F0F1_MANIFEST"
    ):
        raise ValueError("training must remain on HOLD at PRE")
    if training.get("exact_training_mixture_frozen") is not False:
        raise ValueError("PRE may not freeze exact training mixture")

    out["shadow_record_sha256"] = "0" * 64
    out["shadow_record_sha256"] = domain_hash(
        "STRONG_RESEARCHER_PRE_SHADOW_V2",
        out,
        excluded_field="shadow_record_sha256",
    )
    validate_artifact("STRONG_RESEARCHER_PRE_SHADOW_V2", out)
    return out

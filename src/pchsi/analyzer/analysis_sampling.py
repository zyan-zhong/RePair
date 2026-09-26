"""Human-approved, census-bound, failure-priority offline sampling."""

from __future__ import annotations
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import math
from pathlib import Path

from pchsi.reference_loop.canonical import domain_hash, strict_json_loads
from .authorities import AnalysisRegime, TrajectoryOutcome
from .outcome_router import validate_census_semantics
from .schema_contract import validate_payload_against_schema, verify_domain_hash


EXACT_SHARES = {
    AnalysisRegime.FAILURE_CRITICAL.value: 0.85,
    AnalysisRegime.MIXED_PERFORMANCE.value: 0.70,
    AnalysisRegime.HIGH_SUCCESS_REFINEMENT.value: 0.55,
}


@dataclass(frozen=True)
class AnalysisUnit:
    unit_id: str
    task_id: str
    gamefile_sha256: str
    task_family: str | None
    outcome: TrajectoryOutcome
    frozen_order: int
    severe_failure: bool = False
    regression_failure: bool = False
    unresolved_cross_task_failure: bool = False
    success_inefficiency_flag: bool = False
    regression_guard_priority: bool = False


@dataclass(frozen=True)
class MechanicalPolicySignals:
    severe_failure_count: int = 0
    regression_failure_count: int = 0
    unresolved_cross_task_failure_count: int = 0

    def validate(self) -> None:
        for name, value in self.__dict__.items():
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be non-negative integer")


def default_manifest_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "configs/analyzer/mechanical_analysis_sampling_thresholds_v1.json"
    )


def load_sampling_approval(path: Path | None = None) -> dict[str, object]:
    source = default_manifest_path() if path is None else path
    if source.is_symlink() or not source.is_file():
        raise ValueError("sampling approval manifest must be regular no-symlink file")
    value = strict_json_loads(source.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("sampling approval manifest must be object")
    observed = domain_hash(
        "MECHANICAL_ANALYSIS_SAMPLING_THRESHOLDS_V1",
        value,
        excluded_field="approval_sha256",
    )
    if value.get("approval_sha256") != observed:
        raise ValueError("sampling approval SHA mismatch")
    if value.get("approval_status") != "HUMAN_APPROVED_OPERATIONAL_PILOT":
        raise ValueError("sampling thresholds lack human approval")
    if value.get("scheduler_role") != "MECHANICAL_SAMPLING_ONLY":
        raise ValueError("sampling scheduler role is invalid")
    if value.get("research_priority_authority") != "NOT_AUTHORIZED":
        raise ValueError("sampling manifest grants forbidden authority")
    if value.get("formal_a0_a3_u_reg_unchanged") is not True:
        raise ValueError("sampling manifest mutates formal U_reg")
    if value.get("failure_share_by_regime") != EXACT_SHARES:
        raise ValueError("approved 85/70/55 shares were altered")
    if value.get("threshold_claim_status") != (
        "OPERATIONAL_PILOT_NOT_A_PAPER_METHOD_CLAIM"
    ):
        raise ValueError("sampling threshold claim status is invalid")
    return value


def _family_rates(census: Mapping[str, object]) -> list[float]:
    out = []
    for row in census["task_family_rows"]:
        scientific = row["scientific_count"]
        if scientific:
            out.append(row["success_count"] / scientific)
    return out


def select_analysis_regime(
    *,
    census: Mapping[str, object],
    signals: MechanicalPolicySignals,
    approval_manifest_path: Path | None = None,
) -> AnalysisRegime:
    validate_census_semantics(census)
    signals.validate()
    policy = load_sampling_approval(approval_manifest_path)
    if (
        signals.severe_failure_count
        or signals.regression_failure_count
        or signals.unresolved_cross_task_failure_count
    ):
        return AnalysisRegime.FAILURE_CRITICAL
    scientific = census["scientific_outcome_count"]
    if scientific == 0:
        return AnalysisRegime.FAILURE_CRITICAL
    success = census["outcome_counts"]["SUCCESS"]
    failure = census["outcome_counts"]["FAILURE"]
    failure_rate = failure / scientific
    if failure_rate >= policy["failure_critical_failure_rate_minimum"]:
        return AnalysisRegime.FAILURE_CRITICAL
    overall = success / scientific
    rates = _family_rates(census)
    if (
        overall >= policy["high_success_overall_rate_minimum"]
        and (not rates or min(rates) >= policy["high_success_family_rate_minimum"])
    ):
        return AnalysisRegime.HIGH_SUCCESS_REFINEMENT
    return AnalysisRegime.MIXED_PERFORMANCE


def _largest_remainder(total: int, failure_share: float) -> tuple[int, int]:
    raw_failure = total * failure_share
    raw_success = total - raw_failure
    failure = math.floor(raw_failure)
    success = math.floor(raw_success)
    remainder = total - failure - success
    fractions = [
        (raw_failure - failure, 0, "failure"),
        (raw_success - success, 1, "success"),
    ]
    for _, _, label in sorted(fractions, key=lambda x: (-x[0], x[1]))[:remainder]:
        if label == "failure":
            failure += 1
        else:
            success += 1
    return failure, success


def _family_order_key(family: str | None, order: list[str]) -> tuple[int, str]:
    token = "__UNCLASSIFIED__" if family is None else family
    return (
        order.index(token) if token in order else len(order),
        token,
    )


def allocate_analysis_sampling(
    *,
    units: Iterable[AnalysisUnit],
    census: Mapping[str, object],
    total_analysis_budget: int,
    signals: MechanicalPolicySignals | None = None,
    approval_manifest_path: Path | None = None,
) -> dict[str, object]:
    if type(total_analysis_budget) is not int or total_analysis_budget < 0:
        raise ValueError("total_analysis_budget must be non-negative integer")
    validate_census_semantics(census)
    policy = load_sampling_approval(approval_manifest_path)
    rows = list(units)
    if len({u.unit_id for u in rows}) != len(rows):
        raise ValueError("analysis unit IDs must be unique")
    for unit in rows:
        if not isinstance(unit.outcome, TrajectoryOutcome):
            raise ValueError("analysis unit outcome must be frozen enum")
        if unit.frozen_order < 0:
            raise ValueError("analysis unit frozen_order must be non-negative")
    regime = select_analysis_regime(
        census=census,
        signals=signals or MechanicalPolicySignals(),
        approval_manifest_path=approval_manifest_path,
    )
    share = EXACT_SHARES[regime.value]
    failure_target, success_target = _largest_remainder(
        total_analysis_budget, share
    )

    failures = sorted(
        (u for u in rows if u.outcome is TrajectoryOutcome.FAILURE),
        key=lambda u: (
            not u.regression_failure,
            not u.severe_failure,
            not u.unresolved_cross_task_failure,
            u.frozen_order,
            u.unit_id,
        ),
    )
    successes = sorted(
        (u for u in rows if u.outcome is TrajectoryOutcome.SUCCESS),
        key=lambda u: (
            not u.regression_guard_priority,
            not u.success_inefficiency_flag,
            u.frozen_order,
            u.unit_id,
        ),
    )
    family_order = list(policy["frozen_family_order"])
    by_family: dict[str | None, list[AnalysisUnit]] = {}
    for unit in failures:
        by_family.setdefault(unit.task_family, []).append(unit)
    ordered_families = sorted(
        by_family, key=lambda x: _family_order_key(x, family_order)
    )

    selected_failure: list[AnalysisUnit] = []
    selected_ids: set[str] = set()

    # Approved rule: every failing family receives a floor before any success.
    floor_slots = min(total_analysis_budget, len(ordered_families))
    for family in ordered_families[:floor_slots]:
        unit = by_family[family][0]
        selected_failure.append(unit)
        selected_ids.add(unit.unit_id)

    failure_target = max(failure_target, len(selected_failure))
    failure_target = min(total_analysis_budget, failure_target)
    for unit in failures:
        if len(selected_failure) >= failure_target:
            break
        if unit.unit_id not in selected_ids:
            selected_failure.append(unit)
            selected_ids.add(unit.unit_id)

    remaining = total_analysis_budget - len(selected_failure)
    selected_success = successes[: min(success_target, remaining)]
    remaining -= len(selected_success)

    # Only after all eligible failures are selected can failure shortfall move to success.
    if remaining and len(selected_failure) == len(failures):
        extra = successes[len(selected_success):len(selected_success)+remaining]
        selected_success.extend(extra)
        remaining -= len(extra)

    eligible_by_family = {
        fam: len(items) for fam, items in by_family.items()
    }
    selected_by_family: dict[str | None, int] = {}
    for unit in selected_failure:
        selected_by_family[unit.task_family] = (
            selected_by_family.get(unit.task_family, 0) + 1
        )

    payload: dict[str, object] = {
        "schema_id": "ANALYZER_ANALYSIS_BUDGET_V2",
        "schema_version": 2,
        "scientific_role": "SECONDARY_COST_AND_COVERAGE_INFRASTRUCTURE",
        "scheduler_role": "MECHANICAL_SAMPLING_ONLY",
        "research_priority_authority": "NOT_AUTHORIZED",
        "formal_a0_a3_u_reg_unchanged": True,
        "regime": regime.value,
        "approval_sha256": policy["approval_sha256"],
        "census_sha256": census["census_sha256"],
        "total_analysis_budget": total_analysis_budget,
        "failure_share": share,
        "failure_quota": len(selected_failure),
        "success_quota": len(selected_success),
        "selected_failure_unit_ids": [u.unit_id for u in selected_failure],
        "selected_success_unit_ids": [u.unit_id for u in selected_success],
        "failure_family_rows": [
            {
                "task_family": fam,
                "eligible_failure_count": eligible_by_family[fam],
                "selected_failure_count": selected_by_family.get(fam, 0),
            }
            for fam in ordered_families
        ],
        "failure_shortfall_reallocated": max(0, len(selected_success)-success_target),
        "budget_sha256": "0"*64,
    }
    payload["budget_sha256"] = domain_hash(
        "ANALYZER_ANALYSIS_BUDGET_V2",
        payload,
        excluded_field="budget_sha256",
    )
    validate_sampling_allocation(
        payload, census=census, approval=policy
    )
    return payload


def validate_sampling_allocation(
    allocation: Mapping[str, object],
    *,
    census: Mapping[str, object],
    approval: Mapping[str, object],
) -> None:
    validate_payload_against_schema(
        schema_id="ANALYZER_ANALYSIS_BUDGET_V2",
        payload=allocation,
    )
    verify_domain_hash(
        payload=allocation,
        domain="ANALYZER_ANALYSIS_BUDGET_V2",
        hash_field="budget_sha256",
    )
    if allocation["approval_sha256"] != approval["approval_sha256"]:
        raise ValueError("allocation approval binding mismatch")
    if allocation["census_sha256"] != census["census_sha256"]:
        raise ValueError("allocation census binding mismatch")
    expected = EXACT_SHARES[str(allocation["regime"])]
    if allocation["failure_share"] != expected:
        raise ValueError("allocation failure share differs from approval")
    if allocation["failure_quota"] + allocation["success_quota"] > (
        allocation["total_analysis_budget"]
    ):
        raise ValueError("allocation exceeds total budget")

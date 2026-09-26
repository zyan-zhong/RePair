"""Evidence-bound deterministic scientific-outcome routing and census."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping

from pchsi.reference_loop.canonical import domain_hash

from .authorities import (
    AnalysisObjective,
    AnalysisTimeInformationBoundary,
    OutcomeRouteStatus,
    ScientificUse,
    TrajectoryOutcome,
)
from .schema_contract import validate_payload_against_schema, verify_domain_hash


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be object")
    return value


def _pack_incidents(pack: Mapping[str, object]) -> tuple[dict[str, bool], list[str], bool | None]:
    """Derive experiment incidents and terminal outcome from frozen pack evidence."""

    complete = True
    reasons: list[str] = []
    for key in (
        "task_identity", "trajectory_identity", "trajectory", "mechanical_evidence",
        "memory_support_port", "analyzer_output_authority",
    ):
        if key not in pack:
            complete = False
            reasons.append(f"MISSING_PACK_FIELD:{key}")

    mechanical = pack.get("mechanical_evidence")
    generic: Mapping[str, object] = {}
    if isinstance(mechanical, Mapping):
        maybe_generic = mechanical.get("generic_episode_facts")
        if isinstance(maybe_generic, Mapping):
            generic = maybe_generic
        else:
            complete = False
            reasons.append("MISSING_GENERIC_EPISODE_FACTS")
    else:
        complete = False
        reasons.append("MISSING_MECHANICAL_EVIDENCE")

    # Policy format failures are behavior evidence, not an experiment-protocol incident.
    protocol_invalid = bool(
        pack.get("experiment_protocol_valid") is False
        or generic.get("experiment_protocol_valid") is False
        or generic.get("protocol_integrity_status") == "INVALID"
    )
    if protocol_invalid:
        reasons.append("PROTOCOL_INVALID")

    infrastructure_unavailable = bool(
        generic.get("environment_error_count", 0)
        or generic.get("infrastructure_available") is False
        or generic.get("infrastructure_status") == "UNAVAILABLE"
    )
    if infrastructure_unavailable:
        reasons.append("INFRASTRUCTURE_UNAVAILABLE")

    terminal = generic.get("terminal_success")
    if terminal is not None and type(terminal) is not bool:
        complete = False
        reasons.append("TERMINAL_SUCCESS_NOT_BOOLEAN")
        terminal = None
    if terminal is None:
        complete = False
        reasons.append("MISSING_TERMINAL_SCIENTIFIC_OUTCOME")

    if not complete:
        reasons.append("EVIDENCE_INCOMPLETE")
    return (
        {
            "protocol_invalid": protocol_invalid,
            "evidence_incomplete": not complete,
            "infrastructure_unavailable": infrastructure_unavailable,
        },
        sorted(set(reasons)),
        terminal,
    )


def validate_route_semantics(route: Mapping[str, object]) -> None:
    validate_payload_against_schema(
        schema_id="ANALYZER_OUTCOME_ROUTE_V1", payload=route
    )
    verify_domain_hash(
        payload=route, domain="ANALYZER_OUTCOME_ROUTE_V1", hash_field="route_sha256"
    )
    status = OutcomeRouteStatus(str(route["route_status"]))
    eligible = route["semantic_lane_eligible"]
    outcome = route["trajectory_outcome"]
    objective = route["analysis_objective"]
    flags = _require_mapping(route["incident_flags"], "incident_flags")
    if status is OutcomeRouteStatus.SCIENTIFIC_OUTCOME_AVAILABLE:
        if eligible is not True or outcome not in {"SUCCESS", "FAILURE"}:
            raise ValueError("scientific route must contain one terminal outcome")
        expected = (
            "SUCCESS_QUALITY" if outcome == "SUCCESS" else "FAILURE_DIAGNOSIS"
        )
        if objective != expected or any(bool(v) for v in flags.values()):
            raise ValueError("scientific route cross-field semantics are invalid")
    else:
        if eligible is not False or outcome is not None or objective is not None:
            raise ValueError("non-scientific route cannot enter a semantic lane")
        primary_flag = {
            OutcomeRouteStatus.PROTOCOL_INVALID: "protocol_invalid",
            OutcomeRouteStatus.EVIDENCE_INCOMPLETE: "evidence_incomplete",
            OutcomeRouteStatus.INFRASTRUCTURE_UNAVAILABLE: "infrastructure_unavailable",
        }[status]
        if flags.get(primary_flag) is not True:
            raise ValueError("route status is not supported by its incident flag")


def route_episode(evidence_pack: Mapping[str, object]) -> dict[str, object]:
    """Route a validated evidence pack; callers cannot supply outcome booleans."""

    if evidence_pack.get("schema_id") != "ANALYZER_EVIDENCE_PACK_V1":
        raise ValueError("evidence pack schema mismatch")
    pack_sha = evidence_pack.get("evidence_pack_sha256")
    if not isinstance(pack_sha, str) or len(pack_sha) != 64:
        raise ValueError("evidence pack SHA is invalid")
    observed = domain_hash(
        "ANALYZER_EVIDENCE_PACK_V1",
        evidence_pack,
        excluded_field="evidence_pack_sha256",
    )
    if observed != pack_sha:
        raise ValueError("evidence pack SHA does not match pack bytes")

    task = _require_mapping(evidence_pack.get("task_identity"), "task_identity")
    task_id = task.get("task_id")
    gamefile = task.get("gamefile_sha256")
    if not isinstance(task_id, str) or not task_id:
        raise ValueError("task_id is invalid")
    if not isinstance(gamefile, str) or len(gamefile) != 64:
        raise ValueError("gamefile SHA is invalid")

    flags, reasons, terminal = _pack_incidents(evidence_pack)

    # Exact approved precedence: protocol -> incomplete -> infrastructure -> outcome.
    if flags["protocol_invalid"]:
        status = OutcomeRouteStatus.PROTOCOL_INVALID
    elif flags["evidence_incomplete"]:
        status = OutcomeRouteStatus.EVIDENCE_INCOMPLETE
    elif flags["infrastructure_unavailable"]:
        status = OutcomeRouteStatus.INFRASTRUCTURE_UNAVAILABLE
    else:
        status = OutcomeRouteStatus.SCIENTIFIC_OUTCOME_AVAILABLE

    outcome: str | None = None
    objective: str | None = None
    if status is OutcomeRouteStatus.SCIENTIFIC_OUTCOME_AVAILABLE:
        outcome = (
            TrajectoryOutcome.SUCCESS.value
            if terminal is True
            else TrajectoryOutcome.FAILURE.value
        )
        objective = (
            AnalysisObjective.SUCCESS_QUALITY.value
            if terminal is True
            else AnalysisObjective.FAILURE_DIAGNOSIS.value
        )

    payload: dict[str, object] = {
        "schema_id": "ANALYZER_OUTCOME_ROUTE_V1",
        "schema_version": 1,
        "evidence_pack_sha256": pack_sha,
        "task_id": task_id,
        "gamefile_sha256": gamefile,
        "task_family": task.get("task_type"),
        "scientific_use": ScientificUse.PRIVILEGED_OFFLINE_ANALYSIS.value,
        "analysis_time_information_boundary": (
            AnalysisTimeInformationBoundary.POST_EPISODE_DEV_ONLY.value
        ),
        "route_status": status.value,
        "semantic_lane_eligible": (
            status is OutcomeRouteStatus.SCIENTIFIC_OUTCOME_AVAILABLE
        ),
        "trajectory_outcome": outcome,
        "analysis_objective": objective,
        "incident_flags": flags,
        "reason_codes": reasons,
        "outcome_authority": "ENVIRONMENT_AND_PROTOCOL_EVIDENCE_ONLY",
        "route_sha256": "0" * 64,
    }
    payload["route_sha256"] = domain_hash(
        "ANALYZER_OUTCOME_ROUTE_V1", payload, excluded_field="route_sha256"
    )
    validate_route_semantics(payload)
    return payload


def build_mechanical_census(
    routes: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    rows = [dict(x) for x in routes]
    route_hashes: list[str] = []
    pack_ids: set[str] = set()
    status_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    incident_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    family = defaultdict(lambda: Counter())

    for route in rows:
        validate_route_semantics(route)
        pack_sha = str(route["evidence_pack_sha256"])
        if pack_sha in pack_ids:
            raise ValueError("duplicate registered evidence-pack unit")
        pack_ids.add(pack_sha)
        route_hashes.append(str(route["route_sha256"]))
        status = str(route["route_status"])
        status_counts[status] += 1
        fam = route["task_family"]
        family[fam]["registered_count"] += 1
        for key, flag in dict(route["incident_flags"]).items():
            if flag:
                incident_counts[key] += 1
        for reason in route["reason_codes"]:
            reason_counts[str(reason)] += 1
        if status == "SCIENTIFIC_OUTCOME_AVAILABLE":
            outcome = str(route["trajectory_outcome"])
            outcome_counts[outcome] += 1
            family[fam]["scientific_count"] += 1
            family[fam][f"{outcome.lower()}_count"] += 1
        else:
            family[fam][f"{status.lower()}_primary_count"] += 1

    family_rows = []
    for fam in sorted(family, key=lambda x: "" if x is None else str(x)):
        row = family[fam]
        family_rows.append({
            "task_family": fam,
            "registered_count": row["registered_count"],
            "scientific_count": row["scientific_count"],
            "success_count": row["success_count"],
            "failure_count": row["failure_count"],
            "protocol_invalid_primary_count": row["protocol_invalid_primary_count"],
            "evidence_incomplete_primary_count": row["evidence_incomplete_primary_count"],
            "infrastructure_unavailable_primary_count": (
                row["infrastructure_unavailable_primary_count"]
            ),
        })

    payload: dict[str, object] = {
        "schema_id": "ANALYZER_MECHANICAL_CENSUS_V1",
        "schema_version": 1,
        "registered_unit_count": len(rows),
        "scientific_outcome_count": status_counts["SCIENTIFIC_OUTCOME_AVAILABLE"],
        "registered_route_sha256s": route_hashes,
        "status_counts": {
            status.value: status_counts[status.value] for status in OutcomeRouteStatus
        },
        "outcome_counts": {
            outcome.value: outcome_counts[outcome.value] for outcome in TrajectoryOutcome
        },
        "incident_counts": {
            key: incident_counts[key]
            for key in (
                "protocol_invalid", "evidence_incomplete",
                "infrastructure_unavailable",
            )
        },
        "reason_census": [
            {"reason_code": key, "count": reason_counts[key]}
            for key in sorted(reason_counts)
        ],
        "task_family_rows": family_rows,
        "missingness_preserved": True,
        "census_sha256": "0" * 64,
    }
    payload["census_sha256"] = domain_hash(
        "ANALYZER_MECHANICAL_CENSUS_V1",
        payload,
        excluded_field="census_sha256",
    )
    validate_census_semantics(payload)
    return payload


def validate_census_semantics(census: Mapping[str, object]) -> None:
    validate_payload_against_schema(
        schema_id="ANALYZER_MECHANICAL_CENSUS_V1", payload=census
    )
    verify_domain_hash(
        payload=census,
        domain="ANALYZER_MECHANICAL_CENSUS_V1",
        hash_field="census_sha256",
    )
    registered = int(census["registered_unit_count"])
    scientific = int(census["scientific_outcome_count"])
    statuses = dict(census["status_counts"])
    outcomes = dict(census["outcome_counts"])
    hashes = list(census["registered_route_sha256s"])
    if len(hashes) != registered or len(set(hashes)) != registered:
        raise ValueError("census route identities are incomplete or duplicated")
    if sum(statuses.values()) != registered:
        raise ValueError("census status arithmetic mismatch")
    if sum(outcomes.values()) != scientific:
        raise ValueError("census outcome arithmetic mismatch")
    if statuses["SCIENTIFIC_OUTCOME_AVAILABLE"] != scientific:
        raise ValueError("census scientific count mismatch")

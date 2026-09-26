"""Strict A0/A1 local Analyzer validation with exact evidence resolution."""

from __future__ import annotations
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Protocol

from pchsi.reference_loop.canonical import domain_hash
from .authorities import (
    LOCAL_GENERATION_CONDITIONS, AnalysisObjective,
    AnalysisTimeInformationBoundary, AnalyzerCondition, ErrorLifecycleStatus,
    RepairKind, ScientificUse, TerminalFootprint, TrajectoryOutcome,
)
from .schema_contract import validate_payload_against_schema
from .outcome_router import route_episode

_FORBIDDEN = frozenset({
    "benefit","harm","neutral","environment_effect","training_label",
    "promotion_decision","policy_promotion",
})
_SUCCESS_VERIFY = frozenset({"redundancy_candidates","efficiency_candidates"})


class EvidenceReferenceResolver(Protocol):
    def resolve(self, reference: Mapping[str, object]) -> None: ...


@dataclass(frozen=True)
class EvidencePackReferenceResolver:
    pack_sha: str
    trajectory_indices: frozenset[int]
    mechanical_selectors: frozenset[str]
    counterexample_selectors: frozenset[str]

    @classmethod
    def from_pack(
        cls, pack: Mapping[str, object], *, counterexamples: Sequence[str]=()
    ) -> "EvidencePackReferenceResolver":
        sha = pack.get("evidence_pack_sha256")
        if not isinstance(sha, str) or len(sha) != 64:
            raise ValueError("evidence pack SHA invalid")
        indices: set[int] = set()
        for row in pack.get("trajectory", []):
            if not isinstance(row, Mapping):
                raise ValueError("trajectory row must be object")
            index = row.get("model_call_index")
            if type(index) is not int or index < 0 or index in indices:
                raise ValueError("trajectory indices must be unique")
            indices.add(index)
        selectors: set[str] = set()
        def walk(prefix: str, value: object) -> None:
            if isinstance(value, Mapping):
                for key, child in value.items():
                    walk(f"{prefix}.{key}" if prefix else str(key), child)
            elif isinstance(value, (list, tuple)):
                for i, child in enumerate(value):
                    walk(f"{prefix}[{i}]", child)
            else:
                selectors.add(f"mechanical:{prefix}")
        mechanical = pack.get("mechanical_evidence")
        if isinstance(mechanical, Mapping):
            walk("", mechanical)
        return cls(
            pack_sha=sha,
            trajectory_indices=frozenset(indices),
            mechanical_selectors=frozenset(selectors),
            counterexample_selectors=frozenset(counterexamples),
        )

    def resolve(self, ref: Mapping[str, object]) -> None:
        if ref.get("artifact_sha256") != self.pack_sha:
            raise ValueError("evidence reference artifact differs from pack")
        kind = ref.get("evidence_kind")
        selector = ref.get("local_selector")
        authority = ref.get("authority")
        if not isinstance(selector, str):
            raise ValueError("evidence selector must be text")
        if kind == "TRAJECTORY_CALL":
            match = re.fullmatch(r"trajectory:(\d+)", selector)
            if match is None or int(match.group(1)) not in self.trajectory_indices:
                raise ValueError("trajectory evidence reference does not exist")
            if authority != "DETERMINISTIC_FACT":
                raise ValueError("trajectory authority must be deterministic")
        elif kind == "MECHANICAL_FACT":
            if selector not in self.mechanical_selectors:
                raise ValueError("mechanical evidence reference does not exist")
            if authority != "DETERMINISTIC_FACT":
                raise ValueError("mechanical authority must be deterministic")
        elif kind == "COUNTEREXAMPLE":
            if selector not in self.counterexample_selectors:
                raise ValueError("counterexample reference does not exist")
            if authority not in {"DETERMINISTIC_FACT","SEMANTIC_HYPOTHESIS"}:
                raise ValueError("counterexample authority invalid")
        else:
            raise ValueError("unsupported evidence kind")


def _keys(value: object) -> set[str]:
    out: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            out.add(str(key).lower()); out |= _keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value: out |= _keys(child)
    return out


def _refs(refs: object, resolver: EvidenceReferenceResolver) -> None:
    if not isinstance(refs, list):
        raise ValueError("evidence refs must be array")
    for ref in refs:
        if not isinstance(ref, Mapping):
            raise ValueError("evidence ref must be object")
        resolver.resolve(ref)


def _trajectory(pack: Mapping[str, object]) -> dict[int, Mapping[str, object]]:
    rows: dict[int, Mapping[str, object]] = {}
    for row in pack.get("trajectory", []):
        if not isinstance(row, Mapping):
            raise ValueError("trajectory row invalid")
        index = row.get("model_call_index")
        if type(index) is not int or index in rows:
            raise ValueError("trajectory index invalid or duplicate")
        rows[index] = row
    return rows


def _hash_without(domain: str, payload: Mapping[str, object], fields: tuple[str,...]) -> str:
    body = dict(payload)
    for field in fields: body.pop(field, None)
    return domain_hash(domain, body)


def finalize_local_result(payload: Mapping[str, object]) -> dict[str, object]:
    value = deepcopy(dict(payload))
    value["validated_result_sha256"] = _hash_without(
        "ANALYZER_LOCAL_RESULT_VALIDATED_V2", value,
        ("validated_result_sha256","local_result_sha256"),
    )
    value["local_result_sha256"] = domain_hash(
        "ANALYZER_LOCAL_RESULT_V2", value, excluded_field="local_result_sha256"
    )
    return value


def validate_local_result(
    payload: Mapping[str, object],
    *,
    evidence_pack: Mapping[str, object],
    resolver: EvidenceReferenceResolver | None=None,
) -> dict[str, object]:
    value = deepcopy(dict(payload))
    validate_payload_against_schema(
        schema_id="ANALYZER_LOCAL_RESULT_V2", payload=value
    )
    if value["scientific_use"] != ScientificUse.PRIVILEGED_OFFLINE_ANALYSIS.value:
        raise ValueError("local result is not privileged offline")
    if value["analysis_time_information_boundary"] != (
        AnalysisTimeInformationBoundary.POST_EPISODE_DEV_ONLY.value
    ):
        raise ValueError("local result boundary is not POST_EPISODE_DEV_ONLY")
    if AnalyzerCondition(value["condition_id"]) not in LOCAL_GENERATION_CONDITIONS:
        raise ValueError("A2/A3 cannot generate local artifacts")
    forbidden = _keys(value) & _FORBIDDEN
    if forbidden:
        raise ValueError(f"forbidden Analyzer authority fields: {sorted(forbidden)}")
    if evidence_pack.get("schema_id") != "ANALYZER_EVIDENCE_PACK_V1":
        raise ValueError("evidence pack schema mismatch")
    pack_sha = evidence_pack.get("evidence_pack_sha256")
    observed = domain_hash(
        "ANALYZER_EVIDENCE_PACK_V1", evidence_pack,
        excluded_field="evidence_pack_sha256",
    )
    if pack_sha != observed:
        raise ValueError("evidence pack SHA mismatch")
    if value["evidence_pack_sha256"] != pack_sha:
        raise ValueError("local result bound to another evidence pack")
    task = evidence_pack.get("task_identity")
    if not isinstance(task, Mapping):
        raise ValueError("task identity invalid")
    if value["task_id"] != task.get("task_id") or (
        value["gamefile_sha256"] != task.get("gamefile_sha256")
    ):
        raise ValueError("local result task/gamefile mismatch")
    port = evidence_pack.get("memory_support_port")
    if not isinstance(port, Mapping) or (
        port.get("base_pack_exposes_memory") is not False
        or port.get("memory_packet") is not None
    ):
        raise ValueError("local pass must be Memory-blind")

    trajectory = _trajectory(evidence_pack)
    indices = set(trajectory)
    route = route_episode(evidence_pack)
    if route["route_status"] != "SCIENTIFIC_OUTCOME_AVAILABLE":
        raise ValueError("local result cannot bind a non-scientific route")
    if (
        value["trajectory_outcome"] != route["trajectory_outcome"]
        or value["analysis_objective"] != route["analysis_objective"]
    ):
        raise ValueError("local result outcome/lane differs from evidence-bound route")

    effective = resolver or EvidencePackReferenceResolver.from_pack(
        evidence_pack,
        counterexamples=tuple(
            str(x) for x in evidence_pack.get("counterexample_inventory", [])
            if isinstance(x, str)
        ),
    )
    outcome = TrajectoryOutcome(value["trajectory_outcome"])
    objective = AnalysisObjective(value["analysis_objective"])
    errors = value["error_instances"]
    success = value["success_analysis"]
    repairs = value["local_repairs"]
    if not isinstance(errors, list) or not isinstance(repairs, list):
        raise ValueError("local arrays invalid")

    error_ids: set[str] = set()
    hypothesis_ids: set[str] = set()
    alternatives: list[list[str]] = []
    if outcome is TrajectoryOutcome.FAILURE:
        if objective is not AnalysisObjective.FAILURE_DIAGNOSIS or success is not None:
            raise ValueError("failure lane mismatch")
        if not errors and value["abstained"] is not True:
            raise ValueError("non-abstained failure needs error instance")
        principals = 0
        for instance in errors:
            if not isinstance(instance, Mapping):
                raise ValueError("error instance invalid")
            eid = str(instance["error_instance_id"])
            if eid in error_ids: raise ValueError("duplicate error_instance_id")
            error_ids.add(eid)
            points = [
                instance["relevant_start_call_index"],
                instance["critical_window_start_call_index"],
                instance["trigger_call_index"],
                instance["critical_window_end_call_index"],
            ]
            if not all(type(x) is int and x in indices for x in points):
                raise ValueError("error window index absent")
            if not points[0] <= points[1] <= points[2] <= points[3]:
                raise ValueError("error window not ordered")
            ErrorLifecycleStatus(instance["resolution_status"])
            TerminalFootprint(instance["terminal_footprint"])
            _refs(instance["supporting_evidence_refs"], effective)
            _refs(instance["counterevidence_refs"], effective)
            hypotheses = instance["mechanism_hypotheses"]
            ranks = [x["rank"] for x in hypotheses]
            if ranks != list(range(1, len(ranks)+1)) or len(ranks) > 3:
                raise ValueError("hypothesis ranks invalid")
            for hypothesis in hypotheses:
                hid = str(hypothesis["hypothesis_id"])
                if hid in hypothesis_ids: raise ValueError("duplicate hypothesis_id")
                hypothesis_ids.add(hid)
                _refs(hypothesis["supporting_evidence_refs"], effective)
                _refs(hypothesis["counterevidence_refs"], effective)
                alternatives.append(list(hypothesis["alternative_explanation_ids"]))
            principals += int(instance["candidate_principal"])
        if principals > 1: raise ValueError("multiple candidate-principal errors")
        allowed_alt = error_ids | hypothesis_ids
        for refs in alternatives:
            if len(refs) != len(set(refs)) or set(refs) - allowed_alt:
                raise ValueError("alternative explanation contains dangling IDs")
    else:
        if objective is not AnalysisObjective.SUCCESS_QUALITY or errors:
            raise ValueError("success lane mismatch")
        if not isinstance(success, Mapping):
            raise ValueError("success lane requires success_analysis")
        event_ids: set[str] = set()
        for category, events in success.items():
            if not isinstance(events, list):
                raise ValueError("success categories must be arrays")
            for event in events:
                eid = str(event["event_id"])
                if eid in event_ids: raise ValueError("duplicate success event_id")
                event_ids.add(eid)
                start, end = event["start_call_index"], event["end_call_index"]
                if type(start) is not int or type(end) is not int or (
                    start > end or start not in indices or end not in indices
                ):
                    raise ValueError("success event window invalid")
                _refs(event["supporting_evidence_refs"], effective)
                if category in _SUCCESS_VERIFY and (
                    event["requires_environment_verification"] is not True
                ):
                    raise ValueError("success optimization remains candidate-only")

    if value["abstained"] is True:
        if value["abstain_reason"] is None or repairs:
            raise ValueError("abstention must have reason and no repair")
    elif value["abstain_reason"] is not None:
        raise ValueError("non-abstained result cannot contain abstain reason")

    repair_ids: set[str] = set()
    ranks = [x["rank"] for x in repairs]
    if ranks != list(range(1, len(ranks)+1)):
        raise ValueError("repair ranks invalid")
    for repair in repairs:
        rid = str(repair["local_repair_id"])
        if rid in repair_ids: raise ValueError("duplicate local_repair_id")
        repair_ids.add(rid)
        if repair["requires_environment_verification"] is not True:
            raise ValueError("repair requires environment verification")
        decision = repair["decision_call_index"]
        if decision not in indices: raise ValueError("repair call index absent")
        _refs(repair["supporting_evidence_refs"], effective)
        supporting = repair["supporting_hypothesis_ids"]
        if (
            not supporting or len(supporting) != len(set(supporting))
            or set(supporting) - hypothesis_ids
        ):
            raise ValueError("repair supporting hypothesis IDs invalid")
        kind = RepairKind(repair["repair_kind"])
        exact, option = repair["exact_action"], repair["option_actions"]
        termination, rule = repair["termination_condition"], repair["trainable_rule"]
        menu = trajectory[decision].get("admissible_commands")
        if kind is RepairKind.EXACT_ACTION:
            if not isinstance(exact, str) or not isinstance(menu, list) or exact not in menu:
                raise ValueError("exact repair action absent from source menu")
            if option or termination is not None or rule is not None:
                raise ValueError("EXACT_ACTION incompatible fields")
        elif kind is RepairKind.SHORT_OPTION:
            if (
                not isinstance(option, list) or not 1 <= len(option) <= 4
                or not isinstance(menu, list) or option[0] not in menu
                or not isinstance(termination, str) or not termination
            ):
                raise ValueError("SHORT_OPTION invalid or unbound")
            if exact is not None or rule is not None:
                raise ValueError("SHORT_OPTION incompatible fields")
        elif kind is RepairKind.TRAINABLE_RULE:
            if not isinstance(rule, str) or not rule:
                raise ValueError("TRAINABLE_RULE missing rule")
            if exact is not None or option or termination is not None:
                raise ValueError("TRAINABLE_RULE incompatible fields")

    expected_validated = _hash_without(
        "ANALYZER_LOCAL_RESULT_VALIDATED_V2", value,
        ("validated_result_sha256","local_result_sha256"),
    )
    if value["validated_result_sha256"] != expected_validated:
        raise ValueError("validated result SHA mismatch")
    expected_local = domain_hash(
        "ANALYZER_LOCAL_RESULT_V2", value, excluded_field="local_result_sha256"
    )
    if value["local_result_sha256"] != expected_local:
        raise ValueError("local result SHA mismatch")
    return value

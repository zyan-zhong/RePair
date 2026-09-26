"""Research Planner repair-discovery and high-value repair-program contracts.

This module does not execute environment actions and does not assign causal
outcomes.  It records what the Research Planner selected for verification,
while preserving Analyzer/Memory/source-state lineage for the deterministic
projector and the independent environment verifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


class RepairCandidateOriginV1(str, Enum):
    ANALYZER = "ANALYZER"
    FAILURE_EXPERIENCE = "FAILURE_EXPERIENCE"
    RESEARCHER_COMPOSED = "RESEARCHER_COMPOSED"
    RESEARCHER_REQUESTED_ANALYSIS = "RESEARCHER_REQUESTED_ANALYSIS"


class RepairDispositionV1(str, Enum):
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class PortfolioDecisionV1(str, Enum):
    SELECT_ONE_PROGRAM = "SELECT_ONE_PROGRAM"
    ABSTAIN = "ABSTAIN"


class RepairProgramKindV1(str, Enum):
    DIRECT_SOURCE_REPAIR = "DIRECT_SOURCE_REPAIR"
    ABSTRACTED_REPAIR_TEMPLATE = "ABSTRACTED_REPAIR_TEMPLATE"
    COMPOSED_REPAIR_PROGRAM = "COMPOSED_REPAIR_PROGRAM"
    REQUEST_FOR_ADDITIONAL_ANALYSIS = "REQUEST_FOR_ADDITIONAL_ANALYSIS"


_ALLOWED_RESEARCHER_MODES = {
    "HUMAN_REFERENCE",
    "STRONG_API_SHADOW",
    "STRONG_API_PRIMARY",
    "LOCAL_SHADOW",
    "LOCAL_PRIMARY",
}


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_sha256(value: str, name: str) -> None:
    _require_text(value, name)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")


def _require_probability(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")


def _unique_nonempty(values: Iterable[str], name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    materialized = tuple(values)
    if not allow_empty and not materialized:
        raise ValueError(f"{name} must be non-empty")
    for value in materialized:
        _require_text(value, name)
    if len(set(materialized)) != len(materialized):
        raise ValueError(f"{name} contains duplicates")
    return materialized


@dataclass(frozen=True)
class RepairLineageV1:
    source_state_ids: tuple[str, ...]
    source_candidate_ids: tuple[str, ...]
    source_group_ids: tuple[str, ...]
    analyzer_artifact_sha256s: tuple[str, ...]
    memory_record_ids: tuple[str, ...]
    current_evidence_sha256s: tuple[str, ...]

    def validate(self) -> None:
        _unique_nonempty(self.source_state_ids, "source_state_ids")
        _unique_nonempty(
            self.source_candidate_ids,
            "source_candidate_ids",
            allow_empty=True,
        )
        _unique_nonempty(self.source_group_ids, "source_group_ids", allow_empty=True)
        _unique_nonempty(
            self.memory_record_ids,
            "memory_record_ids",
            allow_empty=True,
        )
        _unique_nonempty(
            self.analyzer_artifact_sha256s,
            "analyzer_artifact_sha256s",
            allow_empty=True,
        )
        for digest in self.analyzer_artifact_sha256s:
            _require_sha256(digest, "analyzer_artifact_sha256s")
        _unique_nonempty(
            self.current_evidence_sha256s,
            "current_evidence_sha256s",
        )
        for digest in self.current_evidence_sha256s:
            _require_sha256(digest, "current_evidence_sha256s")

        supporting_refs = (
            len(self.source_candidate_ids)
            + len(self.source_group_ids)
            + len(self.analyzer_artifact_sha256s)
            + len(self.memory_record_ids)
        )
        if supporting_refs == 0:
            raise ValueError(
                "repair lineage requires Analyzer, group, candidate, or Memory support"
            )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "source_state_ids": list(self.source_state_ids),
            "source_candidate_ids": list(self.source_candidate_ids),
            "source_group_ids": list(self.source_group_ids),
            "analyzer_artifact_sha256s": list(self.analyzer_artifact_sha256s),
            "memory_record_ids": list(self.memory_record_ids),
            "current_evidence_sha256s": list(self.current_evidence_sha256s),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RepairLineageV1":
        allowed = {
            "source_state_ids",
            "source_candidate_ids",
            "source_group_ids",
            "analyzer_artifact_sha256s",
            "memory_record_ids",
            "current_evidence_sha256s",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"unknown RepairLineageV1 fields: {sorted(unknown)}")
        return cls(
            source_state_ids=tuple(payload.get("source_state_ids", ())),
            source_candidate_ids=tuple(payload.get("source_candidate_ids", ())),
            source_group_ids=tuple(payload.get("source_group_ids", ())),
            analyzer_artifact_sha256s=tuple(
                payload.get("analyzer_artifact_sha256s", ())
            ),
            memory_record_ids=tuple(payload.get("memory_record_ids", ())),
            current_evidence_sha256s=tuple(
                payload.get("current_evidence_sha256s", ())
            ),
        )


@dataclass(frozen=True)
class ResearchRepairCandidateV1:
    candidate_id: str
    principal_change_id: str
    origin: RepairCandidateOriginV1
    repair_description: str
    repair_contract: str
    mechanism_target: str
    task_family_scope: tuple[str, ...]
    estimated_value: float
    estimated_harm_risk: float
    estimated_verification_calls: int
    evidence_support: float
    novelty_or_nonduplication_reason: str
    disposition: RepairDispositionV1
    disposition_reason: str
    lineage: RepairLineageV1

    def validate(self) -> None:
        for name in (
            "candidate_id",
            "principal_change_id",
            "repair_description",
            "repair_contract",
            "mechanism_target",
            "novelty_or_nonduplication_reason",
            "disposition_reason",
        ):
            _require_text(getattr(self, name), name)
        _unique_nonempty(self.task_family_scope, "task_family_scope")
        _require_probability(self.estimated_value, "estimated_value")
        _require_probability(self.estimated_harm_risk, "estimated_harm_risk")
        _require_probability(self.evidence_support, "evidence_support")
        if not isinstance(self.estimated_verification_calls, int) or self.estimated_verification_calls < 0:
            raise ValueError("estimated_verification_calls must be a non-negative integer")
        self.lineage.validate()
        if self.origin is RepairCandidateOriginV1.RESEARCHER_COMPOSED:
            source_count = (
                len(self.lineage.source_candidate_ids)
                + len(self.lineage.source_group_ids)
                + len(self.lineage.memory_record_ids)
            )
            if source_count < 2:
                raise ValueError(
                    "RESEARCHER_COMPOSED candidate requires at least two explicit source references"
                )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "candidate_id": self.candidate_id,
            "principal_change_id": self.principal_change_id,
            "origin": self.origin.value,
            "repair_description": self.repair_description,
            "repair_contract": self.repair_contract,
            "mechanism_target": self.mechanism_target,
            "task_family_scope": list(self.task_family_scope),
            "estimated_value": float(self.estimated_value),
            "estimated_harm_risk": float(self.estimated_harm_risk),
            "estimated_verification_calls": self.estimated_verification_calls,
            "evidence_support": float(self.evidence_support),
            "novelty_or_nonduplication_reason": self.novelty_or_nonduplication_reason,
            "disposition": self.disposition.value,
            "disposition_reason": self.disposition_reason,
            "lineage": self.lineage.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchRepairCandidateV1":
        allowed = {
            "candidate_id",
            "principal_change_id",
            "origin",
            "repair_description",
            "repair_contract",
            "mechanism_target",
            "task_family_scope",
            "estimated_value",
            "estimated_harm_risk",
            "estimated_verification_calls",
            "evidence_support",
            "novelty_or_nonduplication_reason",
            "disposition",
            "disposition_reason",
            "lineage",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(
                f"unknown ResearchRepairCandidateV1 fields: {sorted(unknown)}"
            )
        return cls(
            candidate_id=str(payload["candidate_id"]),
            principal_change_id=str(payload["principal_change_id"]),
            origin=RepairCandidateOriginV1(str(payload["origin"])),
            repair_description=str(payload["repair_description"]),
            repair_contract=str(payload["repair_contract"]),
            mechanism_target=str(payload["mechanism_target"]),
            task_family_scope=tuple(payload["task_family_scope"]),
            estimated_value=float(payload["estimated_value"]),
            estimated_harm_risk=float(payload["estimated_harm_risk"]),
            estimated_verification_calls=int(payload["estimated_verification_calls"]),
            evidence_support=float(payload["evidence_support"]),
            novelty_or_nonduplication_reason=str(
                payload["novelty_or_nonduplication_reason"]
            ),
            disposition=RepairDispositionV1(str(payload["disposition"])),
            disposition_reason=str(payload["disposition_reason"]),
            lineage=RepairLineageV1.from_dict(payload["lineage"]),
        )


@dataclass(frozen=True)
class ResearchRepairProgramV1:
    program_id: str
    principal_change_id: str
    kind: RepairProgramKindV1
    candidate_ids: tuple[str, ...]
    source_state_ids: tuple[str, ...]
    falsifiable_hypothesis: str
    high_value_rationale: str
    generalization_scope: str
    deterministic_projector_contract: str
    verification_protocol_id: str
    estimated_verification_calls: int

    def validate(self) -> None:
        for name in (
            "program_id",
            "principal_change_id",
            "falsifiable_hypothesis",
            "high_value_rationale",
            "generalization_scope",
            "deterministic_projector_contract",
            "verification_protocol_id",
        ):
            _require_text(getattr(self, name), name)
        _unique_nonempty(self.candidate_ids, "candidate_ids")
        _unique_nonempty(self.source_state_ids, "source_state_ids")
        if self.estimated_verification_calls <= 0:
            raise ValueError("program estimated_verification_calls must be positive")
        if self.kind is RepairProgramKindV1.COMPOSED_REPAIR_PROGRAM and len(self.candidate_ids) < 2:
            raise ValueError("COMPOSED_REPAIR_PROGRAM requires at least two candidates")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "program_id": self.program_id,
            "principal_change_id": self.principal_change_id,
            "kind": self.kind.value,
            "candidate_ids": list(self.candidate_ids),
            "source_state_ids": list(self.source_state_ids),
            "falsifiable_hypothesis": self.falsifiable_hypothesis,
            "high_value_rationale": self.high_value_rationale,
            "generalization_scope": self.generalization_scope,
            "deterministic_projector_contract": self.deterministic_projector_contract,
            "verification_protocol_id": self.verification_protocol_id,
            "estimated_verification_calls": self.estimated_verification_calls,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchRepairProgramV1":
        allowed = {
            "program_id",
            "principal_change_id",
            "kind",
            "candidate_ids",
            "source_state_ids",
            "falsifiable_hypothesis",
            "high_value_rationale",
            "generalization_scope",
            "deterministic_projector_contract",
            "verification_protocol_id",
            "estimated_verification_calls",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(
                f"unknown ResearchRepairProgramV1 fields: {sorted(unknown)}"
            )
        return cls(
            program_id=str(payload["program_id"]),
            principal_change_id=str(payload["principal_change_id"]),
            kind=RepairProgramKindV1(str(payload["kind"])),
            candidate_ids=tuple(payload["candidate_ids"]),
            source_state_ids=tuple(payload["source_state_ids"]),
            falsifiable_hypothesis=str(payload["falsifiable_hypothesis"]),
            high_value_rationale=str(payload["high_value_rationale"]),
            generalization_scope=str(payload["generalization_scope"]),
            deterministic_projector_contract=str(
                payload["deterministic_projector_contract"]
            ),
            verification_protocol_id=str(payload["verification_protocol_id"]),
            estimated_verification_calls=int(payload["estimated_verification_calls"]),
        )


@dataclass(frozen=True)
class ResearchRepairPortfolioV1:
    schema_version: str
    round_id: str
    parent_policy_id: str
    evidence_cutoff_sha256: str
    principal_change_id: str
    researcher_mode: str
    decision: PortfolioDecisionV1
    verification_call_budget: int
    candidates: tuple[ResearchRepairCandidateV1, ...]
    programs: tuple[ResearchRepairProgramV1, ...]
    selected_program_id: str | None
    abstention_reason: str | None

    def validate(self) -> None:
        if self.schema_version != "RESEARCH_REPAIR_PORTFOLIO_V1":
            raise ValueError("unexpected repair portfolio schema_version")
        for name in ("round_id", "parent_policy_id", "principal_change_id"):
            _require_text(getattr(self, name), name)
        _require_sha256(self.evidence_cutoff_sha256, "evidence_cutoff_sha256")
        if self.researcher_mode not in _ALLOWED_RESEARCHER_MODES:
            raise ValueError(f"unsupported researcher_mode: {self.researcher_mode}")
        if self.verification_call_budget < 0:
            raise ValueError("verification_call_budget must be non-negative")

        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("duplicate candidate_id")
        program_ids = [program.program_id for program in self.programs]
        if len(program_ids) != len(set(program_ids)):
            raise ValueError("duplicate program_id")

        candidate_map = {candidate.candidate_id: candidate for candidate in self.candidates}
        for candidate in self.candidates:
            candidate.validate()
            if candidate.principal_change_id != self.principal_change_id:
                raise ValueError("candidate violates single principal change")
        for program in self.programs:
            program.validate()
            if program.principal_change_id != self.principal_change_id:
                raise ValueError("program violates single principal change")
            missing = set(program.candidate_ids) - set(candidate_map)
            if missing:
                raise ValueError(f"program references unknown candidates: {sorted(missing)}")
            for candidate_id in program.candidate_ids:
                candidate = candidate_map[candidate_id]
                if candidate.disposition is not RepairDispositionV1.SELECTED:
                    raise ValueError(
                        "selected program may only contain SELECTED candidates"
                    )

        if self.decision is PortfolioDecisionV1.SELECT_ONE_PROGRAM:
            if self.selected_program_id is None:
                raise ValueError("selected_program_id is required")
            if self.abstention_reason is not None:
                raise ValueError("abstention_reason must be absent when selecting")
            selected = [
                program
                for program in self.programs
                if program.program_id == self.selected_program_id
            ]
            if len(selected) != 1:
                raise ValueError("selected_program_id must identify exactly one program")
            if selected[0].estimated_verification_calls > self.verification_call_budget:
                raise ValueError("selected repair program exceeds verification budget")
        else:
            if self.selected_program_id is not None:
                raise ValueError("ABSTAIN portfolio cannot select a program")
            _require_text(self.abstention_reason or "", "abstention_reason")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "round_id": self.round_id,
            "parent_policy_id": self.parent_policy_id,
            "evidence_cutoff_sha256": self.evidence_cutoff_sha256,
            "principal_change_id": self.principal_change_id,
            "researcher_mode": self.researcher_mode,
            "decision": self.decision.value,
            "verification_call_budget": self.verification_call_budget,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "programs": [program.to_dict() for program in self.programs],
            "selected_program_id": self.selected_program_id,
            "abstention_reason": self.abstention_reason,
            "authority_boundary": {
                "may_discover_or_compose_repair_programs": True,
                "may_execute_environment_action": False,
                "may_assign_benefit_harm_neutral_uncertain": False,
                "causal_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchRepairPortfolioV1":
        allowed = {
            "schema_version",
            "round_id",
            "parent_policy_id",
            "evidence_cutoff_sha256",
            "principal_change_id",
            "researcher_mode",
            "decision",
            "verification_call_budget",
            "candidates",
            "programs",
            "selected_program_id",
            "abstention_reason",
            "authority_boundary",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(
                f"unknown ResearchRepairPortfolioV1 fields: {sorted(unknown)}"
            )
        authority = payload.get("authority_boundary")
        if authority is not None:
            expected = {
                "may_discover_or_compose_repair_programs": True,
                "may_execute_environment_action": False,
                "may_assign_benefit_harm_neutral_uncertain": False,
                "causal_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
            }
            if authority != expected:
                raise ValueError("repair portfolio authority boundary was altered")
        return cls(
            schema_version=str(payload["schema_version"]),
            round_id=str(payload["round_id"]),
            parent_policy_id=str(payload["parent_policy_id"]),
            evidence_cutoff_sha256=str(payload["evidence_cutoff_sha256"]),
            principal_change_id=str(payload["principal_change_id"]),
            researcher_mode=str(payload["researcher_mode"]),
            decision=PortfolioDecisionV1(str(payload["decision"])),
            verification_call_budget=int(payload["verification_call_budget"]),
            candidates=tuple(
                ResearchRepairCandidateV1.from_dict(item)
                for item in payload.get("candidates", ())
            ),
            programs=tuple(
                ResearchRepairProgramV1.from_dict(item)
                for item in payload.get("programs", ())
            ),
            selected_program_id=(
                None
                if payload.get("selected_program_id") is None
                else str(payload["selected_program_id"])
            ),
            abstention_reason=(
                None
                if payload.get("abstention_reason") is None
                else str(payload["abstention_reason"])
            ),
        )


def freeze_repair_portfolio(
    portfolio: ResearchRepairPortfolioV1,
    output_dir: str | Path,
) -> tuple[Path, Path]:
    portfolio.validate()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / "RESEARCH_REPAIR_PORTFOLIO_V1.json"
    sidecar_path = output / "RESEARCH_REPAIR_PORTFOLIO_V1.json.sha256"
    if result_path.exists() or sidecar_path.exists():
        raise FileExistsError("repair portfolio output already exists")
    data = _canonical_json_bytes(portfolio.to_dict())
    digest = hashlib.sha256(data).hexdigest()
    result_path.write_bytes(data)
    sidecar_path.write_text(f"{digest}  {result_path.name}\n", encoding="utf-8")
    return result_path, sidecar_path


def load_repair_portfolio(path: str | Path) -> ResearchRepairPortfolioV1:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    portfolio = ResearchRepairPortfolioV1.from_dict(payload)
    portfolio.validate()
    return portfolio
